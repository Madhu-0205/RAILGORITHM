"""Adversarial stress and boundary tests for CP-SAT and independent validator.

Covers:
- multiple simultaneous conflicts
- resource contention (single-line bottleneck, station throat)
- insufficient headway enforcement and validation
- platform capacity and outage handling
- junction capacity (cumulative throat limit)
- maintenance closures
- honest infeasibility reporting
- solver timeout handling
- multi-profile objective audit
- validator independence (tampered schedules rejected unconditionally)
"""
from __future__ import annotations

import copy
import pytest

from app.domain.optimizer import optimise, optimise_alternatives
from app.domain.state import initialise_state, advance
from app.domain.validator import validate_schedule, VALIDATED, INVALID, NO_FEASIBLE_SOLUTION
from app.domain.conflicts import detect_conflicts


def test_adversarial_timeout_handling():
    """When the solver time limit is microscopic, it must report timeout honestly without claiming optimality."""
    state = initialise_state("evening_peak")
    advance(state, 5)
    # 1 microsecond limit forces timeout
    result = optimise(state, horizon_min=75, time_limit_s=0.000001)
    assert result["status"] in {"FEASIBLE", "UNKNOWN", "MODEL_INVALID"}
    if result["status"] == "UNKNOWN":
        assert result["is_optimal"] is False
        assert result["action"] is None
        assert result["trains"] == {}
    elif result["status"] == "FEASIBLE":
        # If it managed to find a feasible solution in that time, it must not claim optimality
        assert result["is_optimal"] is False


def test_adversarial_infeasible_schedule_never_produces_action():
    """Infeasible scenarios must report INFEASIBLE and produce no executable action."""
    state = initialise_state("no_feasible_schedule")
    advance(state, 5)
    result = optimise(state, horizon_min=75)
    assert result["status"] == "INFEASIBLE"
    assert result["is_optimal"] is False
    assert result["objective_value"] is None
    assert result["action"] is None
    # Independent validator on infeasible result
    val = validate_schedule(state, result)
    assert val["status"] == NO_FEASIBLE_SOLUTION
    assert val["violations"]


def test_adversarial_all_four_objective_profiles():
    """All 4 documented objective profiles solve cleanly and produce validated schedules on feasible traffic."""
    state = initialise_state("evening_peak")
    advance(state, 5)
    alternatives = optimise_alternatives(state, horizon_min=75)
    assert len(alternatives) == 4
    profiles = {item["profile"] for item in alternatives}
    assert profiles == {"balanced", "delay_focused", "priority_focused", "throughput_focused"}
    for alt in alternatives:
        assert alt["status"] in {"OPTIMAL", "FEASIBLE"}
        sched = alt["schedule"]
        assert sched["objective_value"] is not None
        assert sched["objective_bound"] is not None
        if sched["status"] == "OPTIMAL":
            assert sched["is_optimal"] is True
            assert sched["objective_value"] >= sched["objective_bound"] - 1e-6
        # Independent validation
        val = validate_schedule(state, sched)
        assert val["status"] in {VALIDATED, "VALIDATED_WITH_ASSUMPTIONS"}


def test_validator_detects_tampered_headway_violation():
    """If a schedule tampers with entry times violating minimum headway, the validator must fail it."""
    state = initialise_state("single_line_meet")
    advance(state, 2)
    result = optimise(state, horizon_min=75)
    assert result["status"] in {"OPTIMAL", "FEASIBLE"}

    # Tamper with schedule: force second train on B3 to enter with 1 minute headway instead of required 4
    tampered = copy.deepcopy(result)
    b3_segments = []
    for train_id, payload in tampered["trains"].items():
        for seg in payload["segments"]:
            if seg["block_id"] == "B3":
                b3_segments.append(seg)
    assert len(b3_segments) == 2
    b3_segments.sort(key=lambda s: s["entry_min"])
    # Force overlap
    b3_segments[1]["entry_min"] = b3_segments[0]["entry_min"] + 1
    b3_segments[1]["exit_min"] = b3_segments[0]["exit_min"] + 1

    val = validate_schedule(state, tampered)
    assert val["status"] == INVALID
    details = [v.get("detail", "") for v in val["violations"]] + [v.get("kind", "") for v in val["violations"]]
    assert any("headway" in d.lower() or "block" in d.lower() for d in details)


def test_validator_detects_tampered_platform_overflow():
    """If a schedule assigns more trains to a station than available platforms, validator must reject it."""
    state = initialise_state("platform_outage")
    advance(state, 5)
    result = optimise(state, horizon_min=75)
    assert result["status"] in {"OPTIMAL", "FEASIBLE"}

    tampered = copy.deepcopy(result)
    # Station MLG has 3 platforms, but P2 has an outage, leaving 2 platforms available.
    # Force 3 trains to dwell concurrently at MLG between minutes 30 and 45.
    for i, (train_id, payload) in enumerate(tampered["trains"].items()):
        for leg in payload["segments"]:
            if leg.get("to_station") == "MLG":
                leg["exit_min"] = 30
            if leg.get("from_station") == "MLG":
                leg["entry_min"] = 45

    val = validate_schedule(state, tampered)
    assert val["status"] == INVALID
    assert any("platform" in v["kind"] for v in val["violations"])


def test_validator_detects_closure_encroachment():
    """If a schedule routes a train through a closed block during the closure window, validator must reject it."""
    state = initialise_state("block_closure")
    advance(state, 5)
    result = optimise(state, horizon_min=75)
    assert result["status"] in {"OPTIMAL", "FEASIBLE"}

    closure = state["closures"][0]
    tampered = copy.deepcopy(result)
    # Find a train and force its segment into the closure window on closed block
    for train_id, payload in tampered["trains"].items():
        for seg in payload["segments"]:
            if seg["block_id"] == closure["block_id"]:
                seg["entry_min"] = closure["start_min"] + 5
                seg["exit_min"] = closure["start_min"] + 20

    val = validate_schedule(state, tampered)
    assert val["status"] == INVALID
    assert any("closure" in v["kind"] for v in val["violations"])


def test_validator_detects_tampered_junction_throat_overflow():
    """If a schedule forces concurrent movements exceeding throat capacity at MLG, validator must reject it."""
    state = initialise_state("junction_congestion")
    advance(state, 5)
    result = optimise(state, horizon_min=75)
    assert result["status"] in {"OPTIMAL", "FEASIBLE"}

    # MLG throat capacity is 2 concurrent movements
    tampered = copy.deepcopy(result)
    arrivals = 0
    for train_id, payload in tampered["trains"].items():
        for seg in payload["segments"]:
            if seg.get("to_station") == "MLG":
                seg["exit_min"] = 390
                seg["entry_min"] = 380
                arrivals += 1
                if arrivals >= 3:
                    break
        if arrivals >= 3:
            break
    assert arrivals >= 3, "Expected at least 3 trains arriving at MLG in junction_congestion"

    val = validate_schedule(state, tampered)
    assert val["status"] == INVALID
    details = [v.get("detail", "") for v in val["violations"]] + [v.get("kind", "") for v in val["violations"]]
    assert any("throat" in d.lower() or "junction" in d.lower() for d in details)


def test_multiple_simultaneous_conflicts_stress():
    """Under time-varying traffic surge with multiple overlapping conflicts, CP-SAT finds a validated schedule."""
    state = initialise_state("time_varying_demand")
    advance(state, 10)
    conflicts = detect_conflicts(state)
    assert len(conflicts) >= 3

    result = optimise(state, horizon_min=75)
    assert result["status"] in {"OPTIMAL", "FEASIBLE"}
    val = validate_schedule(state, result)
    assert val["status"] in {VALIDATED, "VALIDATED_WITH_ASSUMPTIONS"}
