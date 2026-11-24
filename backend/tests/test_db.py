"""Database schema, seeding and append-only protections."""
from __future__ import annotations

from sqlalchemy import inspect, select, text

from app.db import engine
from app.models import Decision, ModelVersion, User


def test_required_tables_exist():
    tables = set(inspect(engine).get_table_names())
    assert {
        "users",
        "simulations",
        "recommendations",
        "decisions",
        "audit_events",
        "model_versions",
    }.issubset(tables)


def test_demo_users_are_seeded(db_session):
    users = {
        user.username: user for user in db_session.execute(select(User)).scalars().all()
    }
    assert users["section.master"].role == "SECTION_MASTER"
    assert users["section.master"].station_id is None
    assert users["station.master"].role == "STATION_MASTER"
    assert users["station.master"].station_id == "MLG"
    assert users["section.master"].password_hash.startswith("pbkdf2_sha256$")


def test_model_registry_declares_all_components(db_session):
    models = db_session.execute(select(ModelVersion)).scalars().all()
    names = {model.name for model in models}
    assert {"PPO", "CP-SAT", "Baseline"}.issubset(names)
    cpsat = next(model for model in models if model.name == "CP-SAT")
    assert cpsat.trained is False
    assert cpsat.status == "DETERMINISTIC_OPTIMIZER"
    baseline = next(model for model in models if model.name == "Baseline")
    assert baseline.status == "DETERMINISTIC_FALLBACK"


def test_decisions_are_append_only_and_unique(
    client, section_headers, simulation, db_session
):
    generated = client.post(
        f"/api/v1/simulations/{simulation['id']}/recommendations",
        headers=section_headers,
    ).json()
    decided = client.post(
        f"/api/v1/recommendations/{generated['recommendation_id']}/decision",
        headers=section_headers,
        json={"action": "REJECT", "rationale": "Database trigger test decision."},
    )
    assert decided.status_code == 200

    decision_id = db_session.execute(select(Decision.id).limit(1)).scalar_one()

    try:
        db_session.execute(
            text("UPDATE decisions SET action = 'APPROVE' WHERE id = :id"),
            {"id": decision_id},
        )
        db_session.commit()
    except Exception as exc:  # noqa: BLE001
        db_session.rollback()
        assert "append-only" in str(exc)
    else:  # pragma: no cover
        db_session.rollback()
        raise AssertionError("decisions UPDATE was not blocked")

    try:
        db_session.execute(
            text("DELETE FROM decisions WHERE id = :id"), {"id": decision_id}
        )
        db_session.commit()
    except Exception as exc:  # noqa: BLE001
        db_session.rollback()
        assert "append-only" in str(exc)
    else:  # pragma: no cover
        db_session.rollback()
        raise AssertionError("decisions DELETE was not blocked")


def test_one_decision_per_recommendation_is_enforced(db_session):
    decision = db_session.execute(select(Decision).limit(1)).scalar_one_or_none()
    if decision is None:
        return
    duplicate = Decision(
        recommendation_id=decision.recommendation_id,
        simulation_id=decision.simulation_id,
        action="REJECT",
        rationale="Duplicate decision must be rejected.",
        decided_by="tester",
        decided_role="SECTION_MASTER",
        applied=False,
        original_recommendation={},
        validation={},
        model_version="test",
        optimizer_version="test",
    )
    db_session.add(duplicate)
    try:
        db_session.commit()
    except Exception as exc:  # noqa: BLE001
        db_session.rollback()
        assert "UNIQUE" in str(exc).upper() or "unique" in str(exc).lower()
    else:  # pragma: no cover
        db_session.rollback()
        raise AssertionError("duplicate decision was accepted")
