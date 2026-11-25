"""Append-only audit log with a SHA-256 hash chain and truncation detection.

Two independent checks protect integrity:

1. every event hash covers the previous hash, so editing or reordering events
   breaks verification;
2. a single-row chain head records the last hash and total event count, so
   deleting events from the tail is also detected.

The head row is locked with ``SELECT ... FOR UPDATE`` on databases that support
it (PostgreSQL). SQLite serialises writers, so the same invariant holds for the
single-writer development deployment; a multi-instance deployment must use
PostgreSQL and a shared lock as documented in the security report.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import AuditChainHead, AuditEvent

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


def _head(db: Session, *, for_update: bool = False) -> AuditChainHead:
    query = select(AuditChainHead).where(AuditChainHead.id == 1)
    if for_update:
        query = query.with_for_update()
    head = db.execute(query).scalar_one_or_none()
    if head is None:
        head = AuditChainHead(id=1, head_hash=GENESIS_HASH, event_count=0)
        db.add(head)
        db.flush()
    return head


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
    head = _head(db, for_update=True)
    prev_hash = head.head_hash
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
    head.head_hash = digest
    head.event_count = int(head.event_count) + 1
    head.updated_at = created_at
    db.add(head)
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
    head = db.execute(
        select(AuditChainHead).where(AuditChainHead.id == 1)
    ).scalar_one_or_none()
    if head is not None:
        if int(head.event_count) != len(events) or head.head_hash != prev_hash:
            return {
                "valid": False,
                "events": len(events),
                "head_hash": prev_hash,
                "recorded_head_hash": head.head_hash,
                "recorded_event_count": int(head.event_count),
                "detail": (
                    "Audit chain head does not match the stored events. Events may "
                    "have been deleted from the tail or the head record was altered."
                ),
            }
    return {"valid": True, "events": len(events), "head_hash": prev_hash}
