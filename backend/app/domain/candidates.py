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
