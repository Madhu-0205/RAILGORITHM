"""Server-enforced role-based access control and station scope."""
from __future__ import annotations

import uuid

from app.models import Recommendation, Simulation


def test_station_master_cannot_create_simulation(client, station_headers):
    response = client.post(
        "/api/v1/simulations",
        headers=station_headers,
        json={"scenario_key": "normal_traffic"},
    )
    assert response.status_code == 403


def test_station_master_cannot_advance_or_disrupt(client, station_headers, simulation):
    advance = client.post(
        f"/api/v1/simulations/{simulation['id']}/advance",
        headers=station_headers,
        json={"minutes": 5},
    )
    assert advance.status_code == 403
    disruption = client.post(
        f"/api/v1/simulations/{simulation['id']}/disruptions",
        headers=station_headers,
        json={"disruption_type": "TRAIN_DELAY", "payload": {"train_id": "12625", "delay_min": 5}},
    )
    assert disruption.status_code == 403


def test_station_master_cannot_read_audit_trail(client, station_headers):
    assert client.get("/api/v1/audit", headers=station_headers).status_code == 403
    assert client.get("/api/v1/audit/verify", headers=station_headers).status_code == 403


def test_anonymous_access_is_rejected(client, simulation):
    for path in (
        f"/api/v1/simulations/{simulation['id']}/dashboard",
        f"/api/v1/simulations/{simulation['id']}/trains",
        f"/api/v1/simulations/{simulation['id']}/analytics",
        "/api/v1/scenarios",
        "/api/v1/models",
    ):
        assert client.get(path).status_code == 401


def test_station_master_can_read_dashboard(client, station_headers, simulation):
    response = client.get(
        f"/api/v1/simulations/{simulation['id']}/dashboard", headers=station_headers
    )
    assert response.status_code == 200
    assert response.json()["role_scope"]["station_id"] == "MLG"


def test_station_master_cannot_decide_out_of_scope_recommendation(
    client, station_headers, simulation, db_session
):
    record = Recommendation(
        id=str(uuid.uuid4()),
        simulation_id=simulation["id"],
        state_version=simulation["state_version"],
        status="PENDING",
        evidence_status="VALIDATED_WITH_ASSUMPTIONS",
        disagreement=False,
        payload={
            "recommended": {"action": {"type": "DO_NOTHING"}},
            "affected_stations": ["NDL"],
            "conflicts": [],
            "alternatives": [],
            "explanation": {},
        },
        model_version="ppo-unavailable",
        optimizer_version="cpsat-1.0.0",
        created_by="section.master",
    )
    db_session.add(record)
    db_session.commit()

    response = client.post(
        f"/api/v1/recommendations/{record.id}/decision",
        headers=station_headers,
        json={
            "action": "REJECT",
            "rationale": "Out of scope test rejection",
            "confirm_apply": False,
        },
    )
    assert response.status_code == 403
    assert "scope" in response.json()["detail"].lower()


def test_station_master_cannot_read_out_of_scope_recommendation(
    client, station_headers, simulation, db_session
):
    record = Recommendation(
        id=str(uuid.uuid4()),
        simulation_id=simulation["id"],
        state_version=simulation["state_version"],
        status="PENDING",
        evidence_status="VALIDATED_WITH_ASSUMPTIONS",
        disagreement=False,
        payload={
            "recommended": None,
            "affected_stations": ["VSN"],
            "conflicts": [],
            "alternatives": [],
            "explanation": {},
        },
        model_version="ppo-unavailable",
        optimizer_version="cpsat-1.0.0",
        created_by="section.master",
    )
    db_session.add(record)
    db_session.commit()

    response = client.get(
        f"/api/v1/recommendations/{record.id}", headers=station_headers
    )
    assert response.status_code == 403


def test_station_master_conflicts_are_scope_filtered(client, station_headers, simulation):
    response = client.get(
        f"/api/v1/simulations/{simulation['id']}/conflicts", headers=station_headers
    )
    assert response.status_code == 200
    body = response.json()
    assert body["scope_filtered"] is True
    assert body["scope"]["station_id"] == "MLG"
    assert body["total_detected"] >= len(body["conflicts"])
    network = simulation["network"]
    section_lookup = {
        block["id"]: section
        for section in network["sections"]
        for block in section["blocks"]
    }
    for conflict in body["conflicts"]:
        location = conflict["location"]
        if location.get("station_id"):
            assert location["station_id"] == "MLG"
        elif location.get("section_id"):
            section = next(
                item
                for item in network["sections"]
                if item["id"] == location["section_id"]
            )
            assert "MLG" in {section["from_station"], section["to_station"]}
        elif location.get("block_id"):
            section = section_lookup[location["block_id"]]
            assert "MLG" in {section["from_station"], section["to_station"]}


def test_section_master_has_full_scope(client, section_headers, simulation):
    response = client.get(
        f"/api/v1/simulations/{simulation['id']}/dashboard", headers=section_headers
    )
    assert response.status_code == 200
    assert response.json()["role_scope"]["role"] == "SECTION_MASTER"
