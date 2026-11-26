"""Simulation, dashboard, disruption and what-if endpoints."""
from __future__ import annotations

import copy
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, get_simulation, require_roles
from ..domain.conflicts import detect_conflicts
from ..domain.optimizer import OPTIMIZER_VERSION
from ..domain.ppo import metadata_summary
from ..models import ModelVersion, Simulation, User
from ..schemas import (
    AdvanceRequest,
    DisruptionRequest,
    GenerateRecommendationRequest,
    PauseRequest,
    SimulationCreate,
    WhatIfRequest,
)
from ..services.analytics_service import (
    analytics as build_analytics,
    section_controller_kpis,
    station_master_kpis,
)
from ..services.recommendation_service import (
    generate_record,
    list_records,
    serialize,
)
from ..services.simulation_service import (
    ServiceError,
    advance_simulation,
    apply_disruption,
    create_simulation,
    reset_simulation,
    run_what_if,
    set_pause_state,
    simulation_view,
)

router = APIRouter(prefix="/simulations", tags=["simulations"])


def _scoped_conflicts(simulation: Simulation, user: User, conflicts: list[dict]) -> list[dict]:
    if user.is_admin():
        return conflicts
    if user.is_station_master():
        allowed_stations = set(user.get_stations())
        if not allowed_stations:
            return []
        result = []
        for conflict in conflicts:
            location = conflict.get("location", {})
            if location.get("station_id") in allowed_stations:
                result.append(conflict)
                continue
            if location.get("section_id"):
                section = next(
                    (
                        item
                        for item in simulation.state["network"]["sections"]
                        if item["id"] == location["section_id"]
                    ),
                    None,
                )
                if section and (section["from_station"] in allowed_stations or section["to_station"] in allowed_stations):
                    result.append(conflict)
                    continue
            if location.get("block_id"):
                for section in simulation.state["network"]["sections"]:
                    if any(block["id"] == location["block_id"] for block in section["blocks"]):
                        if section["from_station"] in allowed_stations or section["to_station"] in allowed_stations:
                            result.append(conflict)
                        break
        return result
    if user.is_section_controller() and user.control_area not in {None, "CORRIDOR"}:
        allowed_stations = set(user.get_stations())
        result = []
        for conflict in conflicts:
            location = conflict.get("location", {})
            if location.get("station_id") in allowed_stations:
                result.append(conflict)
                continue
            if location.get("section_id"):
                section = next(
                    (
                        item
                        for item in simulation.state["network"]["sections"]
                        if item["id"] == location["section_id"]
                    ),
                    None,
                )
                if section and (section["from_station"] in allowed_stations or section["to_station"] in allowed_stations):
                    result.append(conflict)
                    continue
            if location.get("block_id"):
                for section in simulation.state["network"]["sections"]:
                    if any(block["id"] == location["block_id"] for block in section["blocks"]):
                        if section["from_station"] in allowed_stations or section["to_station"] in allowed_stations:
                            result.append(conflict)
                        break
        return result
    return conflicts


def _recommendation_summary(db: Session, record, simulation: Simulation) -> dict:
    payload = record.payload
    recommended = payload.get("recommended") or {}
    pred_reg = payload.get("predictive_regulation") or {}
    urgency = pred_reg.get("decision_urgency") or {}
    dq = payload.get("data_quality") or {}
    return {
        "id": record.id,
        "status": record.status,
        "evidence_status": record.evidence_status,
        "disagreement": record.disagreement,
        "created_at": record.created_at.isoformat(),
        "headline": (payload.get("explanation") or {}).get("headline"),
        "recommended_label": recommended.get("label"),
        "recommended_candidate_id": recommended.get("candidate_id"),
        "affected_stations": payload.get("affected_stations", []),
        "is_stale": record.status in {"PENDING", "STALE"}
        and int(record.state_version) != int(simulation.state_version),
        "state_version": record.state_version,
        "sim_time": payload.get("simulation_time"),
        "urgency_category": urgency.get("urgency_category", "MONITORING"),
        "overall_quality_state": dq.get("overall_quality_state", "SIMULATION"),
    }


@router.get("")
def list_simulations(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    records = db.execute(
        select(Simulation).order_by(Simulation.created_at.desc())
    ).scalars().all()
    return {
        "simulations": [
            {
                "id": item.id,
                "name": item.name,
                "scenario_key": item.scenario_key,
                "status": item.status,
                "sim_time_min": item.sim_time_min,
                "state_version": item.state_version,
                "seed": item.seed,
                "label": item.label,
                "created_at": item.created_at.isoformat(),
                "created_by": item.created_by,
            }
            for item in records
        ],
        "label": "SYNTHETIC",
    }


@router.post("")
def create(
    payload: SimulationCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SECTION_MASTER")),
) -> dict:
    simulation = create_simulation(
        db, scenario_key=payload.scenario_key, seed=payload.seed, actor=user
    )
    return simulation_view(simulation)


@router.get("/{simulation_id}")
def get_simulation_detail(
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(get_current_user),
) -> dict:
    return simulation_view(simulation)


@router.get("/{simulation_id}/dashboard")
def dashboard(
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(get_current_user),
) -> dict:
    view = simulation_view(simulation)
    conflicts = _scoped_conflicts(simulation, user, view["conflicts"])
    records = list_records(db, simulation, actor=user)
    pending = [record for record in records if record.status == "PENDING"]
    model = metadata_summary()

    all_trains = view["trains"]
    all_blocks = view["block_occupancy"]
    all_platforms = view["platforms"]
    all_closures = view["closures"]
    all_outages = view["platform_outages"]

    # Jurisdiction filtering
    if user.is_station_master():
        st_set = set(user.get_stations())
        scoped_trains = [
            t for t in all_trains
            if t.get("station_id") in st_set or any(st in st_set for st in t.get("route", []))
        ]
        scoped_platforms = [p for p in all_platforms if p.get("station_id") in st_set]
        sec_set = set(user.get_sections())
        scoped_blocks = [
            b for b in all_blocks
            if b.get("station_id") in st_set or b.get("section_id") in sec_set
        ]
        scoped_closures = [c for c in all_closures if c.get("section_id") in sec_set]
        scoped_outages = [o for o in all_outages if o.get("station_id") in st_set]
    elif user.is_section_controller() and user.control_area not in {None, "CORRIDOR"}:
        st_set = set(user.get_stations())
        sec_set = set(user.get_sections())
        scoped_trains = [
            t for t in all_trains
            if t.get("station_id") in st_set or any(st in st_set for st in t.get("route", []))
        ]
        scoped_platforms = [p for p in all_platforms if p.get("station_id") in st_set]
        scoped_blocks = [
            b for b in all_blocks
            if b.get("station_id") in st_set or b.get("section_id") in sec_set
        ]
        scoped_closures = [c for c in all_closures if c.get("section_id") in sec_set]
        scoped_outages = [o for o in all_outages if o.get("station_id") in st_set]
    else:
        scoped_trains = all_trains
        scoped_platforms = all_platforms
        scoped_blocks = all_blocks
        scoped_closures = all_closures
        scoped_outages = all_outages

    occupied_blocks = [
        item for item in scoped_blocks if item.get("occupied_by")
    ]
    available_platforms = [
        item for item in scoped_platforms if item["status"] == "AVAILABLE"
    ]
    now = view["sim_time_min"]
    active_closures = [
        closure
        for closure in scoped_closures
        if closure["start_min"] <= now < closure["end_min"]
    ]
    upcoming_closures = [
        closure for closure in scoped_closures if closure["start_min"] > now
    ]
    active_outages = [
        outage
        for outage in scoped_outages
        if outage["start_min"] <= now < outage["end_min"]
    ]
    return {
        "simulation": {
            "id": simulation.id,
            "name": simulation.name,
            "scenario_key": simulation.scenario_key,
            "status": simulation.status,
            "sim_time": view["sim_time"],
            "sim_time_min": view["sim_time_min"],
            "state_version": simulation.state_version,
            "seed": simulation.seed,
            "label": "SYNTHETIC",
            "scenario_date": view["scenario_date"],
            "timezone": view["timezone"],
        },
        "metrics": view["metrics"],
        "trains": scoped_trains,
        "active_trains": [train for train in scoped_trains if train["status"] != "COMPLETED"],
        "delayed_trains": [
            train for train in scoped_trains if train["projected_delay_min"] > 5
        ],
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "occupied_blocks": occupied_blocks,
        "available_platforms": available_platforms,
        "closures": scoped_closures,
        "platform_outages": scoped_outages,
        "active_closures": active_closures,
        "upcoming_closures": upcoming_closures,
        "active_outages": active_outages,
        "pending_recommendations": [
            _recommendation_summary(db, record, simulation) for record in pending[:6]
        ],
        "pending_recommendation_count": len(pending),
        "model_status": {
            "ppo": {
                "trained": bool(model.get("trained")),
                "status": model.get("status", "UNTRAINED_DEVELOPMENT_COMPONENT"),
                "model_version": model.get("model_version", "ppo-unavailable"),
                "reason": model.get("reason"),
                "evaluation": model.get("evaluation", {}),
            },
            "cpsat": {
                "version": OPTIMIZER_VERSION,
                "status": "DETERMINISTIC_OPTIMIZER",
            },
        },
        "data_label": "SYNTHETIC — NOT REAL INDIAN RAILWAYS DATA",
        "role_scope": {
            "role": user.role,
            "station_id": user.station_id,
            "section_id": user.section_id,
        },
        "jurisdiction": {
            "role": user.role,
            "display_name": user.display_name,
            "station_id": user.station_id,
            "section_id": user.section_id,
            "zone": user.zone or "SWR",
            "division": user.division or "Southern Division",
            "control_area": user.control_area or "CORRIDOR",
            "authorized_stations": user.get_stations(),
            "authorized_sections": user.get_sections(),
            "is_restricted_scope": user.is_station_master() or (user.is_section_controller() and user.control_area not in {None, "CORRIDOR"}),
        },
    }


@router.get("/{simulation_id}/trains")
def trains(
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(get_current_user),
) -> dict:
    view = simulation_view(simulation)
    train_list = view["trains"]
    if user.is_station_master():
        st_set = set(user.get_stations())
        train_list = [
            t for t in train_list
            if t.get("station_id") in st_set or any(st in st_set for st in t.get("route", []))
        ]
    elif user.is_section_controller() and user.control_area not in {None, "CORRIDOR"}:
        st_set = set(user.get_stations())
        train_list = [
            t for t in train_list
            if t.get("station_id") in st_set or any(st in st_set for st in t.get("route", []))
        ]
    return {
        "sim_time": view["sim_time"],
        "state_version": view["state_version"],
        "trains": train_list,
        "label": "SYNTHETIC",
        "jurisdiction_filtered": user.is_station_master() or (user.is_section_controller() and user.control_area not in {None, "CORRIDOR"}),
    }


@router.get("/{simulation_id}/network")
def network(
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(get_current_user),
) -> dict:
    view = simulation_view(simulation)
    net = copy.deepcopy(view["network"])
    block_occ = view["block_occupancy"]
    platforms = view["platforms"]
    closures = view["closures"]
    outages = view["platform_outages"]

    if user.is_station_master():
        st_set = set(user.get_stations())
        neighbor_stations = set(st_set)
        for sec in net["sections"]:
            if sec["from_station"] in st_set:
                neighbor_stations.add(sec["to_station"])
            if sec["to_station"] in st_set:
                neighbor_stations.add(sec["from_station"])
        net["stations"] = [s for s in net["stations"] if s["id"] in neighbor_stations]
        net["sections"] = [s for s in net["sections"] if s["from_station"] in st_set or s["to_station"] in st_set]
        allowed_sec_ids = {s["id"] for s in net["sections"]}
        block_occ = [b for b in block_occ if b.get("section_id") in allowed_sec_ids or b.get("station_id") in st_set]
        platforms = [p for p in platforms if p.get("station_id") in st_set]
        closures = [c for c in closures if c.get("section_id") in allowed_sec_ids]
        outages = [o for o in outages if o.get("station_id") in st_set]
    elif user.is_section_controller() and user.control_area not in {None, "CORRIDOR"}:
        st_set = set(user.get_stations())
        sec_set = set(user.get_sections())
        net["stations"] = [s for s in net["stations"] if s["id"] in st_set]
        net["sections"] = [s for s in net["sections"] if s["id"] in sec_set]
        allowed_sec_ids = {s["id"] for s in net["sections"]}
        block_occ = [b for b in block_occ if b.get("section_id") in allowed_sec_ids or b.get("station_id") in st_set]
        platforms = [p for p in platforms if p.get("station_id") in st_set]
        closures = [c for c in closures if c.get("section_id") in allowed_sec_ids]
        outages = [o for o in outages if o.get("station_id") in st_set]

    return {
        "network": net,
        "block_occupancy": block_occ,
        "platforms": platforms,
        "closures": closures,
        "platform_outages": outages,
        "sim_time": view["sim_time"],
        "state_version": view["state_version"],
        "label": "SYNTHETIC",
        "jurisdiction_filtered": user.is_station_master() or (user.is_section_controller() and user.control_area not in {None, "CORRIDOR"}),
    }


@router.get("/{simulation_id}/conflicts")
def conflicts(
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(get_current_user),
) -> dict:
    detected = detect_conflicts(simulation.state, 75)
    scoped = _scoped_conflicts(simulation, user, detected)
    return {
        "conflicts": scoped,
        "total_detected": len(detected),
        "scope_filtered": user.is_station_master() or (user.is_section_controller() and user.control_area not in {None, "CORRIDOR"}),
        "scope": {
            "role": user.role,
            "station_id": user.station_id,
            "section_id": user.section_id,
            "authorized_stations": user.get_stations(),
            "authorized_sections": user.get_sections(),
            "control_area": user.control_area,
        },
        "sim_time": simulation.state["sim_time_min"],
        "state_version": simulation.state_version,
        "label": "SYNTHETIC",
    }


@router.post("/{simulation_id}/advance")
def advance(
    payload: AdvanceRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SECTION_MASTER")),
    simulation: Simulation = Depends(get_simulation),
) -> dict:
    advance_simulation(db, simulation, minutes=payload.minutes, actor=user)
    return simulation_view(simulation)


@router.post("/{simulation_id}/pause")
def pause(
    payload: PauseRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SECTION_MASTER")),
    simulation: Simulation = Depends(get_simulation),
) -> dict:
    set_pause_state(db, simulation, paused=payload.paused, actor=user)
    return simulation_view(simulation)


@router.post("/{simulation_id}/reset")
def reset(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SECTION_MASTER")),
    simulation: Simulation = Depends(get_simulation),
) -> dict:
    reset_simulation(db, simulation, actor=user)
    return simulation_view(simulation)


@router.post("/{simulation_id}/disruptions")
def disruption(
    payload: DisruptionRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SECTION_MASTER")),
    simulation: Simulation = Depends(get_simulation),
) -> dict:
    apply_disruption(
        db,
        simulation,
        disruption_type=payload.disruption_type,
        payload=payload.payload,
        actor=user,
    )
    return simulation_view(simulation)


@router.post("/{simulation_id}/what-if")
def what_if(
    payload: WhatIfRequest,
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(get_current_user),
) -> dict:
    return run_what_if(
        db,
        simulation,
        action=payload.action,
        minutes=payload.minutes,
        actor=user,
    )


@router.get("/{simulation_id}/analytics")
def analytics(
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(get_current_user),
) -> dict:
    return build_analytics(db, simulation)


@router.get("/{simulation_id}/analytics/station-master")
def station_analytics(
    station_id: str | None = None,
    punctuality_threshold_min: int = Query(default=5, ge=0, le=60),
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(get_current_user),
) -> dict:
    target = station_id or user.station_id or "MLG"
    if user.is_station_master() and not user.can_access_station(target):
        raise HTTPException(
            status_code=403,
            detail=f"Station '{target}' is outside your authorized operational jurisdiction ({user.get_stations()}).",
        )
    return station_master_kpis(
        db, simulation, target, punctuality_threshold_min=punctuality_threshold_min
    )


@router.get("/{simulation_id}/analytics/section-controller")
def section_analytics(
    db: Session = Depends(get_db),
    user: User = Depends(require_roles("SECTION_MASTER")),
    simulation: Simulation = Depends(get_simulation),
) -> dict:
    return section_controller_kpis(db, simulation)


@router.get("/{simulation_id}/recommendations")
def recommendations(
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(get_current_user),
) -> dict:
    records = list_records(db, simulation, actor=user)
    return {
        "recommendations": [
            _recommendation_summary(db, record, simulation) for record in records
        ],
        "simulation_id": simulation.id,
        "state_version": simulation.state_version,
        "label": "SYNTHETIC",
    }


@router.post("/{simulation_id}/recommendations")
def generate(
    payload: GenerateRecommendationRequest | None = None,
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(get_current_user),
) -> dict:
    record = generate_record(
        db,
        simulation,
        actor=user,
        parent_recommendation_id=payload.parent_recommendation_id if payload else None,
    )
    return serialize(db, record, simulation)
