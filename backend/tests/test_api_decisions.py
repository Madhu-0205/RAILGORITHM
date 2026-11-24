"""Human decision workflow: approval, rejection, modification, staleness."""
from __future__ import annotations

import uuid

from app.models import Recommendation


def _generate(client, headers, simulation):
    response = client.post(
        f"/api/v1/simulations/{simulation['id']}/recommendations", headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_generate_recommendation_is_persisted(client, section_headers, simulation):
    payload = _generate(client, section_headers, simulation)
    assert payload["recommendation_id"]
    assert payload["status"] == "PENDING"
    assert payload["evidence_status"]
    assert payload["simulation_id"] == simulation["id"]
    assert payload["affected_stations"] is not None
    assert payload["is_stale"] is False
    listing = client.get(
        f"/api/v1/simulations/{simulation['id']}/recommendations",
        headers=section_headers,
    )
    assert listing.status_code == 200
    assert any(
        item["id"] == payload["recommendation_id"]
        for item in listing.json()["recommendations"]
    )


def test_approve_applies_only_to_simulation(client, section_headers, simulation):
    payload = _generate(client, section_headers, simulation)
    response = client.post(
        f"/api/v1/recommendations/{payload['recommendation_id']}/decision",
        headers=section_headers,
        json={
            "action": "APPROVE",
            "rationale": "Controller approved after reviewing evidence.",
            "confirm_apply": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"]["action"] == "APPROVE"
    assert body["decision"]["applied"] is True
    assert body["decision"]["execution_mode"] == "SIMULATED_ONLY"
    assert body["recommendation"]["status"] == "APPROVED"
    assert body["simulation_state_version"] > simulation["state_version"]
    assert body["decision"]["simulation_result"]["human_confirmed"] is True


def test_approval_of_a_block_closure_schedule_matches_recommendation_evidence(
    client, section_headers
):
    """Regression: evidence and the decision endpoint must use the same horizon."""
    created = client.post(
        "/api/v1/simulations",
        headers=section_headers,
        json={"scenario_key": "block_closure"},
    )
    assert created.status_code == 200, created.text
    simulation = created.json()
    advanced = client.post(
        f"/api/v1/simulations/{simulation['id']}/advance",
        headers=section_headers,
        json={"minutes": 5},
    )
    assert advanced.status_code == 200, advanced.text
    payload = _generate(client, section_headers, simulation)
    assert payload["recommended"] is not None
    assert payload["recommended"]["source"] == "CP_SAT"
    assert payload["recommended"]["expected_outcome"]["residual_critical"] == 0
    response = client.post(
        f"/api/v1/recommendations/{payload['recommendation_id']}/decision",
        headers=section_headers,
        json={
            "action": "APPROVE",
            "rationale": "Controller approved the independently validated schedule.",
            "confirm_apply": True,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["decision"]["applied"] is True


def test_approve_requires_explicit_confirmation(client, section_headers, simulation):
    payload = _generate(client, section_headers, simulation)
    response = client.post(
        f"/api/v1/recommendations/{payload['recommendation_id']}/decision",
        headers=section_headers,
        json={
            "action": "APPROVE",
            "rationale": "Trying without confirmation flag.",
            "confirm_apply": False,
        },
    )
    assert response.status_code == 400


def test_duplicate_decision_is_rejected(client, section_headers, simulation):
    payload = _generate(client, section_headers, simulation)
    url = f"/api/v1/recommendations/{payload['recommendation_id']}/decision"
    first = client.post(
        url,
        headers=section_headers,
        json={"action": "REJECT", "rationale": "First decision recorded."},
    )
    assert first.status_code == 200
    second = client.post(
        url,
        headers=section_headers,
        json={"action": "APPROVE", "rationale": "Second decision attempt.", "confirm_apply": True},
    )
    assert second.status_code == 409


def test_reject_does_not_apply_anything(client, section_headers, simulation):
    payload = _generate(client, section_headers, simulation)
    response = client.post(
        f"/api/v1/recommendations/{payload['recommendation_id']}/decision",
        headers=section_headers,
        json={"action": "REJECT", "rationale": "Controller rejected the advice."},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"]["applied"] is False
    assert body["decision"]["simulation_result"] is None
    assert body["recommendation"]["status"] == "REJECTED"
    assert body["simulation_state_version"] == simulation["state_version"]


def test_defer_does_not_apply_anything(client, section_headers, simulation):
    payload = _generate(client, section_headers, simulation)
    response = client.post(
        f"/api/v1/recommendations/{payload['recommendation_id']}/decision",
        headers=section_headers,
        json={"action": "DEFER", "rationale": "Need more time to assess traffic."},
    )
    assert response.status_code == 200
    assert response.json()["decision"]["applied"] is False
    assert response.json()["recommendation"]["status"] == "DEFERRED"


def test_modify_with_invalid_action_is_blocked(client, section_headers, simulation):
    payload = _generate(client, section_headers, simulation)
    response = client.post(
        f"/api/v1/recommendations/{payload['recommendation_id']}/decision",
        headers=section_headers,
        json={
            "action": "MODIFY",
            "rationale": "Trying an unsupported modification.",
            "modifications": {"action": {"type": "MAGIC"}},
            "confirm_apply": True,
        },
    )
    assert response.status_code == 422


def test_modify_with_valid_action_is_applied(client, section_headers, simulation):
    payload = _generate(client, section_headers, simulation)
    response = client.post(
        f"/api/v1/recommendations/{payload['recommendation_id']}/decision",
        headers=section_headers,
        json={
            "action": "MODIFY",
            "rationale": "Controller chose a safer modified action.",
            "modifications": {"action": {"type": "DO_NOTHING"}},
            "confirm_apply": True,
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["decision"]["applied"] is True
    assert body["recommendation"]["status"] == "MODIFIED"


def test_stale_recommendation_cannot_be_approved(client, section_headers, simulation):
    payload = _generate(client, section_headers, simulation)
    advanced = client.post(
        f"/api/v1/simulations/{simulation['id']}/advance",
        headers=section_headers,
        json={"minutes": 10},
    )
    assert advanced.status_code == 200
    response = client.post(
        f"/api/v1/recommendations/{payload['recommendation_id']}/decision",
        headers=section_headers,
        json={
            "action": "APPROVE",
            "rationale": "Attempting to approve stale advice.",
            "confirm_apply": True,
        },
    )
    assert response.status_code == 409
    fetched = client.get(
        f"/api/v1/recommendations/{payload['recommendation_id']}",
        headers=section_headers,
    )
    assert fetched.status_code == 200
    assert fetched.json()["status"] == "STALE"
    assert fetched.json()["is_stale"] is True


def test_request_alternatives_creates_child_recommendation(
    client, section_headers, simulation
):
    payload = _generate(client, section_headers, simulation)
    response = client.post(
        f"/api/v1/recommendations/{payload['recommendation_id']}/decision",
        headers=section_headers,
        json={
            "action": "REQUEST_ALTERNATIVES",
            "rationale": "Controller wants fresh alternatives.",
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["recommendation"]["status"] == "ALTERNATIVES_REQUESTED"
    assert body["new_recommendation"] is not None
    assert body["new_recommendation"]["recommendation_id"] != payload["recommendation_id"]
    assert body["new_recommendation"]["parent_recommendation_id"] == payload["recommendation_id"]


def test_approve_without_feasible_action_is_blocked(
    client, section_headers, simulation, db_session
):
    record = Recommendation(
        id=str(uuid.uuid4()),
        simulation_id=simulation["id"],
        state_version=simulation["state_version"],
        status="PENDING",
        evidence_status="NO_FEASIBLE_SOLUTION",
        disagreement=False,
        payload={
            "recommended": None,
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
        headers=section_headers,
        json={
            "action": "APPROVE",
            "rationale": "Attempting to approve nothing.",
            "confirm_apply": True,
        },
    )
    assert response.status_code == 409
    assert "fabricate" in response.json()["detail"].lower()


def test_station_master_can_decide_in_scope(client, station_headers, simulation, db_session):
    record = Recommendation(
        id=str(uuid.uuid4()),
        simulation_id=simulation["id"],
        state_version=simulation["state_version"],
        status="PENDING",
        evidence_status="VALIDATED_WITH_ASSUMPTIONS",
        disagreement=False,
        payload={
            "recommended": {"action": {"type": "DO_NOTHING"}},
            "affected_stations": ["MLG"],
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
            "action": "APPROVE",
            "rationale": "Station Master approved within scope.",
            "confirm_apply": True,
        },
    )
    assert response.status_code == 200, response.text
    assert response.json()["decision"]["decided_role"] == "STATION_MASTER"


def test_decision_requires_meaningful_rationale(client, section_headers, simulation):
    payload = _generate(client, section_headers, simulation)
    response = client.post(
        f"/api/v1/recommendations/{payload['recommendation_id']}/decision",
        headers=section_headers,
        json={"action": "REJECT", "rationale": "no"},
    )
    assert response.status_code == 422


def test_unknown_recommendation_is_404(client, section_headers):
    response = client.post(
        "/api/v1/recommendations/does-not-exist/decision",
        headers=section_headers,
        json={"action": "REJECT", "rationale": "Unknown recommendation."},
    )
    assert response.status_code == 404
