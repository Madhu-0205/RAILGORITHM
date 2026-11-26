"""Railway Infrastructure Topology & Branching Scenarios Test Suite.

Verifies:
1. Intermediate stations with linear UP/DOWN directional relationships
2. Junction stations with two converging branches
3. Junction stations with multiple (3+) converging branches
4. Non-linear UP and DOWN directional relationships (chainage x coordinates)
5. Arbitrary preceding and succeeding station sequences (non-standard station codes)
6. Error handling for missing or malformed topology
7. Telemetry degradation states (STALE, OFFLINE) and confidence impact
8. Multi-train junction throat congestion and capacity bottlenecking
"""
from __future__ import annotations

import pytest
from app.domain.network import Block, Network, Section, Station, TopologyError
from app.domain.topology_resolver import get_adjacent_station_ids, resolve_adjacent_stations
from app.domain.data_quality import evaluate_data_quality


def test_01_intermediate_linear_station():
    """Scenario 1: Intermediate station on a linear 3-station section."""
    network = {
        "stations": [
            {"id": "STA_A", "name": "Station Alpha", "code": "STA", "x": 0.0},
            {"id": "STA_B", "name": "Station Beta", "code": "STB", "x": 20.0},
            {"id": "STA_C", "name": "Station Gamma", "code": "STC", "x": 45.0},
        ],
        "sections": [
            {
                "id": "SEC_1",
                "from_station": "STA_A",
                "to_station": "STA_B",
                "mode": "DOUBLE",
                "distance_km": 20.0,
                "blocks": [{"id": "B1U", "direction": "UP"}, {"id": "B1D", "direction": "DOWN"}],
            },
            {
                "id": "SEC_2",
                "from_station": "STA_B",
                "to_station": "STA_C",
                "mode": "SINGLE",
                "distance_km": 25.0,
                "blocks": [{"id": "B2", "direction": "BIDIRECTIONAL"}],
            },
        ],
    }

    # Station B (Intermediate): Upstream is Alpha, Downstream is Gamma
    res_b = resolve_adjacent_stations(network, "STA_B")
    assert res_b["station_id"] == "STA_B"
    assert res_b["upstream_station"]["station_id"] == "STA_A"
    assert res_b["upstream_station"]["relative_position"] == "UPSTREAM (Rear Station)"
    assert res_b["downstream_station"]["station_id"] == "STA_C"
    assert res_b["downstream_station"]["relative_position"] == "DOWNSTREAM (Advance Station)"
    assert len(res_b["junction_branches"]) == 0

    # Station A (Origin Terminal): No upstream, downstream is Beta
    res_a = resolve_adjacent_stations(network, "STA_A")
    assert res_a["upstream_station"] is None
    assert res_a["downstream_station"]["station_id"] == "STA_B"

    # Station C (Destination Terminal): Upstream is Beta, no downstream
    res_c = resolve_adjacent_stations(network, "STA_C")
    assert res_c["upstream_station"]["station_id"] == "STA_B"
    assert res_c["downstream_station"] is None


def test_02_junction_with_two_branches():
    """Scenario 2: Junction station with two converging branch lines."""
    # J is at x=50. Main line comes from W (x=20) and goes to E (x=80).
    # Branch line 1 connects from NW (x=15) to J.
    # Branch line 2 connects from SW (x=10) to J.
    network = {
        "stations": [
            {"id": "NW_BR", "name": "Northwest Mine Branch", "code": "NWB", "x": 15.0},
            {"id": "SW_BR", "name": "Southwest Port Branch", "code": "SWB", "x": 10.0},
            {"id": "W_MAIN", "name": "West Main", "code": "WST", "x": 20.0},
            {"id": "J_STN", "name": "Central Junction", "code": "CJN", "x": 50.0, "is_junction": True},
            {"id": "E_MAIN", "name": "East Main", "code": "EST", "x": 80.0},
        ],
        "sections": [
            {"id": "SEC_W", "from_station": "W_MAIN", "to_station": "J_STN", "mode": "DOUBLE", "distance_km": 30.0},
            {"id": "SEC_E", "from_station": "J_STN", "to_station": "E_MAIN", "mode": "DOUBLE", "distance_km": 30.0},
            {"id": "SEC_NW", "from_station": "NW_BR", "to_station": "J_STN", "mode": "SINGLE", "distance_km": 35.0},
            {"id": "SEC_SW", "from_station": "SW_BR", "to_station": "J_STN", "mode": "SINGLE", "distance_km": 40.0},
        ],
    }

    res_j = resolve_adjacent_stations(network, "J_STN")
    assert res_j["is_junction"] is True
    assert res_j["total_connected_routes"] == 4
    # Primary upstream is W_MAIN (closest x at 20 vs 15 and 10)
    assert res_j["upstream_station"]["station_id"] == "W_MAIN"
    assert res_j["downstream_station"]["station_id"] == "E_MAIN"
    # Secondary upstream connections (NW_BR and SW_BR) are captured as junction branches!
    branch_destinations = {b["destination_station"] for b in res_j["junction_branches"]}
    assert branch_destinations == {"NW_BR", "SW_BR"}


def test_03_junction_with_multiple_branches():
    """Scenario 3: Major Junction station with multiple (4+) converging branch lines."""
    network = {
        "stations": [
            {"id": "JCT", "name": "Hub Junction", "code": "HUB", "x": 100.0, "is_junction": True},
            {"id": "LINE_N", "name": "North Feeder", "x": 70.0},
            {"id": "LINE_S", "name": "South Feeder", "x": 60.0},
            {"id": "LINE_W", "name": "West Trunk", "x": 80.0},
            {"id": "LINE_E", "name": "East Trunk", "x": 130.0},
            {"id": "LINE_SE", "name": "Southeast Express", "x": 140.0},
        ],
        "sections": [
            {"id": "SEC_W", "from_station": "LINE_W", "to_station": "JCT", "distance_km": 20.0},
            {"id": "SEC_N", "from_station": "LINE_N", "to_station": "JCT", "distance_km": 30.0},
            {"id": "SEC_S", "from_station": "LINE_S", "to_station": "JCT", "distance_km": 40.0},
            {"id": "SEC_E", "from_station": "JCT", "to_station": "LINE_E", "distance_km": 30.0},
            {"id": "SEC_SE", "from_station": "JCT", "to_station": "LINE_SE", "distance_km": 40.0},
        ],
    }

    res = resolve_adjacent_stations(network, "JCT")
    assert res["is_junction"] is True
    assert res["total_connected_routes"] == 5
    assert res["upstream_station"]["station_id"] == "LINE_W"  # closest upstream
    assert res["downstream_station"]["station_id"] == "LINE_E"  # closest downstream
    # 3 branches remaining: LINE_N, LINE_S (upstream branches) and LINE_SE (downstream branch)
    assert len(res["junction_branches"]) == 3
    branch_destinations = {b["destination_station"] for b in res["junction_branches"]}
    assert branch_destinations == {"LINE_N", "LINE_S", "LINE_SE"}


def test_04_up_and_down_directional_relationships():
    """Scenario 4: UP and DOWN directional relationships based on chainage and block direction."""
    network = {
        "stations": [
            {"id": "ST_0", "name": "Station Zero", "x": 0.0},
            {"id": "ST_1", "name": "Station One", "x": 50.0},
        ],
        "sections": [
            {
                "id": "SEC_0_1",
                "from_station": "ST_0",
                "to_station": "ST_1",
                "mode": "DOUBLE",
                "blocks": [
                    {"id": "BLK_UP", "direction": "UP", "signaling_type": "ABSOLUTE_BLOCK"},
                    {"id": "BLK_DN", "direction": "DOWN", "signaling_type": "ABSOLUTE_BLOCK"},
                ],
            }
        ],
    }

    # At ST_1: ST_0 is upstream (x=0 < x=50)
    res_1 = resolve_adjacent_stations(network, "ST_1")
    assert res_1["upstream_station"]["station_id"] == "ST_0"
    assert res_1["upstream_station"]["relative_position"] == "UPSTREAM (Rear Station)"
    blocks = res_1["upstream_station"]["blocks"]
    dirs = {b["direction"] for b in blocks}
    assert dirs == {"UP", "DOWN"}

    # At ST_0: ST_1 is downstream (x=50 > x=0)
    res_0 = resolve_adjacent_stations(network, "ST_0")
    assert res_0["downstream_station"]["station_id"] == "ST_1"
    assert res_0["downstream_station"]["relative_position"] == "DOWNSTREAM (Advance Station)"


def test_05_different_preceding_and_succeeding_stations():
    """Scenario 5: Custom non-linear network with arbitrary station identifiers."""
    network = {
        "stations": [
            {"id": "ZULU", "name": "Zulu Terminal", "x": 10.0},
            {"id": "YANKEE", "name": "Yankee Loop", "x": 30.0},
            {"id": "XRAY", "name": "Xray Junction", "x": 60.0, "is_junction": True},
            {"id": "WHISKEY", "name": "Whiskey Terminus", "x": 90.0},
        ],
        "sections": [
            {"id": "SEC_ZY", "from_station": "ZULU", "to_station": "YANKEE", "distance_km": 20.0},
            {"id": "SEC_YX", "from_station": "YANKEE", "to_station": "XRAY", "distance_km": 30.0},
            {"id": "SEC_XW", "from_station": "XRAY", "to_station": "WHISKEY", "distance_km": 30.0},
        ],
    }

    adj_ids = get_adjacent_station_ids(network, "XRAY")
    assert adj_ids == {"YANKEE", "WHISKEY"}

    res = resolve_adjacent_stations(network, "XRAY")
    assert res["upstream_station"]["station_id"] == "YANKEE"
    assert res["downstream_station"]["station_id"] == "WHISKEY"


def test_06_missing_topology_error_handling():
    """Scenario 6: Clean error handling for unknown station in topology."""
    network = {
        "stations": [{"id": "ST_A", "name": "Station A", "x": 0.0}],
        "sections": [],
    }
    with pytest.raises(KeyError) as exc_info:
        resolve_adjacent_stations(network, "UNKNOWN_STATION")
    assert "UNKNOWN_STATION" in str(exc_info.value)


def test_07_missing_telemetry_handling():
    """Scenario 7: Missing or degraded telemetry appropriately downgrades data quality confidence."""
    state_healthy = {
        "sim_time_min": 60,
        "label": "LIVE",
        "trains": [{"id": "T1", "status": "AT_STATION", "station_id": "NDL"}],
        "network": {
            "stations": [{"id": "NDL"}],
            "sections": [{"id": "S1", "blocks": [{"id": "B1"}]}],
        },
    }
    class MockFeed:
        status = "ACTIVE"
        is_stale = False
        freshness_seconds = 5
        feed_id = "FEED-SIGNAL-01"

    res_healthy = evaluate_data_quality(state_healthy, feed_health=MockFeed())
    assert res_healthy["overall_quality_state"] == "HEALTHY"
    assert res_healthy["is_eligible_for_recommendations"] is True

    state_stale = {
        "sim_time_min": 60,
        "trains": [{"id": "T1", "status": "AT_STATION", "station_id": "NDL"}],
        "network": {
            "stations": [{"id": "NDL"}],
            "sections": [{"id": "S1", "blocks": [{"id": "B1"}]}],
        },
        "_telemetry_quality_override": "STALE",
    }
    res_stale = evaluate_data_quality(state_stale)
    assert res_stale["overall_quality_state"] == "STALE"
    assert res_stale["is_eligible_for_recommendations"] is False
    assert res_stale["eligibility"]["eligibility_gate"] == "WITHHELD"

    state_offline = {
        "sim_time_min": 60,
        "trains": [{"id": "T1", "status": "AT_STATION", "station_id": "NDL"}],
        "network": {
            "stations": [{"id": "NDL"}],
            "sections": [{"id": "S1", "blocks": [{"id": "B1"}]}],
        },
        "_telemetry_quality_override": "OFFLINE",
    }
    res_offline = evaluate_data_quality(state_offline)
    assert res_offline["overall_quality_state"] == "OFFLINE"
    assert res_offline["is_eligible_for_recommendations"] is False
    assert res_offline["eligibility"]["eligibility_gate"] == "BLOCKED"


def test_08_multiple_trains_approaching_junction():
    """Scenario 8: Multiple trains converging on a junction station throat."""
    from app.services.analytics_service import section_controller_kpis
    from unittest.mock import MagicMock

    mock_db = MagicMock()
    mock_sim = MagicMock()
    mock_sim.id = "sim-multi-train"
    mock_sim.state = {
        "sim_time_min": 100,
        "start_time_min": 0,
        "counters": {
            "block_busy_min": {"B1": 15},
            "platform_busy_min": {"NDL": {"P1": 0, "P2": 0}, "MLG": {"P1": 20, "P2": 20, "P3": 20}},
            "completed": 0,
            "departures": 0,
            "arrivals": 3,
            "waiting_min": 10,
            "conflicts_detected": 2,
            "recommendations_generated": 1,
        },
        "network": {
            "id": "net-junction-test",
            "name": "Junction Test Network",
            "stations": [
                {"id": "NDL", "name": "Nandpur", "platforms": ["P1", "P2"], "x": 0.0},
                {"id": "MLG", "name": "Malgaon Jn", "platforms": ["P1", "P2", "P3"], "is_junction": True, "junction_throat_capacity": 2, "x": 50.0},
            ],
            "sections": [
                {"id": "S1", "from_station": "NDL", "to_station": "MLG", "mode": "SINGLE", "blocks": [{"id": "B1", "direction": "BIDIRECTIONAL", "run_time_min": 3}]},
            ],
        },
        "platform_occupancy": {"MLG": {"P1": "T1", "P2": "T2", "P3": "T3"}},
        "block_occupancy": {"B1": {"train_id": "T4"}},
        "trains": [
            {
                "id": "T1",
                "name": "Train 1",
                "status": "AT_STATION",
                "station_id": "MLG",
                "current_station": "MLG",
                "priority": 1,
                "delay_min": 0,
                "direction": "UP",
                "dwell_min": 2,
                "route_index": 1,
                "route": ["NDL", "MLG"],
                "entry_min": 90,
                "exit_min": 110,
                "schedule": [
                    {"station_id": "NDL", "arrival_min": None, "departure_min": 0, "run_from_previous_min": 0, "block_id": None, "section_id": None},
                    {"station_id": "MLG", "arrival_min": 90, "departure_min": None, "run_from_previous_min": 10, "block_id": "B1", "section_id": "S1"},
                ],
            },
            {
                "id": "T2",
                "name": "Train 2",
                "status": "AT_STATION",
                "station_id": "MLG",
                "current_station": "MLG",
                "priority": 2,
                "delay_min": 5,
                "direction": "UP",
                "dwell_min": 2,
                "route_index": 1,
                "route": ["NDL", "MLG"],
                "entry_min": 90,
                "exit_min": 110,
                "schedule": [
                    {"station_id": "NDL", "arrival_min": None, "departure_min": 0, "run_from_previous_min": 0, "block_id": None, "section_id": None},
                    {"station_id": "MLG", "arrival_min": 90, "departure_min": None, "run_from_previous_min": 10, "block_id": "B1", "section_id": "S1"},
                ],
            },
            {
                "id": "T3",
                "name": "Train 3",
                "status": "AT_STATION",
                "station_id": "MLG",
                "current_station": "MLG",
                "priority": 3,
                "delay_min": 10,
                "direction": "UP",
                "dwell_min": 2,
                "route_index": 1,
                "route": ["NDL", "MLG"],
                "entry_min": 90,
                "exit_min": 110,
                "schedule": [
                    {"station_id": "NDL", "arrival_min": None, "departure_min": 0, "run_from_previous_min": 0, "block_id": None, "section_id": None},
                    {"station_id": "MLG", "arrival_min": 90, "departure_min": None, "run_from_previous_min": 10, "block_id": "B1", "section_id": "S1"},
                ],
            },
            {
                "id": "T4",
                "name": "Train 4",
                "status": "RUNNING",
                "current_location": "B1",
                "block_id": "B1",
                "priority": 4,
                "delay_min": 15,
                "direction": "UP",
                "dwell_min": 2,
                "route_index": 0,
                "route": ["NDL", "MLG"],
                "entry_min": 95,
                "exit_min": 105,
                "schedule": [
                    {"station_id": "NDL", "arrival_min": None, "departure_min": 0, "run_from_previous_min": 0, "block_id": None, "section_id": None},
                    {"station_id": "MLG", "arrival_min": 105, "departure_min": None, "run_from_previous_min": 10, "block_id": "B1", "section_id": "S1"},
                ],
            },
        ],
    }

    kpis = section_controller_kpis(mock_db, mock_sim)
    # Throat capacity is 2, but 3 trains are in MLG station -> load should be saturated (>= 100%)
    assert kpis["kpis"]["junction_throat_load_pct"] >= 100.0
    assert kpis["kpis"]["junction_congestion_level"] in {"HIGH", "SATURATED"}
    assert kpis["kpis"]["junction_queue_length"] >= 1
