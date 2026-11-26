"""Security and Jurisdiction Access Control Tests for RAILGORITHM v2.8.1."""
from __future__ import annotations

import pytest
from app.routers.auth import _LOGIN_ATTEMPTS


@pytest.fixture(autouse=True)
def clear_rate_limit():
    _LOGIN_ATTEMPTS.clear()
    yield
    _LOGIN_ATTEMPTS.clear()


def test_independent_user_logins(client):
    # Station Master - Nandpur
    res_sm_ndl = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_NDL_001", "password": "Station@123"},
    )
    assert res_sm_ndl.status_code == 200
    body = res_sm_ndl.json()
    assert body["user"]["role"] == "STATION_MASTER"
    assert body["user"]["station_id"] == "NDL"
    assert "NDL" in body["user"]["assigned_stations"]
    assert body["user"]["control_area"] == "NORTHERN_CONTROL_AREA"

    # Station Master - Malgaon
    res_sm_mlg = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_MLG_001", "password": "Station@123"},
    )
    assert res_sm_mlg.status_code == 200
    assert res_sm_mlg.json()["user"]["station_id"] == "MLG"

    # Section Controller - North
    res_sc_north = client.post(
        "/api/v1/auth/login",
        json={"username": "SC_NORTH_001", "password": "Section@123"},
    )
    assert res_sc_north.status_code == 200
    body_sc = res_sc_north.json()
    assert body_sc["user"]["role"] == "SECTION_CONTROLLER"
    assert body_sc["user"]["control_area"] == "NORTHERN_CONTROL_AREA"
    assert set(body_sc["user"]["assigned_stations"]) == {"NDL", "KRN", "MLG"}

    # Administrator
    res_admin = client.post(
        "/api/v1/auth/login",
        json={"username": "ADMIN_001", "password": "Admin@123"},
    )
    assert res_admin.status_code == 200
    assert res_admin.json()["user"]["role"] == "ADMIN"


def test_station_master_cannot_access_section_controller_endpoints(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_NDL_001", "password": "Station@123"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    # Station Master cannot view audit log
    res_audit = client.get("/api/v1/audit", headers=headers)
    assert res_audit.status_code == 403

    # Station Master cannot create simulation
    res_sim = client.post(
        "/api/v1/simulations",
        json={"scenario_key": "baseline_morning_peak"},
        headers=headers,
    )
    assert res_sim.status_code == 403

    # Station Master cannot advance simulation
    res_adv = client.post(
        "/api/v1/simulations/non-existent/advance",
        json={"minutes": 10},
        headers=headers,
    )
    assert res_adv.status_code == 403

    # Station Master cannot view section controller analytics
    res_sec_kpi = client.get(
        "/api/v1/simulations/non-existent/analytics/section-controller",
        headers=headers,
    )
    assert res_sec_kpi.status_code == 403


def test_cross_station_analytics_isolation(client, db_session):
    from app.models import Simulation
    from app.services.seed import seed_default_simulation

    seed_default_simulation(db_session)
    sim = db_session.query(Simulation).first()
    assert sim is not None

    # Station Master for Nandpur
    login_ndl = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_NDL_001", "password": "Station@123"},
    ).json()
    headers_ndl = {"Authorization": f"Bearer {login_ndl['access_token']}"}

    # Accessing authorized station NDL succeeds
    res_ok = client.get(
        f"/api/v1/simulations/{sim.id}/analytics/station-master?station_id=NDL",
        headers=headers_ndl,
    )
    assert res_ok.status_code == 200
    assert res_ok.json()["station_id"] == "NDL"

    # Cross-station attempt: accessing unauthorized station MLG or VSN fails with 403
    res_forbidden = client.get(
        f"/api/v1/simulations/{sim.id}/analytics/station-master?station_id=MLG",
        headers=headers_ndl,
    )
    assert res_forbidden.status_code == 403
    assert "outside your authorized operational jurisdiction" in res_forbidden.json()["detail"]

    res_vsn = client.get(
        f"/api/v1/simulations/{sim.id}/analytics/station-master?station_id=VSN",
        headers=headers_ndl,
    )
    assert res_vsn.status_code == 403


def test_station_master_dashboard_jurisdiction_scoping(client, db_session):
    from app.models import Simulation
    from app.services.seed import seed_default_simulation

    seed_default_simulation(db_session)
    sim = db_session.query(Simulation).first()

    login_ndl = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_NDL_001", "password": "Station@123"},
    ).json()
    headers_ndl = {"Authorization": f"Bearer {login_ndl['access_token']}"}

    res = client.get(f"/api/v1/simulations/{sim.id}/dashboard", headers=headers_ndl)
    assert res.status_code == 200
    data = res.json()

    # Platforms must only be for NDL
    for platform in data["available_platforms"]:
        assert platform["station_id"] == "NDL"

    # Jurisdiction metadata present
    assert data["jurisdiction"]["authorized_stations"] == ["NDL"]
    assert data["jurisdiction"]["is_restricted_scope"] is True


def test_token_logout_revocation(client):
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "SC_NORTH_001", "password": "Section@123"},
    ).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works before logout
    me_before = client.get("/api/v1/auth/me", headers=headers)
    assert me_before.status_code == 200

    # Logout
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200
    assert logout_res.json()["status"] == "LOGGED_OUT"

    # After logout, token is rejected
    me_after = client.get("/api/v1/auth/me", headers=headers)
    assert me_after.status_code == 401
    assert "revoked" in me_after.json()["detail"].lower()


def test_password_change_flow(client):
    # Login with initial password
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_SRP_001", "password": "Station@123"},
    ).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}

    # Wrong old password rejected
    res_bad = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "WrongPassword@123", "new_password": "NewSecret@456"},
        headers=headers,
    )
    assert res_bad.status_code == 400

    # Correct old password succeeds
    res_ok = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "Station@123", "new_password": "NewSecret@456"},
        headers=headers,
    )
    assert res_ok.status_code == 200

    # Old password no longer works
    res_old = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_SRP_001", "password": "Station@123"},
    )
    assert res_old.status_code == 401

    # New password works
    res_new = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_SRP_001", "password": "NewSecret@456"},
    )
    assert res_new.status_code == 200

    # Reset back to Station@123 for test repeatability
    new_headers = {"Authorization": f"Bearer {res_new.json()['access_token']}"}
    client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "NewSecret@456", "new_password": "Station@123"},
        headers=new_headers,
    )


def test_admin_user_management(client):
    # Non-admin cannot list or create users
    sc_login = client.post(
        "/api/v1/auth/login",
        json={"username": "SC_CORRIDOR_001", "password": "Section@123"},
    ).json()
    sc_headers = {"Authorization": f"Bearer {sc_login['access_token']}"}
    assert client.get("/api/v1/auth/users", headers=sc_headers).status_code == 403

    # Admin login
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"username": "ADMIN_001", "password": "Admin@123"},
    ).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    # Admin lists users
    users_res = client.get("/api/v1/auth/users", headers=admin_headers)
    assert users_res.status_code == 200
    usernames = [u["username"] for u in users_res.json()]
    assert "SM_NDL_001" in usernames
    assert "SC_NORTH_001" in usernames

    # Admin creates new user
    new_sm_payload = {
        "username": "SM_TEST_NEW",
        "password": "SecurePassword@123",
        "role": "STATION_MASTER",
        "display_name": "Station Master — Test Station",
        "station_id": "NDL",
        "assigned_stations": ["NDL"],
        "control_area": "NORTHERN_CONTROL_AREA",
    }
    create_res = client.post("/api/v1/auth/users", json=new_sm_payload, headers=admin_headers)
    assert create_res.status_code == 200
    created = create_res.json()
    assert created["username"] == "SM_TEST_NEW"

    # Admin deactivates user
    deactivate_res = client.patch(
        f"/api/v1/auth/users/{created['id']}",
        json={"active": False},
        headers=admin_headers,
    )
    assert deactivate_res.status_code == 200
    assert deactivate_res.json()["active"] is False

    # Deactivated user cannot login
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_TEST_NEW", "password": "SecurePassword@123"},
    )
    assert bad_login.status_code == 401


def test_recommendation_and_decision_jurisdiction(client, db_session):
    from app.models import Recommendation, Simulation
    from app.services.seed import seed_default_simulation

    seed_default_simulation(db_session)
    sim = db_session.query(Simulation).first()

    # Create recommendation affecting Vasanthpur (VSN) only
    rec_vsn = Recommendation(
        simulation_id=sim.id,
        state_version=sim.state_version,
        status="PENDING",
        evidence_status="COMPLETE",
        disagreement=False,
        payload={
            "affected_stations": ["VSN"],
            "explanation": {"headline": "Hold at VSN loop for express crossing"},
            "recommended": {"candidate_id": "c1", "label": "Hold 12626 at VSN"},
            "candidates": [{"id": "c1", "action": {"type": "HOLD", "train_id": "12626", "station_id": "VSN", "duration_min": 8}}],
        },
        model_version="ppo-v1",
        optimizer_version="cpsat-v1",
        created_by="system",
    )
    db_session.add(rec_vsn)
    db_session.commit()
    db_session.refresh(rec_vsn)

    # Station Master for Nandpur (NDL) tries to view recommendation affecting VSN -> 403 Forbidden
    login_ndl = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_NDL_001", "password": "Station@123"},
    ).json()
    headers_ndl = {"Authorization": f"Bearer {login_ndl['access_token']}"}

    res_ndl = client.get(f"/api/v1/recommendations/{rec_vsn.id}", headers=headers_ndl)
    assert res_ndl.status_code == 403
    assert "outside your station scope" in res_ndl.json()["detail"]

    # Station Master for Nandpur tries to DECIDE recommendation affecting VSN -> 403 Forbidden
    res_ndl_decide = client.post(
        f"/api/v1/recommendations/{rec_vsn.id}/decision",
        json={"action": "APPROVE", "rationale": "Approve crossing by SM NDL"},
        headers=headers_ndl,
    )
    assert res_ndl_decide.status_code == 403

    # Section Controller for North (NDL-MLG) tries to view recommendation affecting VSN (South) -> 403 Forbidden
    login_sc_north = client.post(
        "/api/v1/auth/login",
        json={"username": "SC_NORTH_001", "password": "Section@123"},
    ).json()
    headers_sc_north = {"Authorization": f"Bearer {login_sc_north['access_token']}"}

    res_sc_north = client.get(f"/api/v1/recommendations/{rec_vsn.id}", headers=headers_sc_north)
    assert res_sc_north.status_code == 403
    assert "outside your assigned control territory" in res_sc_north.json()["detail"]

    # Section Controller for South or Corridor CAN view
    login_sc_south = client.post(
        "/api/v1/auth/login",
        json={"username": "SC_SOUTH_001", "password": "Section@123"},
    ).json()
    headers_sc_south = {"Authorization": f"Bearer {login_sc_south['access_token']}"}

    res_sc_south = client.get(f"/api/v1/recommendations/{rec_vsn.id}", headers=headers_sc_south)
    assert res_sc_south.status_code == 200


def test_token_revocation_survives_restart_and_cleared_memory_cache(client):
    from app.security import _REVOKED_TOKENS, _REVOKED_HASHES

    # Login and acquire token
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_KRN_001", "password": "Station@123"},
    ).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works initially
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200

    # Logout to revoke token
    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 200

    # Simulate server restart or request landing on another worker by wiping in-memory sets
    _REVOKED_TOKENS.clear()
    _REVOKED_HASHES.clear()

    # Attempt request with revoked token: must be rejected via database check
    me_after = client.get("/api/v1/auth/me", headers=headers)
    assert me_after.status_code == 401
    assert "revoked" in me_after.json()["detail"].lower()


def test_deactivated_account_rejects_active_token(client, db_session):
    from app.models import User

    # Login and acquire token
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_VSN_001", "password": "Station@123"},
    ).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Verify token works
    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    # Deactivate user in database directly (simulating admin action or account disablement)
    user = db_session.query(User).filter(User.username == "SM_VSN_001").first()
    user.active = False
    db_session.commit()

    # Verify request with pre-existing token is immediately rejected
    res_deactivated = client.get("/api/v1/auth/me", headers=headers)
    assert res_deactivated.status_code == 401
    assert "inactive" in res_deactivated.json()["detail"].lower()

    # Restore user active status for other tests
    user.active = True
    db_session.commit()


def test_password_change_invalidates_prior_tokens(client, db_session):
    import time
    from app.models import User

    # Login device 1
    login_1 = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_MLG_001", "password": "Station@123"},
    ).json()
    token_1 = login_1["access_token"]
    headers_1 = {"Authorization": f"Bearer {token_1}"}

    # Verify token 1 works
    assert client.get("/api/v1/auth/me", headers=headers_1).status_code == 200

    # Ensure timestamp advances
    time.sleep(1)

    # Change password
    change_res = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "Station@123", "new_password": "UpdatedPassword@789"},
        headers=headers_1,
    )
    assert change_res.status_code == 200

    # Device 1 token must now be rejected
    res_stale = client.get("/api/v1/auth/me", headers=headers_1)
    assert res_stale.status_code == 401

    # Reset password back to default
    user = db_session.query(User).filter(User.username == "SM_MLG_001").first()
    from app.security import hash_password
    user.password_hash = hash_password("Station@123")
    user.password_changed_at = None
    db_session.commit()


def test_malgaon_boundary_junction_access_separation(client, db_session):
    from app.models import Recommendation, Simulation
    from app.services.seed import seed_default_simulation

    seed_default_simulation(db_session)
    sim = db_session.query(Simulation).first()

    # Create recommendation on Section S1 (NDL-KRN, strictly North)
    rec_north = Recommendation(
        simulation_id=sim.id,
        state_version=sim.state_version,
        status="PENDING",
        evidence_status="COMPLETE",
        disagreement=False,
        payload={
            "affected_stations": ["NDL"],
            "affected_sections": ["S1"],
            "explanation": {"headline": "Speed restriction on S1 single line"},
            "recommended": {"candidate_id": "c_n1", "label": "Hold at NDL"},
            "candidates": [{"id": "c_n1", "action": {"type": "HOLD", "train_id": "12625", "station_id": "NDL", "duration_min": 5}}],
        },
        model_version="ppo-v1",
        optimizer_version="cpsat-v1",
        created_by="system",
    )
    db_session.add(rec_north)
    db_session.commit()
    db_session.refresh(rec_north)

    # Southern Section Controller (MLG-VSN, S3-S4) CANNOT access Northern recommendation
    login_south = client.post(
        "/api/v1/auth/login",
        json={"username": "SC_SOUTH_001", "password": "Section@123"},
    ).json()
    headers_south = {"Authorization": f"Bearer {login_south['access_token']}"}

    res_south = client.get(f"/api/v1/recommendations/{rec_north.id}", headers=headers_south)
    assert res_south.status_code == 403
    assert "outside your assigned control territory" in res_south.json()["detail"]

    # Station Master Malgaon (SM_MLG_001) CANNOT access S1 Northern recommendation
    login_mlg = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_MLG_001", "password": "Station@123"},
    ).json()
    headers_mlg = {"Authorization": f"Bearer {login_mlg['access_token']}"}

    res_mlg = client.get(f"/api/v1/recommendations/{rec_north.id}", headers=headers_mlg)
    assert res_mlg.status_code == 403
    assert "outside your station scope" in res_mlg.json()["detail"]

    # Northern Section Controller (SC_NORTH_001) CAN access S1 Northern recommendation
    login_north = client.post(
        "/api/v1/auth/login",
        json={"username": "SC_NORTH_001", "password": "Section@123"},
    ).json()
    headers_north = {"Authorization": f"Bearer {login_north['access_token']}"}

    res_north = client.get(f"/api/v1/recommendations/{rec_north.id}", headers=headers_north)
    assert res_north.status_code == 200


def test_password_change_same_second_token_version_invalidation(client, db_session):
    """Sub-second password changes must immediately invalidate other active tokens via token_version."""
    from app.models import User
    from app.security import hash_password

    # Login device 1
    login_dev1 = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_NDL_001", "password": "Station@123"},
    ).json()
    token_dev1 = login_dev1["access_token"]
    headers_dev1 = {"Authorization": f"Bearer {token_dev1}"}

    # Login device 2 (in the exact same second)
    login_dev2 = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_NDL_001", "password": "Station@123"},
    ).json()
    token_dev2 = login_dev2["access_token"]
    headers_dev2 = {"Authorization": f"Bearer {token_dev2}"}

    # Both tokens work
    assert client.get("/api/v1/auth/me", headers=headers_dev1).status_code == 200
    assert client.get("/api/v1/auth/me", headers=headers_dev2).status_code == 200

    # Device 1 changes password IMMEDIATELY (no sleep, same second)
    change_res = client.post(
        "/api/v1/auth/change-password",
        json={"old_password": "Station@123", "new_password": "ImmediateNewPassword@123"},
        headers=headers_dev1,
    )
    assert change_res.status_code == 200

    # Device 1 token was directly revoked on password change
    res_dev1 = client.get("/api/v1/auth/me", headers=headers_dev1)
    assert res_dev1.status_code == 401
    assert "revoked" in res_dev1.json()["detail"].lower()

    # Device 2 token was NOT passed to change-password, but token_version caught it immediately!
    res_dev2 = client.get("/api/v1/auth/me", headers=headers_dev2)
    assert res_dev2.status_code == 401
    assert "invalidated by password change" in res_dev2.json()["detail"].lower()

    # Restore password
    user = db_session.query(User).filter(User.username == "SM_NDL_001").first()
    user.password_hash = hash_password("Station@123")
    user.password_changed_at = None
    user.token_version = 1
    db_session.commit()


def test_logout_database_failure_raises_500(client, monkeypatch):
    """If database write fails during logout, HTTP 500 must be raised rather than reporting success."""
    login = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_KRN_001", "password": "Station@123"},
    ).json()
    token = login["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Monkeypatch revoke_token to raise RuntimeError simulating a DB failure
    def mock_revoke_token(*args, **kwargs):
        raise RuntimeError("Disk write failed: table locked")

    monkeypatch.setattr("app.routers.auth.revoke_token", mock_revoke_token)

    logout_res = client.post("/api/v1/auth/logout", headers=headers)
    assert logout_res.status_code == 500
    assert "database write error" in logout_res.json()["detail"].lower()


def test_cleanup_expired_revocations(client, db_session):
    """Expired revocation records are purged, while active revocations are preserved."""
    from datetime import datetime, timedelta, timezone
    from app.models import RevokedToken, User

    now = datetime.now(timezone.utc)
    # Expired token record
    expired = RevokedToken(
        token_hash="hash_expired_12345",
        username="SM_NDL_001",
        expires_at=now - timedelta(hours=2),
    )
    # Valid unexpired token record
    valid = RevokedToken(
        token_hash="hash_valid_67890",
        username="SM_KRN_001",
        expires_at=now + timedelta(hours=5),
    )
    db_session.add(expired)
    db_session.add(valid)
    db_session.commit()

    # Login as admin to call cleanup
    admin_login = client.post(
        "/api/v1/auth/login",
        json={"username": "ADMIN_001", "password": "Admin@123"},
    ).json()
    admin_headers = {"Authorization": f"Bearer {admin_login['access_token']}"}

    cleanup_res = client.post("/api/v1/auth/cleanup-revocations", headers=admin_headers)
    assert cleanup_res.status_code == 200
    assert cleanup_res.json()["cleaned_count"] >= 1

    # Verify expired was deleted and valid remains
    rem_expired = db_session.query(RevokedToken).filter(RevokedToken.token_hash == "hash_expired_12345").first()
    assert rem_expired is None
    rem_valid = db_session.query(RevokedToken).filter(RevokedToken.token_hash == "hash_valid_67890").first()
    assert rem_valid is not None

    # Cleanup test row
    db_session.delete(rem_valid)
    db_session.commit()


def test_production_mode_rejects_demo_credentials(client, monkeypatch):
    """In production mode, demo account logins and creations are rejected."""
    from app.config import settings

    monkeypatch.setattr(type(settings), "is_production", property(lambda self: True))

    # Demo account login attempt in production
    res_login = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_NDL_001", "password": "Station@123"},
    )
    assert res_login.status_code == 401
    assert "demo accounts are disabled in production" in res_login.json()["detail"].lower()


def test_mlg_boundary_junction_thorough_access_matrix(client, db_session):
    """Exhaustive test of Malgaon boundary junction and cross-section authorizations."""
    from app.models import Recommendation, Simulation
    from app.services.seed import seed_default_simulation

    seed_default_simulation(db_session)
    sim = db_session.query(Simulation).first()

    # Create recommendation strictly on Section S4 (VSN)
    rec_s4 = Recommendation(
        simulation_id=sim.id,
        state_version=sim.state_version,
        status="PENDING",
        evidence_status="COMPLETE",
        disagreement=False,
        payload={
            "affected_stations": ["VSN"],
            "affected_sections": ["S4"],
            "recommended": {"candidate_id": "c_s4", "label": "Hold at VSN"},
            "candidates": [{"id": "c_s4", "action": {"type": "HOLD", "train_id": "12626", "station_id": "VSN", "duration_min": 6}}],
        },
        model_version="ppo-v1",
        optimizer_version="cpsat-v1",
        created_by="system",
    )
    # Create recommendation strictly on Section S2 (KRN-MLG boundary)
    rec_s2 = Recommendation(
        simulation_id=sim.id,
        state_version=sim.state_version,
        status="PENDING",
        evidence_status="COMPLETE",
        disagreement=False,
        payload={
            "affected_stations": ["MLG"],
            "affected_sections": ["S2"],
            "recommended": {"candidate_id": "c_s2", "label": "Receive 12625 on Line 2 at MLG"},
            "candidates": [{"id": "c_s2", "action": {"type": "HOLD", "train_id": "12625", "station_id": "MLG", "duration_min": 4}}],
        },
        model_version="ppo-v1",
        optimizer_version="cpsat-v1",
        created_by="system",
    )
    db_session.add(rec_s4)
    db_session.add(rec_s2)
    db_session.commit()
    db_session.refresh(rec_s4)
    db_session.refresh(rec_s2)

    # 1. Northern SC logins
    sc_north_res = client.post(
        "/api/v1/auth/login",
        json={"username": "SC_NORTH_001", "password": "Section@123"},
    ).json()
    headers_sc_north = {"Authorization": f"Bearer {sc_north_res['access_token']}"}

    # 2. Southern SC logins
    sc_south_res = client.post(
        "/api/v1/auth/login",
        json={"username": "SC_SOUTH_001", "password": "Section@123"},
    ).json()
    headers_sc_south = {"Authorization": f"Bearer {sc_south_res['access_token']}"}

    # 3. Chief Controller (Corridor) logins
    sc_corridor_res = client.post(
        "/api/v1/auth/login",
        json={"username": "SC_CORRIDOR_001", "password": "Section@123"},
    ).json()
    headers_corridor = {"Authorization": f"Bearer {sc_corridor_res['access_token']}"}

    # 4. SM Malgaon logins
    sm_mlg_res = client.post(
        "/api/v1/auth/login",
        json={"username": "SM_MLG_001", "password": "Station@123"},
    ).json()
    headers_sm_mlg = {"Authorization": f"Bearer {sm_mlg_res['access_token']}"}

    # Northern SC:
    # - CAN view and decide rec_s2 (MLG is part of assigned_stations for North)
    assert client.get(f"/api/v1/recommendations/{rec_s2.id}", headers=headers_sc_north).status_code == 200
    # - CANNOT view rec_s4 (VSN is South only)
    assert client.get(f"/api/v1/recommendations/{rec_s4.id}", headers=headers_sc_north).status_code == 403
    # - CANNOT decide rec_s4
    decide_s4 = client.post(
        f"/api/v1/recommendations/{rec_s4.id}/decision",
        json={"action": "APPROVE", "rationale": "North SC trying to decide South rec"},
        headers=headers_sc_north,
    )
    assert decide_s4.status_code == 403

    # Southern SC:
    # - CAN view rec_s4 (VSN)
    assert client.get(f"/api/v1/recommendations/{rec_s4.id}", headers=headers_sc_south).status_code == 200
    # - CAN view rec_s2 (MLG is also in Southern assigned_stations)
    assert client.get(f"/api/v1/recommendations/{rec_s2.id}", headers=headers_sc_south).status_code == 200

    # Chief Controller:
    # - CAN view rec_s2 AND rec_s4
    assert client.get(f"/api/v1/recommendations/{rec_s2.id}", headers=headers_corridor).status_code == 200
    assert client.get(f"/api/v1/recommendations/{rec_s4.id}", headers=headers_corridor).status_code == 200

    # SM Malgaon:
    # - CAN view rec_s2 (affects MLG)
    assert client.get(f"/api/v1/recommendations/{rec_s2.id}", headers=headers_sm_mlg).status_code == 200
    # - CANNOT view rec_s4 (VSN)
    assert client.get(f"/api/v1/recommendations/{rec_s4.id}", headers=headers_sm_mlg).status_code == 403


