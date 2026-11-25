"""Tests for Station Master and Section Controller KPI engines and endpoints."""
from __future__ import annotations

import pytest


def test_station_master_kpi_engine_and_endpoint(client, station_headers, simulation):
    """Station Master KPI endpoint returns accurate station-scoped metrics."""
    sim_id = simulation["id"]
    res = client.get(
        f"/api/v1/simulations/{sim_id}/analytics/station-master?station_id=MLG",
        headers=station_headers,
    )
    assert res.status_code == 200
    data = res.json()

    assert data["station_id"] == "MLG"
    assert "station_name" in data
    assert "time_period" in data
    assert "data_freshness" in data
    assert "status" in data["data_freshness"]

    kpis = data["kpis"]
    assert "trains_monitored" in kpis
    assert "on_time_trains" in kpis
    assert "delayed_trains" in kpis
    assert "schedule_adherence_pct" in kpis
    assert "average_arrival_delay_min" in kpis
    assert "platform_availability_pct" in kpis
    assert "platforms_total" in kpis
    assert "platforms_available" in kpis
    assert "pending_recommendations_count" in kpis
    assert "operational_alerts_count" in kpis

    # Structure checks
    assert isinstance(data["platform_slots"], list)
    assert len(data["platform_slots"]) == kpis["platforms_total"]
    for slot in data["platform_slots"]:
        assert slot["status"] in {"OCCUPIED", "AVAILABLE", "OUTAGE"}

    assert isinstance(data["monitored_trains"], list)
    assert "kpi_definitions" in data
    assert "trains_monitored" in data["kpi_definitions"]
    assert "schedule_adherence_pct" in data["kpi_definitions"]


def test_section_controller_kpi_engine_and_endpoint(client, section_headers, simulation):
    """Section Controller KPI endpoint returns comprehensive corridor intelligence."""
    sim_id = simulation["id"]
    res = client.get(
        f"/api/v1/simulations/{sim_id}/analytics/section-controller",
        headers=section_headers,
    )
    assert res.status_code == 200
    data = res.json()

    assert "simulation_time" in data
    assert "time_period" in data
    assert "data_freshness" in data

    kpis = data["kpis"]
    assert "trains_active" in kpis
    assert "trains_completed" in kpis
    assert "average_section_delay_min" in kpis
    assert "block_occupancy_pct" in kpis
    assert "junction_throat_load_pct" in kpis
    assert "junction_congestion_level" in kpis
    assert kpis["junction_congestion_level"] in {"LOW", "MODERATE", "HIGH", "SATURATED"}
    assert "throughput_trains_per_hour" in kpis
    assert "delay_propagation_index" in kpis
    assert "knock_on_risk_level" in kpis
    assert kpis["knock_on_risk_level"] in {"LOW", "MODERATE", "HIGH", "SEVERE"}
    assert "conflicts_total" in kpis
    assert "pending_decisions_count" in kpis
    assert "recovery_clearance_rate_pct" in kpis

    # Junction status
    j_status = data["junction_status"]
    assert j_status["junction_id"] == "MLG"
    assert j_status["throat_capacity"] == 2
    assert "active_transits" in j_status

    # Traceable definitions
    assert "kpi_definitions" in data
    assert "average_section_delay_min" in data["kpi_definitions"]
    assert "delay_propagation_index" in data["kpi_definitions"]
    assert "recovery_clearance_rate_pct" in data["kpi_definitions"]
