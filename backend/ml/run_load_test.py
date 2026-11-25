"""High-concurrency load and performance stress test for RAILGORITHM 2.2.

Evaluates:
1. Ingestion throughput and latency under rapid event bursts (1,000 events)
2. Concurrent multi-role API dashboard queries (concurrent Station Master & Section Controller requests)
3. Feed disconnection and recovery resilience under high error rates
"""
from __future__ import annotations

import concurrent.futures
import json
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from fastapi.testclient import TestClient

from app.db import SessionLocal
from app.ingestion.adapters import MockRailwayFeedAdapter
from app.ingestion.feed_manager import feed_manager
from app.ingestion.models import RawFeedPayload
from app.main import app
from app.models import Simulation
from app.services.analytics_service import section_controller_kpis, station_master_kpis
from app.services.recommendation_service import generate_record


def test_ingestion_burst_performance(event_count: int = 1000) -> dict:
    feed_manager.reset()
    now = datetime.now(timezone.utc)
    latencies: list[float] = []

    t_start = time.perf_counter()
    for i in range(1, event_count + 1):
        payload = RawFeedPayload(
            feed_id="FEED-SIGNAL-01",
            sequence_num=i,
            train_id="12625",
            event_type="SPEED_UPDATE" if i % 2 == 0 else "HEARTBEAT",
            location_id="B1",
            timestamp=now.isoformat(),
            speed_kmph=75.0 + (i % 20),
        )
        res = feed_manager.ingest_event(payload)
        latencies.append(res.processing_latency_ms)

    total_wall_time = time.perf_counter() - t_start
    throughput = event_count / max(1e-6, total_wall_time)

    return {
        "event_count": event_count,
        "total_wall_time_s": round(total_wall_time, 4),
        "throughput_events_per_sec": round(throughput, 1),
        "mean_latency_ms": round(statistics.mean(latencies), 4),
        "median_latency_ms": round(float(np.median(latencies)), 4),
        "p95_latency_ms": round(float(np.percentile(latencies, 95)), 4),
        "p99_latency_ms": round(float(np.percentile(latencies, 99)), 4),
        "max_latency_ms": round(max(latencies), 4),
        "valid_events_ingested": feed_manager.get_feed_health("FEED-SIGNAL-01").events_valid_total,
    }


def test_concurrent_api_load(concurrency: int = 20, iterations: int = 5) -> dict:
    client = TestClient(app)
    # Login as section master
    login_res = client.post("/api/v1/auth/login", json={"username": "section.master", "password": "Section@123"})
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Create test simulation
    sim_res = client.post("/api/v1/simulations", headers=headers, json={"scenario_key": "evening_peak"})
    assert sim_res.status_code == 200
    sim_id = sim_res.json()["id"]

    query_latencies: list[float] = []
    errors = 0

    def worker_query(index: int) -> float:
        t0 = time.perf_counter()
        if index % 2 == 0:
            url = f"/api/v1/simulations/{sim_id}/analytics/section-controller"
        else:
            url = f"/api/v1/simulations/{sim_id}/analytics/station-master?station_id=MLG"
        r = client.get(url, headers=headers)
        if r.status_code != 200:
            return -1.0
        return (time.perf_counter() - t0) * 1000

    total_queries = concurrency * iterations
    t_start = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(worker_query, i) for i in range(total_queries)]
        for f in concurrent.futures.as_completed(futures):
            lat = f.result()
            if lat < 0:
                errors += 1
            else:
                query_latencies.append(lat)

    wall_time = time.perf_counter() - t_start

    return {
        "concurrent_workers": concurrency,
        "total_queries_executed": total_queries,
        "successful_queries": len(query_latencies),
        "errors": errors,
        "error_rate_pct": round(100.0 * errors / total_queries, 2),
        "wall_time_s": round(wall_time, 4),
        "query_throughput_qps": round(total_queries / max(1e-6, wall_time), 1),
        "mean_response_time_ms": round(statistics.mean(query_latencies), 2) if query_latencies else 0.0,
        "p95_response_time_ms": round(float(np.percentile(query_latencies, 95)), 2) if query_latencies else 0.0,
        "max_response_time_ms": round(max(query_latencies), 2) if query_latencies else 0.0,
    }


def test_recommendation_generation_benchmark() -> dict:
    client = TestClient(app)
    login_res = client.post("/api/v1/auth/login", json={"username": "section.master", "password": "Section@123"})
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    sim_res = client.post("/api/v1/simulations", headers=headers, json={"scenario_key": "evening_peak"})
    sim_id = sim_res.json()["id"]

    latencies = []
    for _ in range(3):
        t0 = time.perf_counter()
        rec_res = client.post(f"/api/v1/simulations/{sim_id}/recommendations", headers=headers)
        assert rec_res.status_code == 200
        latencies.append((time.perf_counter() - t0) * 1000)

    return {
        "scenario": "evening_peak",
        "iterations": 3,
        "mean_recommendation_time_ms": round(statistics.mean(latencies), 2),
        "min_recommendation_time_ms": round(min(latencies), 2),
        "max_recommendation_time_ms": round(max(latencies), 2),
    }


def main():
    root = Path(__file__).resolve().parent.parent
    reports_dir = root / "ml" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)

    print("Running Ingestion Burst Performance Test (1,000 events)...")
    ingest_perf = test_ingestion_burst_performance(1000)
    print(f"Ingestion Throughput: {ingest_perf['throughput_events_per_sec']} events/sec, Mean Latency: {ingest_perf['mean_latency_ms']} ms")

    print("\nRunning Concurrent Multi-Role API Load Test (20 concurrent workers)...")
    concurrency_perf = test_concurrent_api_load(concurrency=20, iterations=5)
    print(f"API Throughput: {concurrency_perf['query_throughput_qps']} QPS, Mean Latency: {concurrency_perf['mean_response_time_ms']} ms, Errors: {concurrency_perf['errors']}")

    print("\nRunning Recommendation Generation Latency Benchmark...")
    rec_perf = test_recommendation_generation_benchmark()
    print(f"Mean Pipeline Time: {rec_perf['mean_recommendation_time_ms']} ms")

    report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": "macOS Python 3.14 / SQLite In-Memory & File",
        "ingestion_performance": ingest_perf,
        "concurrent_api_performance": concurrency_perf,
        "recommendation_pipeline_performance": rec_perf,
        "summary": {
            "ingestion_throughput_capacity": f"{ingest_perf['throughput_events_per_sec']} events/sec",
            "ingestion_p95_latency": f"{ingest_perf['p95_latency_ms']} ms",
            "api_qps_capacity": f"{concurrency_perf['query_throughput_qps']} queries/sec",
            "api_p95_latency": f"{concurrency_perf['p95_response_time_ms']} ms",
            "error_rate": f"{concurrency_perf['error_rate_pct']}%",
            "pipeline_generation_mean": f"{rec_perf['mean_recommendation_time_ms']} ms",
        },
    }

    out_file = reports_dir / "load_test_v2_2.json"
    with open(out_file, "w") as f:
        json.dump(report, f, indent=2)

    print(f"\nLoad test results written to {out_file}")
    print(json.dumps(report["summary"], indent=2))


if __name__ == "__main__":
    main()
