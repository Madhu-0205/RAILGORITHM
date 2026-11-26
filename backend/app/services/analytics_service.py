"""Simulation analytics derived from actual simulation and decision records."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.conflicts import detect_conflicts
from ..domain.state import format_minutes, projected_delay, state_metrics
from ..ingestion.feed_manager import feed_manager
from ..models import Decision, Recommendation, Simulation


def analytics(db: Session, simulation: Simulation) -> dict:
    state = simulation.state
    metrics = state_metrics(state)
    conflicts = [
        conflict
        for conflict in detect_conflicts(state, 75)
        if conflict["type"] != "DELAY_RISK"
    ]
    recommendations = db.execute(
        select(Recommendation)
        .where(Recommendation.simulation_id == simulation.id)
        .order_by(Recommendation.created_at.desc())
    ).scalars().all()
    decisions = db.execute(
        select(Decision)
        .where(Decision.simulation_id == simulation.id)
        .order_by(Decision.decided_at.desc())
    ).scalars().all()
    decided = [decision for decision in decisions]
    approved = [decision for decision in decided if decision.action == "APPROVE"]
    modified = [decision for decision in decided if decision.action == "MODIFY"]
    rejected = [decision for decision in decided if decision.action == "REJECT"]
    deferred = [decision for decision in decided if decision.action == "DEFER"]
    alternatives = [
        decision for decision in decided if decision.action == "REQUEST_ALTERNATIVES"
    ]
    decided_count = len(approved) + len(modified) + len(rejected)
    acceptance_rate = (
        round(100 * (len(approved) + len(modified)) / decided_count, 2)
        if decided_count
        else None
    )
    modification_rate = (
        round(100 * len(modified) / decided_count, 2) if decided_count else None
    )

    horizon = max(1, int(state["sim_time_min"]) - int(state["start_time_min"]))
    section_utilization = {}
    for section in state["network"]["sections"]:
        busy = sum(
            state["counters"]["block_busy_min"].get(block["id"], 0)
            for block in section["blocks"]
        )
        section_utilization[section["id"]] = {
            "section_id": section["id"],
            "label": f"{section['from_station']}–{section['to_station']}",
            "mode": section["mode"],
            "utilization_pct": round(
                100 * busy / max(1, horizon * len(section["blocks"])), 2
            ),
        }
    platform_utilization = {}
    for station in state["network"]["stations"]:
        busy_map = state["counters"]["platform_busy_min"].get(station["id"], {})
        busy = sum(busy_map.values())
        platform_utilization[station["id"]] = {
            "station_id": station["id"],
            "label": station["name"],
            "utilization_pct": round(
                100 * busy / max(1, horizon * len(station["platforms"])), 2
            ),
        }
    latest_recommendation = recommendations[0] if recommendations else None
    comparison = (
        latest_recommendation.payload.get("comparison") if latest_recommendation else None
    )
    train_delays = [
        {
            "train_id": train["id"],
            "name": train["name"],
            "status": train["status"],
            "delay_min": train["delay_min"],
            "projected_delay_min": train.get("current_delay_min", train["delay_min"]),
            "priority": train["priority"],
            "train_type": train["train_type"],
        }
        for train in state["trains"]
    ]
    return {
        "simulation_id": simulation.id,
        "scenario_key": simulation.scenario_key,
        "scenario_name": simulation.name,
        "simulation_time": metrics["sim_time"],
        "sim_time_min": state["sim_time_min"],
        "state_version": simulation.state_version,
        "label": "SYNTHETIC",
        "data_disclaimer": (
            "These are simulated KPIs from synthetic data. They are not Indian "
            "Railways performance measurements and must not be presented as such."
        ),
        "kpis": {
            "average_delay_min": metrics["average_delay_min"],
            "total_delay_min": metrics["total_delay_min"],
            "max_delay_min": metrics["max_delay_min"],
            "on_time_performance_pct": metrics["on_time_performance_pct"],
            "section_utilization_pct": metrics["section_utilization_pct"],
            "platform_utilization_pct": metrics["platform_utilization_pct"],
            "throughput_trains_per_hour": metrics["throughput_trains_per_hour"],
            "conflict_frequency_active": len(conflicts),
            "conflicts_detected_total": state["counters"].get("conflicts_detected", 0),
            "trains_total": metrics["trains_total"],
            "trains_active": metrics["trains_active"],
            "trains_completed": metrics["trains_completed"],
            "trains_delayed": metrics["trains_delayed"],
            "waiting_min_total": metrics["waiting_min_total"],
        },
        "recommendation_stats": {
            "total": len(recommendations),
            "pending": sum(1 for item in recommendations if item.status == "PENDING"),
            "approved": len(approved),
            "modified": len(modified),
            "rejected": len(rejected),
            "deferred": len(deferred),
            "alternatives_requested": len(alternatives),
            "stale": sum(1 for item in recommendations if item.status == "STALE"),
            "acceptance_rate_pct": acceptance_rate,
            "modification_rate_pct": modification_rate,
            "decided_count": decided_count,
        },
        "section_utilization": list(section_utilization.values()),
        "platform_utilization": list(platform_utilization.values()),
        "train_delays": train_delays,
        "conflicts": conflicts,
        "latest_recommendation_comparison": comparison,
        "comparison_note": (
            "Per-decision measured comparison: no intervention vs baseline heuristic vs "
            "CP-SAT-only vs hybrid recommendation, evaluated on cloned 30-minute simulations."
        ),
    }


def station_master_kpis(
    db: Session,
    simulation: Simulation,
    station_id: str,
    punctuality_threshold_min: int = 5,
) -> dict:
    """Traceable operational KPIs specifically scoped for Station Master jurisdiction."""
    state = simulation.state
    now = int(state["sim_time_min"])
    station_match = [s for s in state["network"]["stations"] if s["id"] == station_id]
    if not station_match:
        raise ValueError(f"Station '{station_id}' not found in simulation network.")
    station = station_match[0]

    # Find monitored trains: currently at station OR arriving within 60 min
    monitored_trains: list[dict] = []
    arrival_delays: list[int] = []
    departure_delays: list[int] = []

    for train in state["trains"]:
        status = train.get("status")
        is_at_station = status == "AT_STATION" and train.get("station_id") == station_id
        is_approaching = False
        sched_entry = None
        for entry in train.get("schedule", []):
            if entry.get("station_id") == station_id:
                arr = entry.get("arrival_min")
                if arr is not None and now <= arr <= now + 60:
                    is_approaching = True
                    sched_entry = entry
                elif is_at_station:
                    sched_entry = entry
                break

        if is_at_station or is_approaching:
            proj_del = projected_delay(train, now)
            arrival_delays.append(proj_del)
            if is_at_station:
                departure_delays.append(proj_del)

            monitored_trains.append({
                "id": train["id"],
                "name": train["name"],
                "train_type": train["train_type"],
                "priority": train["priority"],
                "status": train["status"],
                "is_at_station": is_at_station,
                "platform": train.get("platform") if is_at_station else None,
                "projected_delay_min": proj_del,
                "is_on_time": proj_del <= punctuality_threshold_min,
                "destination": train["destination"],
                "scheduled_arrival": format_minutes(sched_entry["arrival_min"]) if sched_entry and sched_entry.get("arrival_min") else None,
                "scheduled_departure": format_minutes(sched_entry["departure_min"]) if sched_entry and sched_entry.get("departure_min") else None,
            })

    on_time_count = sum(1 for t in monitored_trains if t["is_on_time"])
    delayed_count = sum(1 for t in monitored_trains if not t["is_on_time"])
    if monitored_trains:
        adherence_pct: float | None = round(100.0 * on_time_count / len(monitored_trains), 1)
        adherence_status = "NORMAL"
        adherence_explanation = f"{on_time_count} of {len(monitored_trains)} monitored trains on-time (<= {punctuality_threshold_min} min delay)"
    else:
        adherence_pct = None
        adherence_status = "NO_DATA"
        adherence_explanation = "No trains scheduled or monitored in station window (T-30m to T+60m)"

    # Platform status breakdown
    platforms = station.get("platforms", [])
    occupancies = state.get("platform_occupancy", {}).get(station_id, {})
    active_outages = [
        o for o in state.get("platform_outages", [])
        if o["station_id"] == station_id and o["start_min"] <= now < o["end_min"]
    ]
    outage_pfs = {o["platform_id"]: o["reason"] for o in active_outages}

    platform_slots = []
    occupied_count = 0
    outage_count = 0
    for pf in platforms:
        occupant_id = occupancies.get(pf)
        if occupant_id:
            occupied_count += 1
            platform_slots.append({
                "platform_id": pf,
                "status": "OCCUPIED",
                "train_id": occupant_id,
                "description": f"Occupied by {occupant_id}",
            })
        elif pf in outage_pfs:
            outage_count += 1
            platform_slots.append({
                "platform_id": pf,
                "status": "OUTAGE",
                "train_id": None,
                "description": f"Outage: {outage_pfs[pf]}",
            })
        else:
            platform_slots.append({
                "platform_id": pf,
                "status": "AVAILABLE",
                "train_id": None,
                "description": "Ready for arrival",
            })

    avail_count = len(platforms) - occupied_count - outage_count
    avail_pct = round(100.0 * avail_count / max(1, len(platforms)), 1)

    # Scoped pending recommendations
    pending_recs = db.execute(
        select(Recommendation)
        .where(Recommendation.simulation_id == simulation.id)
        .where(Recommendation.status == "PENDING")
    ).scalars().all()
    station_recs = [
        r for r in pending_recs
        if station_id in r.payload.get("affected_stations", [])
    ]

    # Scoped conflicts & operational alerts
    conflicts = detect_conflicts(state, 60)
    station_conflicts = [
        c for c in conflicts
        if station_id in c.get("stations", []) or any(t["id"] in c.get("trains", []) for t in monitored_trains)
    ]

    # Feed health
    fh = feed_manager.get_feed_health("FEED-SIGNAL-01")

    return {
        "station_id": station_id,
        "station_name": station.get("name", station_id),
        "simulation_time": format_minutes(now),
        "sim_time_min": now,
        "time_period": "Active operational window: T-30m to T+60m lookahead",
        "data_freshness": {
            "status": fh.status,
            "freshness_seconds": fh.freshness_seconds,
            "is_stale": fh.is_stale,
            "last_heartbeat_at": fh.last_heartbeat_at.isoformat() if fh.last_heartbeat_at else None,
        },
        "kpis": {
            "trains_monitored": len(monitored_trains),
            "on_time_trains": on_time_count,
            "delayed_trains": delayed_count,
            "schedule_adherence_pct": adherence_pct,
            "adherence_status": adherence_status,
            "adherence_explanation": adherence_explanation,
            "punctuality_threshold_min": punctuality_threshold_min,
            "average_arrival_delay_min": round(sum(arrival_delays) / len(arrival_delays), 1) if arrival_delays else None,
            "average_departure_delay_min": round(sum(departure_delays) / len(departure_delays), 1) if departure_delays else None,
            "platform_availability_pct": avail_pct,
            "platforms_total": len(platforms),
            "platforms_available": avail_count,
            "platforms_occupied": occupied_count,
            "platforms_outage": outage_count,
            "pending_recommendations_count": len(station_recs),
            "operational_alerts_count": len(station_conflicts),
        },
        "platform_slots": platform_slots,
        "monitored_trains": monitored_trains,
        "operational_alerts": station_conflicts[:6],
        "pending_recommendations": [
            {
                "id": r.id,
                "label": r.payload.get("recommended", {}).get("label") or "Advisory Action",
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "state_version": r.state_version,
            }
            for r in station_recs[:5]
        ],
        "kpi_definitions": {
            "trains_monitored": "Count of trains currently berthed at or scheduled to arrive at this station within 60 min.",
            "schedule_adherence_pct": "Percentage of monitored trains with projected arrival/departure delay <= punctuality threshold (standard IR Mail/Express reporting guideline). Reports null when no trains are present in the observation window.",
            "punctuality_threshold_min": "Operating delay threshold (default 5 minutes) used to classify train arrivals as on-time according to Indian Railways operating guidelines (Railway Board Operating Directorate punctuality circulars), not a statutory General Rule.",
            "platform_availability_pct": "Percentage of total station platforms not currently occupied or under maintenance outage.",
            "average_arrival_delay_min": "Arithmetic mean of projected arrival delays for all approaching trains at this station. Reports null when no approaching trains are present.",
            "average_departure_delay_min": "Arithmetic mean of projected departure delays for all stationed trains. Reports null when no stationed trains are present.",
            "operational_alerts_count": "Active track exclusivity, headway, or platform conflicts within station interlocking limits.",
        },
    }


def section_controller_kpis(db: Session, simulation: Simulation) -> dict:
    """Traceable corridor-wide operational intelligence specifically for Section Controller."""
    state = simulation.state
    now = int(state["sim_time_min"])
    metrics = state_metrics(state)
    conflicts = detect_conflicts(state, 75)

    # 1. Section-wide train movements
    active_trains = [t for t in state["trains"] if t["status"] in {"RUNNING", "AT_STATION"}]
    completed_trains = [t for t in state["trains"] if t["status"] == "COMPLETED"]
    scheduled_trains = [t for t in state["trains"] if t["status"] == "SCHEDULED"]

    # 2. Block occupancy & bottlenecks
    total_blocks = sum(len(s["blocks"]) for s in state["network"]["sections"])
    occupied_blocks = [
        {"block_id": b, "train_id": occ.get("train_id")}
        for b, occ in state.get("block_occupancy", {}).items()
        if occ.get("train_id")
    ]
    block_occupancy_pct = round(100.0 * len(occupied_blocks) / max(1, total_blocks), 1)

    # Critical single-line bottlenecks (derived from network topology)
    bottlenecks = [
        block["id"]
        for section in state["network"]["sections"]
        if section.get("mode") == "SINGLE"
        for block in section.get("blocks", [])
    ]
    occupied_bottlenecks = [b for b in occupied_blocks if b["block_id"] in bottlenecks]

    # 3. Junction congestion (Malgaon Junction MLG throat)
    station_mlg = next((s for s in state["network"]["stations"] if s["id"] == "MLG"), None)
    throat_capacity = station_mlg.get("junction_throat_capacity", 2) if station_mlg else 2  # Hard constraint HC-006 limit
    mlg_sections = [sec for sec in state["network"]["sections"] if "MLG" in {sec["from_station"], sec["to_station"]}]
    mlg_adjacent_blocks = {blk["id"] for sec in mlg_sections for blk in sec.get("blocks", [])}
    
    mlg_throat_trains = [
        t["id"] for t in active_trains
        if (
            t.get("station_id") == "MLG"
            and (t.get("entry_min") if t.get("entry_min") is not None else now)
            <= now
            <= (t.get("exit_min") if t.get("exit_min") is not None else now)
        )
        or t.get("block_id") in mlg_adjacent_blocks
        or t.get("current_location") in mlg_adjacent_blocks
    ]
    throat_load = min(100.0, round(100.0 * len(mlg_throat_trains) / throat_capacity, 1))
    queue_length = max(0, len(mlg_throat_trains) - throat_capacity)
    congestion_level = (
        "SATURATED" if throat_load >= 100.0
        else "HIGH" if throat_load >= 75.0
        else "MODERATE" if throat_load >= 50.0
        else "LOW"
    )

    # 4. Conflict breakdown by severity
    severity_counts = {"CRITICAL": 0, "MAJOR": 0, "MINOR": 0, "WARNING": 0}
    for c in conflicts:
        sev = c.get("severity", "MINOR")
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    # 5. Delay propagation analysis
    initial_delay_sum = sum(int(t.get("initial_delay_min", 0)) for t in state["trains"])
    total_proj_delay = metrics["total_delay_min"]
    secondary_delay = max(0, total_proj_delay - initial_delay_sum)
    delay_propagation_index = round(secondary_delay / max(1, initial_delay_sum), 2)
    delayed_trains = [t for t in state["trains"] if projected_delay(t, now) > 5]

    knock_on_risk = (
        "SEVERE" if delay_propagation_index > 2.0 or severity_counts["CRITICAL"] > 0
        else "HIGH" if delay_propagation_index > 1.0 or severity_counts["MAJOR"] > 1
        else "MODERATE" if delay_propagation_index > 0.4
        else "LOW"
    )

    # 6. Pending decisions across corridor
    pending_recs = db.execute(
        select(Recommendation)
        .where(Recommendation.simulation_id == simulation.id)
        .where(Recommendation.status == "PENDING")
    ).scalars().all()

    # 7. Recovery performance
    total_conflicts_seen = state["counters"].get("conflicts_detected", len(conflicts))
    if total_conflicts_seen == 0 and len(conflicts) == 0:
        clearance_rate: float | None = None
        recovery_status = "NO_DATA"
    else:
        resolved_count = max(0, total_conflicts_seen - len(conflicts))
        clearance_rate = round(100.0 * resolved_count / max(1, total_conflicts_seen), 1)
        recovery_status = "ACTIVE"

    # Feed health
    fh = feed_manager.get_feed_health("FEED-SIGNAL-01")

    return {
        "simulation_time": metrics["sim_time"],
        "sim_time_min": now,
        "time_period": "Corridor-wide operational horizon [Sim Start to Projected +75m]",
        "data_freshness": {
            "status": fh.status,
            "freshness_seconds": fh.freshness_seconds,
            "is_stale": fh.is_stale,
            "last_heartbeat_at": fh.last_heartbeat_at.isoformat() if fh.last_heartbeat_at else None,
            "error_rate_pct": fh.error_rate_pct,
        },
        "kpis": {
            "trains_active": len(active_trains),
            "trains_completed": len(completed_trains),
            "trains_scheduled": len(scheduled_trains),
            "trains_delayed": len(delayed_trains),
            "average_section_delay_min": metrics["average_delay_min"],
            "total_section_delay_min": total_proj_delay,
            "block_occupancy_pct": block_occupancy_pct,
            "blocks_occupied": len(occupied_blocks),
            "blocks_total": total_blocks,
            "junction_throat_load_pct": throat_load,
            "junction_queue_length": queue_length,
            "junction_congestion_level": congestion_level,
            "throughput_trains_per_hour": metrics["throughput_trains_per_hour"],
            "on_time_performance_pct": metrics["on_time_performance_pct"],
            "delay_propagation_index": delay_propagation_index,
            "secondary_delay_min": secondary_delay,
            "knock_on_risk_level": knock_on_risk,
            "delay_propagation_is_statutory": False,
            "delay_propagation_methodology": "HEURISTIC_SIMULATION_ESTIMATE",
            "conflicts_total": len(conflicts),
            "conflicts_critical": severity_counts["CRITICAL"],
            "conflicts_major": severity_counts["MAJOR"],
            "conflicts_minor": severity_counts["MINOR"],
            "pending_decisions_count": len(pending_recs),
            "recovery_clearance_rate_pct": clearance_rate,
        },
        "delay_propagation_analysis": {
            "is_statutory_standard": False,
            "methodology": "HEURISTIC_SIMULATION_ESTIMATE",
            "initial_delay_sum_min": initial_delay_sum,
            "secondary_delay_min": secondary_delay,
            "delay_propagation_index": delay_propagation_index,
            "knock_on_risk_level": knock_on_risk,
            "description": "Advisory heuristic estimate: ratio of knock-on secondary delays to initial root causes. Not a statutory IR performance metric.",
        },
        "junction_status": {
            "junction_id": "MLG",
            "junction_name": "Malgaon Junction",
            "throat_capacity": throat_capacity,
            "active_transits": len(mlg_throat_trains),
            "transiting_trains": mlg_throat_trains,
            "congestion_level": congestion_level,
        },
        "occupied_bottlenecks": occupied_bottlenecks,
        "severity_breakdown": severity_counts,
        "active_conflicts": conflicts[:8],
        "pending_decisions": [
            {
                "id": r.id,
                "label": r.payload.get("recommended", {}).get("label") or "Corridor Recommendation",
                "affected_stations": r.payload.get("affected_stations", []),
                "disagreement": r.payload.get("disagreement", False),
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in pending_recs[:6]
        ],
        "kpi_definitions": {
            "average_section_delay_min": "Mean projected timetable delay across all active running and stationed trains in the section.",
            "block_occupancy_pct": "Proportion of total running line track blocks currently occupied by trains (excluding sidings/dead-ends).",
            "junction_throat_load_pct": "Current simultaneous transits through Malgaon junction throat divided by physical throat limit (2).",
            "delay_propagation_index": "Advisory heuristic estimate (non-statutory): ratio of secondary knock-on delays to root-cause initial delays (DPI = Secondary Delay / Initial Delay).",
            "recovery_clearance_rate_pct": "Percentage of historical conflicts successfully resolved through dispatcher decisions or spatial clearance. Reports null when no conflicts have occurred.",
        },
    }
