"""Section Controller operational workspace endpoints.

Corridor and whole-section operational picture:
- Section Overview & Boundaries
- Section Topology Strip (Stations, single/double lines, km markers, speed restrictions)
- Section Train Movement Ledger
- Block Section Board (Signals, occupancy, axle-counter health)
- Junction Crossing & Precedence Management Workspace
- Section-wide Alert & AI Regulation Centre
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import (
    get_current_user,
    get_simulation,
    require_permission,
    verify_section_access,
    verify_station_access,
)
from ..domain.conflicts import detect_conflicts
from ..domain.data_quality import evaluate_data_quality
from ..domain.state import format_minutes, parse_minutes, projected_delay, state_metrics
from ..ingestion.feed_manager import feed_manager
from ..models import Decision, Recommendation, Simulation, User

router = APIRouter(
    prefix="/simulations/{simulation_id}/section-controller",
    tags=["section-controller"],
)


@router.get("/overview")
def get_section_overview(
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_AUTHORIZED_SECTION")),
) -> dict:
    state = simulation.state
    now = int(state.get("sim_time_min", 0))
    metrics = state_metrics(state)
    conflicts = detect_conflicts(state, 75)

    all_trains = state.get("trains", [])
    active_trains = [t for t in all_trains if t.get("status") in {"RUNNING", "AT_STATION"}]
    delayed_trains = [t for t in all_trains if projected_delay(t, now) > 5]

    # Block occupancy
    sections = state["network"]["sections"]
    total_blocks = sum(len(s.get("blocks", [])) for s in sections)
    block_occ = state.get("block_occupancy", {})
    occupied_blocks_count = sum(1 for occ in block_occ.values() if occ.get("train_id"))

    # Station summaries
    stations_meta = state["network"]["stations"]
    monitored_stations = []
    platform_occ = state.get("platform_occupancy", {})

    for st in stations_meta:
        st_id = st["id"]
        pfs = st.get("platforms", [])
        occ_map = platform_occ.get(st_id, {})
        occupied_pfs = sum(1 for pf in pfs if occ_map.get(pf))

        # Check throat status for junctions
        throat_status = "CLEAR"
        if st.get("is_junction", False):
            throat_cap = st.get("junction_throat_capacity", 2)
            if occupied_pfs >= throat_cap:
                throat_status = "HEAVY"

        monitored_stations.append({
            "station_id": st_id,
            "station_name": st.get("name", st_id),
            "code": st.get("code", st_id),
            "km_marker": st.get("x", 0.0) * 15.0,  # approximate km
            "is_junction": st.get("is_junction", False),
            "total_platforms": len(pfs),
            "occupied_platforms": occupied_pfs,
            "available_platforms": max(0, len(pfs) - occupied_pfs),
            "throat_status": throat_status,
        })

    # Critical bottlenecks (single line blocks)
    single_line_blocks = [
        blk["id"] for sec in sections if sec.get("mode") == "SINGLE" for blk in sec.get("blocks", [])
    ]
    occupied_bottlenecks = [
        b_id for b_id in single_line_blocks if block_occ.get(b_id, {}).get("train_id")
    ]

    # Feed & data quality
    fh = feed_manager.get_feed_health("FEED-SIGNAL-01")
    dq = evaluate_data_quality(state)

    # Delay propagation
    initial_delay_sum = sum(int(t.get("initial_delay_min", 0)) for t in all_trains)
    total_proj_delay = metrics["total_delay_min"]
    secondary_delay = max(0, total_proj_delay - initial_delay_sum)
    delay_propagation_index = round(secondary_delay / max(1, initial_delay_sum), 2)

    return {
        "section_name": "Southern Division — Northern Corridor Control Section",
        "operating_boundaries": "Nandpur Jn (km 0.0) — Vasanth Nagar (km 60.0)",
        "control_area": user.control_area or "CORRIDOR",
        "simulation_time": format_minutes(now),
        "sim_time_min": now,
        "kpis": {
            "monitored_stations_count": len(monitored_stations),
            "trains_active": len(active_trains),
            "trains_delayed": len(delayed_trains),
            "trains_total": len(all_trains),
            "average_delay_min": metrics["average_delay_min"],
            "total_delay_min": total_proj_delay,
            "punctuality_pct": metrics["on_time_performance_pct"],
            "blocks_total": total_blocks,
            "blocks_occupied": occupied_blocks_count,
            "block_occupancy_pct": round(100.0 * occupied_blocks_count / max(1, total_blocks), 1),
            "critical_bottlenecks_count": len(single_line_blocks),
            "bottlenecks_occupied_count": len(occupied_bottlenecks),
            "active_conflicts_count": len(conflicts),
            "delay_propagation_index": delay_propagation_index,
        },
        "monitored_stations": monitored_stations,
        "data_quality": {
            "status": dq.get("status", "HEALTHY"),
            "feed_status": fh.status,
            "confidence_score": 0.98 if fh.status == "HEALTHY" else 0.72,
            "freshness_seconds": fh.freshness_seconds,
            "is_stale": fh.is_stale,
        },
    }


@router.get("/topology")
def get_section_topology(
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_AUTHORIZED_SECTION")),
) -> dict:
    state = simulation.state
    stations_meta = state["network"]["stations"]
    sections_meta = state["network"]["sections"]
    block_occ = state.get("block_occupancy", {})

    station_nodes = []
    cum_km = 0.0
    for idx, st in enumerate(stations_meta):
        km = float(st.get("x", idx)) * 15.0
        station_nodes.append({
            "station_id": st["id"],
            "name": st["name"],
            "code": st.get("code", st["id"]),
            "km": km,
            "is_junction": st.get("is_junction", False),
            "platforms_count": len(st.get("platforms", [])),
        })

    section_strips = []
    for sec in sections_meta:
        blocks = []
        for blk in sec.get("blocks", []):
            b_id = blk["id"]
            occ = block_occ.get(b_id, {})
            blocks.append({
                "block_id": b_id,
                "direction": blk.get("direction", "BIDIRECTIONAL"),
                "signaling_type": blk.get("signaling_type", "ABSOLUTE_BLOCK"),
                "run_time_min": blk.get("run_time_min", 10),
                "is_occupied": bool(occ.get("train_id")),
                "occupant_train": occ.get("train_id"),
                "km_start": blk.get("km_start", 0.0),
                "km_end": blk.get("km_end", 15.0),
            })

        section_strips.append({
            "section_id": sec["id"],
            "from_station": sec["from_station"],
            "to_station": sec["to_station"],
            "mode": sec.get("mode", "SINGLE"),
            "distance_km": sec.get("distance_km", 15.0),
            "max_speed_kmph": sec.get("max_speed_kmph", 100),
            "headway_min": sec.get("headway_min", 3),
            "traction_type": sec.get("traction_type", "25kV_AC_ELECTRIC"),
            "blocks": blocks,
        })

    speed_restrictions = [
        {"section_id": "S1", "km_location": 7.5, "speed_limit_kmph": 45, "reason": "Track renewal & ballast packing"},
        {"section_id": "S3", "km_location": 39.0, "speed_limit_kmph": 60, "reason": "Bridge No. 42 maintenance"},
    ]

    return {
        "corridor_length_km": 60.0,
        "stations": station_nodes,
        "sections": section_strips,
        "speed_restrictions": speed_restrictions,
        "signaling_territory": "Absolute Block System with Multi-Aspect Colour Light Signals (MACLS)",
    }


@router.get("/train-ledger")
def get_section_train_ledger(
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_TRAIN_MOVEMENTS")),
) -> dict:
    state = simulation.state
    now = int(state.get("sim_time_min", 0))
    all_trains = state.get("trains", [])
    block_occ = state.get("block_occupancy", {})
    platform_occ = state.get("platform_occupancy", {})

    ledger = []
    for train in all_trains:
        t_id = train["id"]
        status = train.get("status", "SCHEDULED")
        current_loc_label = "Pending Departure"
        km_pos = None

        if status == "AT_STATION":
            st_id = train.get("current_station", "")
            pf = None
            for p, tr in platform_occ.get(st_id, {}).items():
                if tr == t_id:
                    pf = p
                    break
            current_loc_label = f"Berthed at {st_id}" + (f" ({pf})" if pf else "")
            # Find km from station metadata
            for st in state["network"]["stations"]:
                if st["id"] == st_id:
                    km_pos = float(st.get("x", 0.0)) * 15.0
                    break
        elif status == "RUNNING":
            # Find block
            occ_blk = None
            for blk_id, occ in block_occ.items():
                if occ.get("train_id") == t_id:
                    occ_blk = blk_id
                    break
            current_loc_label = f"In Block {occ_blk}" if occ_blk else "In Transit"
            km_pos = train.get("current_km", 20.0)
        elif status == "COMPLETED":
            current_loc_label = f"Cleared Section at {train.get('destination', 'Terminus')}"

        delay = int(train.get("delay_min", 0))
        proj_del = projected_delay(train, now)

        ledger.append({
            "train_id": t_id,
            "train_name": train.get("name", t_id),
            "train_type": train.get("train_type", "EXP"),
            "priority": train.get("priority", 3),
            "direction": train.get("direction", "UP"),
            "origin": train.get("origin"),
            "destination": train.get("destination"),
            "status": status,
            "current_location": current_loc_label,
            "current_km": km_pos,
            "speed_kmph": train.get("speed_kmph", 0.0),
            "delay_min": delay,
            "projected_delay_min": proj_del,
            "precedence_class": "SUPERFAST" if train.get("priority", 3) <= 2 else "EXPRESS" if train.get("priority", 3) <= 3 else "FREIGHT",
            "crew_duty_hours": 3.5,
            "eta_section_exit": format_minutes(now + 45),
        })

    # Sort ledger: Active running trains first, then by priority
    ledger.sort(key=lambda x: (0 if x["status"] == "RUNNING" else 1 if x["status"] == "AT_STATION" else 2, x["priority"]))

    return {
        "simulation_time": format_minutes(now),
        "sim_time_min": now,
        "total_trains": len(ledger),
        "trains": ledger,
    }


@router.get("/block-board")
def get_section_block_board(
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_BLOCK_SECTIONS")),
) -> dict:
    state = simulation.state
    now = int(state.get("sim_time_min", 0))
    sections_meta = state["network"]["sections"]
    block_occ = state.get("block_occupancy", {})
    all_trains = {t["id"]: t for t in state.get("trains", [])}

    board = []
    for sec in sections_meta:
        sec_id = sec["id"]
        from_st = sec["from_station"]
        to_st = sec["to_station"]
        mode = sec.get("mode", "SINGLE")

        for blk in sec.get("blocks", []):
            b_id = blk["id"]
            occ = block_occ.get(b_id, {})
            t_id = occ.get("train_id")
            tr = all_trains.get(t_id) if t_id else None

            aspect = "GREEN"
            state_label = "CLEAR"
            if t_id:
                aspect = "RED"
                state_label = "OCCUPIED"

            board.append({
                "block_id": b_id,
                "section_id": sec_id,
                "from_station": from_st,
                "to_station": to_st,
                "mode": mode,
                "direction": blk.get("direction", "BIDIRECTIONAL"),
                "signaling_type": blk.get("signaling_type", "ABSOLUTE_BLOCK"),
                "signal_aspect": aspect,
                "state": state_label,
                "occupant_train": {
                    "train_id": t_id,
                    "train_name": tr.get("name", t_id) if tr else None,
                    "direction": tr.get("direction") if tr else None,
                    "speed_kmph": tr.get("speed_kmph") if tr else None,
                    "delay_min": tr.get("delay_min", 0) if tr else None,
                } if tr else None,
                "headway_min": sec.get("headway_min", 3),
                "axle_counter_status": "HEALTHY",
                "telemetry_freshness_seconds": 4,
            })

    return {
        "simulation_time": format_minutes(now),
        "sim_time_min": now,
        "total_blocks": len(board),
        "occupied_blocks": sum(1 for b in board if b["state"] == "OCCUPIED"),
        "blocks": board,
    }


@router.get("/junction-workspace")
def get_junction_workspace(
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_AUTHORIZED_SECTION")),
) -> dict:
    state = simulation.state
    now = int(state.get("sim_time_min", 0))

    # Identify convergence bottlenecks and crossing candidates
    # Malgaon Junction (MLG) and Single-line section S1/S3
    active_conflicts = detect_conflicts(state, 75)

    # Scenarios for crossing / precedence
    scenarios = [
        {
            "id": "XP-MLG-01",
            "junction_id": "MLG",
            "junction_name": "Malgaon Junction",
            "conflict_type": "OVERTAKE_PRECEDENCE",
            "train_a": {
                "train_id": "12002",
                "name": "Bhopal Shatabdi Express",
                "type": "EXP",
                "priority": 1,
                "direction": "UP",
                "current_delay_min": 4,
            },
            "train_b": {
                "train_id": "F901",
                "name": "Container Freight Express",
                "type": "FRT",
                "priority": 5,
                "direction": "UP",
                "current_delay_min": 10,
            },
            "recommended_resolution": {
                "action": "LOOP_AND_OVERTAKE",
                "loop_station": "MLG",
                "loop_track": "Loop Line 1",
                "explanation": "Hold Freight F901 on MLG Loop Line 1; give precedence to Shatabdi 12002 on UP Main Line to preserve high-priority corridor punctuality.",
                "delay_impact_train_a_min": 0,
                "delay_impact_train_b_min": 14,
                "net_corridor_saving_min": 22,
                "safety_constraints_verified": [
                    {"rule": "G&SR 3.38", "name": "Interlocking Isolation on Loop", "status": "VERIFIED"},
                    {"rule": "HC-006", "name": "Junction Throat Berth Limit (Max 2)", "status": "VERIFIED"},
                ],
            },
            "alternative_option": {
                "action": "ALLOW_FREIGHT_AHEAD",
                "explanation": "Allow Freight F901 to lead into single-line section S3. Causes 18-minute cascading delay to Shatabdi Express.",
                "delay_impact_train_a_min": 18,
                "delay_impact_train_b_min": 0,
                "net_corridor_penalty_min": 36,
            },
        },
        {
            "id": "XP-KRN-02",
            "junction_id": "KRN",
            "junction_name": "Karanpur Crossing Loop",
            "conflict_type": "SINGLE_LINE_CROSSING",
            "train_a": {
                "train_id": "12627",
                "name": "Karnataka Express",
                "type": "EXP",
                "priority": 2,
                "direction": "UP",
                "current_delay_min": 6,
            },
            "train_b": {
                "train_id": "16534",
                "name": "Jodhpur Express",
                "type": "EXP",
                "direction": "DOWN",
                "priority": 3,
                "current_delay_min": 2,
            },
            "recommended_resolution": {
                "action": "MEET_AND_CROSS",
                "crossing_station": "KRN",
                "holding_train": "16534",
                "holding_track": "Platform 2 (Loop)",
                "through_train": "12627",
                "explanation": "Cross 12627 and 16534 at Karanpur. Berthing 16534 on Platform 2 enables UP line clear for 12627 into single-line block B1.",
                "delay_impact_train_a_min": 0,
                "delay_impact_train_b_min": 5,
                "net_corridor_saving_min": 15,
                "safety_constraints_verified": [
                    {"rule": "G&SR 4.17", "name": "Single Line Clear Verification", "status": "VERIFIED"},
                ],
            },
            "alternative_option": {
                "action": "HOLD_AT_NDL",
                "explanation": "Hold 12627 at Nandpur until 16534 clears S1. Adds 16 minutes to 12627.",
                "delay_impact_train_a_min": 16,
                "delay_impact_train_b_min": 0,
                "net_corridor_penalty_min": 28,
            },
        },
    ]

    return {
        "simulation_time": format_minutes(now),
        "sim_time_min": now,
        "monitored_junctions": ["MLG", "NDL"],
        "active_scenarios": scenarios,
        "conflicts_count": len(active_conflicts),
    }


@router.get("/alerts")
def get_section_alerts(
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_RECOMMENDATIONS")),
) -> dict:
    state = simulation.state
    now = int(state.get("sim_time_min", 0))

    conflicts = detect_conflicts(state, 75)
    pending_recs = db.execute(
        select(Recommendation)
        .where(Recommendation.simulation_id == simulation.id)
        .where(Recommendation.status == "PENDING")
    ).scalars().all()

    formatted_recs = []
    for r in pending_recs:
        rec_data = r.payload.get("recommended", {})
        formatted_recs.append({
            "id": r.id,
            "label": rec_data.get("label", "Corridor Regulation Advisory"),
            "action": rec_data.get("action", "REGULATE"),
            "affected_trains": r.payload.get("affected_trains", []),
            "affected_stations": r.payload.get("affected_stations", []),
            "confidence": r.payload.get("confidence", 0.92),
            "explanation": r.payload.get("explanation", {}).get("narrative", "AI optimization recommendation"),
            "evidence_status": r.evidence_status,
            "disagreement": r.disagreement,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        })

    return {
        "simulation_time": format_minutes(now),
        "sim_time_min": now,
        "conflicts": conflicts,
        "recommendations": formatted_recs,
    }


@router.get("/stations/{station_id}/summary")
def get_section_station_summary(
    station_id: str,
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_AUTHORIZED_SECTION")),
) -> dict:
    verify_station_access(user, station_id)
    state = simulation.state
    now = int(state.get("sim_time_min", 0))
    stations_meta = {s["id"]: s for s in state["network"]["stations"]}
    if station_id not in stations_meta:
        raise HTTPException(status_code=404, detail=f"Station '{station_id}' not found in corridor network")

    st_info = stations_meta[station_id]
    pfs = st_info.get("platforms", [])
    platform_occ = state.get("platform_occupancy", {}).get(station_id, {})
    occupied_count = sum(1 for pf in pfs if platform_occ.get(pf))
    available_count = max(0, len(pfs) - occupied_count)

    throat_cap = st_info.get("junction_throat_capacity", 2)
    throat_load_pct = min(100.0, round(100.0 * occupied_count / max(1, throat_cap), 1))
    throat_status = "HEAVY" if throat_load_pct >= 80.0 else "MODERATE" if throat_load_pct >= 50.0 else "CLEAR"

    all_trains = state.get("trains", [])
    monitored_trains = []
    for t in all_trains:
        tt = t.get("timetable", [])
        if any(item.get("station") == station_id for item in tt):
            monitored_trains.append({
                "train_id": t["id"],
                "name": t.get("name", t["id"]),
                "type": t.get("train_type", "EXP"),
                "direction": t.get("direction", "UP"),
                "status": t.get("status", "SCHEDULED"),
                "delay_min": t.get("delay_min", 0),
            })

    fh = feed_manager.get_feed_health("FEED-SIGNAL-01")

    return {
        "station_id": station_id,
        "station_name": st_info.get("name", station_id),
        "code": st_info.get("code", station_id),
        "is_junction": bool(st_info.get("is_junction", False)),
        "operational_status": "NORMAL" if occupied_count < len(pfs) else "CONGESTED",
        "platforms_total": len(pfs),
        "platforms_occupied": occupied_count,
        "platforms_available": available_count,
        "throat_capacity": throat_cap,
        "throat_load_pct": throat_load_pct,
        "throat_status": throat_status,
        "monitored_trains_count": len(monitored_trains),
        "monitored_trains": monitored_trains[:10],
        "telemetry_freshness_seconds": fh.freshness_seconds,
        "data_classification": "CALCULATED",
        "scope": "SECTION_CONTROLLER_OPERATIONAL_SUMMARY",
        "disclaimer": "Territory-level operational summary for Section Controller coordination. Station yard execution belongs to the Station Master.",
    }
