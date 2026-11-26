"""Tests for Feature 2: Explainable Recommendation Reasoning (v2.8)."""
import pytest
from app.domain.pipeline import generate_recommendation
from app.domain.state import initialise_state


def test_structured_reasoning_ten_elements():
    state = initialise_state("single_line_meet")
    payload = generate_recommendation(state)

    assert "explanation" in payload
    explanation = payload["explanation"]
    assert "structured_reasoning" in explanation

    sr = explanation["structured_reasoning"]
    required_keys = [
        "1_operational_situation",
        "2_primary_problem",
        "3_recommended_action",
        "4_operational_reasoning",
        "5_railway_constraints_considered",
        "6_alternative_options_evaluated",
        "7_expected_consequences",
        "8_consequences_of_no_action",
        "9_verified_evidence",
        "10_residual_uncertainty",
    ]
    for key in required_keys:
        assert key in sr, f"Missing {key} in structured_reasoning"
        assert sr[key] is not None

    # Verify constraints considered
    constraints = sr["5_railway_constraints_considered"]
    assert isinstance(constraints, list)
    constraint_ids = [c["constraint_id"] for c in constraints]
    assert "HC-001" in constraint_ids
    assert "HC-002" in constraint_ids
    assert "HC-003" in constraint_ids

    # Verify alternative options list
    alts = sr["6_alternative_options_evaluated"]
    assert isinstance(alts, list)
    assert len(alts) >= 1
    for alt in alts:
        assert "label" in alt
        assert "status" in alt
        assert "reason_not_chosen" in alt

    # Backward compatibility checks
    assert "questions" in explanation
    assert len(explanation["questions"]) == 10
    assert "key_facts" in explanation
