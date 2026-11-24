"""Recommendation review and human decision endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import Simulation, User
from ..schemas import DecisionRequest
from ..services.decision_service import submit_decision
from ..services.recommendation_service import (
    get_record,
    serialize,
)
from ..services.simulation_service import ServiceError

router = APIRouter(prefix="/recommendations", tags=["recommendations"])


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
    if (
        user.role == "STATION_MASTER"
        and user.station_id
        and user.station_id not in record.payload.get("affected_stations", [])
    ):
        raise ServiceError(
            "This recommendation is outside your station scope.", 403
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
    )
