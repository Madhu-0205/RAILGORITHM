"""Synthetic scenario catalogue and deterministic timetable construction."""
from __future__ import annotations

import pytest

from app.domain.scenarios import SCENARIOS, build_scenario, scenario_catalogue
from app.domain.state import initialise_state


EXPECTED_KEYS = {
    "normal_traffic",
    "evening_peak",
    "single_line_meet",
    "delayed_express",
    "block_closure",
    "platform_outage",
    "priority_train",
    "no_feasible_schedule",
}


def test_catalogue_contains_required_scenarios():
    catalogue = scenario_catalogue()
    assert {entry["key"] for entry in catalogue} == EXPECTED_KEYS
    assert all(entry["label"] == "SYNTHETIC" for entry in catalogue)
    assert all(entry["train_count"] > 0 for entry in catalogue)


def test_scenario_keys_are_unique():
    keys = [scenario.key for scenario in SCENARIOS]
    assert len(keys) == len(set(keys))


def test_build_scenario_is_deterministic():
    first = build_scenario("evening_peak")
    second = build_scenario("evening_peak")
    assert first["network"] == second["network"]
    assert first["trains"] == second["trains"]


def test_seed_override_is_reproducible():
    first = initialise_state("evening_peak", seed_override=123)
    second = initialise_state("evening_peak", seed_override=123)
    assert first["seed"] == 123
    assert [train["id"] for train in first["trains"]] == [
        train["id"] for train in second["trains"]
    ]


def test_unknown_scenario_raises():
    with pytest.raises(KeyError):
        build_scenario("does_not_exist")


@pytest.mark.parametrize("key", sorted(EXPECTED_KEYS))
def test_every_scenario_initialises_cleanly(key: str):
    state = initialise_state(key)
    assert state["status"] == "RUNNING"
    assert state["sim_time_min"] == state["start_time_min"]
    assert state["version"] == 1
    assert state["network"]["sections"]
    assert len(state["trains"]) > 0
    for train in state["trains"]:
        assert train["route"][0] == train["origin"]
        assert train["route"][-1] == train["destination"]
        assert len(train["schedule"]) == len(train["route"])
        assert train["schedule"][0]["departure_min"] is not None
        assert train["schedule"][-1]["arrival_min"] is not None


def test_priority_train_departs_at_scenario_start():
    state = initialise_state("priority_train")
    freight = next(train for train in state["trains"] if train["id"] == "FRT-704")
    assert freight["scheduled_departure_min"] >= state["start_time_min"]
