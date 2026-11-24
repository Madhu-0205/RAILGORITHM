"""Independent constraint validator.

The validator must reject invalid actions and schedules on its own, without
trusting the optimizer or the recommendation pipeline.
"""
from __future__ import annotations

import copy

from app.domain.optimizer import optimise
from app.domain.state import advance, initialise_state
from app.domain.validator import (
    INCOMPLETE_DATA,
    INVALID,
    VALIDATED,
    VALIDATED_WITH_ASSUMPTIONS,
    evaluate_candidate,
    validate_action,
    validate_projected_state,
    validate_schedule,
)

ALLOWED = {VALIDATED, VALIDATED_WITH_ASSUMPTIONS}


def test_do_nothing_is_valid():
    state = initialise_state("single_line_meet")
    result = validate_action(state, {"type": "DO_NOTHING"})
    assert result["status"] == VALIDATED
    assert result["validator_version"]
    assert "not certify real-world" in result["disclaimer"]


def test_unknown_action_is_invalid():
    state = initialise_state("single_line_meet")
    result = validate_action(state, {"type": "MAGIC"})
    assert result["status"] == INVALID
    assert result["violations"]


def test_hold_of_running_train_is_invalid():
    state = initialise_state("single_line_meet")
    advance(state, 10)
    running = next(train for train in state["trains"] if train["status"] == "RUNNING")
    result = validate_action(
        state,
        {"type": "HOLD", "train_id": running["id"], "station_id": "NDL", "hold_min": 5},
    )
    assert result["status"] == INVALID


def test_hold_beyond_policy_is_invalid():
    state = initialise_state("single_line_meet")
    train = state["trains"][0]
    result = validate_action(
        state,
        {
            "type": "HOLD",
            "train_id": train["id"],
            "station_id": train["station_id"],
            "hold_min": 500,
        },
    )
    assert result["status"] == INVALID


def test_unknown_train_is_invalid():
    state = initialise_state("single_line_meet")
    result = validate_action(
        state, {"type": "PRECEDENCE", "train_id": "NOPE", "priority_override": 0}
    )
    assert result["status"] == INCOMPLETE_DATA


def test_valid_cp_sat_schedule_passes_independent_validation():
    state = initialise_state("normal_traffic")
    advance(state, 2)
    schedule = optimise(state)
    assert schedule["status"] in {"OPTIMAL", "FEASIBLE"}
    result = validate_schedule(state, schedule)
    assert result["status"] in ALLOWED, [
        check for check in result["checks"] if check["status"] == "FAIL"
    ]
    assert result["checks"]
    assert result["validator_version"]


def test_tampered_schedule_fails_validation():
    state = initialise_state("normal_traffic")
    advance(state, 2)
    schedule = optimise(state)
    tampered = copy.deepcopy(schedule)
    train_id = next(
        key
        for key, payload in tampered["trains"].items()
        if len(payload["segments"]) >= 2
    )
    segments = tampered["trains"][train_id]["segments"]
    # Second leg now starts before the first leg has cleared the block.
    segments[1]["entry_min"] = segments[0]["exit_min"] - 3
    result = validate_schedule(state, tampered)
    assert result["status"] == INVALID
    assert any(check["status"] == "FAIL" for check in result["checks"])


def test_schedule_with_overlapping_block_use_fails():
    state = initialise_state("normal_traffic")
    advance(state, 2)
    schedule = optimise(state)
    tampered = copy.deepcopy(schedule)
    ids = list(tampered["trains"])
    first, second = tampered["trains"][ids[0]], tampered["trains"][ids[1]]
    # Force both trains onto the same single-line block at the same time.
    first["segments"][0].update(
        {"entry_min": 400, "exit_min": 410, "block_id": "B3", "section_id": "S3"}
    )
    second["segments"][0].update(
        {"entry_min": 400, "exit_min": 410, "block_id": "B3", "section_id": "S3"}
    )
    result = validate_schedule(state, tampered)
    assert result["status"] == INVALID


def test_projected_state_validation_runs():
    state = initialise_state("normal_traffic")
    advance(state, 30)
    result = validate_projected_state(state)
    assert result["status"] in ALLOWED


def test_evaluate_candidate_returns_measured_outcome():
    state = initialise_state("single_line_meet")
    advance(state, 2)
    outcome = evaluate_candidate(state, {"type": "DO_NOTHING"}, minutes=30)
    assert outcome["status"] in ALLOWED
    assert outcome["simulation_minutes"] == 30
    assert "metrics" in outcome
    assert "validation" in outcome
    assert "state" in outcome
    assert "post_conflicts" in outcome


def test_candidate_conflicts_cover_the_window_before_advancing():
    """A full-horizon check must include conflicts active at the current time."""
    state = initialise_state("block_closure")
    advance(state, 5)
    outcome = evaluate_candidate(
        state,
        {"type": "DO_NOTHING"},
        minutes=75,
        conflict_horizon_min=75,
    )
    critical = [
        conflict
        for conflict in outcome["post_conflicts"]
        if conflict["severity"] == "CRITICAL" and conflict["type"] == "BLOCK_CLOSURE"
    ]
    assert critical, "DO_NOTHING must not hide the closure by projecting only afterwards"
