"""Regression tests for RAILGORITHM 2.1 unseen scenario generalization and graceful degradation."""
from __future__ import annotations

import pytest

from app.domain.pipeline import generate_recommendation
from app.domain.ppo import PPOAgent
from app.domain.state import advance, apply_action, initialise_state, state_metrics, validate_state_integrity
from ml.run_generalization import GEN_SCENARIOS


def test_generalization_scenarios_integrity():
    """All novel generalization scenario specs produce topologically and schedule-valid states."""
    for spec in GEN_SCENARIOS:
        state = initialise_state(spec, seed_override=1234)
        problems = validate_state_integrity(state)
        assert problems == [], f"Scenario {spec.key} has structural problems: {problems}"
        metrics = state_metrics(state)
        assert metrics["trains_total"] == len(spec.trains)
        assert metrics["label"] == "SYNTHETIC"


def test_generalization_pipeline_generates_valid_candidates():
    """The pipeline generates pre-validated eligible candidates on unseen scenarios."""
    for spec in GEN_SCENARIOS:
        state = initialise_state(spec, seed_override=7001)
        advance(state, 10)
        payload = generate_recommendation(state, horizon_min=75, apply_minutes=45)
        assert payload["evidence_status"] in {
            "EVIDENCE_ATTACHED",
            "MODEL_DISAGREEMENT",
            "VALIDATED",
            "VALIDATED_WITH_ASSUMPTIONS",
        }
        assert payload["conflicts"]  # Conflicted situation should trigger conflict detection
        alternatives = payload.get("alternatives", [])
        assert len(alternatives) > 0
        eligible = [alt for alt in alternatives if alt.get("eligible")]
        assert len(eligible) > 0, f"No eligible candidates produced for {spec.key}"

        # Hard-constraint validator must hold for all eligible options
        for alt in eligible:
            assert alt["action_validation_status"] in {"VALIDATED", "VALIDATED_WITH_ASSUMPTIONS"}
            assert alt["validation_status"] in {"VALIDATED", "VALIDATED_WITH_ASSUMPTIONS"}


def test_generalization_zero_constraint_violations_with_ppo():
    """PPO ranking on unseen scenarios must never propose an action that fails the validator."""
    agent = PPOAgent()
    for spec in GEN_SCENARIOS:
        state = initialise_state(spec, seed_override=7002)
        advance(state, 12)
        payload = generate_recommendation(state, horizon_min=75, apply_minutes=45, ppo_agent=agent)
        rec = payload.get("recommended")
        assert rec is not None
        assert rec["action_validation_status"] in {"VALIDATED", "VALIDATED_WITH_ASSUMPTIONS"}
        assert rec["validation_status"] in {"VALIDATED", "VALIDATED_WITH_ASSUMPTIONS"}


def test_generalization_graceful_degradation_under_junction_gridlock():
    """Under extreme junction gridlock with platform outage, simulation steps safely without deadlock."""
    gridlock_spec = next(s for s in GEN_SCENARIOS if s.key == "gen_cascading_junction_gridlock")
    state = initialise_state(gridlock_spec, seed_override=7003)

    # Advance through the entire platform outage window (minutes 360 to 420)
    for _ in range(6):
        advance(state, 10)
        assert state["status"] in {"RUNNING", "COMPLETED"}

    metrics = state_metrics(state)
    assert metrics["sim_time_min"] == 6 * 60 + 60
    assert metrics["trains_total"] == 7
    # Integrity check after intensive simulation
    assert validate_state_integrity(state) == []
