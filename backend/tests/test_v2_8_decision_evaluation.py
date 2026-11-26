"""Tests for Feature 4: Learning from Previous Decisions & Review Analytics (v2.8)."""
import pytest
from app.db import get_db
from app.models import Decision, Recommendation, Simulation, User
from app.services.decision_service import (
    evaluate_decision_outcome,
    export_decision_dataset,
    get_decision_review_analytics,
    submit_decision,
)
from app.services.recommendation_service import generate_record


def test_submit_decision_records_feedback_and_predictions(client, section_headers, simulation):
    rec_res = client.post(
        f"/api/v1/simulations/{simulation['id']}/recommendations",
        headers=section_headers,
    )
    assert rec_res.status_code == 200
    rec = rec_res.json()

    # Submit decision with structured feedback tag
    dec_res = client.post(
        f"/api/v1/recommendations/{rec['recommendation_id']}/decision",
        headers=section_headers,
        json={
            "action": "REJECT",
            "rationale": "Overridden due to passenger connection priority at junction.",
            "feedback_category": "REJECTED",
            "structured_rationale_tag": "PASSENGER_CONNECTION",
            "confirm_apply": False,
        },
    )
    assert dec_res.status_code == 200
    data = dec_res.json()
    decision = data["decision"]
    assert decision["feedback_category"] == "REJECTED"
    assert decision["structured_rationale_tag"] == "PASSENGER_CONNECTION"
    assert "predicted_outcome" in decision


def test_decision_review_analytics_endpoint(client, section_headers, simulation):
    analytics_res = client.get(
        "/api/v1/recommendations/review/analytics",
        headers=section_headers,
    )
    assert analytics_res.status_code == 200
    analytics = analytics_res.json()
    assert "total_decisions" in analytics
    assert "acceptance_rate_pct" in analytics
    assert "by_action_type" in analytics
    assert "by_feedback_category" in analytics
    assert "modification_patterns" in analytics
    assert "outcome_accuracy" in analytics


def test_decision_review_dataset_export(client, section_headers, simulation):
    dataset_res = client.get(
        "/api/v1/recommendations/review/dataset",
        headers=section_headers,
    )
    assert dataset_res.status_code == 200
    dataset = dataset_res.json()
    assert isinstance(dataset, list)
