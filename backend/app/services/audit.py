"""Append-only audit log with a SHA-256 hash chain."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditEvent

GENESIS_HASH = "0" * 64


def _canonical(payload: dict) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _timestamp(value: datetime | None) -> str | None:
    """Normalise to naive UTC so the hash survives a SQLite round-trip.

    SQLite does not preserve tzinfo, so hashing an aware ISO string at write
    time and a naive ISO string at verification time would always mismatch.
    """
    if value is None:
        return None
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value.isoformat()


def append_audit(
    db: Session,
    *,
    event_type: str,
    actor: str,
    actor_role: str,
    payload: dict,
    simulation_id: str | None = None,
    recommendation_id: str | None = None,
) -> AuditEvent:
    last = db.execute(
        select(AuditEvent).order_by(AuditEvent.id.desc()).limit(1)
    ).scalar_one_or_none()
    prev_hash = last.hash if last else GENESIS_HASH
    created_at = datetime.now(timezone.utc)
    body = {
        "event_type": event_type,
        "actor": actor,
        "actor_role": actor_role,
        "simulation_id": simulation_id,
        "recommendation_id": recommendation_id,
        "payload": payload,
        "created_at": _timestamp(created_at),
    }
    digest = hashlib.sha256((prev_hash + _canonical(body)).encode("utf-8")).hexdigest()
    event = AuditEvent(
        event_type=event_type,
        actor=actor,
        actor_role=actor_role,
        simulation_id=simulation_id,
        recommendation_id=recommendation_id,
        payload=payload,
        prev_hash=prev_hash,
        hash=digest,
        created_at=created_at,
    )
    db.add(event)
    db.flush()
    return event


def verify_audit_chain(db: Session) -> dict:
    events = db.execute(select(AuditEvent).order_by(AuditEvent.id.asc())).scalars().all()
    prev_hash = GENESIS_HASH
    for event in events:
        body = {
            "event_type": event.event_type,
            "actor": event.actor,
            "actor_role": event.actor_role,
            "simulation_id": event.simulation_id,
            "recommendation_id": event.recommendation_id,
            "payload": event.payload,
            "created_at": _timestamp(event.created_at),
        }
        expected = hashlib.sha256((prev_hash + _canonical(body)).encode("utf-8")).hexdigest()
        if event.prev_hash != prev_hash or event.hash != expected:
            return {
                "valid": False,
                "events": len(events),
                "first_invalid_event_id": event.id,
                "detail": "Hash chain mismatch; the audit record may have been tampered with.",
            }
        prev_hash = event.hash
    return {"valid": True, "events": len(events), "head_hash": prev_hash}
