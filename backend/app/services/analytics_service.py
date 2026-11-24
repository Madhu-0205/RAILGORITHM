"""Simulation analytics derived from actual simulation and decision records."""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.conflicts import detect_conflicts
from ..domain.state import state_metrics
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
