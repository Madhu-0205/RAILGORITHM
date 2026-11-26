"""Candidate operational action generation.

Candidates are only proposals. Every candidate must pass the independent
validator before it can be shown as executable. The list intentionally includes
DO_NOTHING so that the human can compare intervention against no intervention.
"""
from __future__ import annotations

import hashlib
import json

from .conflicts import primary_conflicts
from .state import format_minutes

CONFLICT_TYPES = [
    "SINGLE_LINE_CROSSING",
    "HEADWAY",
    "PLATFORM_CAPACITY",
    "JUNCTION_CONFLICT",
    "BLOCK_CLOSURE",
    "DELAY_RISK",
]
ACTION_TYPES = ["HOLD", "PRECEDENCE", "PLATFORM_REASSIGN", "SCHEDULE", "DO_NOTHING"]


def _candidate_id(action: dict) -> str:
    raw = json.dumps(action, sort_keys=True, default=str)
    return "CAND-" + hashlib.sha1(raw.encode()).hexdigest()[:10].upper()


def _candidate(action: dict, label: str, rationale: str, source: str = "HEURISTIC") -> dict:
    return {
        "id": _candidate_id(action),
        "label": label,
        "rationale": rationale,
        "source": source,
        "action": action,
    }


def generate_candidates(
    state: dict,
    conflicts: list[dict],
    *,
    cpsat_schedule: dict | None = None,
    max_candidates: int = 12,
) -> list[dict]:
    now = int(state["sim_time_min"])
    trains = {train["id"]: train for train in state["trains"]}
    candidates: list[dict] = [
        _candidate(
            {"type": "DO_NOTHING"},
            "Continue without intervention",
            "Preserve the current plan and observe the predicted conflicts.",
            source="BASELINE",
        )
    ]

    involved: list[str] = []
    for conflict in primary_conflicts(conflicts, limit=4):
        for train_id in conflict["trains"]:
            if train_id not in involved:
                involved.append(train_id)

    for train_id in involved:
        train = trains.get(train_id)
        if not train or train["status"] == "COMPLETED":
            continue
        if train["status"] == "AT_STATION":
            for hold_min in (5, 10, 15):
                if hold_min > int(train["max_hold_min"]):
                    continue
                candidates.append(
                    _candidate(
                        {
                            "type": "HOLD",
                            "train_id": train_id,
                            "station_id": train["station_id"],
                            "hold_min": hold_min,
                        },
                        f"Hold {train_id} at {train['station_id']} for {hold_min} min",
                        (
                            f"Delay {train_id} at {train['station_id']} to create a "
                            f"clearer crossing or platform window."
                        ),
                    )
                )
        if train["status"] != "COMPLETED":
            candidates.append(
                _candidate(
                    {
                        "type": "PRECEDENCE",
                        "train_id": train_id,
                        "priority_override": 0,
                    },
                    f"Give precedence to {train_id}",
                    (
                        f"Place {train_id} first in departure ordering. This changes "
                        f"precedence only; block and platform safety still apply."
                    ),
                )
            )

    # Intelligent crossing, precedence, and loop line overtaking actions
    for conflict in primary_conflicts(conflicts, limit=4):
        c_trains = [trains.get(tid) for tid in conflict["trains"] if trains.get(tid)]
        if len(c_trains) >= 2:
            c_trains.sort(key=lambda t: (int(t.get("priority", 3)), int(t.get("delay_min", 0))))
            higher_p = c_trains[0]
            lower_p = c_trains[1]

            # 1. Crossing meet-pass dynamic hold (Permutation 1: Hold lower priority train)
            if conflict["type"] in {"SINGLE_LINE_CROSSING", "CROSSING_CONFLICT"}:
                headway = int(conflict.get("evidence", {}).get("headway_min", 5))
                dur = max(3, int(conflict.get("end_min", now + 10)) - int(conflict.get("start_min", now)) + headway)
                
                # Option 1A: Regulate lower priority train
                if lower_p["status"] in {"AT_STATION", "WAITING"}:
                    st_id = lower_p.get("station_id") or lower_p.get("origin")
                    st_info = next((s for s in state["network"]["stations"] if s["id"] == st_id), None)
                    loop_note = "Station has loop line capacity." if (st_info and len(st_info.get("platforms", [])) > 1) else "Single platform station."
                    dynamic_hold = min(int(lower_p["max_hold_min"]), dur)
                    if dynamic_hold > 0:
                        candidates.append(
                            _candidate(
                                {
                                    "type": "HOLD",
                                    "train_id": lower_p["id"],
                                    "station_id": st_id,
                                    "hold_min": dynamic_hold,
                                    "crossing_sequence": f"{higher_p['id']}_BEFORE_{lower_p['id']}",
                                },
                                f"Sequence: {higher_p['id']} before {lower_p['id']} (Hold {lower_p['id']} at {st_id} for {dynamic_hold} min)",
                                f"Regulate lower-priority train {lower_p['id']} (priority {lower_p.get('priority')}) to clear single line block for {higher_p['id']} (priority {higher_p.get('priority')}). {loop_note}",
                            )
                        )

                # Option 1B: Alternative sequence: Regulate higher priority train (e.g. if higher priority already heavily delayed)
                if higher_p["status"] in {"AT_STATION", "WAITING"}:
                    st_id_h = higher_p.get("station_id") or higher_p.get("origin")
                    dynamic_hold_h = min(int(higher_p["max_hold_min"]), dur)
                    if dynamic_hold_h > 0:
                        candidates.append(
                            _candidate(
                                {
                                    "type": "HOLD",
                                    "train_id": higher_p["id"],
                                    "station_id": st_id_h,
                                    "hold_min": dynamic_hold_h,
                                    "crossing_sequence": f"{lower_p['id']}_BEFORE_{higher_p['id']}",
                                },
                                f"Alternative Sequence: {lower_p['id']} before {higher_p['id']} (Hold {higher_p['id']} at {st_id_h} for {dynamic_hold_h} min)",
                                f"Alternative crossing sequence: Hold {higher_p['id']} at {st_id_h} to allow {lower_p['id']} to clear the single line section first.",
                            )
                        )

                # Option 1C: Alternative crossing location at Malgaon Junction (MLG) with loop capacity
                if "MLG" in lower_p.get("route", []) and lower_p["status"] in {"AT_STATION", "WAITING"} and lower_p.get("station_id") != "MLG":
                    candidates.append(
                        _candidate(
                            {
                                "type": "HOLD",
                                "train_id": lower_p["id"],
                                "station_id": "MLG",
                                "hold_min": 5,
                                "crossing_location": "MLG",
                            },
                            f"Alternative Crossing Location: Advance meet to Malgaon Junction (MLG)",
                            f"Advance crossing point to junction station MLG (km 50) utilizing multi-platform loop capacity.",
                        )
                    )

            # 2. Overtaking on loop lines for double-line / following conflicts
            if conflict["type"] in {"OVERTAKING_CONFLICT", "HEADWAY"} and lower_p["status"] == "AT_STATION":
                st_id = lower_p["station_id"]
                st_info = next((s for s in state["network"]["stations"] if s["id"] == st_id), None)
                if st_info and len(st_info.get("platforms", [])) > 1:
                    candidates.append(
                        _candidate(
                            {
                                "type": "HOLD",
                                "train_id": lower_p["id"],
                                "station_id": st_id,
                                "hold_min": 8,
                            },
                            f"Hold {lower_p['id']} at {st_id} for 8 min (Loop overtake)",
                            f"Loop line overtake: Hold {lower_p['id']} (priority {lower_p.get('priority')}) to allow higher-priority {higher_p['id']} (priority {higher_p.get('priority')}) to overtake.",
                        )
                    )

    for conflict in primary_conflicts(conflicts, limit=2):
        if conflict["type"] != "PLATFORM_CAPACITY":
            continue
        station_id = conflict["location"].get("station_id")
        if not station_id:
            continue
        station = next(
            item for item in state["network"]["stations"] if item["id"] == station_id
        )
        for train_id in conflict["trains"]:
            train = trains.get(train_id)
            if not train:
                continue
            for platform in station["platforms"]:
                if platform == train.get("platform"):
                    continue
                candidates.append(
                    _candidate(
                        {
                            "type": "PLATFORM_REASSIGN",
                            "train_id": train_id,
                            "platform_id": platform,
                            "station_id": station_id,
                        },
                        f"Assign {train_id} to platform {platform} at {station_id}",
                        (
                            f"Use an available platform at {station_id} to relieve the "
                            f"projected platform capacity conflict."
                        ),
                    )
                )
                break

    if cpsat_schedule and cpsat_schedule.get("status") in {"OPTIMAL", "FEASIBLE"}:
        action = cpsat_schedule.get("action")
        if action:
            candidates.append(
                _candidate(
                    action,
                    "Apply validated CP-SAT schedule",
                    (
                        "Use the optimizer's feasible schedule with explicit holding and "
                        "precedence instructions. The schedule is independently re-validated."
                    ),
                    source="CP_SAT",
                )
            )

    deduped: dict[str, dict] = {}
    for candidate in candidates:
        deduped.setdefault(candidate["id"], candidate)
    ordered = sorted(
        deduped.values(),
        key=lambda item: (
            0 if item["source"] == "CP_SAT" else 1 if item["source"] == "BASELINE" else 2,
            item["label"],
        ),
    )
    return ordered[:max_candidates]


def describe_action(action: dict) -> str:
    action_type = action.get("type")
    if action_type == "HOLD":
        return (
            f"Hold train {action.get('train_id')} at {action.get('station_id')} for "
            f"{action.get('hold_min')} minutes."
        )
    if action_type == "PRECEDENCE":
        return f"Give departure precedence to train {action.get('train_id')}."
    if action_type == "PLATFORM_REASSIGN":
        return (
            f"Assign train {action.get('train_id')} to platform "
            f"{action.get('platform_id')} at {action.get('station_id')}."
        )
    if action_type == "SCHEDULE":
        holds = action.get("holds", [])
        if not holds:
            return "Apply the validated CP-SAT schedule with precedence ordering."
        parts = [
            f"hold {hold['train_id']} for {hold['hold_min']} min at {hold['station_id']}"
            for hold in holds
        ]
        return "Apply the validated CP-SAT schedule: " + "; ".join(parts) + "."
    return "Continue without intervention."


def baseline_rank(candidates: list[dict]) -> list[dict]:
    """Deterministic baseline heuristic used for comparison, not for safety.

    Preference order: validated CP-SAT schedule, minimal hold of the
    lowest-priority involved train, precedence, no action. This is intentionally
    simple and is reported as a baseline alongside PPO and measured outcomes.
    """
    def key(candidate: dict) -> tuple:
        action = candidate["action"]
        action_type = action.get("type")
        if action_type == "SCHEDULE":
            return (0, 0, candidate["id"])
        if action_type == "HOLD":
            return (1, int(action.get("hold_min", 99)), candidate["id"])
        if action_type == "PRECEDENCE":
            return (2, 0, candidate["id"])
        if action_type == "PLATFORM_REASSIGN":
            return (3, 0, candidate["id"])
        return (4, 0, candidate["id"])

    return sorted(candidates, key=key)
