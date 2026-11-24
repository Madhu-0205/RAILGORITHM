"""Audit trail API and hash-chain integrity."""
from __future__ import annotations

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.db import Base
from app.models import AuditEvent
from app.services.audit import append_audit, verify_audit_chain


def test_audit_chain_is_valid_after_actions(client, section_headers, simulation):
    client.post(
        f"/api/v1/simulations/{simulation['id']}/recommendations",
        headers=section_headers,
    )
    response = client.get("/api/v1/audit/verify", headers=section_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["valid"] is True
    assert body["events"] > 0
    assert body["append_only"] is True
    assert len(body["head_hash"]) == 64


def test_audit_list_contains_login_and_simulation_events(client, section_headers):
    response = client.get("/api/v1/audit?limit=50", headers=section_headers)
    assert response.status_code == 200
    body = response.json()
    types = {event["event_type"] for event in body["events"]}
    assert "USER_LOGIN" in types
    assert body["verification"]["valid"] is True
    for event in body["events"]:
        assert len(event["hash"]) == 64
        assert len(event["prev_hash"]) == 64


def test_audit_chain_detects_direct_tampering(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'audit.db'}", future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    try:
        append_audit(
            session,
            event_type="TEST_EVENT",
            actor="tester",
            actor_role="TEST",
            payload={"value": 1},
        )
        append_audit(
            session,
            event_type="TEST_EVENT",
            actor="tester",
            actor_role="TEST",
            payload={"value": 2},
        )
        session.commit()
        assert verify_audit_chain(session)["valid"] is True

        # Directly rewrite a stored payload, bypassing append_audit.
        session.execute(
            text(
                "UPDATE audit_events SET payload = :payload WHERE id = "
                "(SELECT MIN(id) FROM audit_events)"
            ),
            {"payload": '{"value": 999}'},
        )
        session.commit()
        session.expire_all()
        result = verify_audit_chain(session)
        assert result["valid"] is False
        assert result["first_invalid_event_id"] is not None
        assert "tampered" in result["detail"].lower()
    finally:
        session.close()
        engine.dispose()


def test_audit_events_are_append_only_in_database(db_session):
    event_id = db_session.execute(select(AuditEvent.id).limit(1)).scalar_one()
    try:
        db_session.execute(
            text("UPDATE audit_events SET actor = 'intruder' WHERE id = :id"),
            {"id": event_id},
        )
        db_session.commit()
    except Exception as exc:  # noqa: BLE001 - DBAPI error type varies
        db_session.rollback()
        assert "append-only" in str(exc)
    else:  # pragma: no cover - the trigger must always fire
        db_session.rollback()
        raise AssertionError("audit_events UPDATE was not blocked")

    try:
        db_session.execute(
            text("DELETE FROM audit_events WHERE id = :id"), {"id": event_id}
        )
        db_session.commit()
    except Exception as exc:  # noqa: BLE001
        db_session.rollback()
        assert "append-only" in str(exc)
    else:  # pragma: no cover
        db_session.rollback()
        raise AssertionError("audit_events DELETE was not blocked")
