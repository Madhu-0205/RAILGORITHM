"""Version 2.0 regression tests: assumptions, constraints, conflicts, optimizer,
provenance and deployment posture.

These tests protect the measurable behaviour added in Version 2.0. They do not
weaken any Version 1.0 test.
"""
from __future__ import annotations

from dataclasses import replace

import pytest

from app.config import settings as app_settings
from app.domain.conflicts import (
    CONFLICT_TYPES,
    detect_conflicts,
    primary_conflicts,
)
from app.domain.optimizer import optimise, optimise_alternatives
from app.domain.pipeline import generate_recommendation
from app.domain.scenarios import SCENARIOS, scenario_catalogue
from app.domain.spec import (
    ASSUMPTIONS,
    CONSTRAINTS,
    assumption_manifest,
    constraint_manifest,
    objective_weights,
)
from app.domain.state import advance, initialise_state


NEW_SCENARIOS = [
    "double_line_overtaking",
    "junction_congestion",
    "maintenance_window",
    "cascading_delay",
    "disruption_recovery",
    "time_varying_demand",
]


def test_assumption_manifest_is_explicit_and_unique():
    manifest = assumption_manifest()
    assert manifest["version"] == "assumptions-2.0.0"
    assert manifest["label"] == "SYNTHETIC"
    ids = [item.id for item in ASSUMPTIONS]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 15
    for item in manifest["assumptions"]:
        assert item["source"]
        assert item["category"]
        assert item["value"] is not None


def test_constraint_manifest_has_hard_and_soft_constraints():
    manifest = constraint_manifest()
    assert manifest["version"] == "constraints-2.0.0"
    assert manifest["counts"]["hard"] >= 10
    assert manifest["counts"]["soft"] >= 3
    ids = [item["id"] for item in manifest["constraints"]]
    assert len(ids) == len(set(ids))
    for item in manifest["constraints"]:
        assert item["kind"] in {"HARD", "SOFT"}
        assert item["enforced_by"]
        assert item["statement"]


def test_scenario_catalogue_covers_fourteen_cases():
    catalogue = scenario_catalogue()
    assert len(catalogue) == 14
    keys = {entry["key"] for entry in catalogue}
    assert set(NEW_SCENARIOS) <= keys
    assert all(entry["label"] == "SYNTHETIC" for entry in catalogue)
    assert all(entry["train_count"] > 0 for entry in catalogue)
    assert any(entry["disruption_count"] for entry in catalogue)
    assert any("maintenance" in entry["tags"] for entry in catalogue)


@pytest.mark.parametrize("key", NEW_SCENARIOS)
def test_new_scenarios_initialise_with_versions_and_tags(key: str):
    state = initialise_state(key)
    assert state["scenario_key"] == key
    assert state["service_pattern"]
    assert isinstance(state["tags"], list)
    assert state["speed_restrictions"] == [] or isinstance(state["speed_restrictions"], list)
    assert state["disruptions"] == [] or isinstance(state["disruptions"], list)


def test_conflict_taxonomy_includes_v2_types_and_required_fields():
    state = initialise_state("time_varying_demand")
    advance(state, 4)
    conflicts = detect_conflicts(state)
    types = {conflict["type"] for conflict in conflicts}
    assert types <= set(CONFLICT_TYPES)
    assert "OVERTAKING_CONFLICT" in types
    for conflict in conflicts:
        assert conflict["id"]
        assert conflict["type"] in CONFLICT_TYPES
        assert conflict["related_types"]
        assert conflict["type"] in conflict["related_types"]
        assert conflict["constraint_id"]
        assert conflict["constraint_spec_version"] == "constraints-2.0.0"
        assert conflict["severity"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert conflict["trains"]
        assert conflict["start_min"] <= conflict["end_min"]
        assert conflict["evidence"]
        assert conflict["location"]["kind"] in {"STATION", "SECTION", "BLOCK", "TRAIN"}
    ids = [conflict["id"] for conflict in conflicts]
    assert len(ids) == len(set(ids))


def test_double_line_overtaking_reports_overtaking_evidence():
    state = initialise_state("double_line_overtaking")
    advance(state, 4)
    conflicts = detect_conflicts(state)
    overtaking = next(
        conflict for conflict in conflicts if conflict["type"] == "OVERTAKING_CONFLICT"
    )
    assert len(overtaking["trains"]) == 2
    assert overtaking["evidence"]["follower_speed_factor"] < overtaking["evidence"][
        "leader_speed_factor"
    ]


def test_disruption_recovery_exposes_disruption_and_closure_evidence():
    state = initialise_state("disruption_recovery")
    advance(state, 7)
    conflicts = detect_conflicts(state)
    types = {conflict["type"] for conflict in conflicts}
    assert "BLOCK_CLOSURE" in types
    closure = next(conflict for conflict in conflicts if conflict["type"] == "BLOCK_CLOSURE")
    assert "DISRUPTION_CONFLICT" in closure["related_types"]
    assert closure["constraint_id"] == "HC-007"


def test_cpsat_reports_accurate_status_and_objective_fields():
    state = initialise_state("single_line_meet")
    advance(state, 3)
    result = optimise(state, horizon_min=75)
    assert result["status"] in {"OPTIMAL", "FEASIBLE", "INFEASIBLE"}
    assert result["objective_profile"] == "balanced"
    assert result["objective_weights"] == objective_weights("balanced")
    if result["status"] in {"OPTIMAL", "FEASIBLE"}:
        assert result["objective_value"] is not None
        assert result["objective_bound"] is not None
        assert result["is_optimal"] == (result["status"] == "OPTIMAL")
        # The achieved objective is never below the proven lower bound.
        assert result["objective_value"] >= result["objective_bound"] - 1e-6
    else:
        assert result["objective_value"] is None
        assert result["is_optimal"] is False


def test_cpsat_alternative_profiles_are_reported_separately():
    state = initialise_state("single_line_meet")
    advance(state, 3)
    alternatives = optimise_alternatives(state, horizon_min=75)
    assert len(alternatives) >= 3
    profiles = {item["profile"] for item in alternatives}
    assert {"balanced", "delay_focused", "priority_focused"} <= profiles
    for item in alternatives:
        assert item["status"] in {"OPTIMAL", "FEASIBLE", "INFEASIBLE", "UNKNOWN"}
        assert item["objective_weights"] is not None


def test_recommendation_contains_provenance_and_honest_uncertainty():
    state = initialise_state("block_closure")
    advance(state, 5)
    payload = generate_recommendation(state, apply_minutes=30)
    assert payload["assumption_spec_version"] == "assumptions-2.0.0"
    assert payload["constraint_spec_version"] == "constraints-2.0.0"
    assert payload["provenance"]["state_version"] == state["version"]
    assert payload["provenance"]["solver"]["optimizer_version"].startswith("cpsat-2")
    assert payload["provenance"]["alternatives_considered"]
    assert payload["uncertainty"]["confidence_percentage"] is None
    assert payload["trade_offs"]["selection_rule"]
    assert payload["decision_support"]["human_in_control"] is True
    assert payload["decision_support"]["recommendation_is_not_a_decision"] is True
    recommended = payload["recommended"]
    assert recommended is not None
    assert recommended["affected_resources"]["trains"]
    assert recommended["validation_report"]["validator_version"] == "validator-2.0.0"
    assert recommended["value_labels"]["calculated"]
    assert recommended["value_labels"]["predicted"]
    assert recommended["value_labels"]["assumed"]
    assert recommended["provenance"]["candidate_id"] == recommended["candidate_id"]


def test_no_confidence_percentage_is_fabricated_anywhere():
    state = initialise_state("single_line_meet")
    advance(state, 2)
    payload = generate_recommendation(state, apply_minutes=60)
    assert payload["uncertainty"]["confidence_percentage"] is None
    if payload["recommended"]:
        assert payload["recommended"]["ppo_evidence"]["note"].startswith(
            "Policy probability"
        )


@pytest.mark.parametrize("key", sorted(scenario.key for scenario in SCENARIOS))
def test_every_scenario_produces_a_structured_recommendation(key: str):
    state = initialise_state(key)
    advance(state, 3)
    payload = generate_recommendation(state, apply_minutes=30)
    assert payload["evidence_status"] in {
        "VALIDATED",
        "VALIDATED_WITH_ASSUMPTIONS",
        "MODEL_DISAGREEMENT",
        "NO_FEASIBLE_SOLUTION",
        "INCOMPLETE_DATA",
    }
    assert payload["optimizer"]["status"] in {
        "OPTIMAL",
        "FEASIBLE",
        "INFEASIBLE",
        "UNKNOWN",
        "MODEL_INVALID",
        "NOT_RUN",
    }
    if payload["evidence_status"] == "NO_FEASIBLE_SOLUTION":
        assert payload["recommended"] is None
    else:
        assert payload["recommended"] is not None
        assert payload["recommended"]["action_validation_status"] in {
            "VALIDATED",
            "VALIDATED_WITH_ASSUMPTIONS",
        }


def test_primary_conflicts_remain_severity_ordered():
    state = initialise_state("junction_congestion")
    advance(state, 4)
    primary = primary_conflicts(detect_conflicts(state), limit=5)
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    assert [order[item["severity"]] for item in primary] == sorted(
        order[item["severity"]] for item in primary
    )


def test_production_configuration_rejects_default_secret_and_demo_credentials():
    production = replace(
        app_settings,
        environment="production",
        allow_demo_credentials=True,
        seed_demo=True,
        jwt_secret="railgorithm-dev-only-secret-change-me",
    )
    problems = production.production_problems
    assert any("JWT_SECRET" in problem for problem in problems)
    assert any("DEMO_CREDENTIALS" in problem for problem in problems)
    with pytest.raises(RuntimeError):
        production.assert_safe_for_production()


def test_production_configuration_accepts_postgres_and_explicit_secret():
    production = replace(
        app_settings,
        environment="production",
        allow_demo_credentials=False,
        seed_demo=False,
        jwt_secret="a-strong-secret-that-is-not-the-default-value",
        database_url="postgresql+psycopg://railgorithm:secret@db:5432/railgorithm",
    )
    assert production.production_problems == []
    production.assert_safe_for_production()


def test_schema_compiles_for_postgresql_without_sqlite_only_types():
    """The ORM schema must not depend on SQLite-only column types.

    This is a static portability check, not a claim that a PostgreSQL
    deployment has been load-tested. The SQLite triggers in ``init_db`` are
    replaced by equivalent PostgreSQL rules during a real migration.
    """
    from sqlalchemy.dialects import postgresql
    from sqlalchemy.schema import CreateTable

    from app.db import Base
    import app.models  # noqa: F401  (register mappings)

    for table in Base.metadata.sorted_tables:
        ddl = str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert "CREATE TABLE" in ddl
        assert "BLOB" not in ddl.upper()


def test_system_endpoints_expose_assumptions_and_constraints(client, section_headers):
    response = client.get("/api/v1/system/assumptions", headers=section_headers)
    assert response.status_code == 200
    assert response.json()["assumptions"]
    response = client.get("/api/v1/system/constraints", headers=section_headers)
    assert response.status_code == 200
    assert response.json()["counts"]["hard"] >= 10
    response = client.get("/api/v1/system/versions", headers=section_headers)
    assert response.status_code == 200
    versions = response.json()
    assert versions["optimizer"].startswith("cpsat-2")
    assert versions["validator"] == "validator-2.0.0"
    response = client.get("/api/v1/system/deployment", headers=section_headers)
    assert response.status_code == 200
    deployment = response.json()
    assert deployment["live_railway_connection"] is False
    assert deployment["human_in_control"] is True
