"""Simulation, dashboard and disruption API."""
from __future__ import annotations


def test_list_simulations(client, section_headers):
    response = client.get("/api/v1/simulations", headers=section_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "SYNTHETIC"
    assert body["simulations"]


def test_create_simulation(client, section_headers):
    response = client.post(
        "/api/v1/simulations",
        headers=section_headers,
        json={"scenario_key": "evening_peak", "seed": 42},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scenario_key"] == "evening_peak"
    assert body["seed"] == 42
    assert body["status"] == "RUNNING"
    assert body["data_label"].startswith("SYNTHETIC")
    assert body["network"]["sections"]


def test_create_simulation_rejects_unknown_scenario(client, section_headers):
    response = client.post(
        "/api/v1/simulations",
        headers=section_headers,
        json={"scenario_key": "unknown_scenario"},
    )
    assert response.status_code == 404


def test_dashboard_exposes_required_operational_views(client, section_headers, simulation):
    response = client.get(
        f"/api/v1/simulations/{simulation['id']}/dashboard", headers=section_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["simulation"]["label"] == "SYNTHETIC"
    assert "metrics" in body
    assert "active_trains" in body
    assert "conflicts" in body
    assert "block_occupancy" not in body
    assert "occupied_blocks" in body
    assert "available_platforms" in body
    assert body["role_scope"]["role"] == "SECTION_MASTER"
    assert body["model_status"]["ppo"]["trained"] in {True, False}
    assert body["model_status"]["cpsat"]["status"] == "DETERMINISTIC_OPTIMIZER"


def test_trains_and_network_endpoints(client, section_headers, simulation):
    trains = client.get(
        f"/api/v1/simulations/{simulation['id']}/trains", headers=section_headers
    )
    assert trains.status_code == 200
    assert trains.json()["trains"]
    network = client.get(
        f"/api/v1/simulations/{simulation['id']}/network", headers=section_headers
    )
    assert network.status_code == 200
    assert network.json()["network"]["stations"]
    assert network.json()["block_occupancy"]


def test_conflict_endpoint(client, section_headers, simulation):
    response = client.get(
        f"/api/v1/simulations/{simulation['id']}/conflicts", headers=section_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "SYNTHETIC"
    assert isinstance(body["conflicts"], list)


def test_advance_updates_time_and_version(client, section_headers, simulation):
    before = simulation["state_version"]
    response = client.post(
        f"/api/v1/simulations/{simulation['id']}/advance",
        headers=section_headers,
        json={"minutes": 15},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["sim_time_min"] == simulation["sim_time_min"] + 15
    assert body["state_version"] > before


def test_advance_validation(client, section_headers, simulation):
    response = client.post(
        f"/api/v1/simulations/{simulation['id']}/advance",
        headers=section_headers,
        json={"minutes": 0},
    )
    assert response.status_code == 422


def test_pause_blocks_advance(client, section_headers, simulation):
    paused = client.post(
        f"/api/v1/simulations/{simulation['id']}/pause",
        headers=section_headers,
        json={"paused": True},
    )
    assert paused.status_code == 200
    assert paused.json()["status"] == "PAUSED"
    blocked = client.post(
        f"/api/v1/simulations/{simulation['id']}/advance",
        headers=section_headers,
        json={"minutes": 5},
    )
    assert blocked.status_code == 409
    resumed = client.post(
        f"/api/v1/simulations/{simulation['id']}/pause",
        headers=section_headers,
        json={"paused": False},
    )
    assert resumed.status_code == 200
    assert resumed.json()["status"] == "RUNNING"


def test_reset_is_monotonic(client, section_headers, simulation):
    before = simulation["state_version"]
    response = client.post(
        f"/api/v1/simulations/{simulation['id']}/reset", headers=section_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["state_version"] > before
    assert body["sim_time_min"] == simulation["sim_time_min"]


def test_disruption_block_closure(client, section_headers, simulation):
    response = client.post(
        f"/api/v1/simulations/{simulation['id']}/disruptions",
        headers=section_headers,
        json={
            "disruption_type": "BLOCK_CLOSURE",
            "payload": {
                "block_id": "B3",
                "start_min": simulation["sim_time_min"] + 20,
                "end_min": simulation["sim_time_min"] + 50,
                "reason": "Test possession",
            },
        },
    )
    assert response.status_code == 200
    closures = response.json()["closures"]
    assert any(closure["block_id"] == "B3" for closure in closures)


def test_disruption_validation(client, section_headers, simulation):
    response = client.post(
        f"/api/v1/simulations/{simulation['id']}/disruptions",
        headers=section_headers,
        json={"disruption_type": "NONSENSE", "payload": {}},
    )
    assert response.status_code == 400
    response = client.post(
        f"/api/v1/simulations/{simulation['id']}/disruptions",
        headers=section_headers,
        json={"disruption_type": "BLOCK_CLOSURE", "payload": {"block_id": "ZZZ"}},
    )
    assert response.status_code == 400


def test_what_if_does_not_mutate_live_simulation(client, section_headers, simulation):
    before_version = client.get(
        f"/api/v1/simulations/{simulation['id']}", headers=section_headers
    ).json()["state_version"]
    response = client.post(
        f"/api/v1/simulations/{simulation['id']}/what-if",
        headers=section_headers,
        json={"action": {"type": "DO_NOTHING"}, "minutes": 30},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "COMPLETED"
    assert body["applied_to_live_simulation"] is False
    assert "deltas" in body
    after_version = client.get(
        f"/api/v1/simulations/{simulation['id']}", headers=section_headers
    ).json()["state_version"]
    assert after_version == before_version


def test_what_if_rejects_invalid_action(client, section_headers, simulation):
    response = client.post(
        f"/api/v1/simulations/{simulation['id']}/what-if",
        headers=section_headers,
        json={"action": {"type": "MAGIC"}, "minutes": 30},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "REJECTED"


def test_analytics_endpoint(client, section_headers, simulation):
    response = client.get(
        f"/api/v1/simulations/{simulation['id']}/analytics", headers=section_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["label"] == "SYNTHETIC"
    assert body["kpis"]["trains_total"] > 0
    assert body["kpis"]["trains_active"] > 0
    assert body["recommendation_stats"]["total"] >= 0
    assert body["section_utilization"]
    assert body["platform_utilization"]
