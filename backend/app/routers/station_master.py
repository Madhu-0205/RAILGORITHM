"""Station Master operational workspace endpoints.

Strictly station-centric operational picture:
- Station yard layout (Main lines, Loops, Sidings, Platforms)
- Train movement board (Arriving, Departing, Through)
- Adjacent station awareness (Upstream/Downstream block status, Line Clear, approaching trains)
- Station-scoped alerts and AI recommendations
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
    verify_adjacent_access,
    verify_station_access,
)
from ..domain.conflicts import detect_conflicts
from ..domain.data_quality import evaluate_data_quality
from ..domain.network import Network
from ..domain.state import format_minutes, parse_minutes, projected_delay
from ..domain.topology_resolver import resolve_adjacent_stations
from ..ingestion.feed_manager import feed_manager
from ..models import Decision, Recommendation, Simulation, User

router = APIRouter(
    prefix="/simulations/{simulation_id}/station-master",
    tags=["station-master"],
)


def _get_station_or_default(user: User, station_id: str | None) -> str:
    target = station_id or user.station_id
    if not target:
        stations = user.get_stations()
        target = stations[0] if stations else "NDL"
    verify_station_access(user, target)
    return target


@router.get("/overview")
def get_station_overview(
    station_id: str | None = None,
    punctuality_threshold_min: int = Query(default=5, ge=0, le=60),
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_OWN_STATION")),
) -> dict:
    target_st = _get_station_or_default(user, station_id)
    state = simulation.state
    now = int(state.get("sim_time_min", 0))

    # Retrieve station metadata from simulation network
    station_meta = next(
        (s for s in state["network"]["stations"] if s["id"] == target_st),
        None,
    )
    if not station_meta:
        raise HTTPException(status_code=404, detail=f"Station '{target_st}' not found in simulation network")

    # Evaluate trains interacting with this station
    all_trains = state.get("trains", [])
    station_trains = []
    arriving_30 = 0
    departing_30 = 0
    through_30 = 0
    currently_at_station = 0
    delayed_count = 0
    delays_list = []
    on_time_count = 0

    platform_occ = state.get("platform_occupancy", {}).get(target_st, {})
    occupied_pf_trains = set(platform_occ.values())

    for train in all_trains:
        # Check timetable for target station
        timetable = train.get("timetable", [])
        tt_entry = next((item for item in timetable if item.get("station") == target_st), None)
        if not tt_entry:
            continue

        arr_min = tt_entry.get("arrival_min")
        dep_min = tt_entry.get("departure_min")
        is_origin = (train.get("origin") == target_st)
        is_dest = (train.get("destination") == target_st)
        is_through = (not is_origin and not is_dest and arr_min is not None and dep_min is not None and (dep_min - arr_min <= 2))

        # Check if currently berthed
        is_berthed = (train.get("status") == "AT_STATION" and train.get("current_station") == target_st) or (train.get("id") in occupied_pf_trains)
        if is_berthed:
            currently_at_station += 1

        # Check operational window (T-30 to T+60)
        relevant_time = arr_min if arr_min is not None else dep_min
        if relevant_time is not None and (now - 30 <= relevant_time <= now + 60):
            station_trains.append(train)
            delay = int(train.get("delay_min", 0))
            delays_list.append(delay)
            if delay <= punctuality_threshold_min:
                on_time_count += 1
            else:
                delayed_count += 1

            if arr_min is not None and now <= arr_min <= now + 30:
                arriving_30 += 1
            if dep_min is not None and now <= dep_min <= now + 30:
                departing_30 += 1
            if is_through and relevant_time is not None and now <= relevant_time <= now + 30:
                through_30 += 1

    # Calculation of schedule adherence: Explicitly handle NO_DATA
    if station_trains:
        schedule_adherence_pct = round(100.0 * on_time_count / len(station_trains), 1)
        adherence_status = "NORMAL" if schedule_adherence_pct >= 80.0 else "DEGRADED"
        adherence_text = f"{on_time_count} of {len(station_trains)} monitored trains on-time (<= {punctuality_threshold_min} min delay)"
    else:
        schedule_adherence_pct = None
        adherence_status = "NO_DATA"
        adherence_text = "No trains active or scheduled in station observation window (T-30m to T+60m)"

    avg_delay = round(sum(delays_list) / len(delays_list), 1) if delays_list else None

    # Platform breakdown
    platforms = station_meta.get("platforms", [])
    active_outages = [
        o for o in state.get("platform_outages", [])
        if o.get("station_id") == target_st and o.get("start_min", 0) <= now < o.get("end_min", 0)
    ]
    outage_pfs = {o["platform_id"] for o in active_outages}
    occupied_count = sum(1 for pf in platforms if platform_occ.get(pf))
    outage_count = sum(1 for pf in platforms if pf in outage_pfs)
    avail_count = max(0, len(platforms) - occupied_count - outage_count)

    # Data quality evaluation
    dq = evaluate_data_quality(state)
    fh = feed_manager.get_feed_health("FEED-SIGNAL-01")

    # Operational status synthesis
    if outage_count > 0 or fh.status in {"DEGRADED", "STALE", "OFFLINE"}:
        operational_status = "DEGRADED"
    elif occupied_count >= len(platforms) or (avg_delay and avg_delay > 15):
        operational_status = "CONGESTED"
    elif delayed_count > 0:
        operational_status = "REGULATED"
    else:
        operational_status = "NORMAL"

    return {
        "station_id": target_st,
        "station_name": station_meta.get("name", target_st),
        "station_code": station_meta.get("code", target_st),
        "is_junction": station_meta.get("is_junction", False),
        "operational_status": operational_status,
        "simulation_time": format_minutes(now),
        "sim_time_min": now,
        "summary_counts": {
            "total_scheduled_today": len([t for t in all_trains if any(item.get("station") == target_st for item in t.get("timetable", []))]),
            "monitored_window_trains": len(station_trains),
            "arriving_next_30m": arriving_30,
            "departing_next_30m": departing_30,
            "through_next_30m": through_30,
            "currently_at_station": currently_at_station,
            "delayed_trains_count": delayed_count,
            "on_time_trains_count": on_time_count,
        },
        "adherence": {
            "schedule_adherence_pct": schedule_adherence_pct,
            "adherence_status": adherence_status,
            "explanation": adherence_text,
            "punctuality_threshold_min": punctuality_threshold_min,
            "average_delay_min": avg_delay,
        },
        "platform_summary": {
            "total_platforms": len(platforms),
            "available": avail_count,
            "occupied": occupied_count,
            "outage": outage_count,
            "occupancy_pct": round(100.0 * occupied_count / max(1, len(platforms)), 1),
        },
        "data_quality": {
            "overall_status": dq.get("status", "HEALTHY"),
            "feed_status": fh.status,
            "confidence_score": 0.98 if fh.status == "HEALTHY" else 0.72,
            "freshness_seconds": fh.freshness_seconds,
            "is_stale": fh.is_stale,
        },
    }


@router.get("/layout")
def get_station_layout(
    station_id: str | None = None,
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_OWN_STATION")),
) -> dict:
    target_st = _get_station_or_default(user, station_id)
    state = simulation.state
    now = int(state.get("sim_time_min", 0))

    station_meta = next(
        (s for s in state["network"]["stations"] if s["id"] == target_st),
        None,
    )
    if not station_meta:
        raise HTTPException(status_code=404, detail=f"Station '{target_st}' not found in network")

    platform_occ = state.get("platform_occupancy", {}).get(target_st, {})
    active_outages = [
        o for o in state.get("platform_outages", [])
        if o.get("station_id") == target_st and o.get("start_min", 0) <= now < o.get("end_min", 0)
    ]
    outage_map = {o["platform_id"]: o.get("reason", "Maintenance Outage") for o in active_outages}

    # Find train objects for occupied platforms
    all_trains = {t["id"]: t for t in state.get("trains", [])}

    # Build comprehensive station tracks (Platforms, Main Lines, Loops, Sidings)
    tracks = []
    platforms = station_meta.get("platforms", [])

    for idx, pf in enumerate(platforms, start=1):
        occupant_id = platform_occ.get(pf)
        occupant_info = None
        state_status = "CLEAR"
        if pf in outage_map:
            state_status = "RESTRICTED"
        elif occupant_id:
            state_status = "OCCUPIED"
            tr = all_trains.get(occupant_id, {})
            occupant_info = {
                "train_id": occupant_id,
                "name": tr.get("name", occupant_id),
                "type": tr.get("train_type", "EXP"),
                "priority": tr.get("priority", 3),
                "direction": tr.get("direction", "UP"),
                "origin": tr.get("origin", ""),
                "destination": tr.get("destination", ""),
                "delay_min": tr.get("delay_min", 0),
            }

        tracks.append({
            "track_id": pf,
            "track_name": f"Platform Line {idx} ({pf})",
            "category": "PLATFORM",
            "line_type": "MAIN_LINE" if idx <= 2 else "LOOP_LINE",
            "state": state_status,
            "length_m": station_meta.get("platform_length_m", 650),
            "electrified": station_meta.get("platform_electrification", True),
            "max_speed_kmph": 110 if idx <= 2 else 30,
            "occupied_by": occupant_info,
            "route_locked": occupant_id is not None,
            "locked_for_train": occupant_id,
            "restrictions": outage_map.get(pf),
        })

    # Common Loop Line for crossing / precedence
    tracks.append({
        "track_id": f"{target_st}_LOOP_1",
        "track_name": "Common Loop Line (Precedence / Crossing)",
        "category": "LOOP_LINE",
        "line_type": "COMMON_LOOP",
        "state": "CLEAR",
        "length_m": 720,
        "electrified": True,
        "max_speed_kmph": 30,
        "occupied_by": None,
        "route_locked": False,
        "locked_for_train": None,
        "restrictions": None,
    })

    # Goods Siding for Freight staging
    tracks.append({
        "track_id": f"{target_st}_GOODS_1",
        "track_name": "Goods Siding 1 (Freight Loading / Staging)",
        "category": "SIDING",
        "line_type": "GOODS_SIDING",
        "state": "CLEAR",
        "length_m": 680,
        "electrified": True,
        "max_speed_kmph": 15,
        "occupied_by": None,
        "route_locked": False,
        "locked_for_train": None,
        "restrictions": None,
    })

    # Shunting Neck
    tracks.append({
        "track_id": f"{target_st}_SHUNT_NECK",
        "track_name": "Shunting Neck (Engine Reversal & Shunting)",
        "category": "SHUNTING_NECK",
        "line_type": "SHUNTING_TRACK",
        "state": "CLEAR",
        "length_m": 260,
        "electrified": True,
        "max_speed_kmph": 15,
        "occupied_by": None,
        "route_locked": False,
        "locked_for_train": None,
        "restrictions": None,
    })

    return {
        "station_id": target_st,
        "station_name": station_meta.get("name", target_st),
        "station_code": station_meta.get("code", target_st),
        "is_junction": station_meta.get("is_junction", False),
        "junction_throat_capacity": station_meta.get("junction_throat_capacity", 2),
        "throat_status": "CLEAR",
        "tracks": tracks,
        "berthing_capacity_total_m": sum(t["length_m"] for t in tracks),
        "speed_restrictions": [
            {"location": "Turnouts (Points 101/102)", "speed_limit_kmph": 30, "reason": "Standard 1-in-12 Turnout"},
            {"location": "Loop Line 1", "speed_limit_kmph": 15, "reason": "Caution Order: Joint Replacement"},
        ],
    }


@router.get("/movement-board")
def get_station_movement_board(
    station_id: str | None = None,
    window_ahead_min: int = Query(default=90, ge=15, le=180),
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_TRAIN_MOVEMENTS")),
) -> dict:
    target_st = _get_station_or_default(user, station_id)
    state = simulation.state
    now = int(state.get("sim_time_min", 0))

    all_trains = state.get("trains", [])
    platform_occ = state.get("platform_occupancy", {}).get(target_st, {})

    arriving = []
    departing = []
    through = []
    history = []

    for train in all_trains:
        t_id = train["id"]
        timetable = train.get("timetable", [])
        tt_entry = next((item for item in timetable if item.get("station") == target_st), None)
        if not tt_entry:
            continue

        sched_arr = tt_entry.get("arrival_min")
        sched_dep = tt_entry.get("departure_min")
        delay = int(train.get("delay_min", 0))
        est_arr = sched_arr + delay if sched_arr is not None else None
        est_dep = sched_dep + delay if sched_dep is not None else None

        is_origin = (train.get("origin") == target_st)
        is_dest = (train.get("destination") == target_st)
        dwell_min = (sched_dep - sched_arr) if (sched_arr is not None and sched_dep is not None) else 0
        is_through = (not is_origin and not is_dest and dwell_min <= 2)

        assigned_pf = None
        for pf, occ_t in platform_occ.items():
            if occ_t == t_id:
                assigned_pf = pf
                break
        if not assigned_pf:
            assigned_pf = tt_entry.get("platform")

        status = "ON_TIME"
        if delay > 5:
            status = "DELAYED"
        elif delay < 0:
            status = "EARLY"

        # Indian Railways Line Clear status
        line_clear = "NOT_APPLICABLE"
        if train.get("status") == "RUNNING":
            line_clear = "LINE_CLEAR_GRANTED"
        elif train.get("status") == "AT_STATION":
            line_clear = "TRAIN_IN_STATION_SECTION"

        item = {
            "train_id": t_id,
            "train_name": train.get("name", t_id),
            "train_type": train.get("train_type", "EXP"),
            "priority": train.get("priority", 3),
            "direction": train.get("direction", "UP"),
            "origin": train.get("origin"),
            "destination": train.get("destination"),
            "scheduled_arrival": format_minutes(sched_arr),
            "estimated_arrival": format_minutes(est_arr),
            "scheduled_departure": format_minutes(sched_dep),
            "estimated_departure": format_minutes(est_dep),
            "assigned_platform": assigned_pf,
            "status": status,
            "delay_min": delay,
            "speed_kmph": train.get("speed_kmph", 0.0),
            "line_clear_status": line_clear,
            "dwell_min": dwell_min,
            "traction": train.get("traction", "25kV AC Electric"),
        }

        # Categorize
        if est_dep is not None and est_dep < now:
            history.append(item)
        elif is_through and ((est_arr is not None and now - 15 <= est_arr <= now + window_ahead_min) or (est_dep is not None and now - 15 <= est_dep <= now + window_ahead_min)):
            through.append(item)
        elif train.get("status") == "AT_STATION" or (assigned_pf and platform_occ.get(assigned_pf) == t_id):
            departing.append(item)
        elif est_arr is not None and now - 10 <= est_arr <= now + window_ahead_min:
            arriving.append(item)
        elif est_dep is not None and now <= est_dep <= now + window_ahead_min:
            departing.append(item)

    arriving.sort(key=lambda x: parse_minutes(x["estimated_arrival"]) if x["estimated_arrival"] else 9999)
    departing.sort(key=lambda x: parse_minutes(x["estimated_departure"]) if x["estimated_departure"] else 9999)
    through.sort(key=lambda x: parse_minutes(x["estimated_arrival"] or x["estimated_departure"]) if (x["estimated_arrival"] or x["estimated_departure"]) else 9999)

    return {
        "station_id": target_st,
        "simulation_time": format_minutes(now),
        "sim_time_min": now,
        "window_ahead_min": window_ahead_min,
        "arriving": arriving,
        "departing": departing,
        "through": through,
        "history": history[-5:],
    }


@router.get("/adjacent-stations")
def get_adjacent_stations(
    station_id: str | None = None,
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_ADJACENT_CONTEXT")),
) -> dict:
    target_st = _get_station_or_default(user, station_id)
    verify_adjacent_access(user, target_st, simulation)

    state = simulation.state
    now = int(state.get("sim_time_min", 0))
    network_data = state["network"]
    block_occ = state.get("block_occupancy", {})
    all_trains = {t["id"]: t for t in state.get("trains", [])}

    resolved = resolve_adjacent_stations(
        network_data=network_data,
        station_id=target_st,
        block_occupancy=block_occ,
        all_trains=all_trains,
        now_min=now,
    )
    resolved["simulation_time"] = format_minutes(now)
    resolved["sim_time_min"] = now
    resolved["disclaimer"] = (
        "Adjacent station telemetry is simulated operational awareness for human decision support. "
        "Does not supersede physical Line Clear inquiry or Station Working Rules (SWR)."
    )
    return resolved


@router.get("/alerts")
def get_station_alerts(
    station_id: str | None = None,
    db: Session = Depends(get_db),
    simulation: Simulation = Depends(get_simulation),
    user: User = Depends(require_permission("VIEW_RECOMMENDATIONS")),
) -> dict:
    target_st = _get_station_or_default(user, station_id)
    state = simulation.state
    now = int(state.get("sim_time_min", 0))

    # Detect conflicts scoped to station or adjacent blocks
    conflicts = detect_conflicts(state, 60)
    station_meta = next((s for s in state["network"]["stations"] if s["id"] == target_st), {})
    station_sections = [sec["id"] for sec in state["network"]["sections"] if target_st in {sec["from_station"], sec["to_station"]}]
    station_blocks = [
        blk["id"] for sec in state["network"]["sections"]
        if sec["id"] in station_sections
        for blk in sec.get("blocks", [])
    ]

    scoped_conflicts = []
    for c in conflicts:
        loc = c.get("location", {})
        if loc.get("station_id") == target_st or loc.get("section_id") in station_sections or loc.get("block_id") in station_blocks:
            scoped_conflicts.append(c)

    # Scoped pending recommendations
    pending_recs = db.execute(
        select(Recommendation)
        .where(Recommendation.simulation_id == simulation.id)
        .where(Recommendation.status == "PENDING")
    ).scalars().all()

    scoped_recs = []
    for r in pending_recs:
        affected_stations = r.payload.get("affected_stations", [])
        if target_st in affected_stations or not affected_stations:
            rec_data = r.payload.get("recommended", {})
            scoped_recs.append({
                "id": r.id,
                "label": rec_data.get("label", "Station Advisory"),
                "action": rec_data.get("action", "REGULATE"),
                "confidence": r.payload.get("confidence", 0.90),
                "explanation": r.payload.get("explanation", {}).get("narrative", "AI advisory proposal"),
                "evidence_status": r.evidence_status,
                "safety_checks": [
                    {"rule": "G&SR 3.38", "name": "Facing Point Route Interlocking", "status": "VERIFIED"},
                    {"rule": "HC-004", "name": "Platform Berthing Clearance", "status": "VERIFIED"},
                ],
                "created_at": r.created_at.isoformat() if r.created_at else None,
            })

    return {
        "station_id": target_st,
        "station_name": station_meta.get("name", target_st),
        "simulation_time": format_minutes(now),
        "sim_time_min": now,
        "active_conflicts": scoped_conflicts,
        "pending_recommendations": scoped_recs,
    }
