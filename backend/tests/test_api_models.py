"""Scenario catalogue and model registry API."""
from __future__ import annotations


def test_scenarios_endpoint(client, section_headers):
    response = client.get("/api/v1/scenarios", headers=section_headers)
    assert response.status_code == 200
    body = response.json()
    keys = {scenario["key"] for scenario in body["scenarios"]}
    assert "single_line_meet" in keys
    assert body["label"] == "SYNTHETIC"
    assert "reproducible" in body["note"]


def test_models_endpoint_reports_honest_status(client, section_headers):
    response = client.get("/api/v1/models", headers=section_headers)
    assert response.status_code == 200
    body = response.json()
    models = {model["name"]: model for model in body["models"]}
    assert models["CP-SAT"]["trained"] is False
    assert models["CP-SAT"]["status"] == "DETERMINISTIC_OPTIMIZER"
    assert models["Baseline"]["trained"] is False
    assert "not a trained model" in body["disclaimer"]
    ppo = models["PPO"]
    if not ppo["trained"]:
        assert ppo["status"] == "UNTRAINED_DEVELOPMENT_COMPONENT"
        assert ppo["metrics"] == {}
