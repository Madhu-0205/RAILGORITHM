"""Independent constraint validation engine.

This module is deliberately separate from recommendation generation. It checks
hard operational constraints directly against the topology, the current state,
and a proposed schedule. No recommendation may be shown as executable unless
this validator returns VALIDATED or VALIDATED_WITH_ASSUMPTIONS.

Important limitation: constraint feasibility in this synthetic model does not
guarantee real-world railway safety.
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone
from itertools import combinations

from .conflicts import detect_conflicts
from .network import Network, TopologyError
from .projection import project_state
from .state import (
    advance,
    apply_action,
    format_minutes,
    platform_available,
    state_metrics,
    validate_state_integrity,
)

VALIDATED = "VALIDATED"
VALIDATED_WITH_ASSUMPTIONS = "VALIDATED_WITH_ASSUMPTIONS"
INVALID = "INVALID"
INCOMPLETE_DATA = "INCOMPLETE_DATA"
NO_FEASIBLE_SOLUTION = "NO_FEASIBLE_SOLUTION"

VALIDATOR_VERSION = "validator-1.0.0"
CONSTRAINT_CONFIG = {
    "block_exclusive": True,
    "minimum_headway_from_topology": True,
    "platform_capacity_from_topology": True,
    "directional_restrictions": True,
    "no_departure_before_timetable": True,
    "closures_respected": True,
    "dwell_time_respected": True,
    "max_hold_policy_min": "per train type (EXPRESS 20, PASSENGER 30, MEMU 25, FREIGHT 45)",
    "junction_throat_capacity": 2,
    "note": "Configured simulation assumptions, not verified Indian Railways rules.",
}


def _check(
    check_id: str,
    description: str,
    status: str,
    detail: str,
    *,
    hard: bool = True,
) -> dict:
    return {
        "id": check_id,
        "description": description,
        "status": status,  # PASS | FAIL | WARN
        "detail": detail,
        "hard": hard,
    }


def _result(
    status: str,
    checks: list[dict],
    *,
    assumptions: list[str] | None = None,
    violations: list[dict] | None = None,
    metadata: dict | None = None,
) -> dict:
    return {
        "status": status,
        "checks": checks,
        "assumptions": assumptions or [],
        "violations": violations or [],
        "validator_version": VALIDATOR_VERSION,
        "constraint_config": CONSTRAINT_CONFIG,
        "validated_at": datetime.now(timezone.utc).isoformat(),
        "metadata": metadata or {},
        "disclaimer": (
            "Constraint feasibility is evaluated against configured synthetic "
            "assumptions only. It does not certify real-world railway safety."
        ),
    }


def _trains_by_id(state: dict) -> dict[str, dict]:
    return {train["id"]: train for train in state["trains"]}


def validate_action(state: dict, action: dict) -> dict:
    problems = validate_state_integrity(state)
    if problems:
        return _result(
            INCOMPLETE_DATA,
            [_check("state_integrity", "Simulation state integrity", "FAIL", "; ".join(problems))],
            violations=[{"kind": "INCOMPLETE_DATA", "detail": problem} for problem in problems],
        )
    checks: list[dict] = []
    violations: list[dict] = []
    action_type = action.get("type")
    if action_type not in {"HOLD", "PRECEDENCE", "PLATFORM_REASSIGN", "SCHEDULE", "DO_NOTHING"}:
        return _result(
            INVALID,
            [_check("action_type", "Supported action type", "FAIL", f"Unsupported action '{action_type}'")],
            violations=[{"kind": "UNSUPPORTED_ACTION", "action_type": action_type}],
        )
    checks.append(_check("action_type", "Supported action type", "PASS", str(action_type)))
    trains = _trains_by_id(state)
    now = int(state["sim_time_min"])
    network = Network.from_dict(state["network"])

    if action_type == "HOLD":
        train_id = action.get("train_id")
        if train_id not in trains:
            return _result(
                INCOMPLETE_DATA,
                [_check("train_exists", "Target train exists", "FAIL", f"Unknown train '{train_id}'")],
            )
        train = trains[train_id]
        if train["status"] != "AT_STATION":
            checks.append(
                _check(
                    "hold_location",
                    "Hold only at a station",
                    "FAIL",
                    f"Train {train_id} is {train['status']}; it cannot be held at a station.",
                )
            )
        else:
            checks.append(_check("hold_location", "Hold only at a station", "PASS", train["station_id"]))
        hold_min = action.get("hold_min")
        if not isinstance(hold_min, int) or hold_min < 0:
            checks.append(_check("hold_duration", "Hold duration is a non-negative integer", "FAIL", str(hold_min)))
        elif hold_min > int(train["max_hold_min"]):
            checks.append(
                _check(
                    "hold_duration",
                    "Hold duration within configured policy",
                    "FAIL",
                    f"{hold_min} min exceeds {train['max_hold_min']} min for {train['train_type']}",
                )
            )
        else:
            checks.append(
                _check(
                    "hold_duration",
                    "Hold duration within configured policy",
                    "PASS",
                    f"{hold_min} min ≤ {train['max_hold_min']} min",
                )
            )
    elif action_type == "PRECEDENCE":
        train_id = action.get("train_id")
        if train_id not in trains:
            return _result(
                INCOMPLETE_DATA,
                [_check("train_exists", "Target train exists", "FAIL", f"Unknown train '{train_id}'")],
            )
        train = trains[train_id]
        if train["status"] == "COMPLETED":
            checks.append(_check("train_active", "Target train is active", "FAIL", "Train already completed"))
        else:
            checks.append(_check("train_active", "Target train is active", "PASS", train["status"]))
        override = action.get("priority_override", 0)
        if not isinstance(override, int) or not 0 <= override <= 9:
            checks.append(_check("priority_override", "Priority override valid", "FAIL", str(override)))
        else:
            checks.append(
                _check(
                    "priority_override",
                    "Priority override valid",
                    "PASS",
                    "Precedence changes departure ordering only; it cannot override block or platform safety.",
                )
            )
    elif action_type == "PLATFORM_REASSIGN":
        train_id = action.get("train_id")
        if train_id not in trains:
            return _result(
                INCOMPLETE_DATA,
                [_check("train_exists", "Target train exists", "FAIL", f"Unknown train '{train_id}'")],
            )
        train = trains[train_id]
        next_index = int(train["route_index"]) + 1
        if train["status"] == "RUNNING" and next_index < len(train["route"]):
            station_id = train["route"][next_index]
        elif train["status"] == "AT_STATION":
            station_id = train["station_id"]
        else:
            station_id = train["destination"]
        platform_id = action.get("platform_id")
        try:
            station = network.station(station_id)
        except TopologyError as exc:
            return _result(INCOMPLETE_DATA, [_check("station_exists", "Station exists", "FAIL", str(exc))])
        if platform_id not in station.platforms:
            checks.append(
                _check("platform_exists", "Requested platform exists", "FAIL", f"{platform_id} not at {station_id}")
            )
        else:
            checks.append(_check("platform_exists", "Requested platform exists", "PASS", f"{station_id}/{platform_id}"))
        at_min = now
        if not platform_available(state, station_id, platform_id, at_min):
            checks.append(
                _check("platform_outage", "Requested platform is not outaged", "FAIL", f"{station_id}/{platform_id} unavailable")
            )
        else:
            checks.append(_check("platform_outage", "Requested platform is not outaged", "PASS", f"{station_id}/{platform_id}"))
        occupancy = state["platform_occupancy"].get(station_id, {})
        current = occupancy.get(platform_id) if platform_id else None
        if current and current != train_id:
            checks.append(
                _check("platform_available", "Requested platform is not occupied", "FAIL", f"Occupied by {current}")
            )
        else:
            checks.append(_check("platform_available", "Requested platform is not occupied", "PASS", platform_id))
    elif action_type == "SCHEDULE":
        schedule_result = validate_schedule(state, action.get("schedule", action))
        return schedule_result

    hard_failures = [check for check in checks if check["status"] == "FAIL" and check["hard"]]
    warnings = [check for check in checks if check["status"] == "WARN"]
    status = INVALID if hard_failures else (VALIDATED_WITH_ASSUMPTIONS if warnings else VALIDATED)
    for check in checks:
        if check["status"] == "FAIL":
            violations.append({"kind": check["id"], "detail": check["detail"]})
    return _result(status, checks, violations=violations)


def _schedule_legs(schedule: dict) -> dict[str, list[dict]]:
    result: dict[str, list[dict]] = {}
    for train_id, payload in schedule.get("trains", {}).items():
        legs = payload.get("segments", [])
        result[train_id] = sorted(legs, key=lambda leg: leg["entry_min"])
    return result


def validate_schedule(state: dict, schedule: dict) -> dict:
    """Validate a proposed schedule (typically CP-SAT output)."""
    problems = validate_state_integrity(state)
    if problems:
        return _result(
            INCOMPLETE_DATA,
            [_check("state_integrity", "Simulation state integrity", "FAIL", "; ".join(problems))],
            violations=[{"kind": "INCOMPLETE_DATA", "detail": problem} for problem in problems],
        )
    solver_status = schedule.get("status")
    if solver_status in {"INFEASIBLE", "NO_FEASIBLE_SOLUTION"}:
        return _result(
            NO_FEASIBLE_SOLUTION,
            [_check("solver_status", "Optimizer produced a feasible schedule", "FAIL", f"Solver status: {solver_status}")],
            violations=[{"kind": "NO_FEASIBLE_SOLUTION", "detail": "No schedule satisfies the configured constraints."}],
        )
    if solver_status not in {"OPTIMAL", "FEASIBLE"}:
        return _result(
            INCOMPLETE_DATA,
            [_check("solver_status", "Optimizer produced a usable schedule", "FAIL", f"Solver status: {solver_status}")],
            violations=[{"kind": "SOLVER_INCOMPLETE", "detail": f"Solver status: {solver_status}"}],
        )

    network = Network.from_dict(state["network"])
    trains = _trains_by_id(state)
    now = int(state["sim_time_min"])
    legs_by_train = _schedule_legs(schedule)
    checks: list[dict] = []
    violations: list[dict] = []
    assumptions: list[str] = [
        "Schedule times are simulated clock minutes on the scenario date.",
        "Platform capacity uses configured platform counts minus active outages.",
        "Junction throat capacity is configured as two simultaneous movements.",
    ]

    active_ids = [train["id"] for train in state["trains"] if train["status"] != "COMPLETED"]
    missing = [train_id for train_id in active_ids if train_id not in legs_by_train]
    if missing:
        return _result(
            INCOMPLETE_DATA,
            [_check("train_coverage", "All active trains appear in the schedule", "FAIL", ", ".join(missing))],
            violations=[{"kind": "MISSING_TRAINS", "detail": missing}],
        )
    checks.append(_check("train_coverage", "All active trains appear in the schedule", "PASS", f"{len(active_ids)} trains"))

    block_windows: dict[str, list[dict]] = {}
    station_windows: dict[str, list[dict]] = {}
    for train_id, legs in legs_by_train.items():
        train = trains.get(train_id)
        if train is None:
            checks.append(_check("unknown_train", "Schedule references a known train", "FAIL", train_id))
            continue
        if not legs:
            if train["status"] != "COMPLETED":
                checks.append(_check(f"legs_{train_id}", "Train has scheduled movements", "FAIL", train_id))
            continue
        previous_exit: int | None = None
        for index, leg in enumerate(legs):
            try:
                section = network.section(leg["section_id"])
                block = next(item for item in section.blocks if item.id == leg["block_id"])
                entry = int(leg["entry_min"])
                exit_min = int(leg["exit_min"])
                run_min = int(leg.get("run_min", exit_min - entry))
            except (KeyError, StopIteration, TopologyError, TypeError) as exc:
                checks.append(
                    _check(
                        f"leg_{train_id}_{index}",
                        "Schedule leg references valid topology",
                        "FAIL",
                        f"{exc}",
                    )
                )
                continue
            if exit_min <= entry:
                checks.append(_check(f"leg_{train_id}_{index}", "Leg has positive duration", "FAIL", f"{entry}–{exit_min}"))
            if run_min < 1:
                checks.append(_check(f"leg_{train_id}_{index}", "Leg run time is positive", "FAIL", str(run_min)))
            if entry < now and not (index == 0 and train["status"] == "RUNNING"):
                checks.append(
                    _check(
                        f"leg_{train_id}_{index}",
                        "Schedule does not start in the past",
                        "FAIL",
                        f"Entry {format_minutes(entry)} is before simulation time {format_minutes(now)}",
                    )
                )
            if block.direction not in {train["direction"], "BIDIRECTIONAL"}:
                checks.append(
                    _check(
                        f"leg_{train_id}_{index}",
                        "Directional block restriction",
                        "FAIL",
                        f"{train_id} ({train['direction']}) cannot use {block.id} ({block.direction})",
                    )
                )
            if previous_exit is not None and entry < previous_exit:
                checks.append(
                    _check(
                        f"leg_{train_id}_{index}",
                        "Route continuity and dwell",
                        "FAIL",
                        f"Entry {format_minutes(entry)} before previous exit {format_minutes(previous_exit)}",
                    )
                )
            if previous_exit is not None and index > 0:
                extra_hold = entry - (previous_exit + int(train["dwell_min"]))
                if extra_hold > int(train["max_hold_min"]):
                    checks.append(
                        _check(
                            f"enroute_hold_{train_id}_{index}",
                            "En-route waiting policy",
                            "WARN",
                            f"{train_id} waits {extra_hold} min at {leg.get('from_station')}; "
                            f"policy guide is {train['max_hold_min']} min. Resource-driven waiting "
                            "is reported, not silently treated as a safety violation.",
                            hard=False,
                        )
                    )
            scheduled = None
            if index == 0 and train["status"] == "AT_STATION":
                scheduled = train["schedule"][train["route_index"]].get("departure_min")
            elif index == 0 and train["status"] == "RUNNING":
                scheduled = None
            else:
                route_index = int(train["route_index"]) + index
                if route_index < len(train["schedule"]):
                    scheduled = train["schedule"][route_index].get("departure_min")
            if scheduled is not None and entry < int(scheduled):
                checks.append(
                    _check(
                        f"leg_{train_id}_{index}",
                        "No departure before timetable",
                        "FAIL",
                        f"Entry {format_minutes(entry)} before scheduled {format_minutes(int(scheduled))}",
                    )
                )
            previous_exit = exit_min
            block_windows.setdefault(block.id, []).append(
                {
                    "train_id": train_id,
                    "block_id": block.id,
                    "entry_min": entry,
                    "exit_min": exit_min,
                    "direction": train["direction"],
                    "section_id": section.id,
                }
            )
            if index == 0:
                if train["status"] == "AT_STATION":
                    hold_min = entry - max(now, int(train.get("ready_departure_min") or now))
                    if hold_min > int(train["max_hold_min"]):
                        checks.append(
                            _check(
                                f"hold_policy_{train_id}",
                                "Configured maximum hold",
                                "FAIL",
                                f"First departure is held {hold_min} min; policy limit is "
                                f"{train['max_hold_min']} min for {train['train_type']}",
                            )
                        )
                    if train.get("platform"):
                        station_windows.setdefault(train["station_id"], []).append(
                            {
                                "train_id": train_id,
                                "station_id": train["station_id"],
                                "arrival_min": now,
                                "departure_min": entry,
                            }
                        )
            arrival = exit_min
            route_index = int(train["route_index"]) + index + 1
            if route_index < len(train["route"]):
                next_station = train["route"][route_index]
                departure = legs[index + 1]["entry_min"] if index + 1 < len(legs) else None
                station_windows.setdefault(next_station, []).append(
                    {
                        "train_id": train_id,
                        "station_id": next_station,
                        "arrival_min": arrival,
                        "departure_min": departure if departure is not None else arrival + 1,
                    }
                )
        final_leg = legs[-1]
        final_route_index = int(train["route_index"]) + len(legs) - 1
        if final_route_index + 1 < len(train["schedule"]):
            scheduled_final = train["schedule"][final_route_index + 1]["arrival_min"]
            final_delay = max(0, int(final_leg["exit_min"]) - int(scheduled_final))
            if final_delay > int(train["max_hold_min"]) + 20:
                checks.append(
                    _check(
                        f"max_delay_{train_id}",
                        "Configured delay policy",
                        "WARN",
                        f"{train_id} finishes {final_delay} min late; review operational policy.",
                        hard=False,
                    )
                )

    # Block headway and exclusivity.
    for block_id, windows in block_windows.items():
        section = next(
            section
            for section in network.sections
            if any(block.id == block_id for block in section.blocks)
        )
        for left, right in combinations(sorted(windows, key=lambda w: w["entry_min"]), 2):
            if left["train_id"] == right["train_id"]:
                continue
            if (
                left["exit_min"] + section.headway_min <= right["entry_min"]
                or right["exit_min"] + section.headway_min <= left["entry_min"]
            ):
                continue
            checks.append(
                _check(
                    f"block_{block_id}_{left['train_id']}_{right['train_id']}",
                    "Block exclusivity and headway",
                    "FAIL",
                    (
                        f"{left['train_id']} {format_minutes(left['entry_min'])}–{format_minutes(left['exit_min'])} "
                        f"and {right['train_id']} {format_minutes(right['entry_min'])}–{format_minutes(right['exit_min'])} "
                        f"on {block_id} violate {section.headway_min}-min headway"
                    ),
                )
            )

    # Closures.
    for block_id, windows in block_windows.items():
        for closure in state.get("closures", []):
            if closure["block_id"] != block_id:
                continue
            for window in windows:
                if closure["start_min"] < window["exit_min"] and window["entry_min"] < closure["end_min"]:
                    checks.append(
                        _check(
                            f"closure_{block_id}_{window['train_id']}",
                            "Closure respected",
                            "FAIL",
                            f"{window['train_id']} uses {block_id} during closure "
                            f"{format_minutes(closure['start_min'])}–{format_minutes(closure['end_min'])}",
                        )
                    )

    # Platform capacity.
    for station_id, windows in station_windows.items():
        station = network.station(station_id)
        events: list[tuple[int, int, str]] = []
        for window in windows:
            events.append((int(window["arrival_min"]), 1, window["train_id"]))
            events.append((int(window["departure_min"]), -1, window["train_id"]))
        events.sort(key=lambda event: (event[0], event[1]))
        active: set[str] = set()
        for time_min, delta, train_id in events:
            if delta == -1:
                active.discard(train_id)
                continue
            active.add(train_id)
            available = sum(
                1
                for platform in station.platforms
                if platform_available(state, station_id, platform, time_min)
            )
            if len(active) > available:
                checks.append(
                    _check(
                        f"platform_{station_id}_{time_min}",
                        "Platform capacity",
                        "FAIL",
                        f"{len(active)} trains require {station_id} at {format_minutes(time_min)}; "
                        f"{available} platforms available",
                    )
                )
                violations.append(
                    {
                        "kind": "PLATFORM_CAPACITY",
                        "station_id": station_id,
                        "time_min": time_min,
                        "trains": sorted(active),
                    }
                )

    # Junction throat capacity (configured as 2 simultaneous movements).
    for station in network.stations:
        if not station.is_junction:
            continue
        windows = station_windows.get(station.id, [])
        for left, right in combinations(sorted(windows, key=lambda w: w["arrival_min"]), 2):
            if left["train_id"] == right["train_id"]:
                continue
            if abs(left["arrival_min"] - right["arrival_min"]) < 1:
                checks.append(
                    _check(
                        f"junction_{station.id}_{left['train_id']}_{right['train_id']}",
                        "Junction throat capacity",
                        "WARN",
                        f"Simultaneous arrivals at {station.name} throat; verify interlocking.",
                        hard=False,
                    )
                )

    # Priority policy is soft and never replaces hard safety constraints.
    active_trains = [trains[train_id] for train_id in active_ids if train_id in trains]
    if len(active_trains) >= 2:
        delays = {}
        for train in active_trains:
            legs = legs_by_train.get(train["id"], [])
            if not legs:
                continue
            delays[train["id"]] = int(legs[-1]["exit_min"]) - int(
                train["schedule"][-1]["arrival_min"]
            )
        for high, low in combinations(active_trains, 2):
            if high["priority"] == low["priority"]:
                continue
            high_train, low_train = (high, low) if high["priority"] < low["priority"] else (low, high)
            high_delay = delays.get(high_train["id"], 0)
            low_delay = delays.get(low_train["id"], 0)
            if high_delay > low_delay + 10:
                checks.append(
                    _check(
                        f"priority_{high_train['id']}_{low_train['id']}",
                        "Priority policy consistency",
                        "WARN",
                        f"Higher-priority {high_train['id']} delayed more than {low_train['id']}",
                        hard=False,
                    )
                )

    hard_failures = [check for check in checks if check["status"] == "FAIL" and check["hard"]]
    warnings = [check for check in checks if check["status"] == "WARN"]
    status = INVALID if hard_failures else (VALIDATED_WITH_ASSUMPTIONS if warnings else VALIDATED)
    if hard_failures:
        for check in hard_failures:
            violations.append({"kind": check["id"], "detail": check["detail"]})
    return _result(status, checks, assumptions=assumptions, violations=violations, metadata={
        "objective_value": schedule.get("objective_value"),
        "solve_time_s": schedule.get("solve_time_s"),
    })


def validate_projected_state(
    state: dict, horizon_min: int = 75, *, strict_conflicts: bool = False
) -> dict:
    """Validate the current state's forward projection.

    With strict_conflicts=False (the default for candidate outcomes), predicted
    future conflicts are reported as warnings. They are operational problems to
    resolve, not proof that the current state is unsafe. Actual violations
    (duplicate occupancy, outaged platform occupancy, closure occupation) remain
    hard failures. Schedule validation always uses strict_conflicts=True.
    """
    problems = validate_state_integrity(state)
    if problems:
        return _result(
            INCOMPLETE_DATA,
            [_check("state_integrity", "Simulation state integrity", "FAIL", "; ".join(problems))],
        )
    projection = project_state(state, horizon_min)
    network = Network.from_dict(state["network"])
    checks: list[dict] = []
    now = int(state["sim_time_min"])

    block_windows: dict[str, list[dict]] = {}
    station_windows: dict[str, list[dict]] = {}
    for data in projection["trains"].values():
        for window in data["block_windows"]:
            block_windows.setdefault(window["block_id"], []).append(window)
        for window in data["station_windows"]:
            station_windows.setdefault(window["station_id"], []).append(window)

    for block_id, windows in block_windows.items():
        section = next(
            section
            for section in network.sections
            if any(block.id == block_id for block in section.blocks)
        )
        for left, right in combinations(sorted(windows, key=lambda w: w["entry_min"]), 2):
            if left["train_id"] == right["train_id"]:
                continue
            if (
                left["exit_min"] + section.headway_min <= right["entry_min"]
                or right["exit_min"] + section.headway_min <= left["entry_min"]
            ):
                continue
            checks.append(
                _check(
                    f"projected_block_{block_id}",
                    "Projected block exclusivity and headway",
                    "FAIL" if strict_conflicts else "WARN",
                    f"{left['train_id']} and {right['train_id']} overlap on {block_id}",
                    hard=strict_conflicts,
                )
            )
    for train_id, data in projection["trains"].items():
        for window in data["block_windows"]:
            for closure in state.get("closures", []):
                if (
                    closure["block_id"] == window["block_id"]
                    and closure["start_min"] < window["exit_min"]
                    and window["entry_min"] < closure["end_min"]
                ):
                    checks.append(
                        _check(
                            f"projected_closure_{train_id}",
                            "Projected closure compliance",
                            "FAIL" if strict_conflicts else "WARN",
                            f"{train_id} projected inside closed block {closure['block_id']}",
                            hard=strict_conflicts,
                        )
                    )

    for station_id, windows in station_windows.items():
        station = network.station(station_id)
        events: list[tuple[int, int, str]] = []
        for window in windows:
            if window.get("current") and window.get("platform") is None:
                continue
            events.append((int(window["arrival_min"]), 1, window["train_id"]))
            departure = window["departure_min"]
            if departure is None:
                departure = int(window["arrival_min"]) + 1
            events.append((int(departure), -1, window["train_id"]))
        events.sort(key=lambda event: (event[0], event[1]))
        active: set[str] = set()
        for time_min, delta, train_id in events:
            if delta == -1:
                active.discard(train_id)
                continue
            active.add(train_id)
            available = sum(
                1
                for platform in station.platforms
                if platform_available(state, station_id, platform, time_min)
            )
            if len(active) > available:
                checks.append(
                    _check(
                        f"projected_platform_{station_id}",
                        "Projected platform capacity",
                        "FAIL" if strict_conflicts else "WARN",
                        f"{len(active)} trains demand {station_id} at {format_minutes(time_min)}; "
                        f"{available} platforms available",
                        hard=strict_conflicts,
                    )
                )

    # Actual occupancy consistency.
    seen_blocks: set[str] = set()
    for block_id, occupancy in state.get("block_occupancy", {}).items():
        if occupancy.get("train_id"):
            if block_id in seen_blocks:
                checks.append(_check("occupancy_duplicate", "Block occupancy consistency", "FAIL", block_id))
            seen_blocks.add(block_id)
            for closure in state.get("closures", []):
                if (
                    closure["block_id"] == block_id
                    and closure["start_min"] <= now < closure["end_min"]
                ):
                    checks.append(
                        _check(
                            f"closure_occupied_{block_id}",
                            "Closure not occupied",
                            "FAIL",
                            f"{occupancy['train_id']} occupies closed block {block_id}",
                        )
                    )
    seen_platforms: set[tuple[str, str]] = set()
    for station_id, platforms in state.get("platform_occupancy", {}).items():
        for platform_id, train_id in platforms.items():
            if not train_id:
                continue
            key = (station_id, platform_id)
            if key in seen_platforms:
                checks.append(_check("platform_duplicate", "Platform occupancy consistency", "FAIL", str(key)))
            seen_platforms.add(key)
            if not platform_available(state, station_id, platform_id, now):
                checks.append(
                    _check(
                        "platform_on_outage",
                        "Platform outage respected",
                        "FAIL",
                        f"{train_id} occupies outaged {station_id}/{platform_id}",
                    )
                )

    hard_failures = [check for check in checks if check["status"] == "FAIL" and check["hard"]]
    warnings = [check for check in checks if check["status"] == "WARN"]
    status = INVALID if hard_failures else (VALIDATED_WITH_ASSUMPTIONS if warnings else VALIDATED)
    return _result(
        status,
        checks,
        violations=[{"kind": check["id"], "detail": check["detail"]} for check in hard_failures],
        assumptions=["Projection ignores future human decisions and other unmodelled perturbations."],
    )


def evaluate_candidate(
    state: dict,
    action: dict,
    minutes: int = 30,
    *,
    conflict_horizon_min: int | None = None,
) -> dict:
    """Apply an action to a clone, advance it, and independently validate.

    This is the evidence source for candidate comparisons. The original state is
    never modified.

    ``post_conflicts`` is detected on the post-action state *before* the clone is
    advanced, over ``conflict_horizon_min``. Detecting only after advancing would
    skip the first ``minutes`` of the window, which can hide a closure or block
    conflict that is still active when the action is applied.
    """
    clone = copy.deepcopy(state)
    try:
        apply_action(clone, action)
    except Exception as exc:  # noqa: BLE001 - invalid action must not crash the pipeline
        return {
            "status": INVALID,
            "validation": _result(
                INVALID,
                [_check("action_apply", "Action can be applied to the state", "FAIL", str(exc))],
                violations=[{"kind": "ACTION_APPLY_FAILED", "detail": str(exc)}],
            ),
            "metrics": None,
            "state": None,
            "post_conflicts": [],
            "simulation_minutes": minutes,
        }
    horizon = (
        int(conflict_horizon_min)
        if conflict_horizon_min is not None
        else max(15, 75 - minutes)
    )
    post_conflicts = detect_conflicts(clone, horizon)
    advance(clone, minutes)
    validation = validate_projected_state(
        clone, horizon_min=max(15, 75 - minutes), strict_conflicts=False
    )
    metrics = state_metrics(clone)
    return {
        "status": validation["status"],
        "validation": validation,
        "metrics": metrics,
        "state": clone,
        "post_conflicts": post_conflicts,
        "conflict_horizon_min": horizon,
        "simulation_minutes": minutes,
    }
