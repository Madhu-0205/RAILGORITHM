"""Human decision workflow.

The human decision is stored separately from the AI recommendation. Approvals
and modifications are re-validated on the server, require explicit
confirmation, and are applied only to the synthetic simulation. No railway
signal, point, route or real train is ever controlled by this application.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..config import settings
from ..domain.conflicts import detect_conflicts
from ..domain.state import advance, apply_action, format_minutes, state_metrics
from ..domain.validator import (
    INCOMPLETE_DATA,
    INVALID,
    evaluate_candidate,
    validate_action,
)
from ..models import Decision, Recommendation, Simulation, User
from .audit import append_audit
from .recommendation_service import generate_record, serialize, serialize_decision
from .simulation_service import ServiceError, _save

DECISION_ACTIONS = {"APPROVE", "REJECT", "MODIFY", "REQUEST_ALTERNATIVES", "DEFER"}


def _authorize_scope(user: User, affected: list[str]) -> None:
    if user.role == "SECTION_MASTER":
        return
    if user.role == "STATION_MASTER":
        if not user.station_id:
            raise ServiceError("Station Master has no assigned station scope.", 403)
        if affected and not set(affected).issubset({user.station_id}):
            raise ServiceError(
                "This recommendation affects stations outside your station scope. "
                "Only the Section Master can decide it.",
                403,
            )
        return
    raise ServiceError("Role is not authorized to make operational decisions.", 403)


def _apply_and_advance(
    db: Session,
    simulation: Simulation,
    *,
    action: dict,
    minutes: int,
) -> dict:
    before_state = simulation.state
    before_metrics = state_metrics(before_state)
    state = copy.deepcopy(before_state)
    apply_action(state, action)
    advance(state, minutes)
    _save(db, simulation, state)
    conflicts_after = [
        conflict
        for conflict in detect_conflicts(state, 45)
        if conflict["type"] != "DELAY_RISK"
    ]
    return {
        "execution_mode": "SIMULATED_ONLY",
        "human_confirmed": True,
        "applied_action": action,
        "horizon_minutes": minutes,
        "simulation_time": format_minutes(state["sim_time_min"]),
        "state_version": state["version"],
        "metrics_before": before_metrics,
        "metrics_after": state_metrics(state),
        "conflicts_after": conflicts_after,
        "simulation_status": state["status"],
    }


def submit_decision(
    db: Session,
    *,
    recommendation: Recommendation,
    simulation: Simulation,
    user: User,
    action: str,
    rationale: str,
    modifications: dict | None,
    confirm_apply: bool,
) -> dict:
    action = action.upper()
    if action not in DECISION_ACTIONS:
        raise ServiceError(f"Unsupported decision action '{action}'")
    rationale = (rationale or "").strip()
    if len(rationale) < 5:
        raise ServiceError("A decision rationale of at least 5 characters is required.")

    existing = db.execute(
        select(Decision).where(Decision.recommendation_id == recommendation.id)
    ).scalar_one_or_none()
    if existing:
        raise ServiceError(
            "A human decision already exists for this recommendation. "
            "Duplicate decisions are not permitted.",
            409,
        )

    affected = recommendation.payload.get("affected_stations", [])
    _authorize_scope(user, affected)

    stale = int(simulation.state_version) != int(recommendation.state_version)
    if stale and action in {"APPROVE", "MODIFY"}:
        if recommendation.status == "PENDING":
            recommendation.status = "STALE"
            db.add(recommendation)
            append_audit(
                db,
                event_type="RECOMMENDATION_STALE",
                actor=user.username,
                actor_role=user.role,
                simulation_id=simulation.id,
                recommendation_id=recommendation.id,
                payload={
                    "recommendation_state_version": recommendation.state_version,
                    "current_state_version": simulation.state_version,
                    "attempted_action": action,
                },
            )
            db.commit()
        raise ServiceError(
            "Recommendation is stale: the simulation state has changed since it was "
            "generated. Request alternatives and review the new evidence.",
            409,
        )
    if recommendation.status not in {"PENDING", "STALE"}:
        raise ServiceError(
            f"Recommendation is already {recommendation.status}; no further decision is allowed.",
            409,
        )
    if action in {"APPROVE", "MODIFY"} and simulation.status != "RUNNING":
        raise ServiceError(
            f"Simulation status is {simulation.status}. Resume it before approving or modifying.",
            409,
        )
    if action in {"APPROVE", "MODIFY"} and not confirm_apply:
        raise ServiceError(
            "Explicit confirmation is required before applying a decision to the simulation.",
            400,
        )

    recommended = recommendation.payload.get("recommended")
    applied_action = None
    validation = None
    simulation_result = None

    if action == "APPROVE":
        if not recommended:
            raise ServiceError(
                "There is no feasible recommendation to approve. The system will not "
                "fabricate an executable action.",
                409,
            )
        applied_action = recommended["action"]
        validation = validate_action(simulation.state, applied_action)
        if validation["status"] in {INVALID, INCOMPLETE_DATA}:
            raise ServiceError(
                "The recommendation no longer passes independent validation: "
                + "; ".join(
                    violation.get("detail", "")
                    for violation in validation.get("violations", [])[:3]
                ),
                422,
            )
        outcome = evaluate_candidate(
            simulation.state,
            applied_action,
            minutes=settings.decision_apply_minutes,
            conflict_horizon_min=settings.recommendation_horizon_min,
        )
        if outcome["status"] in {INVALID, INCOMPLETE_DATA}:
            raise ServiceError(
                "The simulated outcome fails independent validation; the decision was not applied.",
                422,
            )
        critical = [
            conflict
            for conflict in outcome.get("post_conflicts", [])
            if conflict["severity"] == "CRITICAL" and conflict["type"] != "DELAY_RISK"
        ]
        if critical:
            raise ServiceError(
                "The simulated outcome leaves a critical unresolved conflict; the decision was not applied.",
                422,
            )
        simulation_result = _apply_and_advance(
            db,
            simulation,
            action=applied_action,
            minutes=settings.decision_apply_minutes,
        )
        recommendation.status = "APPROVED"
    elif action == "MODIFY":
        modified_action = (modifications or {}).get("action")
        if not isinstance(modified_action, dict):
            raise ServiceError(
                "Modify requires modifications.action containing a supported operational action.",
                400,
            )
        applied_action = modified_action
        validation = validate_action(simulation.state, applied_action)
        if validation["status"] in {INVALID, INCOMPLETE_DATA}:
            raise ServiceError(
                "The modified action fails independent validation: "
                + "; ".join(
                    violation.get("detail", "")
                    for violation in validation.get("violations", [])[:3]
                ),
                422,
            )
        outcome = evaluate_candidate(
            simulation.state,
            applied_action,
            minutes=settings.decision_apply_minutes,
            conflict_horizon_min=settings.recommendation_horizon_min,
        )
        if outcome["status"] in {INVALID, INCOMPLETE_DATA}:
            raise ServiceError(
                "The modified action's simulated outcome fails validation; the decision was not applied.",
                422,
            )
        critical = [
            conflict
            for conflict in outcome.get("post_conflicts", [])
            if conflict["severity"] == "CRITICAL" and conflict["type"] != "DELAY_RISK"
        ]
        if critical:
            raise ServiceError(
                "The modified action leaves a critical unresolved conflict; the decision was not applied.",
                422,
            )
        simulation_result = _apply_and_advance(
            db,
            simulation,
            action=applied_action,
            minutes=settings.decision_apply_minutes,
        )
        recommendation.status = "MODIFIED"
    elif action == "REJECT":
        recommendation.status = "REJECTED"
        validation = {
            "status": "HUMAN_REJECTED",
            "note": "The AI recommendation was rejected; no simulation action was applied.",
        }
    elif action == "DEFER":
        recommendation.status = "DEFERRED"
        validation = {
            "status": "HUMAN_DEFERRED",
            "note": "Decision deferred; no simulation action was applied.",
        }
    elif action == "REQUEST_ALTERNATIVES":
        recommendation.status = "ALTERNATIVES_REQUESTED"
        validation = {
            "status": "ALTERNATIVES_REQUESTED",
            "note": "The controller requested fresh alternatives; no simulation action was applied.",
        }

    decision = Decision(
        recommendation_id=recommendation.id,
        simulation_id=simulation.id,
        action=action,
        rationale=rationale,
        modifications=modifications,
        decided_by=user.username,
        decided_role=user.role,
        decided_at=datetime.now(timezone.utc),
        applied=action in {"APPROVE", "MODIFY"},
        simulation_result=simulation_result,
        original_recommendation=recommendation.payload,
        validation=validation or {},
        model_version=recommendation.model_version,
        optimizer_version=recommendation.optimizer_version,
    )
    db.add(decision)
    db.add(recommendation)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ServiceError("A human decision already exists for this recommendation.", 409) from exc

    append_audit(
        db,
        event_type="HUMAN_DECISION_RECORDED",
        actor=user.username,
        actor_role=user.role,
        simulation_id=simulation.id,
        recommendation_id=recommendation.id,
        payload={
            "decision_action": action,
            "rationale": rationale,
            "modifications": modifications,
            "applied": decision.applied,
            "execution_mode": "SIMULATED_ONLY" if decision.applied else "NOT_APPLIED",
            "validation_status": (validation or {}).get("status"),
            "simulation_result": {
                key: value
                for key, value in (simulation_result or {}).items()
                if key in {"simulation_time", "state_version", "horizon_minutes", "metrics_after"}
            },
            "recommendation_state_version": recommendation.state_version,
            "model_version": recommendation.model_version,
            "optimizer_version": recommendation.optimizer_version,
        },
    )
    db.commit()
    db.refresh(decision)
    db.refresh(recommendation)
    db.refresh(simulation)

    new_recommendation = None
    if action == "REQUEST_ALTERNATIVES":
        new_recommendation = generate_record(
            db,
            simulation,
            actor=user,
            parent_recommendation_id=recommendation.id,
        )

    return {
        "decision": serialize_decision(decision),
        "recommendation": serialize(db, recommendation, simulation),
        "new_recommendation": (
            serialize(db, new_recommendation, simulation) if new_recommendation else None
        ),
        "simulation_state_version": simulation.state_version,
        "note": (
            "Decision recorded. Only an explicitly confirmed approval or modification "
            "is applied to the synthetic simulation."
            if decision.applied
            else "Decision recorded without applying any operational action."
        ),
    }
