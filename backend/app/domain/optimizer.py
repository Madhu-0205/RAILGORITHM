"""Google OR-Tools CP-SAT scheduling optimizer.

The model schedules every active train's remaining legs. It enforces:
- block exclusivity and section headway,
- single-line directional ordering (via disjunctive constraints),
- platform capacity (cumulative) including configured outages,
- junction throat capacity,
- temporary block closures,
- no departure before the timetable,
- route continuity and dwell.

The optimizer returns a schedule and solver status. It never claims feasibility
when the solver reports INFEASIBLE/UNKNOWN; the independent validator re-checks
every returned schedule.
"""
from __future__ import annotations

import time
from typing import Any

from ortools.sat.python import cp_model

from ..config import settings
from .network import Network
from .spec import configured_objective_profile, objective_weights
from .state import format_minutes

OPTIMIZER_VERSION = "cpsat-2.0.0"

SOLVER_STATUS = {
    cp_model.OPTIMAL: "OPTIMAL",
    cp_model.FEASIBLE: "FEASIBLE",
    cp_model.INFEASIBLE: "INFEASIBLE",
    cp_model.UNKNOWN: "UNKNOWN",
    cp_model.MODEL_INVALID: "MODEL_INVALID",
}


def _available_capacity_min(state: dict, station_id: str, now: int, horizon: int) -> int:
    station = next(
        item for item in state["network"]["stations"] if item["id"] == station_id
    )
    minimum = len(station["platforms"])
    for sample in range(now, now + horizon + 1, 5):
        available = 0
        for platform in station["platforms"]:
            blocked = any(
                outage["station_id"] == station_id
                and outage["platform_id"] == platform
                and outage["start_min"] <= sample < outage["end_min"]
                for outage in state.get("platform_outages", [])
            )
            if not blocked:
                available += 1
        minimum = min(minimum, available)
    return minimum


def _build_legs(train: dict, now: int) -> tuple[list[dict], int]:
    """Build remaining movement legs and the first-departure release time."""
    route = train["route"]
    schedule = train["schedule"]
    route_index = int(train["route_index"])
    legs: list[dict] = []
    if train["status"] == "RUNNING":
        segment = schedule[route_index + 1]
        entry = int(train.get("entry_min") or now)
        exit_min = max(int(train.get("exit_min") or now), entry + 1)
        legs.append(
            {
                "from_station": route[route_index],
                "to_station": route[route_index + 1],
                "section_id": segment["section_id"],
                "block_id": segment["block_id"],
                "run_min": exit_min - entry,
                "scheduled_departure": None,
                "scheduled_arrival": segment["arrival_min"],
                "fixed_entry": entry,
                "fixed_exit": exit_min,
                "is_first": True,
            }
        )
        start_index = route_index + 1
        release = exit_min
    else:
        release = max(now, int(train.get("ready_departure_min") or now), int(train.get("hold_until_min") or 0))
        start_index = route_index
    for index in range(start_index, len(route) - 1):
        segment = schedule[index + 1]
        legs.append(
            {
                "from_station": route[index],
                "to_station": route[index + 1],
                "section_id": segment["section_id"],
                "block_id": segment["block_id"],
                "run_min": int(segment["run_from_previous_min"]),
                "scheduled_departure": schedule[index].get("departure_min"),
                "scheduled_arrival": segment["arrival_min"],
                "fixed_entry": None,
                "fixed_exit": None,
                "is_first": not legs,
            }
        )
    return legs, release


def _solver_status_name(status: int) -> str:
    return SOLVER_STATUS.get(status, f"UNKNOWN_{status}")


def optimise(
    state: dict,
    *,
    horizon_min: int | None = None,
    profile: str | None = None,
    weights: dict[str, int] | None = None,
    time_limit_s: float | None = None,
) -> dict:
    started = time.perf_counter()
    network = Network.from_dict(state["network"])
    now = int(state["sim_time_min"])
    horizon_min = horizon_min or settings.recommendation_horizon_min
    max_time = now + max(horizon_min + 180, 240)
    seed = int(state.get("seed", 0)) % (2**31 - 1)
    profile = profile or configured_objective_profile()
    weights = weights or objective_weights(profile)

    active_trains = [train for train in state["trains"] if train["status"] != "COMPLETED"]
    if not active_trains:
        return {
            "status": "FEASIBLE",
            "optimizer_version": OPTIMIZER_VERSION,
            "objective_value": 0,
            "objective_bound": 0,
            "is_optimal": True,
            "objective_profile": profile,
            "objective_weights": weights,
            "solve_time_s": 0.0,
            "horizon_min": horizon_min,
            "trains": {},
            "precedence": [],
            "message": "No active trains require scheduling.",
            "action": {"type": "DO_NOTHING"},
        }

    model = cp_model.CpModel()
    dep_vars: dict[tuple[str, int], Any] = {}
    arr_vars: dict[tuple[str, int], Any] = {}
    legs_by_train: dict[str, list[dict]] = {}
    releases: dict[str, int] = {}
    objective_terms: list[Any] = []
    final_delay_vars: dict[str, Any] = {}
    block_entries: dict[str, list[tuple[str, int, Any, Any]]] = {}
    station_intervals: dict[str, list[Any]] = {}
    station_demands: dict[str, list[int]] = {}

    for train in active_trains:
        train_id = train["id"]
        legs, release = _build_legs(train, now)
        if not legs:
            continue
        legs_by_train[train_id] = legs
        releases[train_id] = release
        previous_arr = None
        for index, leg in enumerate(legs):
            dep = model.NewIntVar(0, max_time, f"dep_{train_id}_{index}")
            arr = model.NewIntVar(0, max_time, f"arr_{train_id}_{index}")
            dep_vars[(train_id, index)] = dep
            arr_vars[(train_id, index)] = arr
            if leg["fixed_entry"] is not None:
                model.Add(dep == int(leg["fixed_entry"]))
                model.Add(arr == int(leg["fixed_exit"]))
            else:
                model.Add(arr == dep + int(leg["run_min"]))
                if index == 0:
                    model.Add(dep >= release)
                    if train["status"] == "AT_STATION":
                        model.Add(dep <= release + int(train["max_hold_min"]))
                else:
                    model.Add(dep >= previous_arr + int(train["dwell_min"]))
                if leg["scheduled_departure"] is not None:
                    model.Add(dep >= int(leg["scheduled_departure"]))
                else:
                    model.Add(dep >= now)
            if previous_arr is not None:
                model.Add(dep >= previous_arr + int(train["dwell_min"]))
            previous_arr = arr
            block_entries.setdefault(leg["block_id"], []).append((train_id, index, dep, arr))

            # Closures: either finish before the closure or start after it.
            for closure in state.get("closures", []):
                if closure["block_id"] != leg["block_id"]:
                    continue
                if closure["end_min"] <= now:
                    continue
                if closure["start_min"] <= now and closure["end_min"] >= max_time:
                    model.Add(0 == 1)
                    continue
                before = model.NewBoolVar(f"before_{train_id}_{index}_{closure['start_min']}")
                model.Add(arr <= int(closure["start_min"])).OnlyEnforceIf(before)
                model.Add(dep >= int(closure["end_min"])).OnlyEnforceIf(before.Not())

        # Station platform windows.
        if train["status"] == "AT_STATION" and train.get("platform"):
            first_dep = dep_vars[(train_id, 0)]
            current_duration = model.NewIntVar(
                0, max_time, f"currentsize_{train_id}_{train['station_id']}"
            )
            model.Add(current_duration == first_dep - now)
            interval = model.NewIntervalVar(
                now,
                current_duration,
                first_dep,
                f"station_{train_id}_{train['station_id']}_current",
            )
            station_intervals.setdefault(train["station_id"], []).append(interval)
            station_demands.setdefault(train["station_id"], []).append(1)
        for index, leg in enumerate(legs):
            arrival = arr_vars[(train_id, index)]
            if index + 1 < len(legs):
                departure = dep_vars[(train_id, index + 1)]
                size = model.NewIntVar(0, max_time, f"dwellsize_{train_id}_{index}")
                model.Add(size == departure - arrival)
            else:
                departure = arrival + 1
                size = 1
            interval = model.NewIntervalVar(
                arrival, size, departure, f"station_{train_id}_{leg['to_station']}_{index}"
            )
            station_intervals.setdefault(leg["to_station"], []).append(interval)
            station_demands.setdefault(leg["to_station"], []).append(1)

        final_arr = arr_vars[(train_id, len(legs) - 1)]
        scheduled_final = int(legs[-1]["scheduled_arrival"])
        delay = model.NewIntVar(0, max_time, f"delay_{train_id}")
        model.Add(delay >= final_arr - scheduled_final)
        model.Add(delay >= 0)
        final_delay_vars[train_id] = delay
        weight = max(1, 6 - int(train["priority"]))
        objective_terms.append(delay * weight * int(weights["final_delay"]))
        for index, leg in enumerate(legs):
            if leg["fixed_entry"] is None:
                scheduled_departure = leg["scheduled_departure"]
                if scheduled_departure is not None:
                    departure_delay = model.NewIntVar(0, max_time, f"depdelay_{train_id}_{index}")
                    model.Add(departure_delay >= dep_vars[(train_id, index)] - int(scheduled_departure))
                    objective_terms.append(
                        departure_delay * int(weights["departure_delay"])
                    )
        # Discourage holding beyond the first legal release.
        if legs and legs[0]["fixed_entry"] is None:
            hold_penalty = model.NewIntVar(0, max_time, f"hold_{train_id}")
            model.Add(hold_penalty >= dep_vars[(train_id, 0)] - release)
            model.Add(hold_penalty >= 0)
            objective_terms.append(hold_penalty * int(weights["hold"]))

    if not legs_by_train:
        return {
            "status": "FEASIBLE",
            "optimizer_version": OPTIMIZER_VERSION,
            "objective_value": 0,
            "objective_bound": 0,
            "is_optimal": True,
            "objective_profile": profile,
            "objective_weights": weights,
            "solve_time_s": round(time.perf_counter() - started, 3),
            "horizon_min": horizon_min,
            "trains": {},
            "precedence": [],
            "message": "No remaining movements to schedule.",
            "action": {"type": "DO_NOTHING"},
        }

    # Block disjunctions with headway.
    for block_id, entries in block_entries.items():
        section = next(
            section
            for section in network.sections
            if any(block.id == block_id for block in section.blocks)
        )
        for (train_a, index_a, dep_a, arr_a), (train_b, index_b, dep_b, arr_b) in (
            (entries[i], entries[j])
            for i in range(len(entries))
            for j in range(i + 1, len(entries))
        ):
            if train_a == train_b:
                continue
            order = model.NewBoolVar(f"order_{block_id}_{train_a}_{index_a}_{train_b}_{index_b}")
            model.Add(arr_a + section.headway_min <= dep_b).OnlyEnforceIf(order)
            model.Add(arr_b + section.headway_min <= dep_a).OnlyEnforceIf(order.Not())

    # Platform capacity.
    for station_id, intervals in station_intervals.items():
        capacity = _available_capacity_min(state, station_id, now, horizon_min + 180)
        if capacity <= 0:
            model.Add(0 == 1)
            continue
        model.AddCumulative(intervals, station_demands[station_id], capacity)

    # Junction throat capacity: configured as two simultaneous movements.
    for station in network.stations:
        if not station.is_junction:
            continue
        throat_intervals: list[Any] = []
        for train_id, legs in legs_by_train.items():
            for index, leg in enumerate(legs):
                if leg["to_station"] != station.id:
                    continue
                arrival = arr_vars[(train_id, index)]
                throat_intervals.append(
                    model.NewIntervalVar(
                        arrival, 2, arrival + 2, f"throat_{station.id}_{train_id}_{index}"
                    )
                )
        if throat_intervals:
            model.AddCumulative(
                throat_intervals,
                [1] * len(throat_intervals),
                max(1, int(station.junction_throat_capacity)),
            )

    model.Minimize(sum(objective_terms) if objective_terms else 0)

    model_error = model.Validate()
    if model_error:
        return {
            "status": "MODEL_INVALID",
            "optimizer_version": OPTIMIZER_VERSION,
            "objective_value": None,
            "objective_bound": None,
            "is_optimal": False,
            "objective_profile": profile,
            "objective_weights": weights,
            "solve_time_s": round(time.perf_counter() - started, 3),
            "horizon_min": horizon_min,
            "trains": {},
            "precedence": [],
            "message": f"CP-SAT model validation failed: {model_error}",
            "action": None,
        }

    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = (
        float(time_limit_s) if time_limit_s is not None else settings.cp_sat_time_limit_s
    )
    solver.parameters.num_search_workers = settings.cp_sat_workers
    solver.parameters.random_seed = seed
    response_status = solver.Solve(model)
    status_name = _solver_status_name(response_status)
    solve_time = round(time.perf_counter() - started, 3)

    if status_name not in {"OPTIMAL", "FEASIBLE"}:
        message = (
            "No feasible schedule was found for the configured constraints. "
            "The system does not fabricate a feasible alternative."
            if status_name == "INFEASIBLE"
            else f"Solver did not reach a usable solution (status {status_name})."
        )
        return {
            "status": status_name,
            "optimizer_version": OPTIMIZER_VERSION,
            "objective_value": None,
            "objective_bound": None,
            "is_optimal": False,
            "objective_profile": profile,
            "objective_weights": weights,
            "solve_time_s": solve_time,
            "horizon_min": horizon_min,
            "trains": {},
            "precedence": [],
            "message": message,
            "action": None,
        }

    trains_payload: dict[str, dict] = {}
    precedence: list[dict] = []
    block_orders: dict[str, list[tuple[int, str]]] = {}
    for train in active_trains:
        train_id = train["id"]
        legs = legs_by_train.get(train_id)
        if not legs:
            continue
        segments = []
        for index, leg in enumerate(legs):
            entry = int(solver.Value(dep_vars[(train_id, index)]))
            exit_min = int(solver.Value(arr_vars[(train_id, index)]))
            segments.append(
                {
                    "section_id": leg["section_id"],
                    "block_id": leg["block_id"],
                    "entry_min": entry,
                    "exit_min": exit_min,
                    "run_min": exit_min - entry,
                    "from_station": leg["from_station"],
                    "to_station": leg["to_station"],
                }
            )
            block_orders.setdefault(leg["block_id"], []).append((entry, train_id))
        station_windows = []
        if train["status"] == "AT_STATION":
            station_windows.append(
                {
                    "station_id": train["station_id"],
                    "arrival_min": now,
                    "departure_min": segments[0]["entry_min"],
                }
            )
        for index, leg in enumerate(legs):
            departure = segments[index + 1]["entry_min"] if index + 1 < len(segments) else segments[index]["exit_min"] + 1
            station_windows.append(
                {
                    "station_id": leg["to_station"],
                    "arrival_min": segments[index]["exit_min"],
                    "departure_min": departure,
                }
            )
        release = releases[train_id]
        first_dep = segments[0]["entry_min"]
        hold_min = max(0, first_dep - release)
        final_arrival = segments[-1]["exit_min"]
        scheduled_final = int(train["schedule"][-1]["arrival_min"])
        trains_payload[train_id] = {
            "segments": segments,
            "station_windows": station_windows,
            "final_arrival_min": final_arrival,
            "final_delay_min": max(0, final_arrival - scheduled_final),
            "hold_min": hold_min,
            "release_min": release,
            "weighted_delay": max(0, final_arrival - scheduled_final) * max(1, 6 - int(train["priority"])),
            "status": train["status"],
        }

    for block_id, entries in block_orders.items():
        entries.sort()
        ordered = [train_id for _, train_id in entries]
        if len(ordered) > 1:
            precedence.append({"block_id": block_id, "order": ordered})

    schedule = {
        "status": status_name,
        "optimizer_version": OPTIMIZER_VERSION,
        # ObjectiveValue() is the value of the returned solution for both
        # OPTIMAL and FEASIBLE. BestObjectiveBound() is a bound, not the
        # achieved objective, and must not be reported as the objective.
        "objective_value": float(solver.ObjectiveValue()),
        "objective_bound": float(solver.BestObjectiveBound()),
        "is_optimal": status_name == "OPTIMAL",
        "objective_profile": profile,
        "objective_weights": weights,
        "solve_time_s": solve_time,
        "horizon_min": horizon_min,
        "trains": trains_payload,
        "precedence": precedence,
        "message": "Feasible schedule returned by CP-SAT.",
        "solver": {
            "name": "Google OR-Tools CP-SAT",
            "version": getattr(__import__("ortools"), "__version__", "unknown"),
            "status": status_name,
            "wall_time_s": solver.WallTime(),
            "branches": solver.NumBranches(),
            "conflicts": solver.NumConflicts(),
        },
    }

    holds = []
    for train in active_trains:
        payload = trains_payload.get(train["id"])
        if not payload:
            continue
        if train["status"] == "AT_STATION" and payload["hold_min"] > 0:
            holds.append(
                {
                    "train_id": train["id"],
                    "station_id": train["station_id"],
                    "hold_min": int(payload["hold_min"]),
                    "until_min": int(payload["segments"][0]["entry_min"]),
                    "until": format_minutes(payload["segments"][0]["entry_min"]),
                    "scope": "CURRENT",
                }
            )
        segments = payload["segments"]
        for index in range(1, len(segments)):
            previous_arrival = int(segments[index - 1]["exit_min"])
            departure = int(segments[index]["entry_min"])
            extra_hold = departure - (previous_arrival + int(train["dwell_min"]))
            if extra_hold > 0:
                holds.append(
                    {
                        "train_id": train["id"],
                        "station_id": segments[index]["from_station"],
                        "hold_min": int(extra_hold),
                        "until_min": departure,
                        "until": format_minutes(departure),
                        "scope": "EN_ROUTE",
                    }
                )
    precedence_list: list[str] = []
    for item in precedence:
        for train_id in item["order"]:
            if train_id not in precedence_list:
                precedence_list.append(train_id)
    action = {
        "type": "SCHEDULE",
        "source": "CP_SAT",
        "holds": holds,
        "precedence": precedence_list,
        "schedule": schedule,
    }
    return {**schedule, "action": action}


def optimise_alternatives(
    state: dict,
    *,
    horizon_min: int | None = None,
    time_limit_s: float | None = None,
    profiles: tuple[str, ...] = (
        "balanced",
        "delay_focused",
        "priority_focused",
        "throughput_focused",
    ),
) -> list[dict]:
    """Solve the same model under several documented objective profiles.

    These are genuinely distinct feasible schedules where the solver finds
    them. They are *not* claimed to be globally optimal for the dispatcher's
    real objective, and every returned schedule still requires independent
    validation. The pipeline uses this only for comparison/reporting, never to
    silently replace the balanced recommendation.
    """
    results: list[dict] = []
    for profile in profiles:
        result = optimise(
            state,
            horizon_min=horizon_min,
            profile=profile,
            time_limit_s=time_limit_s,
        )
        results.append(
            {
                "profile": profile,
                "status": result.get("status"),
                "is_optimal": result.get("is_optimal", False),
                "objective_value": result.get("objective_value"),
                "objective_bound": result.get("objective_bound"),
                "objective_weights": result.get("objective_weights"),
                "solve_time_s": result.get("solve_time_s"),
                "schedule": result,
            }
        )
    return results
