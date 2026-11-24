"""Forward projection of the current state onto a planning horizon.

Projection is intentionally naive: it ignores other trains and only uses each
train's own timetable and current resource state. It is used for conflict
detection and as a starting point for optimization, never as proof of
feasibility.
"""
from __future__ import annotations

from .network import Network


def project_train(train: dict, network: Network, now: int, horizon: int) -> dict:
    block_windows: list[dict] = []
    station_windows: list[dict] = []
    if train["status"] == "COMPLETED":
        return {
            "train_id": train["id"],
            "block_windows": block_windows,
            "station_windows": station_windows,
            "final_delay_min": int(train["delay_min"]),
            "completion_min": train.get("completed_at_min"),
        }

    route = train["route"]
    schedule = train["schedule"]
    direction = train["direction"]

    if train["status"] == "RUNNING":
        route_index = int(train["route_index"])
        entry = int(train.get("entry_min") or now)
        exit_min = max(int(train.get("exit_min") or now), now + 1)
        segment = schedule[route_index + 1]
        block_windows.append(
            {
                "train_id": train["id"],
                "section_id": segment["section_id"],
                "block_id": segment["block_id"],
                "direction": direction,
                "entry_min": entry,
                "exit_min": exit_min,
                "current": True,
            }
        )
        next_index = route_index + 1
        arrival = exit_min
        departure = None
        if next_index < len(route) - 1:
            next_station = route[next_index]
            planned_hold = int(
                train.get("planned_holds", {}).get(next_station, 0) or 0
            )
            departure = arrival + int(train["dwell_min"]) + planned_hold
        station_windows.append(
            {
                "train_id": train["id"],
                "station_id": route[next_index],
                "arrival_min": arrival,
                "departure_min": departure,
                "platform": None,
                "current": True,
            }
        )
        cursor = departure if departure is not None else arrival
        segment_start_index = next_index
    else:
        route_index = int(train["route_index"])
        ready = int(train.get("ready_departure_min") or now)
        hold = int(train.get("hold_until_min") or 0)
        departure = max(now, ready, hold)
        station_windows.append(
            {
                "train_id": train["id"],
                "station_id": train["station_id"],
                "arrival_min": now,
                "departure_min": departure,
                "platform": train.get("platform"),
                "current": True,
            }
        )
        cursor = departure
        segment_start_index = route_index

    final_delay = int(train["delay_min"])
    for index in range(segment_start_index, len(route) - 1):
        segment = schedule[index + 1]
        run_min = int(segment["run_from_previous_min"])
        entry = cursor
        exit_min = entry + run_min
        if entry > horizon:
            break
        block_windows.append(
            {
                "train_id": train["id"],
                "section_id": segment["section_id"],
                "block_id": segment["block_id"],
                "direction": direction,
                "entry_min": entry,
                "exit_min": exit_min,
                "current": False,
            }
        )
        next_station = route[index + 1]
        is_destination = index + 1 == len(route) - 1
        departure_next = None
        if not is_destination:
            planned_hold = int(
                train.get("planned_holds", {}).get(next_station, 0) or 0
            )
            departure_next = exit_min + int(train["dwell_min"]) + planned_hold
        station_windows.append(
            {
                "train_id": train["id"],
                "station_id": next_station,
                "arrival_min": exit_min,
                "departure_min": departure_next,
                "platform": None,
                "current": False,
            }
        )
        if is_destination:
            scheduled_arrival = int(schedule[index + 1]["arrival_min"])
            final_delay = max(0, exit_min - scheduled_arrival)
            break
        cursor = departure_next

    return {
        "train_id": train["id"],
        "block_windows": block_windows,
        "station_windows": station_windows,
        "final_delay_min": final_delay,
        "completion_min": (
            station_windows[-1]["arrival_min"] if station_windows else None
        ),
    }


def project_state(state: dict, horizon_min: int = 75) -> dict:
    network = Network.from_dict(state["network"])
    now = int(state["sim_time_min"])
    horizon = now + horizon_min
    projections = {
        train["id"]: project_train(train, network, now, horizon)
        for train in state["trains"]
    }
    return {"now": now, "horizon": horizon, "trains": projections}


def project_after_action(state: dict, action: dict, horizon_min: int = 75) -> dict:
    """Project a hypothetical action without advancing the simulation clock.

    This is a cheap approximation used for candidate screening. Final evidence
    always comes from an actual cloned simulation, not from this function.
    """
    from .state import apply_action

    clone = __import__("copy").deepcopy(state)
    apply_action(clone, action)
    return project_state(clone, horizon_min)
