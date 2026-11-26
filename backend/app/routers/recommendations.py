"""Recommendation review and human decision endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Decision, Simulation, User
from ..schemas import DecisionRequest
from ..services.decision_service import (
    evaluate_decision_outcome,
    evaluate_offline_model_candidates,
    export_decision_dataset,
    get_decision_review_analytics,
    submit_decision,
)
from ..services.recommendation_service import (
    get_record,
    serialize,
)
from ..services.simulation_service import ServiceError

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


@router.get("/review/analytics")
def review_analytics(
    simulation_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return get_decision_review_analytics(db, simulation_id=simulation_id)


@router.get("/review/dataset")
def review_dataset(
    simulation_id: str | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    return export_decision_dataset(db, simulation_id=simulation_id)


@router.get("/{recommendation_id}")
def get_recommendation(
    recommendation_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    record = get_record(db, recommendation_id)
    simulation = db.get(Simulation, record.simulation_id)
    if not simulation:
        raise ServiceError("Simulation for this recommendation no longer exists.", 404)
    affected = record.payload.get("affected_stations", [])
    if user.is_station_master():
        user_stations = set(user.get_stations())
        if affected and not (set(affected) & user_stations):
            raise ServiceError(
                f"This recommendation is outside your station scope. Affected: {affected}, Authorized: {list(user_stations)}",
                403,
            )
    elif user.is_section_controller() and user.control_area not in {None, "CORRIDOR"}:
        user_stations = set(user.get_stations())
        if affected and not (set(affected) & user_stations):
            raise ServiceError(
                f"This recommendation is outside your assigned control territory ({user.control_area}). Affected stations: {affected}.",
                403,
            )
    return serialize(db, record, simulation)


@router.post("/{recommendation_id}/decision")
def decide(
    recommendation_id: str,
    payload: DecisionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    record = get_record(db, recommendation_id)
    simulation = db.get(Simulation, record.simulation_id)
    if not simulation:
        raise ServiceError("Simulation for this recommendation no longer exists.", 404)
    return submit_decision(
        db,
        recommendation=record,
        simulation=simulation,
        user=user,
        action=payload.action,
        rationale=payload.rationale,
        modifications=payload.modifications,
        confirm_apply=payload.confirm_apply,
        feedback_category=payload.feedback_category,
        structured_rationale_tag=payload.structured_rationale_tag,
    )


@router.post("/decisions/{decision_id}/evaluate")
def evaluate_decision(
    decision_id: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return evaluate_decision_outcome(db, decision_id)


@router.post("/models/offline-evaluation")
def offline_evaluation(
    candidate_name: str = "railgorithm-ppo-v2.9",
    candidate_version: str = "v2.9-candidate",
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    return evaluate_offline_model_candidates(db, candidate_name, candidate_version)
