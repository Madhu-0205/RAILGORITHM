"""Simulation lifecycle, disruption and what-if services."""
from __future__ import annotations

import copy
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..domain.conflicts import detect_conflicts
from ..domain.state import (
    SimulationError,
    advance,
    apply_action,
    format_minutes,
    initialise_state,
    state_metrics,
    validate_state_integrity,
)
from ..domain.validator import evaluate_candidate, validate_action
from ..models import Simulation, User
from .audit import append_audit

DISRUPTION_TYPES = {
    "BLOCK_CLOSURE",
    "SECTION_CLOSURE",
    "PLATFORM_OUTAGE",
    "TRAIN_DELAY",
    "PRIORITY_CHANGE",
}


class ServiceError(Exception):
    def __init__(self, message: str, status_code: int = 400):
        super().__init__(message)
        self.message = message
        self.status_code = status_code


def _state_clone(simulation: Simulation) -> dict:
    return copy.deepcopy(simulation.state)


def _save(db: Session, simulation: Simulation, state: dict) -> None:
    simulation.state = state
    simulation.sim_time_min = int(state["sim_time_min"])
    simulation.state_version = int(state["version"])
    simulation.status = state["status"]
    simulation.updated_at = datetime.now(timezone.utc)
    db.add(simulation)
    db.flush()


def create_simulation(
    db: Session, *, scenario_key: str, seed: int | None, actor: User
) -> Simulation:
    try:
        state = initialise_state(scenario_key, seed_override=seed)
    except KeyError as exc:
        raise ServiceError(str(exc), 404) from exc
    state["scenario_date"] = datetime.now(timezone.utc).date().isoformat()
    simulation = Simulation(
        scenario_key=scenario_key,
        name=state["scenario_name"],
        seed=state["seed"],
        status="RUNNING",
        sim_time_min=state["sim_time_min"],
        state_version=state["version"],
        state=state,
        label="SYNTHETIC",
        created_by=actor.username,
    )
    db.add(simulation)
    db.flush()
    append_audit(
        db,
        event_type="SIMULATION_CREATED",
        actor=actor.username,
        actor_role=actor.role,
        simulation_id=simulation.id,
        payload={
            "scenario_key": scenario_key,
            "seed": simulation.seed,
            "state_version": simulation.state_version,
            "label": "SYNTHETIC",
        },
    )
    db.commit()
    db.refresh(simulation)
    return simulation


def advance_simulation(
    db: Session, simulation: Simulation, *, minutes: int, actor: User
) -> Simulation:
    if minutes < 1 or minutes > 180:
        raise ServiceError("Advance minutes must be between 1 and 180")
    if simulation.status == "PAUSED":
        raise ServiceError("Simulation is paused. Resume it before advancing.", 409)
    if simulation.status == "COMPLETED":
        raise ServiceError("Simulation is already complete.", 409)
    state = _state_clone(simulation)
    try:
        advance(state, minutes)
    except SimulationError as exc:
        raise ServiceError(str(exc), 409) from exc
    _save(db, simulation, state)
    append_audit(
        db,
        event_type="SIMULATION_ADVANCED",
        actor=actor.username,
        actor_role=actor.role,
        simulation_id=simulation.id,
        payload={
            "minutes": minutes,
            "simulation_time": format_minutes(state["sim_time_min"]),
            "state_version": state["version"],
            "metrics": state_metrics(state),
            "status": state["status"],
        },
    )
    db.commit()
    db.refresh(simulation)
    return simulation


def set_pause_state(
    db: Session, simulation: Simulation, *, paused: bool, actor: User
) -> Simulation:
    if simulation.status == "COMPLETED":
        raise ServiceError("Completed simulations cannot be paused or resumed.", 409)
    state = _state_clone(simulation)
    state["status"] = "PAUSED" if paused else "RUNNING"
    state["version"] = int(state["version"]) + 1
    _save(db, simulation, state)
    append_audit(
        db,
        event_type="SIMULATION_PAUSED" if paused else "SIMULATION_RESUMED",
        actor=actor.username,
        actor_role=actor.role,
        simulation_id=simulation.id,
        payload={"state_version": state["version"]},
    )
    db.commit()
    db.refresh(simulation)
    return simulation


def reset_simulation(db: Session, simulation: Simulation, *, actor: User) -> Simulation:
    state = initialise_state(simulation.scenario_key)
    state["scenario_date"] = simulation.state.get(
        "scenario_date", datetime.now(timezone.utc).date().isoformat()
    )
    # Keep version monotonic so old recommendations can never look current.
    state["version"] = int(simulation.state_version) + 1
    state["seed"] = simulation.seed
    _save(db, simulation, state)
    append_audit(
        db,
        event_type="SIMULATION_RESET",
        actor=actor.username,
        actor_role=actor.role,
        simulation_id=simulation.id,
        payload={
            "scenario_key": simulation.scenario_key,
            "seed": simulation.seed,
            "state_version": state["version"],
        },
    )
    db.commit()
    db.refresh(simulation)
    return simulation


def _block_exists(state: dict, block_id: str) -> bool:
    return any(
        block["id"] == block_id
        for section in state["network"]["sections"]
        for block in section["blocks"]
    )


def _section_exists(state: dict, section_id: str) -> bool:
    return any(section["id"] == section_id for section in state["network"]["sections"])


def _platform_exists(state: dict, station_id: str, platform_id: str) -> bool:
    station = next(
        (item for item in state["network"]["stations"] if item["id"] == station_id), None
    )
    return bool(station and platform_id in station["platforms"])


def apply_disruption(
    db: Session,
    simulation: Simulation,
    *,
    disruption_type: str,
    payload: dict,
    actor: User,
) -> Simulation:
    if disruption_type not in DISRUPTION_TYPES:
        raise ServiceError(f"Unsupported disruption type '{disruption_type}'")
    state = _state_clone(simulation)
    now = int(state["sim_time_min"])
    if disruption_type in {"BLOCK_CLOSURE", "SECTION_CLOSURE"}:
        start_min = int(payload.get("start_min", now))
        end_min = int(payload.get("end_min", now + 30))
        reason = str(payload.get("reason", "Temporary engineering block")).strip()
        if end_min <= start_min:
            raise ServiceError("Closure end must be after closure start")
        if end_min <= now:
            raise ServiceError("Closure must end after the current simulation time")
        if disruption_type == "BLOCK_CLOSURE":
            block_id = payload.get("block_id")
            if not block_id or not _block_exists(state, block_id):
                raise ServiceError(f"Unknown block '{block_id}'")
            blocks = [block_id]
        else:
            section_id = payload.get("section_id")
            if not section_id or not _section_exists(state, section_id):
                raise ServiceError(f"Unknown section '{section_id}'")
            section = next(
                item for item in state["network"]["sections"] if item["id"] == section_id
            )
            blocks = [block["id"] for block in section["blocks"]]
        for block_id in blocks:
            if start_min <= now < end_min:
                occupancy = state["block_occupancy"].get(block_id, {})
                if occupancy.get("train_id"):
                    raise ServiceError(
                        f"Block {block_id} is occupied by {occupancy['train_id']}; "
                        "it cannot be closed immediately. Schedule the closure later.",
                        409,
                    )
            for existing in state["closures"]:
                if (
                    existing["block_id"] == block_id
                    and existing["start_min"] < end_min
                    and start_min < existing["end_min"]
                ):
                    raise ServiceError(
                        f"Block {block_id} already has an overlapping closure", 409
                    )
            state["closures"].append(
                {
                    "id": f"CLS-{block_id}-{start_min}",
                    "block_id": block_id,
                    "start_min": start_min,
                    "end_min": end_min,
                    "reason": reason,
                    "created_by": actor.username,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
    elif disruption_type == "PLATFORM_OUTAGE":
        station_id = payload.get("station_id")
        platform_id = payload.get("platform_id")
        if not _platform_exists(state, station_id, platform_id):
            raise ServiceError(f"Unknown platform '{station_id}/{platform_id}'")
        start_min = int(payload.get("start_min", now))
        end_min = int(payload.get("end_min", now + 30))
        if end_min <= start_min:
            raise ServiceError("Outage end must be after outage start")
        if end_min <= now:
            raise ServiceError("Outage must end after the current simulation time")
        current = state["platform_occupancy"].get(station_id, {}).get(platform_id)
        if start_min <= now < end_min and current:
            raise ServiceError(
                f"Platform {station_id}/{platform_id} is occupied by {current}; "
                "schedule the outage later.",
                409,
            )
        state["platform_outages"].append(
            {
                "id": f"OUT-{station_id}-{platform_id}-{start_min}",
                "station_id": station_id,
                "platform_id": platform_id,
                "start_min": start_min,
                "end_min": end_min,
                "reason": str(payload.get("reason", "Platform unavailable")),
                "created_by": actor.username,
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )
    elif disruption_type == "TRAIN_DELAY":
        train_id = payload.get("train_id")
        delay_min = int(payload.get("delay_min", 0))
        if delay_min <= 0 or delay_min > 180:
            raise ServiceError("Delay must be between 1 and 180 minutes")
        train = next((item for item in state["trains"] if item["id"] == train_id), None)
        if not train:
            raise ServiceError(f"Unknown train '{train_id}'", 404)
        if train["status"] != "AT_STATION":
            raise ServiceError(
                "Only a train at a station can receive an injected departure delay", 409
            )
        train["ready_departure_min"] = max(
            now, int(train.get("ready_departure_min") or now)
        ) + delay_min
        train["delay_min"] = int(train["delay_min"]) + delay_min
        train["waiting_reason"] = "INJECTED_DELAY"
    elif disruption_type == "PRIORITY_CHANGE":
        train_id = payload.get("train_id")
        priority = int(payload.get("priority", 5))
        if not 0 <= priority <= 9:
            raise ServiceError("Priority override must be between 0 and 9")
        train = next((item for item in state["trains"] if item["id"] == train_id), None)
        if not train:
            raise ServiceError(f"Unknown train '{train_id}'", 404)
        train["priority_override"] = priority
    state["version"] = int(state["version"]) + 1
    _save(db, simulation, state)
    append_audit(
        db,
        event_type="DISRUPTION_APPLIED",
        actor=actor.username,
        actor_role=actor.role,
        simulation_id=simulation.id,
        payload={
            "disruption_type": disruption_type,
            "payload": payload,
            "state_version": state["version"],
            "simulation_time": format_minutes(now),
        },
    )
    db.commit()
    db.refresh(simulation)
    return simulation


def simulation_view(simulation: Simulation, state: dict | None = None) -> dict:
    state = state or simulation.state
    network = state["network"]
    now = int(state["sim_time_min"])
    conflicts = detect_conflicts(state, settings.recommendation_horizon_min)
    trains = []
    for train in state["trains"]:
        next_index = int(train["route_index"]) + 1
        next_station = train["route"][next_index] if next_index < len(train["route"]) else None
        trains.append(
            {
                "id": train["id"],
                "name": train["name"],
                "train_type": train["train_type"],
                "priority": train["priority"],
                "effective_priority": train.get("priority_override")
                if train.get("priority_override") is not None
                else train["priority"],
                "direction": train["direction"],
                "origin": train["origin"],
                "destination": train["destination"],
                "status": train["status"],
                "station_id": train.get("station_id"),
                "next_station": next_station,
                "section_id": train.get("section_id"),
                "block_id": train.get("block_id"),
                "platform": train.get("platform"),
                "delay_min": train["delay_min"],
                "projected_delay_min": train.get("current_delay_min", train["delay_min"]),
                "scheduled_departure": (
                    format_minutes(train["schedule"][train["route_index"]].get("departure_min"))
                    if train["route_index"] < len(train["schedule"])
                    else None
                ),
                "scheduled_arrival_next": (
                    format_minutes(train["schedule"][next_index]["arrival_min"])
                    if next_index < len(train["schedule"])
                    else None
                ),
                "hold_until": (
                    format_minutes(train.get("hold_until_min"))
                    if train.get("hold_until_min")
                    else None
                ),
                "waiting_reason": train.get("waiting_reason"),
                "total_wait_min": train.get("total_wait_min", 0),
                "route": train["route"],
                "label": "SYNTHETIC",
            }
        )
    block_occupancy = []
    for section in network["sections"]:
        for block in section["blocks"]:
            occupancy = state["block_occupancy"].get(block["id"], {})
            block_occupancy.append(
                {
                    "block_id": block["id"],
                    "section_id": section["id"],
                    "from_station": section["from_station"],
                    "to_station": section["to_station"],
                    "mode": section["mode"],
                    "direction": block["direction"],
                    "run_time_min": block["run_time_min"],
                    "headway_min": section["headway_min"],
                    "occupied_by": occupancy.get("train_id"),
                    "entry_min": occupancy.get("entry_min"),
                    "exit_min": occupancy.get("exit_min"),
                    "closure": next(
                        (
                            closure
                            for closure in state["closures"]
                            if closure["block_id"] == block["id"]
                            and closure["start_min"] <= now < closure["end_min"]
                        ),
                        None,
                    ),
                }
            )
    platforms = []
    for station in network["stations"]:
        for platform in station["platforms"]:
            occupied_by = state["platform_occupancy"].get(station["id"], {}).get(platform)
            outage = next(
                (
                    outage
                    for outage in state["platform_outages"]
                    if outage["station_id"] == station["id"]
                    and outage["platform_id"] == platform
                    and outage["start_min"] <= now < outage["end_min"]
                ),
                None,
            )
            platforms.append(
                {
                    "station_id": station["id"],
                    "platform_id": platform,
                    "occupied_by": occupied_by,
                    "outage": outage,
                    "status": "OCCUPIED" if occupied_by else ("OUTAGE" if outage else "AVAILABLE"),
                }
            )
    return {
        "id": simulation.id,
        "scenario_key": simulation.scenario_key,
        "name": simulation.name,
        "seed": simulation.seed,
        "status": simulation.status,
        "label": simulation.label,
        "scenario_date": state.get("scenario_date"),
        "timezone": network.get("timezone", "Asia/Kolkata"),
        "sim_time": format_minutes(now),
        "sim_time_min": now,
        "state_version": simulation.state_version,
        "network": network,
        "trains": trains,
        "conflicts": conflicts,
        "block_occupancy": block_occupancy,
        "platforms": platforms,
        "closures": state["closures"],
        "platform_outages": state["platform_outages"],
        "metrics": state_metrics(state),
        "events": state["events"][-80:],
        "data_label": "SYNTHETIC — NOT REAL INDIAN RAILWAYS DATA",
        "created_by": simulation.created_by,
        "created_at": simulation.created_at.isoformat(),
        "updated_at": simulation.updated_at.isoformat(),
    }


def run_what_if(
    db: Session,
    simulation: Simulation,
    *,
    action: dict,
    minutes: int,
    actor: User,
) -> dict:
    if minutes < 5 or minutes > 120:
        raise ServiceError("What-if horizon must be between 5 and 120 minutes")
    state = simulation.state
    validation = validate_action(state, action)
    if validation["status"] in {"INVALID", "INCOMPLETE_DATA"}:
        return {
            "status": "REJECTED",
            "validation": validation,
            "message": "Hypothetical action failed independent validation; no comparison was run.",
            "applied_to_live_simulation": False,
        }
    baseline = evaluate_candidate(state, {"type": "DO_NOTHING"}, minutes=minutes)
    candidate = evaluate_candidate(state, action, minutes=minutes)
    if candidate["status"] in {"INVALID", "INCOMPLETE_DATA"}:
        return {
            "status": "REJECTED",
            "validation": candidate["validation"],
            "message": "Hypothetical action produced an invalid simulated outcome.",
            "applied_to_live_simulation": False,
        }
    baseline_conflicts = detect_conflicts(baseline["state"], 45) if baseline.get("state") else []
    candidate_conflicts = detect_conflicts(candidate["state"], 45) if candidate.get("state") else []
    baseline_metrics = baseline.get("metrics") or {}
    candidate_metrics = candidate.get("metrics") or {}
    append_audit(
        db,
        event_type="WHAT_IF_RUN",
        actor=actor.username,
        actor_role=actor.role,
        simulation_id=simulation.id,
        payload={
            "action": action,
            "minutes": minutes,
            "state_version": simulation.state_version,
            "applied_to_live_simulation": False,
        },
    )
    db.commit()
    return {
        "status": "COMPLETED",
        "action": action,
        "minutes": minutes,
        "validation": validation,
        "outcome_validation": candidate["validation"],
        "baseline_metrics": baseline_metrics,
        "hypothetical_metrics": candidate_metrics,
        "deltas": {
            "total_delay_min": candidate_metrics.get("total_delay_min", 0)
            - baseline_metrics.get("total_delay_min", 0),
            "average_delay_min": candidate_metrics.get("average_delay_min", 0)
            - baseline_metrics.get("average_delay_min", 0),
            "on_time_performance_pct": candidate_metrics.get("on_time_performance_pct", 0)
            - baseline_metrics.get("on_time_performance_pct", 0),
            "conflicts": len(
                [item for item in candidate_conflicts if item["type"] != "DELAY_RISK"]
            )
            - len([item for item in baseline_conflicts if item["type"] != "DELAY_RISK"]),
        },
        "baseline_conflicts": [item for item in baseline_conflicts if item["type"] != "DELAY_RISK"],
        "hypothetical_conflicts": [item for item in candidate_conflicts if item["type"] != "DELAY_RISK"],
        "baseline_trains": [
            {
                "train_id": train["id"],
                "status": train["status"],
                "delay_min": train["delay_min"],
            }
            for train in (baseline["state"]["trains"] if baseline.get("state") else [])
        ],
        "hypothetical_trains": [
            {
                "train_id": train["id"],
                "status": train["status"],
                "delay_min": train["delay_min"],
            }
            for train in (candidate["state"]["trains"] if candidate.get("state") else [])
        ],
        "applied_to_live_simulation": False,
        "data_label": "SYNTHETIC",
        "note": (
            "What-if results come from a cloned simulation. The live scenario, "
            "state version and audit decisions are unchanged."
        ),
    }


def state_integrity(state: dict) -> list[str]:
    return validate_state_integrity(state)
