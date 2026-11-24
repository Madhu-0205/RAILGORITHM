"""Independent conflict detection over a projected traffic state.

Conflict detection does not resolve anything. It reports predicted resource
conflicts with explicit evidence (block windows, platform demand, closures) so
that the recommendation pipeline can generate and validate candidate actions.
"""
from __future__ import annotations

import hashlib
import json
from itertools import combinations

from .network import Network
from .projection import project_state
from .state import format_minutes

SEVERITY_ORDER = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}


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

    # ---- block occupancy / crossing conflicts ----------------------------
    for block_id, windows in block_windows.items():
        if len(windows) < 2:
            continue
        section = next(
            section
            for section in network.sections
            if any(block.id == block_id for block in section.blocks)
        )
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
            if section.mode == "SINGLE" and opposing:
                kind = "SINGLE_LINE_CROSSING"
                severity = "HIGH"
                description = (
                    f"Opposing trains {left['train_id']} and {right['train_id']} are "
                    f"projected to require single-line block {block_id} "
                    f"({section.from_station}–{section.to_station}) at overlapping times "
                    f"({format_minutes(left['entry_min'])}–{format_minutes(left['exit_min'])} vs "
                    f"{format_minutes(right['entry_min'])}–{format_minutes(right['exit_min'])})."
                )
            else:
                kind = "HEADWAY"
                gap = max(
                    0,
                    max(left["entry_min"], right["entry_min"])
                    - min(left["exit_min"], right["exit_min"]),
                )
                severity = "HIGH" if gap < headway else "MEDIUM"
                description = (
                    f"Trains {left['train_id']} and {right['train_id']} are projected on "
                    f"block {block_id} with less than the configured {headway}-minute "
                    f"headway."
                )
            conflict_id = _conflict_id(
                kind, block_id, [left["train_id"], right["train_id"]], min(left["entry_min"], right["entry_min"])
            )
            conflicts.append(
                {
                    "id": conflict_id,
                    "type": kind,
                    "severity": severity,
                    "status": "ACTIVE",
                    "location": {
                        "kind": "BLOCK",
                        "section_id": section.id,
                        "block_id": block_id,
                        "label": f"{section.from_station}–{section.to_station} / {block_id}",
                    },
                    "trains": [left["train_id"], right["train_id"]],
                    "train_names": [trains[left["train_id"]]["name"], trains[right["train_id"]]["name"]],
                    "start_min": min(left["entry_min"], right["entry_min"]),
                    "start": format_minutes(min(left["entry_min"], right["entry_min"])),
                    "end_min": max(left["exit_min"], right["exit_min"]),
                    "end": format_minutes(max(left["exit_min"], right["exit_min"])),
                    "headway_min": headway,
                    "description": description,
                    "evidence": {
                        "block_windows": [left, right],
                        "section_mode": section.mode,
                        "headway_min": headway,
                        "opposing": opposing,
                    },
                }
            )

    # ---- closure conflicts ------------------------------------------------
    for train_id, data in projection["trains"].items():
        for window in data["block_windows"]:
            for closure in state.get("closures", []):
                if (
                    closure["block_id"] == window["block_id"]
                    and closure["start_min"] < window["exit_min"]
                    and window["entry_min"] < closure["end_min"]
                ):
                    conflict_id = _conflict_id(
                        "BLOCK_CLOSURE", closure["block_id"], [train_id], window["entry_min"]
                    )
                    conflicts.append(
                        {
                            "id": conflict_id,
                            "type": "BLOCK_CLOSURE",
                            "severity": "CRITICAL",
                            "status": "ACTIVE",
                            "location": {
                                "kind": "BLOCK",
                                "block_id": closure["block_id"],
                                "label": closure["block_id"],
                            },
                            "trains": [train_id],
                            "train_names": [trains[train_id]["name"]],
                            "start_min": max(window["entry_min"], closure["start_min"]),
                            "start": format_minutes(max(window["entry_min"], closure["start_min"])),
                            "end_min": min(window["exit_min"], closure["end_min"]),
                            "end": format_minutes(min(window["exit_min"], closure["end_min"])),
                            "description": (
                                f"Train {train_id} is projected to need block "
                                f"{closure['block_id']} while it is closed for "
                                f"'{closure['reason']}' "
                                f"({format_minutes(closure['start_min'])}–{format_minutes(closure['end_min'])}). "
                                f"No alternative route exists in this topology."
                            ),
                            "evidence": {
                                "closure": closure,
                                "block_window": window,
                            },
                        }
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
            # A train already at a station without a platform does not consume one.
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
                conflict_id = _conflict_id(
                    "PLATFORM_CAPACITY", station_id, list(group), time_min
                )
                conflicts.append(
                    {
                        "id": conflict_id,
                        "type": "PLATFORM_CAPACITY",
                        "severity": (
                            "CRITICAL" if capacity == 0 else "HIGH" if capacity == 1 else "MEDIUM"
                        ),
                        "status": "ACTIVE",
                        "location": {
                            "kind": "STATION",
                            "station_id": station_id,
                            "label": f"{station.name} ({station_id})",
                        },
                        "trains": sorted(group),
                        "train_names": [trains[item]["name"] for item in sorted(group)],
                        "start_min": time_min,
                        "start": format_minutes(time_min),
                        "end_min": time_min + 1,
                        "end": format_minutes(time_min + 1),
                        "description": (
                            f"{len(active)} trains require a platform at {station.name} at "
                            f"{format_minutes(time_min)} but only {capacity} of "
                            f"{len(station.platforms)} platforms are available."
                        ),
                        "evidence": {
                            "available_platforms": capacity,
                            "configured_platforms": list(station.platforms),
                            "demand": len(active),
                            "outages": [
                                outage
                                for outage in state.get("platform_outages", [])
                                if outage["station_id"] == station_id
                            ],
                        },
                    }
                )

    # ---- junction throat conflicts ---------------------------------------
    for station in network.stations:
        if not station.is_junction:
            continue
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
            if len(group) < 3:
                continue
            group_ids = frozenset(window["train_id"] for window in group)
            if group_ids in seen_groups:
                continue
            seen_groups.add(group_ids)
            start_min = min(window["arrival_min"] for window in group)
            end_min = max(window["arrival_min"] for window in group)
            conflict_id = _conflict_id(
                "JUNCTION_CONFLICT", station.id, list(group_ids), start_min
            )
            conflicts.append(
                {
                    "id": conflict_id,
                    "type": "JUNCTION_CONFLICT",
                    "severity": "MEDIUM",
                    "status": "ACTIVE",
                    "location": {
                        "kind": "STATION",
                        "station_id": station.id,
                        "label": f"{station.name} junction throat",
                    },
                    "trains": sorted(group_ids),
                    "train_names": [
                        trains[item]["name"] for item in sorted(group_ids)
                    ],
                    "start_min": start_min,
                    "start": format_minutes(start_min),
                    "end_min": end_min,
                    "end": format_minutes(end_min),
                    "description": (
                        f"{len(group)} trains are projected to approach the {station.name} "
                        f"junction throat within 3 minutes; configured throat capacity is 2."
                    ),
                    "evidence": {
                        "arrivals": [window["arrival_min"] for window in group],
                        "throat_window_min": 3,
                        "throat_capacity": 2,
                    },
                }
            )

    # ---- projected delay risk --------------------------------------------
    for train_id, data in projection["trains"].items():
        final_delay = int(data["final_delay_min"])
        if final_delay >= 15:
            conflict_id = _conflict_id("DELAY_RISK", "TRAIN", [train_id], now)
            conflicts.append(
                {
                    "id": conflict_id,
                    "type": "DELAY_RISK",
                    "severity": "MEDIUM" if final_delay >= 25 else "LOW",
                    "status": "ACTIVE",
                    "location": {"kind": "TRAIN", "label": train_id},
                    "trains": [train_id],
                    "train_names": [trains[train_id]["name"]],
                    "start_min": now,
                    "start": format_minutes(now),
                    "end_min": now + horizon_min,
                    "end": format_minutes(now + horizon_min),
                    "description": (
                        f"Train {train_id} is projected to complete with {final_delay} "
                        f"minutes of delay without intervention."
                    ),
                    "evidence": {
                        "projected_final_delay_min": final_delay,
                        "threshold_min": 15,
                    },
                }
            )

    deduped: dict[str, dict] = {}
    for conflict in conflicts:
        deduped.setdefault(conflict["id"], conflict)
    return sorted(
        deduped.values(),
        key=lambda item: (SEVERITY_ORDER.get(item["severity"], 9), item["start_min"], item["id"]),
    )


def primary_conflicts(conflicts: list[dict], limit: int = 3) -> list[dict]:
    actionable = [
        conflict
        for conflict in conflicts
        if conflict["type"] != "DELAY_RISK"
    ]
    return actionable[:limit] if actionable else conflicts[:limit]
