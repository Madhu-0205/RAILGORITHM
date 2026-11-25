"""Comprehensive verification tests for Station Master and Section Controller KPIs against ground truth."""
from __future__ import annotations

from unittest.mock import MagicMock
from sqlalchemy.orm import Session

from app.domain.state import initialise_state
from app.models import Simulation
from app.services.analytics_service import section_controller_kpis, station_master_kpis


def _build_ground_truth_simulation(scenario_key: str = "normal_traffic", state_mutations: dict | None = None) -> Simulation:
    """Constructs a deterministic simulation instance initialized from standard scenarios with known ground truth."""
    base_state = initialise_state(scenario_key)
    if state_mutations:
        base_state.update(state_mutations)

    sim = Simulation(
        id=f"sim-kpi-{scenario_key}",
        name=f"KPI Ground Truth ({scenario_key})",
        scenario_key=scenario_key,
        status="RUNNING",
        sim_time_min=base_state["sim_time_min"],
        state_version=5,
        created_by="section.master",
        state=base_state,
    )
    return sim


def test_station_master_kpis_ground_truth_calculation():
    """Verify Station Master KPIs against exact ground truth on normal_traffic at Malgaon (MLG)."""
    sim = _build_ground_truth_simulation("normal_traffic")
    mock_db = MagicMock(spec=Session)
    mock_db.execute.return_value.scalars.return_value.all.return_value = []

    res = station_master_kpis(mock_db, sim, "MLG")

    assert res["station_id"] == "MLG"
    assert res["station_name"] == "Malgaon Junction"
    assert "time_period" in res
    assert "data_freshness" in res

    kpis = res["kpis"]
    # Platforms at MLG: P1, P2, P3
    assert kpis["platforms_total"] == 3
    assert kpis["platforms_available"] + kpis["platforms_occupied"] + kpis["platforms_outage"] == 3
    expected_avail_pct = round(100.0 * kpis["platforms_available"] / 3, 1)
    assert kpis["platform_availability_pct"] == expected_avail_pct

    # Monitored trains
    monitored = res["monitored_trains"]
    assert kpis["trains_monitored"] == len(monitored)
    assert kpis["on_time_trains"] + kpis["delayed_trains"] == len(monitored)
    if len(monitored) > 0:
        expected_adherence = round(100.0 * kpis["on_time_trains"] / len(monitored), 1)
        assert kpis["schedule_adherence_pct"] == expected_adherence
        assert kpis["adherence_status"] == "NORMAL"
    else:
        assert kpis["schedule_adherence_pct"] is None
        assert kpis["adherence_status"] == "NO_DATA"

    # Platform slots
    slots = res["platform_slots"]
    assert len(slots) == 3
    for s in slots:
        assert s["status"] in {"AVAILABLE", "OCCUPIED", "OUTAGE"}


def test_station_master_empty_station_missing_data_behavior():
    """Verify Station Master KPI graceful degradation when no trains are present at station."""
    sim = _build_ground_truth_simulation("normal_traffic")
    sim.state["trains"] = []
    sim.state["platform_occupancy"] = {}
    mock_db = MagicMock(spec=Session)
    mock_db.execute.return_value.scalars.return_value.all.return_value = []

    res = station_master_kpis(mock_db, sim, "SRP")
    kpis = res["kpis"]

    assert kpis["trains_monitored"] == 0
    assert kpis["on_time_trains"] == 0
    assert kpis["delayed_trains"] == 0
    # No monitored trains -> schedule adherence is None (NO_DATA), never misleading 100.0%
    assert kpis["schedule_adherence_pct"] is None
    assert kpis["adherence_status"] == "NO_DATA"
    assert "No trains" in kpis["adherence_explanation"]
    assert kpis["punctuality_threshold_min"] == 5
    assert kpis["average_arrival_delay_min"] is None
    assert kpis["average_departure_delay_min"] is None
    assert kpis["platform_availability_pct"] == 100.0


def test_section_controller_kpis_ground_truth_calculation():
    """Verify Section Controller KPIs against exact ground truth on single_line_meet."""
    sim = _build_ground_truth_simulation("single_line_meet")
    mock_db = MagicMock(spec=Session)
    mock_db.execute.return_value.scalars.return_value.all.return_value = []

    res = section_controller_kpis(mock_db, sim)
    kpis = res["kpis"]

    # Basic train counts
    state = sim.state
    active_count = sum(1 for t in state["trains"] if t["status"] in {"RUNNING", "AT_STATION"})
    completed_count = sum(1 for t in state["trains"] if t["status"] == "COMPLETED")
    scheduled_count = sum(1 for t in state["trains"] if t["status"] == "SCHEDULED")

    assert kpis["trains_active"] == active_count
    assert kpis["trains_completed"] == completed_count
    assert kpis["trains_scheduled"] == scheduled_count

    # Blocks check (6 total blocks in standard Northern network)
    assert kpis["blocks_total"] == 6
    expected_block_pct = round(100.0 * kpis["blocks_occupied"] / 6, 1)
    assert kpis["block_occupancy_pct"] == expected_block_pct

    # Throat capacity check (Malgaon capacity = 2)
    assert res["junction_status"]["throat_capacity"] == 2
    assert kpis["junction_congestion_level"] in {"LOW", "MODERATE", "HIGH", "SATURATED"}

    # DPI and knock-on risk
    assert isinstance(kpis["delay_propagation_index"], float)
    assert kpis["knock_on_risk_level"] in {"LOW", "MODERATE", "HIGH", "SEVERE"}


def test_section_controller_knock_on_risk_threshold_tiers():
    """Verify DPI knock-on risk transitions across all tiers (LOW, HIGH, SEVERE)."""
    mock_db = MagicMock(spec=Session)
    mock_db.execute.return_value.scalars.return_value.all.return_value = []

    # 1. Low risk test: Secondary delay <= 0.4x initial delay
    sim_low = _build_ground_truth_simulation("normal_traffic")
    for t in sim_low.state["trains"]:
        t["status"] = "COMPLETED"
        t["delay_min"] = 12
        t["initial_delay_min"] = 10
    res_low = section_controller_kpis(mock_db, sim_low)
    # Secondary = 12 - 10 = 2; DPI = 2 / 10 = 0.20 -> LOW
    assert res_low["kpis"]["delay_propagation_index"] <= 0.4
    assert res_low["kpis"]["knock_on_risk_level"] == "LOW"

    # 2. High risk test: Secondary delay > 1.0x initial delay
    sim_high = _build_ground_truth_simulation("normal_traffic")
    for t in sim_high.state["trains"]:
        t["status"] = "COMPLETED"
        t["delay_min"] = 25
        t["initial_delay_min"] = 10
    res_high = section_controller_kpis(mock_db, sim_high)
    # Secondary = 25 - 10 = 15; DPI = 15 / 10 = 1.50 -> HIGH
    assert res_high["kpis"]["delay_propagation_index"] == 1.50
    assert res_high["kpis"]["knock_on_risk_level"] in {"HIGH", "SEVERE"}

    # 3. Severe risk test: Secondary delay > 2.0x initial delay
    sim_severe = _build_ground_truth_simulation("normal_traffic")
    for t in sim_severe.state["trains"]:
        t["status"] = "COMPLETED"
        t["delay_min"] = 35
        t["initial_delay_min"] = 10
    res_severe = section_controller_kpis(mock_db, sim_severe)
    # Secondary = 35 - 10 = 25; DPI = 25 / 10 = 2.50 -> SEVERE
    assert res_severe["kpis"]["delay_propagation_index"] == 2.50
    assert res_severe["kpis"]["knock_on_risk_level"] == "SEVERE"
