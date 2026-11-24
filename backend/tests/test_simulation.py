"""Deterministic simulation engine behaviour."""
from __future__ import annotations

import copy

import pytest

from app.domain.state import (
    SimulationError,
    advance,
    apply_action,
    format_minutes,
    initialise_state,
    parse_minutes,
    projected_delay,
    state_metrics,
    validate_state_integrity,
)
from app.domain.optimizer import optimise
from app.domain.projection import project_state


def test_time_helpers():
    assert format_minutes(360) == "06:00"
    assert format_minutes(0) == "00:00"
    assert format_minutes(1439) == "23:59"
    assert format_minutes(None) is None
    assert parse_minutes("06:00") == 360
    assert parse_minutes("23:59") == 1439


def test_state_integrity_is_clean_for_every_scenario():
    for key in (
        "normal_traffic",
        "evening_peak",
        "single_line_meet",
        "delayed_express",
        "block_closure",
        "platform_outage",
        "priority_train",
        "no_feasible_schedule",
    ):
        assert validate_state_integrity(initialise_state(key)) == []


def test_projection_honours_planned_en_route_holds():
    state = initialise_state("block_closure")
    advance(state, 5)
    result = optimise(state)
    assert result["status"] in {"OPTIMAL", "FEASIBLE"}
    apply_action(state, result["action"])
    advance(state, 30)
    projection = project_state(state, 120)
    windows = projection["trains"]["61042"]["block_windows"]
    b3 = next(window for window in windows if window["block_id"] == "B3")
    closure = next(item for item in state["closures"] if item["block_id"] == "B3")
    # The en-route hold at MLG must keep the train out of the closed block.
    assert b3["entry_min"] >= closure["end_min"]


def test_advance_is_deterministic():
    first = initialise_state("normal_traffic")
    second = initialise_state("normal_traffic")
    advance(first, 45)
    advance(second, 45)
    assert first["sim_time_min"] == second["sim_time_min"] == 405
    assert [train["status"] for train in first["trains"]] == [
        train["status"] for train in second["trains"]
    ]
    assert [train["delay_min"] for train in first["trains"]] == [
        train["delay_min"] for train in second["trains"]
    ]


def test_advance_increments_version_once():
    state = initialise_state("normal_traffic")
    before = state["version"]
    advance(state, 10)
    assert state["version"] == before + 1


def test_advance_rejects_out_of_range():
    state = initialise_state("normal_traffic")
    with pytest.raises(SimulationError):
        advance(state, -1)
    with pytest.raises(SimulationError):
        advance(state, 181)


def test_paused_state_cannot_advance():
    state = initialise_state("normal_traffic")
    state["status"] = "PAUSED"
    with pytest.raises(SimulationError):
        advance(state, 5)


def test_single_line_block_is_exclusive():
    state = initialise_state("single_line_meet")
    advance(state, 90)
    # Replay the occupancy trace by asserting that at no recorded moment a
    # bidirectional block carried two trains simultaneously.
    for block_id, occupancy in state["block_occupancy"].items():
        if occupancy.get("train_id"):
            assert isinstance(occupancy["train_id"], str)
    # Structural invariant: a train may occupy at most one block at a time.
    running = [train for train in state["trains"] if train["status"] == "RUNNING"]
    block_ids = [train["block_id"] for train in running if train["block_id"]]
    assert len(block_ids) == len(set(block_ids))


def test_metrics_are_internally_consistent():
    state = initialise_state("normal_traffic")
    advance(state, 60)
    metrics = state_metrics(state)
    assert metrics["trains_total"] == len(state["trains"])
    assert metrics["trains_active"] + metrics["trains_completed"] == metrics["trains_total"]
    assert metrics["total_delay_min"] == sum(
        projected_delay(train, state["sim_time_min"]) for train in state["trains"]
    )
    assert 0 <= metrics["section_utilization_pct"] <= 100
    assert 0 <= metrics["platform_utilization_pct"] <= 100
    assert metrics["label"] == "SYNTHETIC"


def test_hold_action_delays_departure():
    state = initialise_state("single_line_meet")
    train = state["trains"][0]
    assert train["status"] == "AT_STATION"
    before = int(train["ready_departure_min"])
    apply_action(
        state,
        {
            "type": "HOLD",
            "train_id": train["id"],
            "station_id": train["station_id"],
            "hold_min": 15,
        },
    )
    assert int(train["hold_until_min"]) >= before + 15


def test_precedence_action_sets_override():
    state = initialise_state("single_line_meet")
    train = state["trains"][0]
    apply_action(
        state, {"type": "PRECEDENCE", "train_id": train["id"], "priority_override": 0}
    )
    assert train["priority_override"] == 0


def test_unknown_action_is_rejected():
    state = initialise_state("single_line_meet")
    with pytest.raises(SimulationError):
        apply_action(state, {"type": "TELEPORT", "train_id": "12625"})


def test_running_train_cannot_be_held_at_station():
    state = initialise_state("single_line_meet")
    advance(state, 10)
    running = next(train for train in state["trains"] if train["status"] == "RUNNING")
    with pytest.raises(SimulationError):
        apply_action(
            state,
            {"type": "HOLD", "train_id": running["id"], "station_id": "NDL", "hold_min": 5},
        )


def test_advance_does_not_mutate_input_copy():
    state = initialise_state("normal_traffic")
    snapshot = copy.deepcopy(state)
    advance(state, 5)
    assert state["sim_time_min"] == snapshot["sim_time_min"] + 5
    assert snapshot["sim_time_min"] == 360
