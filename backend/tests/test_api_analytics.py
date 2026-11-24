"""Analytics endpoint: measured KPIs, decision statistics and honest labelling."""
from __future__ import annotations


def test_analytics_returns_kpis_and_disclaimer(client, section_headers, simulation):
    response = client.get(
        f"/api/v1/simulations/{simulation['id']}/analytics", headers=section_headers
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["simulation_id"] == simulation["id"]
    assert body["label"] == "SYNTHETIC"
    assert "not Indian Railways performance measurements" in body["data_disclaimer"]
    kpis = body["kpis"]
    for key in (
        "average_delay_min",
        "total_delay_min",
        "on_time_performance_pct",
        "throughput_trains_per_hour",
        "section_utilization_pct",
        "conflict_frequency_active",
        "trains_total",
        "trains_active",
    ):
        assert key in kpis
    assert len(body["section_utilization"]) == 4
    assert len(body["platform_utilization"]) == 5
    assert len(body["train_delays"]) == kpis["trains_total"]
    assert body["recommendation_stats"]["total"] == 0
    assert body["recommendation_stats"]["acceptance_rate_pct"] is None


def test_analytics_reflects_generated_recommendation(client, section_headers, simulation):
    client.post(
        f"/api/v1/simulations/{simulation['id']}/recommendations",
        headers=section_headers,
    )
    response = client.get(
        f"/api/v1/simulations/{simulation['id']}/analytics", headers=section_headers
    )
    assert response.status_code == 200
    stats = response.json()["recommendation_stats"]
    assert stats["total"] == 1
    assert stats["pending"] == 1
    assert stats["decided_count"] == 0
    assert response.json()["latest_recommendation_comparison"] is not None


def test_analytics_counts_human_decisions(client, section_headers, simulation):
    generated = client.post(
        f"/api/v1/simulations/{simulation['id']}/recommendations",
        headers=section_headers,
    ).json()
    client.post(
        f"/api/v1/recommendations/{generated['recommendation_id']}/decision",
        headers=section_headers,
        json={"action": "REJECT", "rationale": "Analytics rejection test."},
    )
    response = client.get(
        f"/api/v1/simulations/{simulation['id']}/analytics", headers=section_headers
    )
    assert response.status_code == 200
    stats = response.json()["recommendation_stats"]
    assert stats["rejected"] == 1
    assert stats["decided_count"] == 1
    assert stats["acceptance_rate_pct"] == 0.0
    assert stats["modification_rate_pct"] == 0.0


def test_analytics_unknown_simulation_is_404(client, section_headers):
    response = client.get(
        "/api/v1/simulations/does-not-exist/analytics", headers=section_headers
    )
    assert response.status_code == 404
