"""Tests for Feature 1: Predictive Train Regulation (v2.8)."""
import pytest
from app.domain.projection import (
    classify_delay_trend,
    compute_comparative_timeline,
    compute_decision_urgency,
    compute_knock_on_propagation,
    compute_multi_horizon_projections,
)
from app.domain.state import advance, initialise_state


def test_delay_trend_classification_on_time():
    state = initialise_state("normal_traffic")
    train = state["trains"][0]
    trend = classify_delay_trend(train, state)
    assert trend["trend"] in {"STABLE", "DECREASING"}
    assert trend["primary_cause"] == "ON_TIME"
    assert trend["current_delay_min"] == 0


def test_delay_trend_classification_delayed():
    state = initialise_state("delayed_express")
    delayed_train = next((t for t in state["trains"] if int(t.get("delay_min", 0)) > 0), None)
    assert delayed_train is not None
    trend = classify_delay_trend(delayed_train, state)
    assert trend["trend"] in {"INCREASING", "DECREASING", "STABLE"}
    assert trend["current_delay_min"] > 0
    assert trend["primary_cause"] in {
        "TERMINAL_DWELL",
        "STATION_DWELL",
        "HEADWAY_COMPRESSION",
        "SPEED_RESTRICTION",
        "BLOCK_CLOSURE",
        "CASCADING_DELAY",
        "REGULATION_HOLD",
    }


def test_multi_horizon_projections():
    state = initialise_state("evening_peak")
    projections = compute_multi_horizon_projections(state, horizons=(30, 60, 90))
    assert len(projections) == 3
    for p, h in zip(projections, (30, 60, 90)):
        assert p["horizon_min"] == h
        assert "target_time" in p
        assert "total_conflicts" in p
        assert "actionable_conflicts" in p
        assert "critical_conflicts" in p
        assert p["projected_total_delay_min"] >= 0


def test_knock_on_propagation():
    state = initialise_state("cascading_delay")
    delayed_train = next((t for t in state["trains"] if int(t.get("delay_min", 0)) > 0), None)
    assert delayed_train is not None
    result = compute_knock_on_propagation(state, delayed_train["id"], horizon_min=90)
    assert result["delayed_train_id"] == delayed_train["id"]
    assert "affected_train_count" in result
    assert "total_knock_on_delay_min" in result
    assert isinstance(result["affected_trains"], list)
    assert isinstance(result["bottleneck_locations"], list)


def test_comparative_timeline():
    state = initialise_state("single_line_meet")
    rec_action = {
        "action": {
            "type": "HOLD",
            "train_id": state["trains"][0]["id"],
            "station_id": state["trains"][0].get("station_id") or "VSN",
            "hold_min": 10,
        }
    }
    timeline = compute_comparative_timeline(state, recommended_action=rec_action, horizon_min=90)
    assert timeline["available"] is True
    assert "stations" in timeline
    assert len(timeline["stations"]) > 0
    st0 = timeline["stations"][0]
    assert "scheduled_arrival" in st0
    assert "no_action_arrival" in st0
    assert "recommended_arrival" in st0
    assert "delay_savings_min" in st0


def test_decision_urgency_calculation():
    state = initialise_state("single_line_meet")
    from app.domain.conflicts import detect_conflicts
    confs = detect_conflicts(state, 60)
    urgency = compute_decision_urgency(state, confs)
    assert urgency["urgency_category"] in {"IMMEDIATE", "NEAR_TERM", "PLANNED", "MONITORING"}
    if urgency["action_required"]:
        assert urgency["time_to_act_min"] is not None
        assert urgency["critical_location"] is not None
        assert urgency["earliest_conflict_time"] is not None
