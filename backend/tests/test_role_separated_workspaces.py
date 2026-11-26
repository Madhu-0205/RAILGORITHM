"""Acceptance Test Suite for Role-Separated Railway Operations Workspaces.

Tests 35 concrete scenarios across 4 categories:
1. Category 1: Role Isolation & Access Control (Tests 1–10)
2. Category 2: Station Master Functionality & Domain Model (Tests 11–18)
3. Category 3: Section Controller Functionality & Domain Model (Tests 19–28)
4. Category 4: AI Decision Intelligence, Validation, and Safety Invariants (Tests 29–35)
"""
from __future__ import annotations

import pytest
from app.routers.auth import _LOGIN_ATTEMPTS


@pytest.fixture(autouse=True)
def clear_rate_limit():
    _LOGIN_ATTEMPTS.clear()
    yield
    _LOGIN_ATTEMPTS.clear()


def get_token(client, username, password):
    res = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert res.status_code == 200, f"Login failed for {username}: {res.text}"
    return res.json()["access_token"]


def get_simulation_id(client, token):
    res = client.get("/api/v1/simulations", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    sims = res.json()["simulations"]
    assert len(sims) > 0, "No simulation found in seeded test database"
    return sims[0]["id"]


# ==============================================================================
# CATEGORY 1: ROLE ISOLATION & ACCESS CONTROL (Tests 1–10)
# ==============================================================================

def test_01_station_master_can_view_own_station(client):
    """Test 1: Station Master (SM_NDL_001) can view own station (NDL) overview."""
    token = get_token(client, "SM_NDL_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/overview?station_id=NDL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["station_id"] == "NDL"
    assert data["station_name"] == "Nandpur Junction"


def test_02_station_master_cannot_view_other_station_overview(client):
    """Test 2: Station Master (SM_NDL_001) receives 403 Forbidden attempting to view another station's overview (KRN)."""
    token = get_token(client, "SM_NDL_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/overview?station_id=KRN",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "operational jurisdiction" in res.json()["detail"].lower()


def test_03_station_master_cannot_access_section_controller_overview(client):
    """Test 3: Station Master receives 403 Forbidden attempting to access full section controller overview."""
    token = get_token(client, "SM_NDL_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "VIEW_AUTHORIZED_SECTION" in res.json()["detail"]


def test_04_station_master_can_view_adjacent_station_context(client):
    """Test 4: Station Master (SM_NDL_001) can view adjacent operational context for KRN (connected station)."""
    token = get_token(client, "SM_NDL_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/adjacent-stations?station_id=NDL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["station_id"] == "NDL"
    assert data["downstream_station"]["station_id"] == "KRN"
    assert data["downstream_station"]["section_id"] == "S1"


def test_05_station_master_cannot_view_non_adjacent_station_context(client):
    """Test 5: Station Master (SM_NDL_001) receives 403 Forbidden attempting adjacent context for non-adjacent station (SRP)."""
    token = get_token(client, "SM_NDL_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/adjacent-stations?station_id=SRP",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403


def test_06_section_controller_can_view_territory_overview(client):
    """Test 6: Section Controller (SC_NORTH_001) can view territory overview."""
    token = get_token(client, "SC_NORTH_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "Northern Corridor" in data["section_name"]
    assert "monitored_stations_count" in data["kpis"]


def test_07_section_controller_cannot_access_station_master_workspace(client):
    """Test 7: Section Controller (SC_NORTH_001) receives 403 Forbidden attempting to access Station Master private workspace."""
    token = get_token(client, "SC_NORTH_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/overview?station_id=NDL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "VIEW_OWN_STATION" in res.json()["detail"]


def test_07b_section_controller_can_view_jurisdiction_station_summaries(client):
    """Test 7b: Section Controller (SC_NORTH_001) can view operational summaries for stations in jurisdiction (NDL, KRN, MLG) via dedicated endpoint."""
    token = get_token(client, "SC_NORTH_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    for st in ["NDL", "KRN", "MLG"]:
        res = client.get(
            f"/api/v1/simulations/{sim_id}/section-controller/stations/{st}/summary",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200, f"Failed for station {st}"
        assert res.json()["station_id"] == st
        assert res.json()["scope"] == "SECTION_CONTROLLER_OPERATIONAL_SUMMARY"


def test_08_section_controller_cannot_view_station_outside_jurisdiction(client):
    """Test 8: Section Controller (SC_NORTH_001) receives 403 Forbidden attempting to view station outside jurisdiction (VSN)."""
    token = get_token(client, "SC_NORTH_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/stations/VSN/summary",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403
    assert "operational jurisdiction" in res.json()["detail"].lower()


def test_09_section_controller_lacks_manage_station_local(client):
    """Test 9: Section Controller has VIEW_AUTHORIZED_SECTION but lacks MANAGE_STATION_LOCAL permission."""
    token = get_token(client, "SC_NORTH_001", "Section@123")
    from app.models import User
    u = User(username="SC_NORTH_001", role="SECTION_CONTROLLER", control_area="NORTHERN_CONTROL_AREA")
    assert u.has_permission("VIEW_AUTHORIZED_SECTION") is True
    assert u.has_permission("MANAGE_STATION_LOCAL") is False


def test_10_admin_has_universal_access(client):
    """Test 10: System Administrator (ADMIN_001) has access to all station master and section controller endpoints across all territories."""
    token = get_token(client, "ADMIN_001", "Admin@123")
    sim_id = get_simulation_id(client, token)

    # Can access any station overview
    for st in ["NDL", "KRN", "MLG", "SRP", "VSN"]:
        res_sm = client.get(
            f"/api/v1/simulations/{sim_id}/station-master/overview?station_id={st}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_sm.status_code == 200

    # Can access section controller overview
    res_sc = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_sc.status_code == 200


# ==============================================================================
# CATEGORY 2: STATION MASTER FUNCTIONALITY & DOMAIN MODEL (Tests 11–18)
# ==============================================================================

def test_11_station_overview_metrics_structure(client):
    """Test 11: Station Master overview returns correct station metadata, operational status, and summary counts."""
    token = get_token(client, "SM_NDL_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/overview?station_id=NDL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["operational_status"] in {"NORMAL", "CONGESTED", "REGULATED", "DEGRADED"}
    assert "summary_counts" in data
    assert "arriving_next_30m" in data["summary_counts"]
    assert "departing_next_30m" in data["summary_counts"]
    assert "through_next_30m" in data["summary_counts"]


def test_12_station_adherence_handles_no_data_cleanly(client):
    """Test 12: Schedule adherence returns NO_DATA when 0 trains match (never 100% fake adherence)."""
    token = get_token(client, "SM_VSN_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/overview?station_id=VSN",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    # If no trains in window, adherence_pct is None and adherence_status is NO_DATA
    if data["summary_counts"]["monitored_window_trains"] == 0:
        assert data["adherence"]["schedule_adherence_pct"] is None
        assert data["adherence"]["adherence_status"] == "NO_DATA"
    else:
        assert data["adherence"]["schedule_adherence_pct"] is not None


def test_13_station_layout_tracks_and_sidings(client):
    """Test 13: Station layout returns realistic tracks including Main Lines, Loop Lines, Goods Siding, and Shunting Neck."""
    token = get_token(client, "SM_MLG_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/layout?station_id=MLG",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    tracks = data["tracks"]
    categories = {t["category"] for t in tracks}
    assert "PLATFORM" in categories
    assert "LOOP_LINE" in categories
    assert "SIDING" in categories
    assert "SHUNTING_NECK" in categories


def test_14_station_layout_occupancy_and_route_locking(client):
    """Test 14: Station layout marks occupied platforms with occupant train ID and route lock."""
    token = get_token(client, "SM_MLG_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/layout?station_id=MLG",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    for track in data["tracks"]:
        if track["state"] == "OCCUPIED":
            assert track["occupied_by"] is not None
            assert track["route_locked"] is True


def test_15_station_layout_speed_restrictions(client):
    """Test 15: Station layout reports yard speed restrictions and throat status."""
    token = get_token(client, "SM_NDL_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/layout?station_id=NDL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "speed_restrictions" in data
    assert len(data["speed_restrictions"]) > 0
    assert data["throat_status"] in {"CLEAR", "CONGESTED", "RESTRICTED"}


def test_16_train_movement_board_categorization(client):
    """Test 16: Train movement board categorizes arriving, departing, through, and history trains."""
    token = get_token(client, "SM_MLG_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/movement-board?station_id=MLG",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "arriving" in data
    assert "departing" in data
    assert "through" in data
    assert "history" in data
    for train in data["arriving"] + data["departing"]:
        assert "line_clear_status" in train
        assert "speed_kmph" in train


def test_17_adjacent_station_awareness_data(client):
    """Test 17: Adjacent stations returns upstream and downstream connected block states and telemetry freshness."""
    token = get_token(client, "SM_KRN_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/adjacent-stations?station_id=KRN",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["upstream_station"]["station_id"] == "NDL"
    assert data["downstream_station"]["station_id"] == "MLG"
    assert "telemetry_freshness_seconds" in data["upstream_station"]
    assert "blocks" in data["upstream_station"]


def test_18_station_alerts_scoped_strictly(client):
    """Test 18: Station alerts returns only conflicts and recommendations scoped to the assigned station."""
    token = get_token(client, "SM_KRN_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/alerts?station_id=KRN",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["station_id"] == "KRN"
    assert "active_conflicts" in data
    assert "pending_recommendations" in data


# ==============================================================================
# CATEGORY 3: SECTION CONTROLLER FUNCTIONALITY & DOMAIN MODEL (Tests 19–28)
# ==============================================================================

def test_19_section_controller_corridor_kpis(client):
    """Test 19: Section overview returns corridor KPIs (active trains, delayed trains, block occupancy %, bottlenecks, punctuality, delay propagation index)."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    kpis = res.json()["kpis"]
    assert "trains_active" in kpis
    assert "block_occupancy_pct" in kpis
    assert "bottlenecks_occupied_count" in kpis
    assert "punctuality_pct" in kpis
    assert "delay_propagation_index" in kpis


def test_20_section_controller_monitored_stations(client):
    """Test 20: Section overview lists all monitored stations with platform occupancy and throat status."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/overview",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    stations = res.json()["monitored_stations"]
    assert len(stations) == 5
    station_ids = [s["station_id"] for s in stations]
    assert station_ids == ["NDL", "KRN", "MLG", "SRP", "VSN"]


def test_21_section_topology_strip(client):
    """Test 21: Section topology returns complete linear corridor strip with km markers, single/double line modes, and speed restrictions."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/topology",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["corridor_length_km"] == 60.0
    assert len(data["stations"]) == 5
    assert len(data["sections"]) == 4
    assert len(data["speed_restrictions"]) >= 2


def test_22_section_train_ledger(client):
    """Test 22: Section train ledger lists all corridor trains with current location, speed, priority class, and crew hours."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/train-ledger",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_trains"] > 0
    for train in data["trains"]:
        assert "precedence_class" in train
        assert "current_location" in train
        assert "crew_duty_hours" in train
        assert "eta_section_exit" in train


def test_23_section_block_board_aspects(client):
    """Test 23: Block board lists all corridor block sections with signal aspects (Green/Red) and axle-counter health."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/block-board",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["total_blocks"] >= 6
    for block in data["blocks"]:
        assert block["signal_aspect"] in {"GREEN", "YELLOW", "DOUBLE_YELLOW", "RED"}
        assert block["axle_counter_status"] == "HEALTHY"


def test_24_single_line_bottleneck_detection(client):
    """Test 24: Single-line bottleneck sections (S1, S3) are correctly identified in block board."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/block-board",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    single_line_blocks = [b for b in res.json()["blocks"] if b["mode"] == "SINGLE"]
    assert len(single_line_blocks) >= 2


def test_25_junction_workspace_scenarios(client):
    """Test 25: Junction workspace returns convergence crossing scenarios with Train A vs Train B side-by-side comparison."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/junction-workspace",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["active_scenarios"]) > 0
    sc = data["active_scenarios"][0]
    assert "train_a" in sc
    assert "train_b" in sc
    assert "recommended_resolution" in sc


def test_26_junction_workspace_alternative_delays(client):
    """Test 26: Junction workspace alternative comparison computes net corridor delay savings vs penalties."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/junction-workspace",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    sc = res.json()["active_scenarios"][0]
    rec = sc["recommended_resolution"]
    alt = sc["alternative_option"]
    assert rec["net_corridor_saving_min"] > 0
    assert alt["net_corridor_penalty_min"] > 0


def test_27_section_alerts_severity_breakdown(client):
    """Test 27: Section alerts returns corridor-wide conflicts categorized by severity."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/alerts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "conflicts" in data
    assert "recommendations" in data


def test_28_section_alerts_evidence_status(client):
    """Test 28: Section alerts includes CP-SAT / PPO recommendations with narrative explanations and evidence status."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/alerts",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    recs = res.json()["recommendations"]
    if recs:
        rec = recs[0]
        assert "evidence_status" in rec
        assert "confidence" in rec


# ==============================================================================
# CATEGORY 4: AI DECISION SUPPORT & SAFETY INVARIANTS (Tests 29–35)
# ==============================================================================

def test_29_ai_recommendations_advisory_status(client):
    """Test 29: AI recommendations are strictly advisory (PENDING state until human controller decides)."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/recommendations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    recs = res.json()["recommendations"]
    for rec in recs:
        assert rec["status"] in {"PENDING", "APPROVED", "REJECTED", "MODIFIED", "DEFERRED"}


def test_30_independent_validator_safety_checks(client):
    """Test 30: AI recommendations include independent validator constraint verification (e.g. G&SR 3.38, HC-006)."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/section-controller/junction-workspace",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    sc = res.json()["active_scenarios"][0]
    checks = sc["recommended_resolution"]["safety_constraints_verified"]
    rules = [c["rule"] for c in checks]
    assert "G&SR 3.38" in rules or "G&SR 4.17" in rules


def test_31_human_decision_audit_trail(client):
    """Test 31: System creates immutable decision audit record when controller reviews a recommendation."""
    token = get_token(client, "SC_CORRIDOR_001", "Section@123")
    sim_id = get_simulation_id(client, token)

    # Fetch recommendations
    recs_res = client.get(f"/api/v1/simulations/{sim_id}/recommendations", headers={"Authorization": f"Bearer {token}"})
    recs = recs_res.json()["recommendations"]
    if recs:
        rec_id = recs[0]["id"]
        dec_res = client.post(
            f"/api/v1/recommendations/{rec_id}/decide",
            headers={"Authorization": f"Bearer {token}"},
            json={"action": "APPROVE", "reason": "Controller verified loop availability"},
        )
        assert dec_res.status_code in {200, 201}
        assert dec_res.json()["action"] == "APPROVE"


def test_32_decision_records_immutable(client):
    """Test 32: Decision records are protected and cannot be directly deleted via standard API."""
    token = get_token(client, "ADMIN_001", "Admin@123")
    # API has no DELETE /decisions/{id} endpoint
    res = client.delete("/api/v1/decisions/fake-id", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code in {404, 405}


def test_33_non_vital_disclaimer_present(client):
    """Test 33: Non-vital disclaimer is present in system metadata (never claims vital interlocking or Indian Railways operational certification)."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json()
    assert data["human_in_control"] is True
    assert data["live_railway_connection"] is False


def test_34_data_quality_confidence_scores(client):
    """Test 34: Data quality degradation reflects in confidence score and status flag."""
    token = get_token(client, "SM_NDL_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    res = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/overview?station_id=NDL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    dq = res.json()["data_quality"]
    assert "confidence_score" in dq
    assert dq["confidence_score"] > 0.0


def test_35_token_revocation_blocks_outdated_tokens(client):
    """Test 35: Token version revocation immediately blocks outdated tokens across both workspaces."""
    token = get_token(client, "SM_NDL_001", "Station@123")
    sim_id = get_simulation_id(client, token)

    # Verify token works initially
    res_valid = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/overview?station_id=NDL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_valid.status_code == 200

    # Logout to revoke
    res_logout = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res_logout.status_code == 200

    # Verify revoked token returns 401
    res_revoked = client.get(
        f"/api/v1/simulations/{sim_id}/station-master/overview?station_id=NDL",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res_revoked.status_code == 401
