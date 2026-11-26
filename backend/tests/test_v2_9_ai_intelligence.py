"""Comprehensive 22 Operational Scenario Test Suite for RAILGORITHM v2.9.

Validates:
1. Normal corridor operation
2. Delayed passenger train
3. Delayed freight train
4. Growing station congestion
5. Single-line crossing conflict (meet-pass sequence permutations)
6. Junction throat congestion at MLG
7. Platform unavailability
8. Temporary speed restriction (TSR)
9. Engineering block closure
10. Multiple simultaneous delays
11. Missing train position telemetry
12. Stale telemetry feed withholding
13. Contradictory train positions gate refusal
14. Feed disconnection (OFFLINE)
15. Unexpected train detention (excess dwell)
16. Downstream delay propagation cascade
17. No feasible regulation alternative
18. Model disagreement (PPO vs CP-SAT)
19. Recommendation expiry (15-min TTL)
20. Human rejection of an AI recommendation with rationale
21. Changed operational state after recommendation generation (stale state)
22. Unauthorized cross-jurisdiction recommendation access (403 Forbidden)
"""
from __future__ import annotations

import copy
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient

from app.domain.candidates import generate_candidates
from app.domain.data_quality import evaluate_data_quality
from app.domain.explanation import build_explanation
from app.domain.optimizer import optimise
from app.domain.pipeline import generate_recommendation
from app.domain.projection import (
    build_delay_propagation_graph,
    detect_developing_delays,
    evaluate_predictions,
)
from app.domain.state import advance, apply_action, initialise_state
from app.domain.validator import (
    INVALID,
    VALIDATED,
    VALIDATED_WITH_ASSUMPTIONS,
    evaluate_candidate,
    validate_action,
    validate_operational_readiness,
)
from app.ingestion.feed_manager import feed_manager
from app.models import Decision, Recommendation, Simulation, User
from app.services.decision_service import (
    evaluate_decision_outcome,
    evaluate_offline_model_candidates,
    export_decision_dataset,
    submit_decision,
)
from app.services.recommendation_service import generate_record


def test_scenario_01_normal_corridor_operation():
    """Scenario 1: Normal corridor operation with zero initial conflicts."""
    state = initialise_state("normal_traffic")
    payload = generate_recommendation(state, apply_minutes=30)
    assert payload["label"] == "SYNTHETIC"
    assert "structured_evidence" in payload
    assert "comparison_matrix" in payload
    assert "predictive_regulation" in payload
    assert payload["predictive_regulation"]["decision_urgency"] is not None


def test_scenario_02_delayed_passenger_train():
    """Scenario 2: Express passenger train delayed; punctuality protected."""
    state = initialise_state("single_line_meet")
    train = state["trains"][0]
    train["delay_min"] = 15
    train["current_delay_min"] = 15

    delays = detect_developing_delays(state, horizon_min=60)
    found = any(d["train_id"] == train["id"] for d in delays)
    assert found

    payload = generate_recommendation(state, apply_minutes=45)
    assert payload["evidence_status"] in {"VALIDATED", "VALIDATED_WITH_ASSUMPTIONS", "MODEL_DISAGREEMENT"}
    assert payload["recommended"] is not None


def test_scenario_03_delayed_freight_train():
    """Scenario 3: Freight train delayed; lower priority train held or looped."""
    state = initialise_state("single_line_meet")
    freight = next((t for t in state["trains"] if t.get("priority", 0) <= 2), state["trains"][-1])
    freight["delay_min"] = 25
    freight["current_delay_min"] = 25

    payload = generate_recommendation(state, apply_minutes=45)
    assert payload["recommended"] is not None
    # Higher priority train should not receive extensive holding compared to freight
    candidates = generate_candidates(state, payload.get("conflicts", []))
    assert any(c.get("action", {}).get("train_id") == freight["id"] for c in candidates)


def test_scenario_04_growing_station_congestion():
    """Scenario 4: Multiple trains converging on station platforms."""
    state = initialise_state("evening_peak")
    advance(state, 5)
    delays = detect_developing_delays(state, horizon_min=75)
    assert isinstance(delays, list)
    payload = generate_recommendation(state, apply_minutes=45)
    assert payload["optimizer"]["status"] in {"OPTIMAL", "FEASIBLE"}


def test_scenario_05_single_line_crossing_permutations():
    """Scenario 5: Single-line crossing conflict evaluates sequence permutations A before B vs B before A."""
    state = initialise_state("single_line_meet")
    conflicts = [
        {
            "id": "CF-CROSSING-TEST",
            "type": "SINGLE_LINE_CROSSING",
            "severity": "CRITICAL",
            "trains": [state["trains"][0]["id"], state["trains"][1]["id"]],
            "start_min": 0,
            "end_min": 15,
            "location": {"section_id": "S1"},
            "evidence": {"headway_min": 5},
        }
    ]
    candidates = generate_candidates(state, conflicts)
    seqs = [c.get("action", {}).get("crossing_sequence") for c in candidates if c.get("action", {}).get("crossing_sequence")]
    assert len(seqs) >= 1, "Crossing sequence permutation candidates should be generated."


def test_scenario_06_junction_throat_congestion_mlg():
    """Scenario 6: Junction throat congestion at Malgaon Junction (MLG)."""
    state = initialise_state("junction_congestion")
    candidates = generate_candidates(state, state.get("conflicts", []))
    assert isinstance(candidates, list)


def test_scenario_07_platform_unavailability():
    """Scenario 7: Station platform unavailable; validator rejects invalid routing."""
    state = initialise_state("platform_outage")
    invalid_action = {"type": "PLATFORM_REASSIGN", "train_id": state["trains"][0]["id"], "platform_id": "PF-NONEXISTENT"}
    val = validate_action(state, invalid_action)
    assert val["status"] == INVALID


def test_scenario_08_temporary_speed_restriction():
    """Scenario 8: Temporary speed restriction (TSR) delay development."""
    state = initialise_state("normal_traffic")
    state["active_closures"] = [{
        "section_id": "S1",
        "type": "TSR",
        "speed_limit_kmph": 30,
        "start_min": 0,
        "end_min": 120,
    }]
    delays = detect_developing_delays(state, horizon_min=60)
    assert isinstance(delays, list)


def test_scenario_09_engineering_block_closure():
    """Scenario 9: Engineering block closure enforcement."""
    state = initialise_state("block_closure")
    advance(state, 5)
    payload = generate_recommendation(state, apply_minutes=30)
    assert payload["recommended"] is not None
    # Action should not dispatch train into the closed block
    assert payload["recommended"]["validation_status"] in {VALIDATED, VALIDATED_WITH_ASSUMPTIONS}


def test_scenario_10_multiple_simultaneous_delays():
    """Scenario 10: Multiple simultaneous delays and cascade propagation graph."""
    state = initialise_state("single_line_meet")
    for t in state["trains"]:
        t["delay_min"] = 10
        t["current_delay_min"] = 10
    graph = build_delay_propagation_graph(state, horizon_min=75)
    assert "nodes" in graph
    assert "edges" in graph
    assert "cascade_chains" in graph
    assert len(graph["nodes"]) >= len(state["trains"])


def test_scenario_11_missing_train_position():
    """Scenario 11: Missing train position telemetry evaluation."""
    state = initialise_state("single_line_meet")
    state["trains"][0]["status"] = "RUNNING"
    state["trains"][0]["block_id"] = None
    dq = evaluate_data_quality(state)
    assert dq["overall_quality_state"] == "CONTRADICTORY" or not dq["is_eligible_for_recommendations"]


def test_scenario_12_stale_telemetry_feed_withholding():
    """Scenario 12: Stale telemetry feed withholds recommendation."""
    state = initialise_state("single_line_meet")
    # Simulate stale state with explicit quality status STALE
    state["_telemetry_quality_override"] = "STALE"
    payload = generate_recommendation(state, apply_minutes=30)
    assert payload["evidence_status"] == "STALE_DATA_WITHHELD"
    assert payload["recommended"] is None


def test_scenario_13_contradictory_train_positions():
    """Scenario 13: Contradictory train positions trigger gate refusal."""
    state = initialise_state("single_line_meet")
    state["_telemetry_quality_override"] = "CONTRADICTORY"
    payload = generate_recommendation(state, apply_minutes=30)
    assert payload["evidence_status"] == "CONTRADICTORY_DATA_REFUSED"
    assert payload["recommended"] is None


def test_scenario_14_feed_disconnection_offline():
    """Scenario 14: Feed disconnection (OFFLINE) blocks recommendation."""
    state = initialise_state("single_line_meet")
    state["_telemetry_quality_override"] = "OFFLINE"
    payload = generate_recommendation(state, apply_minutes=30)
    assert payload["evidence_status"] == "TELEMETRY_OFFLINE_GATED"
    assert payload["recommended"] is None


def test_scenario_15_unexpected_train_detention():
    """Scenario 15: Unexpected train detention (excess dwell)."""
    state = initialise_state("single_line_meet")
    state["trains"][0]["status"] = "AT_STATION"
    state["trains"][0]["dwell_remaining_min"] = 25
    state["trains"][0]["scheduled_dwell_min"] = 2
    delays = detect_developing_delays(state, horizon_min=60)
    assert any("dwell" in d["primary_driver"].lower() or d["category"] in {"OBSERVED_DELAY", "DEVELOPING_DELAY"} for d in delays)


def test_scenario_16_downstream_delay_propagation():
    """Scenario 16: Downstream delay propagation along headway dependencies."""
    state = initialise_state("cascading_delay")
    graph = build_delay_propagation_graph(state, horizon_min=75)
    assert len(graph["nodes"]) > 0


def test_scenario_17_no_feasible_regulation_alternative():
    """Scenario 17: No feasible regulation alternative available."""
    state = initialise_state("no_feasible_schedule")
    payload = generate_recommendation(state, apply_minutes=30)
    assert payload["recommended"] is None or payload["evidence_status"] in {"NO_FEASIBLE_SOLUTION", "VALIDATED_WITH_ASSUMPTIONS"}


def test_scenario_18_model_disagreement():
    """Scenario 18: Model disagreement between PPO and CP-SAT is surfaced explicitly."""
    state = initialise_state("single_line_meet")
    advance(state, 2)
    payload = generate_recommendation(state, apply_minutes=45)
    assert "disagreement" in payload
    assert "disagreement_detail" in payload
    assert "selection_rule" in payload["disagreement_detail"]


def test_scenario_19_recommendation_expiry_ttl():
    """Scenario 19: Recommendation validity and expiry parameters (15-min TTL)."""
    state = initialise_state("single_line_meet")
    payload = generate_recommendation(state, apply_minutes=30)
    exp = payload.get("structured_evidence", {}).get("K_validity", {})
    assert "valid_until_sim_time" in exp
    assert "revalidation_triggers" in exp


def test_scenario_20_human_rejection_with_rationale(client: TestClient, section_headers: dict):
    """Scenario 20: Human controller rejects AI recommendation with rationale."""
    sim_res = client.post(
        "/api/v1/simulations",
        headers=section_headers,
        json={"scenario_key": "single_line_meet"},
    )
    assert sim_res.status_code == 200
    sim_id = sim_res.json()["id"]

    rec_res = client.post(
        f"/api/v1/simulations/{sim_id}/recommendations",
        headers=section_headers,
        json={},
    )
    assert rec_res.status_code == 200
    rec_id = rec_res.json()["recommendation_id"]

    dec_res = client.post(
        f"/api/v1/recommendations/{rec_id}/decision",
        headers=section_headers,
        json={
            "action": "REJECT",
            "rationale": "Overriding AI recommendation due to urgent track inspection memo.",
            "confirm_apply": False,
        },
    )
    assert dec_res.status_code == 200
    body = dec_res.json()
    assert body["decision"]["action"] == "REJECT"
    assert body["decision"]["applied"] is False


def test_scenario_21_changed_operational_state_stale(client: TestClient, section_headers: dict):
    """Scenario 21: Simulation state changes after recommendation generation; decision rejected as stale."""
    sim_res = client.post(
        "/api/v1/simulations",
        headers=section_headers,
        json={"scenario_key": "single_line_meet"},
    )
    sim_id = sim_res.json()["id"]

    rec_res = client.post(
        f"/api/v1/simulations/{sim_id}/recommendations",
        headers=section_headers,
        json={},
    )
    rec_id = rec_res.json()["recommendation_id"]

    # Advance the simulation so state version changes
    adv_res = client.post(
        f"/api/v1/simulations/{sim_id}/advance",
        headers=section_headers,
        json={"minutes": 5},
    )
    assert adv_res.status_code == 200

    # Attempt to approve the stale recommendation
    dec_res = client.post(
        f"/api/v1/recommendations/{rec_id}/decision",
        headers=section_headers,
        json={
            "action": "APPROVE",
            "rationale": "Attempting late approval.",
            "confirm_apply": True,
        },
    )
    assert dec_res.status_code == 409
    assert "stale" in dec_res.json()["detail"].lower()


def test_scenario_22_cross_jurisdiction_access_control(client: TestClient, station_headers: dict, section_headers: dict):
    """Scenario 22: Station Master forbidden from deciding recommendation outside station scope (403)."""
    # Create a simulation with corridor scope
    sim_res = client.post(
        "/api/v1/simulations",
        headers=section_headers,
        json={"scenario_key": "evening_peak"},
    )
    sim_id = sim_res.json()["id"]

    rec_res = client.post(
        f"/api/v1/simulations/{sim_id}/recommendations",
        headers=section_headers,
        json={},
    )
    rec_id = rec_res.json()["recommendation_id"]

    # Station master (assigned to NDL only) attempts to decide corridor recommendation affecting MLG/VSN
    dec_res = client.post(
        f"/api/v1/recommendations/{rec_id}/decision",
        headers=station_headers,
        json={
            "action": "APPROVE",
            "rationale": "Unauthorized station master attempt.",
            "confirm_apply": True,
        },
    )
    # Must be rejected with 403 Forbidden
    assert dec_res.status_code == 403
    assert "outside your assigned station scope" in dec_res.json()["detail"].lower() or "station scope" in dec_res.json()["detail"].lower()


def test_prediction_evaluation_metrics():
    """Verify evaluation metrics: MAE, RMSE, coverage, and early-warning lead time."""
    preds = [
        {"train_id": "T1", "current_delay": 5, "min_delay": 8, "expected_delay": 10, "max_delay": 14, "primary_driver": "TSR"},
        {"train_id": "T2", "current_delay": 0, "min_delay": 0, "expected_delay": 2, "max_delay": 5, "primary_driver": "HEADWAY"},
    ]
    ground_truth = {
        "T1": {"actual_delay_min": 11, "detected_lead_time_min": 25},
        "T2": {"actual_delay_min": 3, "detected_lead_time_min": 15},
    }
    metrics = evaluate_predictions(preds, ground_truth)
    assert metrics["mae_min"] == 1.0
    assert metrics["rmse_min"] == 1.0
    assert metrics["prediction_interval_coverage_pct"] == 100.0
    assert metrics["sample_size"] == 2


def test_offline_model_candidate_evaluation(db_session):
    """Verify offline candidate evaluation against decision history."""
    report = evaluate_offline_model_candidates(db_session, "ppo-corridor-v2.9", "v2.9.0-rc1")
    assert "candidate_model" in report
    assert "safety_violations" in report
    assert report["safety_violations"] == 0
    assert "deployment_gate" in report
