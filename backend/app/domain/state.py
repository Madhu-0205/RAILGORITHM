"""Deterministic railway traffic simulation engine.

The engine advances a synthetic timetable minute by minute. It enforces
resource exclusivity (blocks and platforms), closures, dwell and priority
ordering. It is deliberately separate from the recommendation logic: the
validator can re-check any proposed schedule without trusting this module.

Units: all times are integer minutes since 00:00 on the scenario date.
"""
from __future__ import annotations

import copy
from typing import Any

from .network import Network
from .scenarios import build_scenario


class SimulationError(ValueError):
    """Raised when a simulation transition is invalid."""


def format_minutes(value: int | float | None) -> str | None:
    if value is None:
        return None
    total = int(round(value))
    return f"{total // 60:02d}:{total % 60:02d}"


def parse_minutes(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def label_for_minute(value: int) -> str:
    return format_minutes(value) or ""


def _assign_platform(
    state: dict, station_id: str, train_id: str, preferred: str | None = None
) -> str | None:
    station = next(
        item for item in state["network"]["stations"] if item["id"] == station_id
    )
    occupancy = state["platform_occupancy"].setdefault(station_id, {})
    available = [
        platform
        for platform in station["platforms"]
        if occupancy.get(platform) is None
        and platform_available(state, station_id, platform, state["sim_time_min"])
    ]
    if preferred and preferred in available:
        chosen = preferred
    elif available:
        chosen = available[0]
    else:
        return None
    occupancy[chosen] = train_id
    return chosen


def platform_available(state: dict, station_id: str, platform_id: str, at_min: int) -> bool:
    for outage in state.get("platform_outages", []):
        if (
            outage["station_id"] == station_id
            and outage["platform_id"] == platform_id
            and outage["start_min"] <= at_min < outage["end_min"]
        ):
            return False
    return True


def block_closure_at(state: dict, block_id: str, at_min: int) -> dict | None:
    for closure in state.get("closures", []):
        if (
            closure["block_id"] == block_id
            and closure["start_min"] <= at_min < closure["end_min"]
        ):
            return closure
    return None


def block_closure_overlapping(
    state: dict, block_id: str, start_min: int, end_min: int
) -> dict | None:
    for closure in state.get("closures", []):
        if (
            closure["block_id"] == block_id
            and closure["start_min"] < end_min
            and start_min < closure["end_min"]
        ):
            return closure
    return None


def _append_event(state: dict, event_type: str, message: str, **data: Any) -> None:
    event = {
        "time_min": state["sim_time_min"],
        "time": format_minutes(state["sim_time_min"]),
        "type": event_type,
        "message": message,
        **data,
    }
    state["events"].append(event)
    if len(state["events"]) > 600:
        state["events"] = state["events"][-600:]


def _train(state: dict, train_id: str) -> dict:
    for train in state["trains"]:
        if train["id"] == train_id:
            return train
    raise SimulationError(f"Unknown train '{train_id}'")


def _available_platform_count(state: dict, station_id: str, at_min: int) -> int:
    station = next(
        item for item in state["network"]["stations"] if item["id"] == station_id
    )
    return sum(
        1
        for platform in station["platforms"]
        if platform_available(state, station_id, platform, at_min)
    )


def initialise_state(scenario_key: str, *, seed_override: int | None = None) -> dict:
    scenario = build_scenario(scenario_key)
    network = Network.from_dict(scenario["network"])
    start = scenario["start_time_min"]
    state: dict = {
        "scenario_key": scenario["scenario_key"],
        "scenario_name": scenario["scenario_name"],
        "description": scenario["description"],
        "service_pattern": scenario.get("service_pattern", "MIXED"),
        "tags": list(scenario.get("tags", [])),
        "label": "SYNTHETIC",
        "network": scenario["network"],
        "start_time_min": start,
        "sim_time_min": start,
        "horizon_end_min": start + 180,
        "seed": int(seed_override if seed_override is not None else scenario["seed"]),
        "status": "RUNNING",
        "version": 1,
        "trains": [],
        "closures": copy.deepcopy(scenario["closures"]),
        "platform_outages": copy.deepcopy(scenario["platform_outages"]),
        "speed_restrictions": copy.deepcopy(scenario.get("speed_restrictions", [])),
        "disruptions": copy.deepcopy(scenario.get("disruptions", [])),
        "block_occupancy": {},
        "platform_occupancy": {},
        "counters": {
            "block_busy_min": {},
            "platform_busy_min": {},
            "completed": 0,
            "departures": 0,
            "arrivals": 0,
            "waiting_min": 0,
            "conflicts_detected": 0,
            "recommendations_generated": 0,
        },
        "events": [],
    }
    for raw_train in scenario["trains"]:
        train = copy.deepcopy(raw_train)
        train.update(
            {
                "status": "AT_STATION",
                "route_index": 0,
                "station_id": train["origin"],
                "section_id": None,
                "block_id": None,
                "entry_min": None,
                "exit_min": None,
                "platform": None,
                "actual_arrivals": {},
                "actual_departures": {},
                "ready_departure_min": max(
                    start, train["scheduled_departure_min"] + train["initial_delay_min"]
                ),
                "delay_min": train["initial_delay_min"],
                "hold_until_min": 0,
                "priority_override": None,
                "planned_holds": {},
                "waiting_reason": (
                    "INITIAL_DELAY" if train["initial_delay_min"] else "READY"
                ),
                "completed_at_min": None,
                "total_wait_min": 0,
                "platform_preference": None,
                "label": "SYNTHETIC",
            }
        )
        train["platform"] = _assign_platform(state, train["station_id"], train["id"])
        if train["platform"] is None:
            train["waiting_reason"] = "PLATFORM_UNAVAILABLE"
        state["trains"].append(train)
    _append_event(
        state,
        "SIMULATION_CREATED",
        f"Synthetic scenario '{scenario['scenario_name']}' initialised at "
        f"{format_minutes(start)} with {len(state['trains'])} trains.",
        scenario_key=scenario_key,
        seed=state["seed"],
    )
    state["counters"]["platform_busy_min"] = {
        station["id"]: {platform: 0 for platform in station["platforms"]}
        for station in state["network"]["stations"]
    }
    state["counters"]["block_busy_min"] = {
        block["id"]: 0
        for section in state["network"]["sections"]
        for block in section["blocks"]
    }
    return state


def _effective_priority(train: dict) -> int:
    override = train.get("priority_override")
    return int(override) if override is not None else int(train["priority"])


def _run_minutes(train: dict, route_index: int) -> int:
    return int(train["schedule"][route_index + 1]["run_from_previous_min"])


def _next_segment(train: dict) -> tuple[str, str, str, int] | None:
    """Return (section_id, block_id, direction, run_min) for the next movement."""
    next_index = int(train["route_index"]) + 1
    if next_index >= len(train["route"]):
        return None
    segment = train["schedule"][next_index]
    return (
        segment["section_id"],
        segment["block_id"],
        train["direction"],
        int(segment["run_from_previous_min"]),
    )


def _can_use_block(state: dict, block_id: str, direction: str, at_min: int, run_min: int) -> tuple[bool, str]:
    occupancy = state["block_occupancy"].get(block_id)
    if occupancy and occupancy.get("train_id"):
        return False, "BLOCK_OCCUPIED"
    if block_closure_overlapping(state, block_id, at_min, at_min + run_min):
        return False, "BLOCK_CLOSED"
    return True, "AVAILABLE"


def _free_platform(state: dict, train: dict) -> None:
    station_id = train.get("station_id")
    platform = train.get("platform")
    if station_id and platform:
        occupancy = state["platform_occupancy"].get(station_id, {})
        if occupancy.get(platform) == train["id"]:
            occupancy[platform] = None
    train["platform"] = None


def _handle_arrivals(state: dict) -> None:
    now = state["sim_time_min"]
    for train in sorted(state["trains"], key=lambda item: _effective_priority(item)):
        if train["status"] != "RUNNING":
            continue
        exit_min = train.get("exit_min")
        if exit_min is None or now < exit_min:
            continue
        block_id = train.get("block_id")
        if block_id and state["block_occupancy"].get(block_id, {}).get("train_id") == train["id"]:
            state["block_occupancy"][block_id] = {}
        next_index = int(train["route_index"]) + 1
        station_id = train["route"][next_index]
        platform = _assign_platform(
            state, station_id, train["id"], train.get("platform_preference")
        )
        if platform is None:
            # No platform available: remain in the block and retry next minute.
            train["waiting_reason"] = "PLATFORM_UNAVAILABLE"
            train["exit_min"] = now + 1
            train["delay_min"] = max(0, now + 1 - int(train["schedule"][next_index]["arrival_min"]))
            if block_id:
                state["block_occupancy"][block_id] = {
                    "train_id": train["id"],
                    "direction": train["direction"],
                    "entry_min": train.get("entry_min"),
                    "exit_min": now + 1,
                }
            continue
        train["route_index"] = next_index
        train["station_id"] = station_id
        train["platform"] = platform
        train["status"] = "AT_STATION"
        train["section_id"] = None
        train["block_id"] = None
        train["entry_min"] = None
        train["exit_min"] = None
        train["actual_arrivals"][station_id] = now
        state["counters"]["arrivals"] += 1
        scheduled_arrival = train["schedule"][next_index]["arrival_min"]
        train["delay_min"] = max(0, now - int(scheduled_arrival))
        train["waiting_reason"] = "READY"
        if station_id == train["destination"]:
            train["status"] = "COMPLETED"
            train["completed_at_min"] = now
            train["ready_departure_min"] = None
            state["counters"]["completed"] += 1
            _append_event(
                state,
                "ARRIVAL",
                f"{train['id']} {train['name']} arrived at {station_id} "
                f"({format_minutes(now)}), delay {train['delay_min']} min.",
                train_id=train["id"],
                station_id=station_id,
                delay_min=train["delay_min"],
                final=True,
            )
        else:
            scheduled_departure = train["schedule"][next_index]["departure_min"]
            train["ready_departure_min"] = max(
                int(scheduled_departure), now + int(train["dwell_min"])
            )
            planned_hold = int(train.get("planned_holds", {}).get(station_id, 0) or 0)
            if planned_hold > 0:
                train["hold_until_min"] = max(
                    int(train["ready_departure_min"]),
                    now + int(train["dwell_min"]) + planned_hold,
                )
                train["waiting_reason"] = "HOLD"
                _append_event(
                    state,
                    "HOLD_APPLIED",
                    f"{train['id']} will be held at {station_id} for {planned_hold} min "
                    f"as instructed by the approved schedule.",
                    train_id=train["id"],
                    station_id=station_id,
                    hold_min=planned_hold,
                )
            _append_event(
                state,
                "ARRIVAL",
                f"{train['id']} arrived at {station_id} ({format_minutes(now)}), "
                f"delay {train['delay_min']} min.",
                train_id=train["id"],
                station_id=station_id,
                delay_min=train["delay_min"],
            )


def _handle_departures(state: dict) -> None:
    now = state["sim_time_min"]
    candidates = [
        train
        for train in state["trains"]
        if train["status"] == "AT_STATION"
        and now >= int(train.get("ready_departure_min") or 0)
        and now >= int(train.get("hold_until_min") or 0)
    ]
    candidates.sort(key=lambda item: (_effective_priority(item), item["ready_departure_min"], item["id"]))
    for train in candidates:
        segment = _next_segment(train)
        if segment is None:
            continue
        section_id, block_id, direction, run_min = segment
        can_use, reason = _can_use_block(state, block_id, direction, now, run_min)
        if not can_use:
            train["waiting_reason"] = reason
            continue
        next_index = int(train["route_index"]) + 1
        next_station = train["route"][next_index]
        available = _available_platform_count(state, next_station, now + run_min)
        if available == 0:
            train["waiting_reason"] = "DESTINATION_PLATFORM_UNAVAILABLE"
            continue
        _free_platform(state, train)
        state["block_occupancy"][block_id] = {
            "train_id": train["id"],
            "direction": direction,
            "entry_min": now,
            "exit_min": now + run_min,
        }
        train["status"] = "RUNNING"
        train["section_id"] = section_id
        train["block_id"] = block_id
        train["entry_min"] = now
        train["exit_min"] = now + run_min
        train["actual_departures"][train["station_id"]] = now
        scheduled_departure = train["schedule"][train["route_index"]]["departure_min"]
        train["delay_min"] = max(0, now - int(scheduled_departure))
        train["waiting_reason"] = None
        state["counters"]["departures"] += 1
        _append_event(
            state,
            "DEPARTURE",
            f"{train['id']} departed {train['station_id']} at {format_minutes(now)} "
            f"into block {block_id}.",
            train_id=train["id"],
            station_id=train["station_id"],
            section_id=section_id,
            block_id=block_id,
            delay_min=train["delay_min"],
        )


def _update_running_and_waiting(state: dict) -> None:
    now = state["sim_time_min"]
    for train in state["trains"]:
        if train["status"] == "RUNNING":
            scheduled_arrival = train["schedule"][int(train["route_index"]) + 1]["arrival_min"]
            projected = now + max(0, int(train["exit_min"]) - now)
            train["delay_min"] = max(0, projected - int(scheduled_arrival))
        elif train["status"] == "AT_STATION":
            ready = int(train.get("ready_departure_min") or now)
            hold = int(train.get("hold_until_min") or 0)
            if now >= ready and now >= hold:
                train["waiting_reason"] = train.get("waiting_reason") or "WAITING_RESOURCE"
                train["total_wait_min"] = int(train.get("total_wait_min", 0)) + 1
                state["counters"]["waiting_min"] += 1
            elif hold > now:
                train["waiting_reason"] = "HOLD"
            scheduled_arrival = train["schedule"][train["route_index"]].get("arrival_min")
            scheduled_departure = train["schedule"][train["route_index"]].get("departure_min")
            if scheduled_arrival is not None:
                train["delay_min"] = max(0, now - int(scheduled_arrival))
            elif scheduled_departure is not None:
                train["delay_min"] = max(0, now - int(scheduled_departure))
        if train["status"] in {"RUNNING", "AT_STATION"}:
            train["current_delay_min"] = train["delay_min"]
        if train["status"] == "COMPLETED":
            train["current_delay_min"] = train["delay_min"]
    for block_id, occupancy in state["block_occupancy"].items():
        if occupancy.get("train_id"):
            state["counters"]["block_busy_min"][block_id] = (
                state["counters"]["block_busy_min"].get(block_id, 0) + 1
            )
    for station_id, platforms in state["platform_occupancy"].items():
        for platform, train_id in platforms.items():
            if train_id:
                station_busy = state["counters"]["platform_busy_min"].setdefault(
                    station_id, {}
                )
                station_busy[platform] = station_busy.get(platform, 0) + 1


def tick(state: dict) -> dict:
    if state["status"] != "RUNNING":
        return state
    _handle_arrivals(state)
    _handle_departures(state)
    _update_running_and_waiting(state)
    state["sim_time_min"] += 1
    if all(train["status"] == "COMPLETED" for train in state["trains"]):
        state["status"] = "COMPLETED"
        _append_event(
            state,
            "SIMULATION_COMPLETED",
            "All trains completed their journeys in simulation.",
        )
    return state


def advance(state: dict, minutes: int) -> dict:
    if minutes < 0 or minutes > 180:
        raise SimulationError("Advance minutes must be between 0 and 180")
    if state["status"] == "PAUSED":
        raise SimulationError("Simulation is paused; resume before advancing")
    if state["status"] == "COMPLETED":
        return state
    for _ in range(minutes):
        if state["status"] != "RUNNING":
            break
        tick(state)
    state["version"] = int(state["version"]) + 1
    return state


def apply_action(state: dict, action: dict) -> dict:
    """Apply a *human-confirmed* or hypothetical action to a state copy.

    This function never performs validation of its own; callers must validate
    the action against the topology and current state first. It is used both by
    the approved-decision path and by read-only what-if simulation.
    """
    action_type = action.get("type")
    now = state["sim_time_min"]
    if action_type == "DO_NOTHING":
        _append_event(state, "ACTION_APPLIED", "Controller selected no operational change.", action=action)
    elif action_type == "HOLD":
        train = _train(state, action["train_id"])
        if train["status"] != "AT_STATION":
            raise SimulationError("A train can only be held at a station")
        hold_min = int(action.get("hold_min", 0))
        if hold_min < 0 or hold_min > 120:
            raise SimulationError("Hold duration outside supported range")
        train["hold_until_min"] = max(now, int(train["ready_departure_min"] or now)) + hold_min
        train["waiting_reason"] = "HOLD"
        _append_event(
            state,
            "ACTION_APPLIED",
            f"Hold applied to {train['id']} at {train['station_id']} for {hold_min} min "
            f"(until {format_minutes(train['hold_until_min'])}).",
            action=action,
            train_id=train["id"],
        )
    elif action_type == "PRECEDENCE":
        train = _train(state, action["train_id"])
        train["priority_override"] = int(action.get("priority_override", 0))
        _append_event(
            state,
            "ACTION_APPLIED",
            f"Precedence granted to {train['id']} (effective priority "
            f"{train['priority_override']}).",
            action=action,
            train_id=train["id"],
        )
    elif action_type == "PLATFORM_REASSIGN":
        train = _train(state, action["train_id"])
        train["platform_preference"] = action["platform_id"]
        _append_event(
            state,
            "ACTION_APPLIED",
            f"Platform preference for {train['id']} set to {action['platform_id']}.",
            action=action,
            train_id=train["id"],
        )
    elif action_type == "SCHEDULE":
        for hold in action.get("holds", []):
            train = _train(state, hold["train_id"])
            hold_min = int(hold.get("hold_min", 0))
            if hold_min <= 0:
                continue
            station_id = hold.get("station_id")
            if train["status"] == "AT_STATION" and train["station_id"] == station_id:
                train["hold_until_min"] = max(
                    now, int(train["ready_departure_min"] or now)
                ) + hold_min
                train["waiting_reason"] = "HOLD"
            else:
                train.setdefault("planned_holds", {})[station_id] = hold_min
        for index, train_id in enumerate(action.get("precedence", [])):
            train = _train(state, train_id)
            train["priority_override"] = min(int(train["priority"]), index)
        _append_event(
            state,
            "ACTION_APPLIED",
            "Validated CP-SAT schedule applied as holding and precedence instructions.",
            action=action,
        )
    else:
        raise SimulationError(f"Unsupported action type '{action_type}'")
    state["version"] = int(state["version"]) + 1
    return state


def projected_delay(train: dict, now: int) -> int:
    if train["status"] == "COMPLETED":
        return int(train["delay_min"])
    if train["status"] == "RUNNING" and train.get("exit_min") is not None:
        next_index = int(train["route_index"]) + 1
        scheduled = int(train["schedule"][next_index]["arrival_min"])
        return max(0, int(train["exit_min"]) - scheduled)
    ready = int(train.get("ready_departure_min") or now)
    hold = int(train.get("hold_until_min") or 0)
    departure = max(now, ready, hold)
    next_index = int(train["route_index"]) + 1
    if next_index >= len(train["schedule"]):
        return int(train["delay_min"])
    run = int(train["schedule"][next_index]["run_from_previous_min"])
    scheduled = int(train["schedule"][next_index]["arrival_min"])
    return max(0, departure + run - scheduled)


def state_metrics(state: dict) -> dict:
    now = state["sim_time_min"]
    active = [train for train in state["trains"] if train["status"] != "COMPLETED"]
    completed = [train for train in state["trains"] if train["status"] == "COMPLETED"]
    delays = [projected_delay(train, now) for train in state["trains"]]
    completed_delays = [int(train["delay_min"]) for train in completed]
    on_time = sum(1 for delay in completed_delays if delay <= 5)
    total_delay = sum(delays)
    horizon = max(1, now - int(state["start_time_min"]))
    block_busy = state["counters"]["block_busy_min"]
    block_total = max(1, len(block_busy) * horizon)
    platform_busy = state["counters"]["platform_busy_min"]
    platform_slots = sum(len(platforms) for platforms in platform_busy.values())
    platform_total = max(1, platform_slots * horizon)
    return {
        "sim_time_min": now,
        "sim_time": format_minutes(now),
        "trains_total": len(state["trains"]),
        "trains_active": len(active),
        "trains_completed": len(completed),
        "trains_delayed": sum(1 for delay in delays if delay > 5),
        "total_delay_min": total_delay,
        "average_delay_min": round(total_delay / max(1, len(state["trains"])), 2),
        "average_completed_delay_min": round(
            sum(completed_delays) / max(1, len(completed_delays)), 2
        ),
        "max_delay_min": max(delays) if delays else 0,
        "on_time_arrivals": on_time,
        "on_time_performance_pct": round(100 * on_time / max(1, len(completed)), 2),
        "throughput_trains_per_hour": round(len(completed) / max(horizon / 60, 0.1), 2),
        "section_utilization_pct": round(100 * sum(block_busy.values()) / block_total, 2),
        "platform_utilization_pct": round(
            100 * sum(sum(platforms.values()) for platforms in platform_busy.values())
            / platform_total,
            2,
        ),
        "waiting_min_total": state["counters"]["waiting_min"],
        "label": "SYNTHETIC",
    }


def validate_state_integrity(state: dict) -> list[str]:
    """Return a list of structural problems; used before analysis."""
    problems: list[str] = []
    if not state.get("network"):
        problems.append("Network topology is missing")
        return problems
    try:
        Network.from_dict(state["network"]).validate()
    except Exception as exc:  # noqa: BLE001 - surface exact topology error
        problems.append(f"Invalid topology: {exc}")
    train_ids = [train["id"] for train in state.get("trains", [])]
    if len(train_ids) != len(set(train_ids)):
        problems.append("Duplicate train identifiers")
    for train in state.get("trains", []):
        if not train.get("schedule"):
            problems.append(f"Train {train['id']} has no timetable")
        if train.get("route_index", 0) >= len(train.get("route", [])):
            problems.append(f"Train {train['id']} has an invalid route index")
    for block_id, occupancy in state.get("block_occupancy", {}).items():
        if occupancy.get("train_id") and occupancy["train_id"] not in train_ids:
            problems.append(f"Block {block_id} references unknown train")
    return problems
