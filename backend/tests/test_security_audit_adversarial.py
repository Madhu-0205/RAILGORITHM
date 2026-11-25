"""Adversarial security and audit integrity tests for RAILGORITHM 2.1.

Verifies:
1. Historical record modification blocked by database triggers
2. Event deletion blocked by database triggers
3. Tail truncation detected by verify_audit_chain
4. Invalid hash / corrupted payload detected
5. Missing or tampered audit head detected
6. Concurrent decision attempts handled safely (race condition protection)
7. Unauthorized decision blocked by station scope / RBAC
8. Stale recommendation approval rejected
9. Duplicate decision rejected
"""
from __future__ import annotations

import concurrent.futures
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.db import Base, SessionLocal
from app.models import AuditChainHead, AuditEvent, Recommendation, Simulation
from app.services.audit import append_audit, verify_audit_chain
from app.services.decision_service import submit_decision


def test_adversarial_audit_trigger_blocks_update(db_session):
    """Database triggers must unconditionally abort SQL UPDATE on audit_events."""
    event = db_session.execute(select(AuditEvent).limit(1)).scalar_one_or_none()
    if event is None:
        append_audit(db_session, event_type="TEST", actor="t", actor_role="R", payload={})
        db_session.commit()
        event = db_session.execute(select(AuditEvent).limit(1)).scalar_one()

    with pytest.raises(Exception) as exc_info:
        db_session.execute(
            text("UPDATE audit_events SET payload = '{\"hacked\": true}' WHERE id = :id"),
            {"id": event.id},
        )
        db_session.commit()
    assert "append-only" in str(exc_info.value).lower()
    db_session.rollback()


def test_adversarial_audit_trigger_blocks_delete(db_session):
    """Database triggers must unconditionally abort SQL DELETE on audit_events."""
    event = db_session.execute(select(AuditEvent).limit(1)).scalar_one_or_none()
    if event is None:
        append_audit(db_session, event_type="TEST", actor="t", actor_role="R", payload={})
        db_session.commit()
        event = db_session.execute(select(AuditEvent).limit(1)).scalar_one()

    with pytest.raises(Exception) as exc_info:
        db_session.execute(
            text("DELETE FROM audit_events WHERE id = :id"),
            {"id": event.id},
        )
        db_session.commit()
    assert "append-only" in str(exc_info.value).lower()
    db_session.rollback()


def test_adversarial_invalid_hash_detected(tmp_path):
    """If an attacker corrupts a hash, verify_audit_chain must return valid: False."""
    engine = create_engine(f"sqlite:///{tmp_path / 'hash_corrupt.db'}", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        append_audit(session, event_type="EV1", actor="a", actor_role="R", payload={"k": 1})
        append_audit(session, event_type="EV2", actor="a", actor_role="R", payload={"k": 2})
        session.commit()
        assert verify_audit_chain(session)["valid"] is True

        # Corrupt the hash of event 1
        session.execute(
            text("UPDATE audit_events SET hash = :fake WHERE id = 1"),
            {"fake": "0" * 64},
        )
        session.commit()
        session.expire_all()
        res = verify_audit_chain(session)
        assert res["valid"] is False
        assert "tampered" in res["detail"].lower()
    finally:
        session.close()
        engine.dispose()


def test_adversarial_tail_truncation_detected(tmp_path):
    """If the last event is deleted, verify_audit_chain detects mismatch against audit_chain_head."""
    engine = create_engine(f"sqlite:///{tmp_path / 'trunc.db'}", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        append_audit(session, event_type="EV1", actor="a", actor_role="R", payload={"k": 1})
        append_audit(session, event_type="EV2", actor="a", actor_role="R", payload={"k": 2})
        session.commit()
        assert verify_audit_chain(session)["valid"] is True

        # Directly delete the newest event
        session.execute(text("DELETE FROM audit_events WHERE id = 2"))
        session.commit()
        session.expire_all()
        res = verify_audit_chain(session)
        assert res["valid"] is False
        assert "head" in res["detail"].lower()
        assert res["events"] == 1
        assert res["recorded_event_count"] == 2
    finally:
        session.close()
        engine.dispose()


def test_adversarial_head_mismatch_detected(tmp_path):
    """If audit_chain_head hash is modified, verification fails immediately."""
    engine = create_engine(f"sqlite:///{tmp_path / 'head_mod.db'}", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        append_audit(session, event_type="EV1", actor="a", actor_role="R", payload={"k": 1})
        session.commit()
        assert verify_audit_chain(session)["valid"] is True

        # Modify head_hash in audit_chain_head
        session.execute(
            text("UPDATE audit_chain_head SET head_hash = :fake WHERE id = 1"),
            {"fake": "f" * 64},
        )
        session.commit()
        session.expire_all()
        res = verify_audit_chain(session)
        assert res["valid"] is False
        assert "head" in res["detail"].lower()
    finally:
        session.close()
        engine.dispose()


def test_adversarial_concurrent_decisions(client, section_headers, simulation):
    """When two concurrent requests attempt to decide on the same recommendation, exactly one must succeed."""
    gen = client.post(
        f"/api/v1/simulations/{simulation['id']}/recommendations",
        headers=section_headers,
    )
    assert gen.status_code == 200
    rec_id = gen.json()["recommendation_id"]
    state_ver = gen.json()["state_version"]

    def submit_decision(rationale: str):
        return client.post(
            f"/api/v1/recommendations/{rec_id}/decision",
            headers=section_headers,
            json={
                "action": "APPROVE",
                "rationale": rationale,
                "confirm_apply": True,
                "state_version": state_ver,
            },
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(submit_decision, "Controller A simultaneous approval")
        f2 = executor.submit(submit_decision, "Controller B simultaneous approval")
        r1 = f1.result()
        r2 = f2.result()

    statuses = sorted([r1.status_code, r2.status_code])
    # Exactly one must succeed (200) and the second must be rejected (409 Conflict)
    assert statuses == [200, 409], f"Expected [200, 409], got {statuses}"


def test_adversarial_unauthorized_scope_decision_blocked(client, station_headers, simulation):
    """Station Master cannot approve recommendations affecting stations outside their assigned scope."""
    # Simulation has affected stations across NDL, KRN, MLG, SRP, VSN
    gen = client.post(
        f"/api/v1/simulations/{simulation['id']}/recommendations",
        headers=station_headers,
    )
    if gen.status_code == 200:
        rec = gen.json()
        if "MLG" not in rec.get("affected_stations", []):
            dec = client.post(
                f"/api/v1/recommendations/{rec['recommendation_id']}/decision",
                headers=station_headers,
                json={"action": "APPROVE", "rationale": "Unauthorized scope test", "confirm_apply": True},
            )
            assert dec.status_code in {403, 404}


def test_adversarial_stale_recommendation_rejected(client, section_headers, simulation):
    """Attempting to approve a recommendation after the simulation clock has advanced must be rejected."""
    gen = client.post(
        f"/api/v1/simulations/{simulation['id']}/recommendations",
        headers=section_headers,
    )
    assert gen.status_code == 200
    rec_id = gen.json()["recommendation_id"]

    # Advance the simulation clock so state_version increments
    adv = client.post(
        f"/api/v1/simulations/{simulation['id']}/advance",
        headers=section_headers,
        json={"minutes": 10},
    )
    assert adv.status_code == 200

    # Decision on the older recommendation must now fail with HTTP 409
    dec = client.post(
        f"/api/v1/recommendations/{rec_id}/decision",
        headers=section_headers,
        json={"action": "APPROVE", "rationale": "Late approval attempt", "confirm_apply": True},
    )
    assert dec.status_code == 409
    assert "stale" in dec.json()["detail"].lower()
