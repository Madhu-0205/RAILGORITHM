"""Recommendation persistence, retrieval and staleness handling."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..domain.pipeline import generate_recommendation
from ..domain.ppo import PPOAgent
from ..models import Decision, Recommendation, Simulation, User
from .audit import append_audit
from .simulation_service import ServiceError


def _affected_stations(payload: dict, state: dict) -> list[str]:
    stations: set[str] = set()
    network = state["network"]
    section_map = {section["id"]: section for section in network["sections"]}
    for conflict in payload.get("conflicts", []):
        location = conflict.get("location", {})
        if location.get("station_id"):
            stations.add(location["station_id"])
        if location.get("section_id"):
            section = section_map.get(location["section_id"])
            if section:
                stations.add(section["from_station"])
                stations.add(section["to_station"])
        if location.get("block_id"):
            for section in network["sections"]:
                if any(block["id"] == location["block_id"] for block in section["blocks"]):
                    stations.add(section["from_station"])
                    stations.add(section["to_station"])
    recommended = payload.get("recommended") or {}
    action = recommended.get("action") or {}
    if action.get("station_id"):
        stations.add(action["station_id"])
    if action.get("type") == "HOLD":
        train = next(
            (train for train in state["trains"] if train["id"] == action.get("train_id")),
            None,
        )
        if train and train.get("station_id"):
            stations.add(train["station_id"])
    if action.get("type") == "SCHEDULE":
        for train_id in payload.get("optimizer", {}).get("trains", {}):
            train = next(
                (train for train in state["trains"] if train["id"] == train_id), None
            )
            if train:
                stations.update(train["route"])
    for item in payload.get("alternatives", []):
        candidate_action = item.get("action") or {}
        if candidate_action.get("station_id"):
            stations.add(candidate_action["station_id"])
        if candidate_action.get("type") == "HOLD":
            train = next(
                (
                    train
                    for train in state["trains"]
                    if train["id"] == candidate_action.get("train_id")
                ),
                None,
            )
            if train and train.get("station_id"):
                stations.add(train["station_id"])
    return sorted(station for station in stations if station)


def generate_record(
    db: Session,
    simulation: Simulation,
    *,
    actor: User,
    parent_recommendation_id: str | None = None,
    ppo_agent: PPOAgent | None = None,
) -> Recommendation:
    if simulation.status == "COMPLETED":
        raise ServiceError("Cannot generate a recommendation for a completed simulation.", 409)
    payload = generate_recommendation(
        simulation.state,
        horizon_min=settings.recommendation_horizon_min,
        apply_minutes=settings.evaluation_horizon_min,
        ppo_agent=ppo_agent,
    )
    recommendation_id = str(uuid4())
    payload["recommendation_id"] = recommendation_id
    payload["simulation_id"] = simulation.id
    payload["parent_recommendation_id"] = parent_recommendation_id
    payload["affected_stations"] = _affected_stations(payload, simulation.state)
    payload["requested_by"] = actor.username
    recommendation = Recommendation(
        id=recommendation_id,
        simulation_id=simulation.id,
        state_version=int(simulation.state_version),
        status="PENDING",
        evidence_status=payload["evidence_status"],
        disagreement=bool(payload.get("disagreement")),
        payload=payload,
        model_version=payload.get("model_version", "ppo-unavailable"),
        optimizer_version=payload.get("optimizer_version", "cpsat-unknown"),
        created_by=actor.username,
    )
    db.add(recommendation)
    db.flush()
    append_audit(
        db,
        event_type="RECOMMENDATION_GENERATED",
        actor=actor.username,
        actor_role=actor.role,
        simulation_id=simulation.id,
        recommendation_id=recommendation.id,
        payload={
            "state_version": recommendation.state_version,
            "evidence_status": recommendation.evidence_status,
            "disagreement": recommendation.disagreement,
            "recommended_candidate_id": (payload.get("recommended") or {}).get("candidate_id"),
            "optimizer_status": payload.get("optimizer", {}).get("status"),
            "model_version": recommendation.model_version,
            "affected_stations": payload["affected_stations"],
            "parent_recommendation_id": parent_recommendation_id,
        },
    )
    db.commit()
    db.refresh(recommendation)
    return recommendation


def serialize(
    db: Session, recommendation: Recommendation, simulation: Simulation
) -> dict:
    decision = db.execute(
        select(Decision).where(Decision.recommendation_id == recommendation.id)
    ).scalar_one_or_none()
    is_stale = recommendation.status in {"PENDING", "STALE"} and int(
        simulation.state_version
    ) != int(recommendation.state_version)
    payload = dict(recommendation.payload)
    payload.update(
        {
            "recommendation_id": recommendation.id,
            "status": recommendation.status,
            "evidence_status": recommendation.evidence_status,
            "disagreement": recommendation.disagreement,
            "created_at": recommendation.created_at.isoformat(),
            "created_by": recommendation.created_by,
            "model_version": recommendation.model_version,
            "optimizer_version": recommendation.optimizer_version,
            "is_stale": is_stale,
            "current_state_version": simulation.state_version,
            "simulation_status": simulation.status,
            "affected_stations": payload.get("affected_stations", []),
            "decision": serialize_decision(decision) if decision else None,
        }
    )
    return payload


def serialize_decision(decision: Decision) -> dict:
    return {
        "id": decision.id,
        "recommendation_id": decision.recommendation_id,
        "action": decision.action,
        "rationale": decision.rationale,
        "modifications": decision.modifications,
        "decided_by": decision.decided_by,
        "decided_role": decision.decided_role,
        "decided_at": decision.decided_at.isoformat(),
        "applied": decision.applied,
        "simulation_result": decision.simulation_result,
        "validation_status": (decision.validation or {}).get("status"),
        "model_version": decision.model_version,
        "optimizer_version": decision.optimizer_version,
        "execution_mode": "SIMULATED_ONLY",
        "feedback_category": getattr(decision, "feedback_category", None),
        "structured_rationale_tag": getattr(decision, "structured_rationale_tag", None),
        "predicted_outcome": getattr(decision, "predicted_outcome", None),
        "actual_outcome": getattr(decision, "actual_outcome", None),
        "prediction_error": getattr(decision, "prediction_error", None),
        "data_quality": getattr(decision, "data_quality", None),
        "three_way_comparison": getattr(decision, "three_way_comparison", None),
    }


def list_records(
    db: Session,
    simulation: Simulation,
    *,
    actor: User,
    status: str | None = None,
) -> list[Recommendation]:
    query = select(Recommendation).where(
        Recommendation.simulation_id == simulation.id
    ).order_by(Recommendation.created_at.desc())
    if status:
        query = query.where(Recommendation.status == status)
    records = db.execute(query).scalars().all()
    if actor.is_station_master():
        allowed_stations = set(actor.get_stations())
        records = [
            record
            for record in records
            if any(st in allowed_stations for st in record.payload.get("affected_stations", []))
        ]
    elif actor.is_section_controller() and actor.control_area not in {None, "CORRIDOR"}:
        allowed_stations = set(actor.get_stations())
        records = [
            record
            for record in records
            if any(st in allowed_stations for st in record.payload.get("affected_stations", []))
        ]
    return records


def get_record(db: Session, recommendation_id: str) -> Recommendation:
    record = db.execute(
        select(Recommendation).where(Recommendation.id == recommendation_id)
    ).scalar_one_or_none()
    if not record:
        raise ServiceError("Recommendation not found", 404)
    return record


def affected_stations(record: Recommendation) -> list[str]:
    return record.payload.get("affected_stations", [])
