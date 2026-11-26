"""Comprehensive 9-Account Jurisdiction & Workspace Isolation Test Matrix.

Tests all 9 accounts:
1. SC_NORTH_001 (territory: NDL, KRN, MLG)
2. SC_SOUTH_001 (territory: MLG, SRP, VSN)
3. SC_CORRIDOR_001 (territory: All 5 stations: NDL, KRN, MLG, SRP, VSN)
4. SM_NDL_001 (assigned: NDL)
5. SM_KRN_001 (assigned: KRN)
6. SM_MLG_001 (assigned: MLG)
7. SM_SRP_001 (assigned: SRP)
8. SM_VSN_001 (assigned: VSN)
9. ADMIN_001 (universal authority)

Verifies:
- Read access boundaries across stations and sections
- Station Master workspace privacy
- Section Controller territory boundaries
- Station operational visibility vs station-local execution authority
- User directory and credential protection
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db import Base, get_db
from app.main import app
from app.services.seed import seed_users, seed_default_simulation
from app.models import Simulation
from app.routers.auth import _LOGIN_ATTEMPTS

ALL_STATIONS = ["NDL", "KRN", "MLG", "SRP", "VSN"]

ACCOUNTS = {
    "SC_NORTH_001": {"pwd": "Section@123", "role": "SECTION_CONTROLLER", "allowed_st": {"NDL", "KRN", "MLG"}},
    "SC_SOUTH_001": {"pwd": "Section@123", "role": "SECTION_CONTROLLER", "allowed_st": {"MLG", "SRP", "VSN"}},
    "SC_CORRIDOR_001": {"pwd": "Section@123", "role": "SECTION_CONTROLLER", "allowed_st": set(ALL_STATIONS)},
    "SM_NDL_001": {"pwd": "Station@123", "role": "STATION_MASTER", "own_st": "NDL", "adj_st": {"KRN"}},
    "SM_KRN_001": {"pwd": "Station@123", "role": "STATION_MASTER", "own_st": "KRN", "adj_st": {"NDL", "MLG"}},
    "SM_MLG_001": {"pwd": "Station@123", "role": "STATION_MASTER", "own_st": "MLG", "adj_st": {"KRN", "SRP"}},
    "SM_SRP_001": {"pwd": "Station@123", "role": "STATION_MASTER", "own_st": "SRP", "adj_st": {"MLG", "VSN"}},
    "SM_VSN_001": {"pwd": "Station@123", "role": "STATION_MASTER", "own_st": "VSN", "adj_st": {"SRP"}},
    "ADMIN_001": {"pwd": "Admin@123", "role": "ADMIN", "allowed_st": set(ALL_STATIONS)},
}


@pytest.fixture(scope="module")
def test_client():
    test_db_url = "sqlite:///./test_jurisdiction_matrix.db"
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    with TestingSessionLocal() as session:
        seed_users(session)
        seed_default_simulation(session)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def auth_tokens(test_client):
    tokens = {}
    for username, creds in ACCOUNTS.items():
        res = test_client.post(
            "/api/v1/auth/login",
            json={"username": username, "password": creds["pwd"]},
        )
        assert res.status_code == 200, f"Login failed for {username}: {res.text}"
        tokens[username] = res.json()["access_token"]
    return tokens


@pytest.fixture(scope="module")
def sim_id(test_client, auth_tokens):
    token = auth_tokens["ADMIN_001"]
    res = test_client.get(
        "/api/v1/simulations",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    sims = res.json()["simulations"]
    assert len(sims) > 0
    return sims[0]["id"]


# ==============================================================================
# 1. STATION MASTER WORKSPACE ISOLATION TESTS
# ==============================================================================

def test_station_master_access_matrix(test_client, auth_tokens, sim_id):
    """Test all 5 Station Masters across all 5 stations for /station-master/overview."""
    sm_accounts = [acc for acc in ACCOUNTS if acc.startswith("SM_")]
    for username in sm_accounts:
        token = auth_tokens[username]
        own_st = ACCOUNTS[username]["own_st"]

        for station in ALL_STATIONS:
            res = test_client.get(
                f"/api/v1/simulations/{sim_id}/station-master/overview?station_id={station}",
                headers={"Authorization": f"Bearer {token}"},
            )
            if station == own_st:
                assert res.status_code == 200, f"{username} should have access to own station {station}"
                data = res.json()
                assert data["station_id"] == station
            else:
                assert res.status_code == 403, f"{username} must be forbidden from {station}"


def test_section_controllers_blocked_from_station_master_overview(test_client, auth_tokens, sim_id):
    """Section Controllers cannot access /station-master/overview under any circumstances."""
    sc_accounts = ["SC_NORTH_001", "SC_SOUTH_001", "SC_CORRIDOR_001"]
    for username in sc_accounts:
        token = auth_tokens[username]
        for station in ALL_STATIONS:
            res = test_client.get(
                f"/api/v1/simulations/{sim_id}/station-master/overview?station_id={station}",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 403, (
                f"{username} must receive 403 on /station-master/overview for {station}"
            )


# ==============================================================================
# 2. SECTION CONTROLLER WORKSPACE ISOLATION TESTS
# ==============================================================================

def test_section_controllers_can_view_section_console(test_client, auth_tokens, sim_id):
    """All Section Controllers can view corridor console /section-controller/overview."""
    for username in ["SC_NORTH_001", "SC_SOUTH_001", "SC_CORRIDOR_001"]:
        token = auth_tokens[username]
        res = test_client.get(
            f"/api/v1/simulations/{sim_id}/section-controller/overview",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 200, f"{username} failed to access /section-controller/overview"
        data = res.json()
        assert "kpis" in data
        assert "monitored_stations" in data


def test_station_masters_blocked_from_section_console(test_client, auth_tokens, sim_id):
    """Station Masters cannot access /section-controller/overview (lacks VIEW_AUTHORIZED_SECTION)."""
    sm_accounts = [acc for acc in ACCOUNTS if acc.startswith("SM_")]
    for username in sm_accounts:
        token = auth_tokens[username]
        res = test_client.get(
            f"/api/v1/simulations/{sim_id}/section-controller/overview",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res.status_code == 403, f"{username} must receive 403 on /section-controller/overview"


# ==============================================================================
# 3. SECTION CONTROLLER STATION SUMMARY JURISDICTION MATRIX
# ==============================================================================

def test_section_controller_station_summary_jurisdiction_matrix(test_client, auth_tokens, sim_id):
    """Verify SC_NORTH, SC_SOUTH, and SC_CORRIDOR against all 5 station summary endpoints."""
    sc_accounts = ["SC_NORTH_001", "SC_SOUTH_001", "SC_CORRIDOR_001"]
    for username in sc_accounts:
        token = auth_tokens[username]
        allowed = ACCOUNTS[username]["allowed_st"]

        for station in ALL_STATIONS:
            res = test_client.get(
                f"/api/v1/simulations/{sim_id}/section-controller/stations/{station}/summary",
                headers={"Authorization": f"Bearer {token}"},
            )
            if station in allowed:
                assert res.status_code == 200, f"{username} should access station summary {station}"
                data = res.json()
                assert data["station_id"] == station
                assert "platforms_total" in data
                assert "throat_capacity" in data
            else:
                assert res.status_code == 403, (
                    f"{username} must receive 403 on station summary {station} outside jurisdiction"
                )


def test_station_masters_blocked_from_sc_station_summary(test_client, auth_tokens, sim_id):
    """Station Masters cannot access /section-controller/stations/{st}/summary (lacks VIEW_AUTHORIZED_SECTION)."""
    sm_accounts = [acc for acc in ACCOUNTS if acc.startswith("SM_")]
    for username in sm_accounts:
        token = auth_tokens[username]
        for station in ALL_STATIONS:
            res = test_client.get(
                f"/api/v1/simulations/{sim_id}/section-controller/stations/{station}/summary",
                headers={"Authorization": f"Bearer {token}"},
            )
            assert res.status_code == 403, (
                f"{username} must receive 403 on /section-controller/stations/{station}/summary"
            )


# ==============================================================================
# 4. ADJACENT STATION CONTEXT BOUNDARY TESTS
# ==============================================================================

def test_station_master_adjacent_awareness_boundaries(test_client, auth_tokens, sim_id):
    """Verify that Station Masters can only view adjacent stations on /station-master/adjacent-stations."""
    for username in ["SM_NDL_001", "SM_VSN_001"]:
        token = auth_tokens[username]
        own_st = ACCOUNTS[username]["own_st"]
        allowed_adj = ACCOUNTS[username]["adj_st"]

        # Requesting adjacent context for own station
        res_own = test_client.get(
            f"/api/v1/simulations/{sim_id}/station-master/adjacent-stations?station_id={own_st}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_own.status_code == 200

        # Requesting context for a distant station
        distant_station = "VSN" if own_st == "NDL" else "NDL"
        res_distant = test_client.get(
            f"/api/v1/simulations/{sim_id}/station-master/adjacent-stations?station_id={distant_station}",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert res_distant.status_code == 403, (
            f"{username} must receive 403 when probing non-adjacent {distant_station}"
        )


# ==============================================================================
# 5. USER MANAGEMENT & CREDENTIAL ISOLATION TESTS
# ==============================================================================

def test_user_management_strictly_admin_only(test_client, auth_tokens):
    """Only ADMIN_001 can access /api/v1/auth/users; all 8 other accounts receive 403."""
    # Admin test
    admin_res = test_client.get(
        "/api/v1/auth/users",
        headers={"Authorization": f"Bearer {auth_tokens['ADMIN_001']}"},
    )
    assert admin_res.status_code == 200
    users = admin_res.json()
    assert len(users) >= 9

    # Non-admin accounts test
    non_admin_accounts = [acc for acc in ACCOUNTS if acc != "ADMIN_001"]
    for username in non_admin_accounts:
        res = test_client.get(
            "/api/v1/auth/users",
            headers={"Authorization": f"Bearer {auth_tokens[username]}"},
        )
        assert res.status_code == 403, f"{username} must receive 403 on /api/v1/auth/users"


def test_private_account_info_not_leaked(test_client, auth_tokens):
    """Ensure /api/v1/auth/me returns only authenticated user's profile and never exposes password_hash."""
    for username in ACCOUNTS:
        res = test_client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {auth_tokens[username]}"},
        )
        assert res.status_code == 200
        profile = res.json()
        assert profile["username"] == username
        assert "password_hash" not in profile
        assert "password" not in profile


# ==============================================================================
# 6. LOCAL EXECUTION AUTHORITY VS CORRIDOR REGULATION TESTS
# ==============================================================================

def test_operational_visibility_does_not_grant_unauthorized_execution(test_client, auth_tokens, sim_id):
    """Verify that viewing station data does not grant unauthorized decision execution authority."""
    # Generate recommendations for simulation
    rec_res = test_client.post(
        f"/api/v1/simulations/{sim_id}/recommendations",
        headers={"Authorization": f"Bearer {auth_tokens['ADMIN_001']}"},
    )
    assert rec_res.status_code == 200
    recs_data = rec_res.json()
    recs = recs_data.get("recommendations", [])
    if recs:
        # Find a recommendation that affects stations outside NDL
        non_ndl_rec = next((r for r in recs if "NDL" not in r.get("affected_stations", [])), recs[0])
        affected = non_ndl_rec.get("affected_stations", [])
        if not set(affected).issubset({"NDL"}):
            dec_res = test_client.post(
                f"/api/v1/recommendations/{non_ndl_rec['id']}/decision",
                json={
                    "action": "APPROVE",
                    "rationale": "Attempting unauthorized remote approval from Nandpur",
                },
                headers={"Authorization": f"Bearer {auth_tokens['SM_NDL_001']}"},
            )
            assert dec_res.status_code == 403, (
                f"SM_NDL_001 must receive 403 when attempting decision on external recommendation: {dec_res.text}"
            )


# ==============================================================================
# 7. DEDICATED PORTAL SERVER-SIDE AUTHENTICATION ISOLATION TESTS
# ==============================================================================

def test_portal_authentication_isolation_station_master_portal(test_client):
    """Station Master Portal strictly rejects Section Controller accounts."""
    _LOGIN_ATTEMPTS.clear()
    # 1. Station Master succeeds
    res_sm = test_client.post(
        "/api/v1/auth/login/station-master",
        json={"username": "SM_NDL_001", "password": "Station@123"},
    )
    assert res_sm.status_code == 200
    assert res_sm.json()["user"]["role"] == "STATION_MASTER"

    # 2. Section Controllers are strictly rejected
    for sc_user in ["SC_NORTH_001", "SC_SOUTH_001", "SC_CORRIDOR_001"]:
        _LOGIN_ATTEMPTS.clear()
        res_sc = test_client.post(
            "/api/v1/auth/login/station-master",
            json={"username": sc_user, "password": "Section@123"},
        )
        assert res_sc.status_code == 403, f"{sc_user} must be rejected on Station Master portal"
        assert "cannot authenticate through the Station Master Portal" in res_sc.json()["detail"]


def test_portal_authentication_isolation_section_controller_portal(test_client):
    """Section Controller Portal strictly rejects Station Master accounts."""
    _LOGIN_ATTEMPTS.clear()
    # 1. Section Controller succeeds
    res_sc = test_client.post(
        "/api/v1/auth/login/section-controller",
        json={"username": "SC_CORRIDOR_001", "password": "Section@123"},
    )
    assert res_sc.status_code == 200
    assert res_sc.json()["user"]["role"] == "SECTION_CONTROLLER"

    # 2. Station Masters are strictly rejected
    for sm_user in ["SM_NDL_001", "SM_KRN_001", "SM_MLG_001", "SM_SRP_001", "SM_VSN_001"]:
        _LOGIN_ATTEMPTS.clear()
        res_sm = test_client.post(
            "/api/v1/auth/login/section-controller",
            json={"username": sm_user, "password": "Station@123"},
        )
        assert res_sm.status_code == 403, f"{sm_user} must be rejected on Section Controller portal"
        assert "cannot authenticate through the Section Controller Portal" in res_sm.json()["detail"]


def test_portal_payload_rejection(test_client):
    """Generic login endpoint with portal parameter enforces identical server-side role restriction."""
    _LOGIN_ATTEMPTS.clear()
    # Cross-role attempt on generic login with portal constraint
    res = test_client.post(
        "/api/v1/auth/login",
        json={"username": "SC_NORTH_001", "password": "Section@123", "portal": "STATION_MASTER"},
    )
    assert res.status_code == 403
    assert "cannot authenticate through the Station Master Portal" in res.json()["detail"]

