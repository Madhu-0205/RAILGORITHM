import requests
import json
import sys
import traceback

BASE_URL = "http://127.0.0.1:8080"

def get_sim_id(token):
    resp = requests.get(f"{BASE_URL}/api/v1/simulations", headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, f"Failed to get simulations: {resp.text}"
    sims = resp.json()["simulations"]
    assert len(sims) > 0, "No simulation found"
    return sims[0]["id"]

def run_tests():
    print("=" * 70)
    print("RAILGORITHM STRICT ROLE PORTAL & WORKSPACE VERIFICATION SUITE")
    print("=" * 70)
    
    results = {}
    
    # -------------------------------------------------------------
    # JOURNEY A: Station Master Portal & Jurisdiction Enforcement
    # -------------------------------------------------------------
    print("\n[JOURNEY A] Testing Station Master Authentication & Boundary Enforcement...")
    
    # A1: SM Authenticates via Station Master Portal
    sm_resp = requests.post(f"{BASE_URL}/api/v1/auth/login/station-master", json={
        "username": "SM_NDL_001",
        "password": "Station@123",
        "portal": "STATION_MASTER"
    })
    assert sm_resp.status_code == 200, f"Expected 200, got {sm_resp.status_code}: {sm_resp.text}"
    sm_data = sm_resp.json()
    sm_token = sm_data["access_token"]
    sm_headers = {"Authorization": f"Bearer {sm_token}"}
    print("  ✓ SM_NDL_001 successfully authenticated via /auth/login/station-master")
    
    sim_id = get_sim_id(sm_token)
    print(f"  ✓ Active simulation ID: {sim_id}")
    
    # A2: SM accesses own station overview (NDL)
    ndl_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/station-master/overview?station_id=NDL", headers=sm_headers)
    assert ndl_resp.status_code == 200, f"Expected 200 for NDL overview, got {ndl_resp.status_code}: {ndl_resp.text}"
    ndl_data = ndl_resp.json()
    assert ndl_data["station_id"] == "NDL"
    assert "summary_counts" in ndl_data
    assert "adherence" in ndl_data
    print(f"  ✓ SM can access assigned station overview: {ndl_data['station_name']} ({ndl_data['station_id']})")
    print(f"    - Operational Status: {ndl_data['operational_status']}")
    print(f"    - Arriving next 30m: {ndl_data['summary_counts']['arriving_next_30m']}")
    print(f"    - Departing next 30m: {ndl_data['summary_counts']['departing_next_30m']}")

    # A2b: SM accesses station yard layout
    layout_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/station-master/layout?station_id=NDL", headers=sm_headers)
    assert layout_resp.status_code == 200
    layout_data = layout_resp.json()
    print(f"  ✓ SM station yard layout contains {len(layout_data['tracks'])} tracks / loop lines")

    # A2c: SM accesses movement board
    mb_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/station-master/movement-board?station_id=NDL", headers=sm_headers)
    assert mb_resp.status_code == 200
    mb_data = mb_resp.json()
    total_trains = len(mb_data["arriving"]) + len(mb_data["departing"]) + len(mb_data["through"])
    print(f"  ✓ SM train movement board contains {total_trains} active trains categorized into arriving, departing, and through")
    
    # A3: SM cannot access another station overview (e.g. KRN)
    krn_sm_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/station-master/overview?station_id=KRN", headers=sm_headers)
    assert krn_sm_resp.status_code == 403, f"Expected 403 for unauthorized station KRN, got {krn_sm_resp.status_code}"
    print("  ✓ SM_NDL_001 strictly blocked with 403 when requesting other station (KRN) private overview")
    
    # A4: SM cannot access Section Controller corridor overview
    sc_ov_sm_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/section-controller/overview", headers=sm_headers)
    assert sc_ov_sm_resp.status_code == 403, f"Expected 403 for SC overview, got {sc_ov_sm_resp.status_code}"
    print("  ✓ SM_NDL_001 strictly blocked with 403 when requesting Section Controller corridor overview")
    
    # A5: SM cannot access Section Controller station summaries endpoint
    sc_sm_summary_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/section-controller/stations/NDL/summary", headers=sm_headers)
    assert sc_sm_summary_resp.status_code == 403, f"Expected 403 for SC station summary, got {sc_sm_summary_resp.status_code}"
    print("  ✓ SM_NDL_001 strictly blocked with 403 from Section Controller station summary endpoint")
    
    results["JOURNEY_A"] = "PASSED"

    # -------------------------------------------------------------
    # JOURNEY B: Section Controller Portal & Territory Scope Enforcement
    # -------------------------------------------------------------
    print("\n[JOURNEY B] Testing Section Controller Authentication & Territory Scope...")
    
    # B1: SC Authenticates via Section Controller Portal
    sc_resp = requests.post(f"{BASE_URL}/api/v1/auth/login/section-controller", json={
        "username": "SC_CORRIDOR_001",
        "password": "Section@123",
        "portal": "SECTION_CONTROLLER"
    })
    assert sc_resp.status_code == 200, f"Expected 200, got {sc_resp.status_code}: {sc_resp.text}"
    sc_data = sc_resp.json()
    sc_token = sc_data["access_token"]
    sc_headers = {"Authorization": f"Bearer {sc_token}"}
    print("  ✓ SC_CORRIDOR_001 successfully authenticated via /auth/login/section-controller")
    
    # B2: SC accesses whole-corridor territory overview
    sc_overview_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/section-controller/overview", headers=sc_headers)
    assert sc_overview_resp.status_code == 200, f"Expected 200, got {sc_overview_resp.status_code}: {sc_overview_resp.text}"
    sc_ov_data = sc_overview_resp.json()
    assert "kpis" in sc_ov_data
    assert "monitored_stations" in sc_ov_data
    assert len(sc_ov_data["monitored_stations"]) == 5
    print(f"  ✓ SC corridor overview contains {len(sc_ov_data['monitored_stations'])} stations")
    print(f"    - Punctuality KPI: {sc_ov_data['kpis']['punctuality_pct']}%")
    print(f"    - Active Trains: {sc_ov_data['kpis']['trains_active']}")

    # B2b: SC accesses corridor topology strip
    topo_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/section-controller/topology", headers=sc_headers)
    assert topo_resp.status_code == 200
    topo_data = topo_resp.json()
    assert len(topo_data["stations"]) == 5
    assert len(topo_data["sections"]) == 4
    print(f"  ✓ SC corridor topology strip contains {len(topo_data['stations'])} stations and {len(topo_data['sections'])} sections (corridor length: {topo_data['corridor_length_km']} km)")
    
    # B3: SC accesses authorized station summary
    sc_summary_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/section-controller/stations/NDL/summary", headers=sc_headers)
    assert sc_summary_resp.status_code == 200, f"Expected 200, got {sc_summary_resp.status_code}"
    print("  ✓ SC can view operational station summary for NDL in jurisdiction")
    
    # B4: SC strictly blocked from Station Master private workspace
    sc_into_sm_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/station-master/overview?station_id=NDL", headers=sc_headers)
    assert sc_into_sm_resp.status_code == 403, f"Expected 403 for SC calling SM overview, got {sc_into_sm_resp.status_code}"
    print("  ✓ SC strictly blocked with 403 from private /station-master/overview")
    
    # B5: Scoped controller test (SC_NORTH_001 cannot view southern station VSN)
    sc_north_resp = requests.post(f"{BASE_URL}/api/v1/auth/login/section-controller", json={
        "username": "SC_NORTH_001",
        "password": "Section@123",
        "portal": "SECTION_CONTROLLER"
    })
    sc_north_token = sc_north_resp.json()["access_token"]
    sc_north_headers = {"Authorization": f"Bearer {sc_north_token}"}
    sc_vsn_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/section-controller/stations/VSN/summary", headers=sc_north_headers)
    assert sc_vsn_resp.status_code == 403, f"Expected 403 for out-of-jurisdiction station, got {sc_vsn_resp.status_code}"
    print("  ✓ Sub-area controller SC_NORTH_001 strictly blocked with 403 from southern station VSN summary")
    
    results["JOURNEY_B"] = "PASSED"

    # -------------------------------------------------------------
    # JOURNEY C: Cross-Portal Server-Side Login Rejection
    # -------------------------------------------------------------
    print("\n[JOURNEY C] Testing Cross-Portal Login Rejection (Server-Side 403)...")
    
    # C1: Section Controller attempting to log in via Station Master Portal
    sc_on_sm = requests.post(f"{BASE_URL}/api/v1/auth/login/station-master", json={
        "username": "SC_CORRIDOR_001",
        "password": "Section@123"
    })
    assert sc_on_sm.status_code == 403, f"Expected 403, got {sc_on_sm.status_code}: {sc_on_sm.text}"
    sc_on_sm_err = sc_on_sm.json()["detail"]
    assert "Portal Access Denied" in sc_on_sm_err
    assert "Section Controller Portal" in sc_on_sm_err
    print(f"  ✓ SC_CORRIDOR_001 rejected on Station Master Portal: 403 Forbidden")
    print(f"    Message: \"{sc_on_sm_err}\"")
    
    # C2: Station Master attempting to log in via Section Controller Portal
    sm_on_sc = requests.post(f"{BASE_URL}/api/v1/auth/login/section-controller", json={
        "username": "SM_NDL_001",
        "password": "Station@123"
    })
    assert sm_on_sc.status_code == 403, f"Expected 403, got {sm_on_sc.status_code}: {sm_on_sc.text}"
    sm_on_sc_err = sm_on_sc.json()["detail"]
    assert "Portal Access Denied" in sm_on_sc_err
    assert "Station Master Portal" in sm_on_sc_err
    print(f"  ✓ SM_NDL_001 rejected on Section Controller Portal: 403 Forbidden")
    print(f"    Message: \"{sm_on_sc_err}\"")
    
    # C3: Explicit payload portal parameter enforcement on standard /auth/login
    sm_cross_payload = requests.post(f"{BASE_URL}/api/v1/auth/login", json={
        "username": "SM_NDL_001",
        "password": "Station@123",
        "portal": "SECTION_CONTROLLER"
    })
    assert sm_cross_payload.status_code == 403
    print("  ✓ Server validates portal parameter on standard /auth/login endpoint (403 returned)")
    
    results["JOURNEY_C"] = "PASSED"

    # -------------------------------------------------------------
    # JOURNEY D: Session Isolation & Logout Token Invalidation
    # -------------------------------------------------------------
    print("\n[JOURNEY D] Testing Session Isolation & Revocation Invalidation...")
    
    # D1: Log out SM session
    logout_resp = requests.post(f"{BASE_URL}/api/v1/auth/logout", headers=sm_headers)
    assert logout_resp.status_code == 200, f"Expected 200, got {logout_resp.status_code}"
    print("  ✓ SM session successfully logged out via /auth/logout")
    
    # D2: Revoked token submitted to protected endpoint
    revoked_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/station-master/overview?station_id=NDL", headers=sm_headers)
    assert revoked_resp.status_code == 401, f"Expected 401 for revoked token, got {revoked_resp.status_code}"
    print("  ✓ Revoked SM token immediately rejected with 401 Unauthorized")
    
    # D3: Unauthenticated request to protected endpoint
    no_auth_resp = requests.get(f"{BASE_URL}/api/v1/simulations/{sim_id}/section-controller/overview")
    assert no_auth_resp.status_code == 401, f"Expected 401 for unauthenticated request, got {no_auth_resp.status_code}"
    print("  ✓ Unauthenticated access to /section-controller/overview rejected with 401 Unauthorized")
    
    results["JOURNEY_D"] = "PASSED"

    print("\n" + "=" * 70)
    print("ALL 4 VERIFICATION JOURNEYS PASSED WITH 100% SUCCESS!")
    print("=" * 70)
    return results

if __name__ == "__main__":
    try:
        run_tests()
    except Exception as e:
        print(f"VERIFICATION FAILURE: {e}")
        traceback.print_exc()
        sys.exit(1)
