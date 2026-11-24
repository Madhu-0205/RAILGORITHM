"""Hybrid recommendation pipeline: evidence, eligibility and honesty."""
from __future__ import annotations

from app.domain.pipeline import generate_recommendation
from app.domain.state import advance, initialise_state

ALLOWED = {"VALIDATED", "VALIDATED_WITH_ASSUMPTIONS"}


def test_pipeline_returns_structured_evidence():
    state = initialise_state("single_line_meet")
    advance(state, 2)
    payload = generate_recommendation(state, apply_minutes=60)
    assert payload["evidence_status"] in {
        "VALIDATED",
        "VALIDATED_WITH_ASSUMPTIONS",
        "MODEL_DISAGREEMENT",
        "NO_FEASIBLE_SOLUTION",
    }
    assert payload["label"] == "SYNTHETIC"
    assert payload["limitations"]
    assert payload["conflicts"]
    assert payload["alternatives"]
    assert payload["optimizer"]["status"] in {"OPTIMAL", "FEASIBLE", "INFEASIBLE"}
    assert payload["explanation"]["questions"]
    assert payload["comparison"]["measurement_note"]
    assert payload["state_version"] == state["version"]


def test_every_eligible_candidate_is_independently_validated():
    state = initialise_state("single_line_meet")
    advance(state, 2)
    payload = generate_recommendation(state, apply_minutes=60)
    eligible = [item for item in payload["alternatives"] if item["eligible"]]
    assert eligible
    for item in eligible:
        assert item["validation_status"] in ALLOWED
        assert item["score"] is not None
    for item in payload["alternatives"]:
        if not item["eligible"]:
            assert item["rejection_reason"]


def test_recommended_candidate_is_the_best_eligible_score():
    state = initialise_state("evening_peak")
    advance(state, 5)
    payload = generate_recommendation(state, apply_minutes=45)
    recommended = payload["recommended"]
    assert recommended is not None
    eligible_scores = sorted(
        item["score"] for item in payload["alternatives"] if item["eligible"]
    )
    assert recommended["score"] == eligible_scores[0]


def test_block_closure_waits_out_the_closure_with_a_validated_schedule():
    state = initialise_state("block_closure")
    advance(state, 5)
    payload = generate_recommendation(state, apply_minutes=30)
    assert payload["recommended"] is not None
    assert payload["evidence_status"] in {
        "VALIDATED",
        "VALIDATED_WITH_ASSUMPTIONS",
        "MODEL_DISAGREEMENT",
    }
    outcome = payload["recommended"]["expected_outcome"]
    assert outcome["residual_critical"] == 0
    assert payload["recommended"]["source"] == "CP_SAT"


def test_block_closure_rejects_do_nothing_at_the_full_decision_horizon():
    """Regression: a 75-minute evaluation must not look past an active closure.

    The decision endpoint re-checks the post-action projection from the current
    time. If candidate scoring only inspected the window after a 75-minute
    advance, DO_NOTHING appeared to avoid the closure because the projection
    started after the closure had ended.
    """
    state = initialise_state("block_closure")
    advance(state, 5)
    payload = generate_recommendation(state, apply_minutes=75)
    do_nothing = next(
        item for item in payload["alternatives"] if item["action"]["type"] == "DO_NOTHING"
    )
    assert do_nothing["eligible"] is False
    assert do_nothing["rejection_reason"]
    assert do_nothing["expected_outcome"]["residual_critical"] > 0
    assert payload["recommended"] is not None
    assert payload["recommended"]["source"] == "CP_SAT"
    assert payload["recommended"]["expected_outcome"]["residual_critical"] == 0


def test_infeasible_scenario_fabricates_nothing():
    state = initialise_state("no_feasible_schedule")
    advance(state, 2)
    payload = generate_recommendation(state, apply_minutes=60)
    assert payload["evidence_status"] == "NO_FEASIBLE_SOLUTION"
    assert payload["recommended"] is None
    assert payload["optimizer"]["status"] == "INFEASIBLE"
    assert all(not item["eligible"] for item in payload["alternatives"])


def test_ppo_unavailable_is_declared():
    state = initialise_state("single_line_meet")
    advance(state, 2)
    payload = generate_recommendation(state, apply_minutes=60)
    if not payload["ppo"].get("available"):
        assert payload["ppo"]["reason"]
        assert payload["ppo"]["model_version"] == "ppo-unavailable"


def test_explanation_answers_all_ten_questions():
    state = initialise_state("block_closure")
    advance(state, 3)
    payload = generate_recommendation(state, apply_minutes=60)
    questions = payload["explanation"]["questions"]
    assert len(questions) == 10
    assert all(isinstance(answer, str) and answer for answer in questions.values())


def test_comparison_contains_measured_baselines():
    state = initialise_state("single_line_meet")
    advance(state, 2)
    payload = generate_recommendation(state, apply_minutes=60)
    comparison = payload["comparison"]
    assert comparison["no_intervention"]["measurement"] == "SIMULATED_ESTIMATE"
    assert comparison["no_intervention"]["simulation_minutes"] == 60
    assert "baseline_heuristic_choice" in comparison
