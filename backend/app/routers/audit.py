"""Audit trail endpoints (Section Master only)."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import require_roles
from ..models import AuditEvent, User
from ..services.audit import verify_audit_chain

router = APIRouter(prefix="/audit", tags=["audit"])


def _event_payload(event: AuditEvent) -> dict:
    return {
        "id": event.id,
        "event_type": event.event_type,
        "actor": event.actor,
        "actor_role": event.actor_role,
        "simulation_id": event.simulation_id,
        "recommendation_id": event.recommendation_id,
        "payload": event.payload,
        "prev_hash": event.prev_hash,
        "hash": event.hash,
        "created_at": event.created_at.isoformat(),
    }


@router.get("")
def list_audit(
    simulation_id: str | None = Query(default=None),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SECTION_MASTER")),
) -> dict:
    query = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit)
    if simulation_id:
        query = (
            select(AuditEvent)
            .where(AuditEvent.simulation_id == simulation_id)
            .order_by(AuditEvent.id.desc())
            .limit(limit)
        )
    events = db.execute(query).scalars().all()
    return {
        "events": [_event_payload(event) for event in events],
        "verification": verify_audit_chain(db),
        "append_only": True,
    }


@router.get("/verify")
def verify(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SECTION_MASTER")),
) -> dict:
    return {
        **verify_audit_chain(db),
        "append_only": True,
        "note": "Audit events and decisions are protected by database triggers against UPDATE/DELETE.",
    }
