"""Explicit, configurable simulation assumptions and constraint specification.

Version 2.0 requires every modelling assumption to be inspectable rather than
buried in code. This module is the single source of truth for:

* the values used by the simulation, validator and optimizer;
* where each value comes from (configured synthetic assumption, not railway law);
* which hard constraint each value supports;
* how a deployment can override it through environment variables.

Nothing here is a claim about real Indian Railways rules. The values are
deliberately conservative synthetic inputs so that behaviour is measurable and
reproducible.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from typing import Any

SIMULATION_MODEL_VERSION = "simulation-2.0.0"
CONSTRAINT_SPEC_VERSION = "constraints-2.0.0"
ASSUMPTION_SPEC_VERSION = "assumptions-2.0.0"

SOURCE = "Configured synthetic assumption — not verified Indian Railways rules."


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Assumption:
    id: str
    category: str
    title: str
    value: Any
    unit: str
    source: str
    configurable_via: str | None = None
    affects: tuple[str, ...] = ()


def _build_assumptions() -> tuple[Assumption, ...]:
    return (
        Assumption(
            "NET-001",
            "network",
            "Synthetic linear section",
            "5 stations, 4 sections, 2 single-line and 2 double-line sections",
            "topology",
            SOURCE,
            affects=("routing", "block occupancy", "crossing conflicts"),
        ),
        Assumption(
            "NET-002",
            "network",
            "Junction throat capacity",
            _int_env("RAILGORITHM_JUNCTION_THROAT_CAPACITY", 2),
            "simultaneous movements",
            SOURCE,
            "RAILGORITHM_JUNCTION_THROAT_CAPACITY",
            ("junction conflicts", "optimizer cumulative constraint"),
        ),
        Assumption(
            "NET-003",
            "network",
            "Block run times",
            "Per-block configured run time multiplied by train category speed factor",
            "minutes",
            SOURCE,
            affects=("timetable", "projection", "optimizer"),
        ),
        Assumption(
            "TRN-001",
            "trains",
            "Train categories and priorities",
            "EXPRESS=1, PASSENGER=3, MEMU=4, FREIGHT=5 (lower number = higher priority)",
            "priority class",
            SOURCE,
            affects=("weighted delay", "precedence policy", "hold policy"),
        ),
        Assumption(
            "TRN-002",
            "trains",
            "Maximum hold policy",
            "EXPRESS 20, PASSENGER 30, MEMU 25, FREIGHT 45",
            "minutes",
            SOURCE,
            affects=("hard hold policy", "candidate eligibility"),
        ),
        Assumption(
            "TRN-003",
            "trains",
            "Minimum dwell",
            "EXPRESS 1, PASSENGER 2, MEMU 1, FREIGHT 2",
            "minutes",
            SOURCE,
            affects=("route continuity", "platform occupancy"),
        ),
        Assumption(
            "TRN-004",
            "trains",
            "Speed factors",
            "EXPRESS 0.85, PASSENGER 1.00, MEMU 1.00, FREIGHT 1.25",
            "multiplier",
            SOURCE,
            affects=("run times", "overtaking conflicts"),
        ),
        Assumption(
            "HDW-001",
            "headway",
            "Section headway",
            "Per-section configured value (default 3 minutes; S1 4 minutes)",
            "minutes",
            "RAILGORITHM_HEADWAY_OVERRIDE"
            if os.getenv("RAILGORITHM_HEADWAY_OVERRIDE")
            else SOURCE,
            "RAILGORITHM_HEADWAY_OVERRIDE",
            ("headway conflicts", "block disjunction"),
        ),
        Assumption(
            "PLT-001",
            "platforms",
            "Platform capacity",
            "Configured platforms per station minus active outages",
            "trains",
            SOURCE,
            affects=("platform conflicts", "optimizer cumulative constraint"),
        ),
        Assumption(
            "PLT-002",
            "platforms",
            "Platform assignment",
            "First available platform, honouring an explicit preference",
            "rule",
            SOURCE,
            affects=("platform occupancy", "reassignment candidates"),
        ),
        Assumption(
            "MNT-001",
            "maintenance",
            "Temporary block closures",
            "Half-open interval [start, end); overlapping use is infeasible",
            "interval",
            SOURCE,
            affects=("closure conflicts", "optimizer disjunction"),
        ),
        Assumption(
            "DIS-001",
            "disruptions",
            "Disruption catalogue",
            "BLOCK_CLOSURE, SECTION_CLOSURE, PLATFORM_OUTAGE, TRAIN_DELAY, PRIORITY_CHANGE, SPEED_RESTRICTION",
            "catalogue",
            SOURCE,
            affects=("conflict evidence", "scenario construction"),
        ),
        Assumption(
            "TIM-001",
            "time",
            "Clock and horizon",
            "Integer minutes since 00:00; planning horizon and application window are configurable",
            "minutes",
            SOURCE,
            "RAILGORITHM_RECOMMENDATION_HORIZON / RAILGORITHM_DECISION_APPLY_MINUTES",
            ("projection", "candidate measurement", "conflict window"),
        ),
        Assumption(
            "OCC-001",
            "occupancy",
            "Time-varying occupancy",
            "Occupancy is recomputed each simulated minute from train state, not from a static table",
            "rule",
            SOURCE,
            affects=("conflicts", "utilisation metrics"),
        ),
        Assumption(
            "CSC-001",
            "cascading",
            "Cascading delay model",
            "A delayed train propagates delay through its own remaining legs; cross-train propagation is via resource contention only",
            "rule",
            SOURCE,
            affects=("delay-risk conflicts", "measured outcomes"),
        ),
        Assumption(
            "VAL-001",
            "validation",
            "Independent validation",
            "Validator re-checks topology, occupancy, headway, closures, platforms, hold policy and solver status",
            "rule",
            SOURCE,
            affects=("candidate eligibility", "decision re-validation"),
        ),
        Assumption(
            "OPT-001",
            "optimization",
            "CP-SAT objective",
            "Weighted final delay + departure delay + hold penalty; weights configurable per profile",
            "objective",
            SOURCE,
            "RAILGORITHM_OBJECTIVE_PROFILE / RAILGORITHM_CP_SAT_TIME_LIMIT",
            ("schedule selection", "trade-off reporting"),
        ),
        Assumption(
            "PPO-001",
            "learning",
            "PPO role",
            "Ranks pre-validated candidates only; never creates, filters or executes an action",
            "rule",
            SOURCE,
            affects=("ranking", "disagreement reporting"),
        ),
    )


ASSUMPTIONS: tuple[Assumption, ...] = _build_assumptions()
ASSUMPTION_MAP = {item.id: item for item in ASSUMPTIONS}


@dataclass(frozen=True)
class Constraint:
    id: str
    name: str
    kind: str  # HARD | SOFT
    scope: str
    statement: str
    enforced_by: tuple[str, ...]
    assumption_ids: tuple[str, ...] = ()
    failure_effect: str = "Candidate is ineligible; the recommendation is not executable."


CONSTRAINTS: tuple[Constraint, ...] = (
    Constraint(
        "HC-001",
        "Block exclusivity",
        "HARD",
        "block",
        "At most one train may occupy a block at a time.",
        ("simulation", "validator", "optimizer"),
        ("NET-001",),
    ),
    Constraint(
        "HC-002",
        "Section headway",
        "HARD",
        "section",
        "Successive block uses must be separated by the configured section headway.",
        ("conflicts", "validator", "optimizer"),
        ("HDW-001",),
    ),
    Constraint(
        "HC-003",
        "Single-line direction",
        "HARD",
        "section",
        "A single-line bidirectional block cannot serve opposing movements concurrently.",
        ("conflicts", "validator", "optimizer"),
        ("NET-001",),
    ),
    Constraint(
        "HC-004",
        "Directional block restriction",
        "HARD",
        "block",
        "A train may only use a block whose configured direction matches its movement.",
        ("simulation", "validator", "optimizer"),
        ("NET-001",),
    ),
    Constraint(
        "HC-005",
        "Platform capacity",
        "HARD",
        "station",
        "Concurrent platform demand must not exceed available platforms minus outages.",
        ("conflicts", "validator", "optimizer"),
        ("PLT-001",),
    ),
    Constraint(
        "HC-006",
        "Junction throat capacity",
        "HARD",
        "junction",
        "Simultaneous junction throat movements must not exceed the configured capacity.",
        ("conflicts", "validator", "optimizer"),
        ("NET-002",),
    ),
    Constraint(
        "HC-007",
        "Maintenance / closure respect",
        "HARD",
        "block",
        "No train may use a block during a configured closure.",
        ("simulation", "conflicts", "validator", "optimizer"),
        ("MNT-001",),
    ),
    Constraint(
        "HC-008",
        "No departure before timetable",
        "HARD",
        "train",
        "A scheduled departure may not be advanced before its published time.",
        ("validator", "optimizer"),
        ("TRN-001",),
    ),
    Constraint(
        "HC-009",
        "Route continuity and dwell",
        "HARD",
        "train",
        "A train must follow its route in order and respect minimum dwell at stations.",
        ("simulation", "validator", "optimizer"),
        ("TRN-003",),
    ),
    Constraint(
        "HC-010",
        "Maximum hold policy",
        "HARD",
        "train",
        "A planned hold may not exceed the category limit.",
        ("simulation", "validator", "optimizer"),
        ("TRN-002",),
    ),
    Constraint(
        "HC-011",
        "Platform outage respect",
        "HARD",
        "platform",
        "A train may not occupy a platform during a configured outage.",
        ("simulation", "validator"),
        ("PLT-001",),
    ),
    Constraint(
        "HC-012",
        "Action applicability",
        "HARD",
        "action",
        "The proposed action must be applicable to the current state and supported by the action schema.",
        ("validator",),
        ("VAL-001",),
    ),
    Constraint(
        "SC-001",
        "Priority policy",
        "SOFT",
        "train",
        "Higher-priority trains should not be delayed materially more than lower-priority trains.",
        ("validator", "optimizer"),
        ("TRN-001", "OPT-001"),
        "Reported as a warning; never overrides a hard constraint.",
    ),
    Constraint(
        "SC-002",
        "En-route waiting policy",
        "SOFT",
        "train",
        "En-route waiting beyond the category guide is reported for controller review.",
        ("validator",),
        ("TRN-002",),
        "Reported as a warning; never overrides a hard constraint.",
    ),
    Constraint(
        "SC-003",
        "Delay policy",
        "SOFT",
        "train",
        "Large final delays are surfaced for operational review.",
        ("validator",),
        ("TRN-002",),
        "Reported as a warning; never overrides a hard constraint.",
    ),
)


def assumption_manifest() -> dict:
    return {
        "version": ASSUMPTION_SPEC_VERSION,
        "simulation_model_version": SIMULATION_MODEL_VERSION,
        "label": "SYNTHETIC",
        "disclaimer": (
            "These are configurable synthetic assumptions, not verified Indian "
            "Railways operating rules. Override them only with qualified review."
        ),
        "assumptions": [asdict(item) for item in ASSUMPTIONS],
    }


def constraint_manifest() -> dict:
    return {
        "version": CONSTRAINT_SPEC_VERSION,
        "label": "SYNTHETIC",
        "disclaimer": (
            "Hard constraints are evaluated against configured synthetic "
            "assumptions. They do not certify real-world railway safety."
        ),
        "constraints": [asdict(item) for item in CONSTRAINTS],
        "counts": {
            "hard": sum(1 for item in CONSTRAINTS if item.kind == "HARD"),
            "soft": sum(1 for item in CONSTRAINTS if item.kind == "SOFT"),
        },
    }


def objective_weights(profile: str = "balanced") -> dict[str, int]:
    """Configurable CP-SAT objective weights.

    The profiles are measured alternatives, not claims of optimality. The
    pipeline defaults to ``balanced``; reports may compare profiles.
    """
    profiles = {
        "balanced": {"final_delay": 100, "departure_delay": 2, "hold": 3, "throughput": 0},
        "delay_focused": {"final_delay": 160, "departure_delay": 4, "hold": 1, "throughput": 0},
        "priority_focused": {"final_delay": 100, "departure_delay": 2, "hold": 2, "throughput": 0},
        "throughput_focused": {"final_delay": 80, "departure_delay": 1, "hold": 2, "throughput": 5},
    }
    return profiles.get(profile, profiles["balanced"])


def configured_objective_profile() -> str:
    return os.getenv("RAILGORITHM_OBJECTIVE_PROFILE", "balanced")
