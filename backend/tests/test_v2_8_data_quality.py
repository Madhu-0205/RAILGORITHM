"""Tests for Feature 5: Data Quality States, Eligibility Gates & Calibration Disclosure (v2.8)."""
import pytest
from app.domain.data_quality import (
    DATA_QUALITY_STATES,
    evaluate_data_quality,
    get_confidence_disclosure,
)
from app.domain.pipeline import generate_recommendation
from app.domain.state import initialise_state


def test_data_quality_states_taxonomy():
    expected = {
        "VERIFIED_SOURCE_DATA",
        "OBSERVED",
        "CALCULATED",
        "PREDICTED",
        "SIMULATION",
        "HEURISTIC",
        "UNKNOWN",
        "STALE",
        "CONFLICTING",
        "NO_DATA",
    }
    assert DATA_QUALITY_STATES == expected


def test_data_quality_evaluation_healthy_state():
    state = initialise_state("normal_traffic")
    quality = evaluate_data_quality(state)
    assert quality["is_eligible_for_recommendations"] is True
    assert quality["overall_quality_state"] in {"SIMULATION", "OBSERVED", "CALCULATED"}
    assert "signal_feed" in quality["items"]
    assert "train_positions" in quality["items"]
    assert "topology" in quality["items"]


def test_data_quality_gate_blocks_on_empty_trains():
    state = initialise_state("normal_traffic")
    state["trains"] = []
    quality = evaluate_data_quality(state)
    assert quality["is_eligible_for_recommendations"] is False
    assert quality["items"]["train_positions"]["quality_state"] == "NO_DATA"


def test_confidence_disclosure_uncalibrated():
    disclosure = get_confidence_disclosure(is_calibrated=False)
    assert disclosure["is_calibrated"] is False
    assert disclosure["confidence_label"] == "Confidence: Not calibrated"
    assert disclosure["display_percentage"] is None
    assert "safety_note" in disclosure


def test_recommendation_payload_includes_quality_and_confidence():
    state = initialise_state("single_line_meet")
    payload = generate_recommendation(state)
    assert "data_quality" in payload
    assert "confidence_disclosure" in payload
    assert payload["confidence_disclosure"]["confidence_label"] == "Confidence: Not calibrated"
    assert "predictive_regulation" in payload
