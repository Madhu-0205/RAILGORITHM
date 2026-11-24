"""CP-SAT scheduling optimizer."""
from __future__ import annotations

from app.domain.optimizer import OPTIMIZER_VERSION, optimise
from app.domain.state import advance, initialise_state


def test_optimizer_solves_single_line_meet():
    state = initialise_state("single_line_meet")
    advance(state, 2)
    result = optimise(state, horizon_min=75)
    assert result["status"] in {"OPTIMAL", "FEASIBLE"}
    assert result["optimizer_version"] == OPTIMIZER_VERSION
    assert result["objective_value"] is not None
    assert result["trains"]
    assert result["action"]["type"] == "SCHEDULE"


def test_optimizer_respects_single_line_ordering():
    state = initialise_state("single_line_meet")
    advance(state, 2)
    result = optimise(state, horizon_min=75)
    windows = []
    for payload in result["trains"].values():
        for segment in payload["segments"]:
            if segment["block_id"] == "B3":
                windows.append((segment["entry_min"], segment["exit_min"]))
    windows.sort()
    for (_, first_exit), (second_entry, _) in zip(windows, windows[1:]):
        assert second_entry >= first_exit, "single-line block windows overlap"


def test_optimizer_reports_infeasible_without_fabricating():
    state = initialise_state("no_feasible_schedule")
    advance(state, 2)
    result = optimise(state, horizon_min=75)
    assert result["status"] in {"INFEASIBLE", "MODEL_INVALID"}
    assert result["action"] is None
    assert result["trains"] == {}


def test_optimizer_is_deterministic_with_one_worker():
    first = initialise_state("delayed_express")
    second = initialise_state("delayed_express")
    advance(first, 5)
    advance(second, 5)
    result_a = optimise(first, horizon_min=60)
    result_b = optimise(second, horizon_min=60)
    assert result_a["objective_value"] == result_b["objective_value"]
    assert {
        key: value["final_arrival_min"] for key, value in result_a["trains"].items()
    } == {key: value["final_arrival_min"] for key, value in result_b["trains"].items()}


def test_optimizer_output_contains_action_and_schedule():
    state = initialise_state("normal_traffic")
    advance(state, 2)
    result = optimise(state, horizon_min=45)
    assert result["status"] in {"OPTIMAL", "FEASIBLE"}
    action = result["action"]
    assert action["type"] == "SCHEDULE"
    assert action["schedule"]["status"] == result["status"]
    assert isinstance(action["holds"], list)
    assert isinstance(action["precedence"], list)
    assert result["horizon_min"] == 45
