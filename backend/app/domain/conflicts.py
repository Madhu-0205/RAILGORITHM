"""Independent conflict detection over a projected traffic state.

Version 2.0 reports a wider conflict taxonomy while keeping one canonical event
per underlying resource interaction. Every conflict carries:

* a stable unique id derived from type, location, trains and start time;
* the resource, trains and time window;
* a severity and the hard/soft constraint reference it relates to;
* explicit evidence (block windows, platform demand, closures, disruption);
* related conflict types when one event has more than one operational reading
  (for example a single-line crossing is also a headway event).

Detection never resolves anything and never trusts the optimizer.
"""
from __future__ import annotations

import hashlib
import json
from itertools import combinations

from .network import Network
from .projection import project_state
from .spec import CONSTRAINT_SPEC_VERSION
from .state import format_minutes

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}

CONFLICT_TYPES = [
    "BLOCK_EXCLUSIVITY",
    "HEADWAY",
    "SINGLE_LINE_CROSSING",
    "CROSSING_CONFLICT",
    "ROUTE_CONFLICT",
    "OVERTAKING_CONFLICT",
    "PLATFORM_CAPACITY",
    "JUNCTION_CONFLICT",
    "BLOCK_CLOSURE",
    "MAINTENANCE_CONFLICT",
    "DISRUPTION_CONFLICT",
    "CASCADING_DELAY",
    "DELAY_RISK",
]

CONSTRAINT_FOR_TYPE = {
    "BLOCK_EXCLUSIVITY": "HC-001",
    "HEADWAY": "HC-002",
    "SINGLE_LINE_CROSSING": "HC-003",
    "CROSSING_CONFLICT": "HC-003",
    "ROUTE_CONFLICT": "HC-001",
    "OVERTAKING_CONFLICT": "HC-002",
    "PLATFORM_CAPACITY": "HC-005",
    "JUNCTION_CONFLICT": "HC-006",
    "BLOCK_CLOSURE": "HC-007",
    "MAINTENANCE_CONFLICT": "HC-007",
    "DISRUPTION_CONFLICT": "HC-007",
    "CASCADING_DELAY": "SC-003",
    "DELAY_RISK": "SC-003",
}


def _conflict_id(kind: str, location: str, train_ids: list[str], start_min: int) -> str:
    raw = json.dumps(
        {"kind": kind, "location": location, "trains": sorted(train_ids), "start": start_min},
        sort_keys=True,
    )
    return "CF-" + hashlib.sha1(raw.encode()).hexdigest()[:12].upper()


def _available_platform_count(state: dict, station_id: str, at_min: int) -> int:
    station = next(
        item for item in state["network"]["stations"] if item["id"] == station_id
    )
    count = 0
    for platform in station["platforms"]:
        blocked = any(
            outage["station_id"] == station_id
            and outage["platform_id"] == platform
            and outage["start_min"] <= at_min < outage["end_min"]
            for outage in state.get("platform_outages", [])
        )
        if not blocked:
            count += 1
    return count


def _conflict(
    *,
    kind: str,
    severity: str,
    location: dict,
    trains: list[str],
    train_names: list[str],
    start_min: int,
    end_min: int,
    description: str,
    evidence: dict,
    related_types: list[str] | None = None,
    status: str = "ACTIVE",
) -> dict:
    return {
        "id": _conflict_id(kind, location.get("label", ""), trains, start_min),
        "type": kind,
        "related_types": list(dict.fromkeys([kind] + (related_types or []))),
        "severity": severity,
        "status": status,
        "constraint_id": CONSTRAINT_FOR_TYPE.get(kind),
        "constraint_spec_version": CONSTRAINT_SPEC_VERSION,
        "location": location,
        "trains": trains,
        "train_names": train_names,
        "start_min": int(start_min),
        "start": format_minutes(start_min),
        "end_min": int(max(start_min, end_min)),
        "end": format_minutes(max(start_min, end_min)),
        "description": description,
        "evidence": evidence,
    }


def detect_conflicts(state: dict, horizon_min: int = 75) -> list[dict]:
    network = Network.from_dict(state["network"])
    projection = project_state(state, horizon_min)
    now = projection["now"]
    horizon = projection["horizon"]
    trains = {train["id"]: train for train in state["trains"]}
    conflicts: list[dict] = []

    block_windows: dict[str, list[dict]] = {}
    station_windows: dict[str, list[dict]] = {}
    for train_id, data in projection["trains"].items():
        for window in data["block_windows"]:
            block_windows.setdefault(window["block_id"], []).append(window)
        for window in data["station_windows"]:
            station_windows.setdefault(window["station_id"], []).append(window)

    # ---- block occupancy / crossing / overtaking conflicts ---------------
    for block_id, windows in block_windows.items():
        if len(windows) < 2:
            continue
        section = network.section_for_block(block_id)
        headway = section.headway_min
        for left, right in combinations(sorted(windows, key=lambda w: w["entry_min"]), 2):
            if left["train_id"] == right["train_id"]:
                continue
            if (
                left["exit_min"] + headway <= right["entry_min"]
                or right["exit_min"] + headway <= left["entry_min"]
            ):
                continue
            opposing = left["direction"] != right["direction"]
            overlap_min = max(
                0,
                min(left["exit_min"], right["exit_min"])
                - max(left["entry_min"], right["entry_min"]),
            )
            related: list[str] = []
            if opposing:
                if section.mode == "SINGLE":
                    kind = "SINGLE_LINE_CROSSING"
                    severity = "HIGH"
                    related = ["CROSSING_CONFLICT", "HEADWAY"]
                    description = (
                        f"Opposing trains {left['train_id']} and {right['train_id']} are "
                        f"projected to require single-line block {block_id} "
                        f"({section.from_station}–{section.to_station}) at overlapping times "
                        f"({format_minutes(left['entry_min'])}–{format_minutes(left['exit_min'])} vs "
                        f"{format_minutes(right['entry_min'])}–{format_minutes(right['exit_min'])})."
                    )
                else:
                    kind = "ROUTE_CONFLICT"
                    severity = "HIGH"
                    related = ["HEADWAY"]
                    description = (
                        f"Trains {left['train_id']} and {right['train_id']} have an "
                        f"unexpected opposing route overlap on {block_id} despite the "
                        f"double-line configuration."
                    )
            else:
                if overlap_min > 0:
                    kind = "BLOCK_EXCLUSIVITY"
                    severity = "HIGH"
                    related = ["HEADWAY"]
                    description = (
                        f"Trains {left['train_id']} and {right['train_id']} are projected "
                        f"to occupy block {block_id} simultaneously "
                        f"({format_minutes(max(left['entry_min'], right['entry_min']))}–"
                        f"{format_minutes(min(left['exit_min'], right['exit_min']))})."
                    )
                else:
                    gap = max(
                        0,
                        max(left["entry_min"], right["entry_min"])
                        - min(left["exit_min"], right["exit_min"]),
                    )
                    kind = "HEADWAY"
                    severity = "HIGH" if gap < headway else "MEDIUM"
                    related = []
                    description = (
                        f"Trains {left['train_id']} and {right['train_id']} are projected on "
                        f"block {block_id} with less than the configured {headway}-minute "
                        f"headway."
                    )
                # Overtaking: a faster train is behind a slower one in the same direction.
                left_train = trains.get(left["train_id"], {})
                right_train = trains.get(right["train_id"], {})
                left_speed = _speed_factor(left_train)
                right_speed = _speed_factor(right_train)
                later = left if left["entry_min"] >= right["entry_min"] else right
                earlier = right if later is left else left
                later_speed = left_speed if later is left else right_speed
                earlier_speed = right_speed if later is left else left_speed
                if later_speed + 0.05 < earlier_speed:
                    related.append("OVERTAKING_CONFLICT")
                    if kind == "HEADWAY":
                        kind = "OVERTAKING_CONFLICT"
                        severity = "MEDIUM"
                    description += (
                        f" Faster train {later['train_id']} is projected behind slower "
                        f"train {earlier['train_id']}; an overtaking decision is required."
                    )
            conflict = _conflict(
                kind=kind,
                severity=severity,
                location={
                    "kind": "BLOCK",
                    "section_id": section.id,
                    "block_id": block_id,
                    "label": f"{section.from_station}–{section.to_station} / {block_id}",
                },
                trains=[left["train_id"], right["train_id"]],
                train_names=[
                    trains[left["train_id"]]["name"],
                    trains[right["train_id"]]["name"],
                ],
                start_min=min(left["entry_min"], right["entry_min"]),
                end_min=max(left["exit_min"], right["exit_min"]),
                description=description,
                evidence={
                    "block_windows": [left, right],
                    "section_mode": section.mode,
                    "headway_min": headway,
                    "opposing": opposing,
                    "overlap_min": overlap_min,
                    "distance_km": section.distance_km,
                    "max_speed_kmph": section.max_speed_kmph,
                },
                related_types=related,
            )
            conflict["headway_min"] = headway
            conflicts.append(conflict)

    # ---- closure / maintenance conflicts ---------------------------------
    for train_id, data in projection["trains"].items():
        for window in data["block_windows"]:
            for closure in state.get("closures", []):
                if (
                    closure["block_id"] == window["block_id"]
                    and closure["start_min"] < window["exit_min"]
                    and window["entry_min"] < closure["end_min"]
                ):
                    reason = str(closure.get("reason", ""))
                    maintenance = any(
                        word in reason.lower()
                        for word in ("maintenance", "engineering", "renewal", "possession")
                    )
                    related = ["DISRUPTION_CONFLICT"]
                    if maintenance:
                        related.append("MAINTENANCE_CONFLICT")
                    conflict = _conflict(
                        kind="BLOCK_CLOSURE",
                        severity="CRITICAL",
                        location={
                            "kind": "BLOCK",
                            "block_id": closure["block_id"],
                            "label": closure["block_id"],
                        },
                        trains=[train_id],
                        train_names=[trains[train_id]["name"]],
                        start_min=max(window["entry_min"], closure["start_min"]),
                        end_min=min(window["exit_min"], closure["end_min"]),
                        description=(
                            f"Train {train_id} is projected to need block "
                            f"{closure['block_id']} while it is closed for "
                            f"'{closure['reason']}' "
                            f"({format_minutes(closure['start_min'])}–{format_minutes(closure['end_min'])}). "
                            f"No alternative route exists in this topology."
                        ),
                        evidence={
                            "closure": closure,
                            "block_window": window,
                            "maintenance": maintenance,
                            "closure_source": closure.get("source", "CONFIGURED"),
                        },
                        related_types=related,
                    )
                    conflicts.append(conflict)

    # ---- explicit disruption evidence ------------------------------------
    for disruption in state.get("disruptions", []):
        kind = str(disruption.get("kind", ""))
        if kind not in {"TRAIN_DELAY", "SPEED_RESTRICTION"}:
            continue
        target = str(disruption.get("target", ""))
        affected = [target] if target in trains else []
        if not affected:
            continue
        start_min = int(disruption.get("start_min", now))
        end_min = int(disruption.get("end_min", start_min + 1))
        if end_min < now:
            continue
        conflicts.append(
            _conflict(
                kind="DISRUPTION_CONFLICT",
                severity="MEDIUM",
                location={"kind": "TRAIN", "label": target, "train_id": target},
                trains=affected,
                train_names=[trains[target]["name"]],
                start_min=max(now, start_min),
                end_min=max(now + 1, end_min),
                description=(
                    f"Disruption {disruption.get('id', kind)} ({kind}) affects train "
                    f"{target}: {disruption.get('reason', 'scenario disruption')}."
                ),
                evidence={"disruption": disruption},
                related_types=["CASCADING_DELAY"] if kind == "TRAIN_DELAY" else [],
            )
        )

    # ---- platform capacity conflicts -------------------------------------
    for station_id, windows in station_windows.items():
        station = network.station(station_id)
        events: list[tuple[int, int, str]] = []
        for window in windows:
            arrival = int(window["arrival_min"])
            departure = window["departure_min"]
            if departure is None:
                departure = arrival + 1
            if window.get("current") and window.get("platform") is None:
                continue
            events.append((arrival, 1, window["train_id"]))
            events.append((int(departure), -1, window["train_id"]))
        events.sort(key=lambda event: (event[0], event[1]))
        active: set[str] = set()
        seen_groups: set[frozenset[str]] = set()
        for time_min, delta, train_id in events:
            if delta == -1:
                active.discard(train_id)
                continue
            active.add(train_id)
            capacity = _available_platform_count(state, station_id, time_min)
            if len(active) > capacity:
                group = frozenset(active)
                if group in seen_groups:
                    continue
                seen_groups.add(group)
                conflicts.append(
                    _conflict(
                        kind="PLATFORM_CAPACITY",
                        severity=(
                            "CRITICAL" if capacity == 0 else "HIGH" if capacity == 1 else "MEDIUM"
                        ),
                        location={
                            "kind": "STATION",
                            "station_id": station_id,
                            "label": f"{station.name} ({station_id})",
                        },
                        trains=sorted(group),
                        train_names=[trains[item]["name"] for item in sorted(group)],
                        start_min=time_min,
                        end_min=time_min + 1,
                        description=(
                            f"{len(active)} trains require a platform at {station.name} at "
                            f"{format_minutes(time_min)} but only {capacity} of "
                            f"{len(station.platforms)} platforms are available."
                        ),
                        evidence={
                            "available_platforms": capacity,
                            "configured_platforms": list(station.platforms),
                            "demand": len(active),
                            "outages": [
                                outage
                                for outage in state.get("platform_outages", [])
                                if outage["station_id"] == station_id
                            ],
                        },
                    )
                )

    # ---- junction throat conflicts ---------------------------------------
    for station in network.stations:
        if not station.is_junction:
            continue
        capacity = int(station.junction_throat_capacity)
        windows = station_windows.get(station.id, [])
        arrivals = sorted(
            [
                window
                for window in windows
                if not window.get("current") or window.get("platform") is not None
            ],
            key=lambda window: window["arrival_min"],
        )
        seen_groups: set[frozenset[str]] = set()
        for anchor in arrivals:
            group = [
                window
                for window in arrivals
                if 0 <= window["arrival_min"] - anchor["arrival_min"] <= 3
            ]
            if len(group) <= capacity:
                continue
            group_ids = frozenset(window["train_id"] for window in group)
            if group_ids in seen_groups:
                continue
            seen_groups.add(group_ids)
            start_min = min(window["arrival_min"] for window in group)
            end_min = max(window["arrival_min"] for window in group)
            conflicts.append(
                _conflict(
                    kind="JUNCTION_CONFLICT",
                    severity="MEDIUM",
                    location={
                        "kind": "STATION",
                        "station_id": station.id,
                        "label": f"{station.name} junction throat",
                    },
                    trains=sorted(group_ids),
                    train_names=[trains[item]["name"] for item in sorted(group_ids)],
                    start_min=start_min,
                    end_min=end_min,
                    description=(
                        f"{len(group)} trains are projected to approach the {station.name} "
                        f"junction throat within 3 minutes; configured throat capacity is "
                        f"{capacity}."
                    ),
                    evidence={
                        "arrivals": [window["arrival_min"] for window in group],
                        "throat_window_min": 3,
                        "throat_capacity": capacity,
                    },
                )
            )

    # ---- overtaking risk from current relative position ------------------
    # Projection deliberately ignores other trains, so a faster train that is
    # physically behind a slower one can appear ahead in its own timetable.
    # This detector uses current route progress to report the operational
    # overtaking risk without pretending it is already a block conflict.
    active = [
        train
        for train in state["trains"]
        if train["status"] in {"RUNNING", "AT_STATION"}
        and train["direction"] in {"UP", "DOWN"}
    ]
    for leader, follower in combinations(
        sorted(active, key=lambda item: (item["direction"], item["id"])), 2
    ):
        if leader["direction"] != follower["direction"]:
            continue
        leader_progress = _route_progress(leader)
        follower_progress = _route_progress(follower)
        if leader_progress < follower_progress:
            leader, follower = follower, leader
            leader_progress, follower_progress = follower_progress, leader_progress
        if leader_progress - follower_progress > 1.5:
            continue
        leader_speed = _speed_factor(leader)
        follower_speed = _speed_factor(follower)
        if follower_speed + 0.05 >= leader_speed:
            continue
        section = None
        block_id = None
        next_index = int(follower["route_index"]) + 1
        if next_index < len(follower["schedule"]):
            segment = follower["schedule"][next_index]
            block_id = segment.get("block_id")
            section = segment.get("section_id")
        conflicts.append(
            _conflict(
                kind="OVERTAKING_CONFLICT",
                severity="MEDIUM",
                location={
                    "kind": "TRAIN",
                    "train_id": follower["id"],
                    "section_id": section,
                    "block_id": block_id,
                    "label": f"{follower['id']} behind {leader['id']}",
                },
                trains=[follower["id"], leader["id"]],
                train_names=[follower["name"], leader["name"]],
                start_min=now,
                end_min=now + horizon_min,
                description=(
                    f"Faster train {follower['id']} (speed factor {follower_speed:.2f}) "
                    f"is behind slower train {leader['id']} (speed factor "
                    f"{leader_speed:.2f}) in the {follower['direction']} direction. "
                    f"An overtaking or precedence decision may be required."
                ),
                evidence={
                    "follower_progress": round(follower_progress, 2),
                    "leader_progress": round(leader_progress, 2),
                    "follower_speed_factor": follower_speed,
                    "leader_speed_factor": leader_speed,
                    "follower_status": follower["status"],
                    "leader_status": leader["status"],
                    "model": "current relative position + configured speed factors",
                },
            )
        )

    # ---- projected delay risk and cascading delay ------------------------
    for train_id, data in projection["trains"].items():
        final_delay = int(data["final_delay_min"])
        if final_delay >= 15:
            conflicts.append(
                _conflict(
                    kind="DELAY_RISK",
                    severity="MEDIUM" if final_delay >= 25 else "LOW",
                    location={"kind": "TRAIN", "label": train_id, "train_id": train_id},
                    trains=[train_id],
                    train_names=[trains[train_id]["name"]],
                    start_min=now,
                    end_min=now + horizon_min,
                    description=(
                        f"Train {train_id} is projected to complete with {final_delay} "
                        f"minutes of delay without intervention."
                    ),
                    evidence={
                        "projected_final_delay_min": final_delay,
                        "threshold_min": 15,
                    },
                )
            )
            if final_delay >= 25:
                downstream = _downstream_trains(data, block_windows, train_id)
                if downstream:
                    conflicts.append(
                        _conflict(
                            kind="CASCADING_DELAY",
                            severity="MEDIUM",
                            location={
                                "kind": "TRAIN",
                                "label": train_id,
                                "train_id": train_id,
                            },
                            trains=[train_id] + downstream,
                            train_names=[trains[item]["name"] for item in [train_id] + downstream],
                            start_min=now,
                            end_min=now + horizon_min,
                            description=(
                                f"Delay on {train_id} ({final_delay} min) is projected to "
                                f"affect {len(downstream)} downstream train(s) through "
                                f"shared block occupancy."
                            ),
                            evidence={
                                "root_train": train_id,
                                "projected_final_delay_min": final_delay,
                                "downstream_trains": downstream,
                                "model": "shared-resource propagation only",
                            },
                        )
                    )

    # Deduplicate identical events and merge related types.
    merged: dict[str, dict] = {}
    for conflict in conflicts:
        key = conflict["id"]
        if key not in merged:
            merged[key] = conflict
            continue
        existing = merged[key]
        existing["related_types"] = list(
            dict.fromkeys(existing["related_types"] + conflict["related_types"])
        )
        if SEVERITY_ORDER[conflict["severity"]] < SEVERITY_ORDER[existing["severity"]]:
            existing["severity"] = conflict["severity"]
    return sorted(
        merged.values(),
        key=lambda item: (SEVERITY_ORDER.get(item["severity"], 9), item["start_min"], item["id"]),
    )


def _speed_factor(train: dict) -> float:
    return float(train.get("speed_factor", 1.0) or 1.0)


def _route_progress(train: dict) -> float:
    progress = float(int(train.get("route_index", 0)))
    if train.get("status") == "RUNNING":
        entry = train.get("entry_min")
        exit_min = train.get("exit_min")
        if entry is not None and exit_min is not None and exit_min > entry:
            progress += 0.5
        else:
            progress += 0.25
    return progress


def _downstream_trains(
    data: dict, block_windows: dict[str, list[dict]], train_id: str
) -> list[str]:
    result: list[str] = []
    own_blocks = {window["block_id"] for window in data.get("block_windows", [])}
    last_exit = max(
        (window["exit_min"] for window in data.get("block_windows", [])), default=0
    )
    for block_id in own_blocks:
        for window in block_windows.get(block_id, []):
            if window["train_id"] == train_id:
                continue
            if window["entry_min"] >= last_exit and window["train_id"] not in result:
                result.append(window["train_id"])
    return result


def primary_conflicts(conflicts: list[dict], limit: int = 3) -> list[dict]:
    actionable = [
        conflict
        for conflict in conflicts
        if conflict["type"] != "DELAY_RISK"
    ]
    return actionable[:limit] if actionable else conflicts[:limit]
