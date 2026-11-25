"""Unit and integration tests for RAILGORITHM 2.2 real-time data ingestion."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import pytest

from app.ingestion.adapters import MockRailwayFeedAdapter
from app.ingestion.feed_manager import OperationalFeedManager, feed_manager
from app.ingestion.models import RawFeedPayload
from app.ingestion.validator import IngestionValidator


def test_ingestion_valid_movement_normalization():
    validator = IngestionValidator()
    raw = RawFeedPayload(
        feed_id="FEED-TEST-01",
        sequence_num=1,
        train_id="12625",
        event_type="BLOCK_ENTRY",
        location_id="B1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        speed_kmph=85.0,
        delay_min=2.0,
    )
    res = validator.validate_and_normalize(raw)
    assert res.status == "VALID"
    assert res.event is not None
    assert res.event.train_id == "12625"
    assert res.event.event_type == "BLOCK_ENTRY"
    assert res.event.location_id == "B1"
    assert res.event.speed_kmph == 85.0
    assert res.processing_latency_ms >= 0


def test_ingestion_duplicate_detection():
    validator = IngestionValidator()
    ts = datetime.now(timezone.utc).isoformat()
    raw = RawFeedPayload(
        feed_id="FEED-TEST-01",
        sequence_num=10,
        train_id="12625",
        event_type="BLOCK_ENTRY",
        location_id="B1",
        timestamp=ts,
    )
    r1 = validator.validate_and_normalize(raw)
    assert r1.status == "VALID"

    # Re-sending identical payload must be recognized as duplicate
    r2 = validator.validate_and_normalize(raw)
    assert r2.status == "DUPLICATE"
    assert "duplicate" in r2.message.lower()


def test_ingestion_sequence_gap_detection():
    validator = IngestionValidator()
    now = datetime.now(timezone.utc)
    # Event 1
    r1 = validator.validate_and_normalize(RawFeedPayload(
        feed_id="FEED-TEST-01", sequence_num=1, train_id="12625",
        event_type="BLOCK_ENTRY", location_id="B1", timestamp=now.isoformat(),
    ))
    assert r1.status == "VALID"
    assert r1.sequence_gap_detected is False

    # Event 5 (gap of 3 events: 2, 3, 4 missing)
    r2 = validator.validate_and_normalize(RawFeedPayload(
        feed_id="FEED-TEST-01", sequence_num=5, train_id="12625",
        event_type="BLOCK_EXIT", location_id="B1", timestamp=(now + timedelta(seconds=15)).isoformat(),
    ))
    assert r2.status == "VALID"
    assert r2.sequence_gap_detected is True
    assert r2.gap_size == 3


def test_ingestion_physical_speed_impossibility():
    validator = IngestionValidator()
    raw = RawFeedPayload(
        feed_id="FEED-TEST-01",
        sequence_num=1,
        train_id="12625",
        event_type="SPEED_UPDATE",
        location_id="B1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        speed_kmph=240.0,  # Exceeds max limit of 160 km/h
    )
    res = validator.validate_and_normalize(raw)
    assert res.status == "CONTRADICTION"
    assert res.contradiction is not None
    assert res.contradiction.contradiction_type == "PHYSICAL_IMPOSSIBILITY"


def test_ingestion_temporal_inversion_future_drift():
    validator = IngestionValidator()
    future_time = datetime.now(timezone.utc) + timedelta(minutes=5)
    raw = RawFeedPayload(
        feed_id="FEED-TEST-01",
        sequence_num=1,
        train_id="12625",
        event_type="BLOCK_ENTRY",
        location_id="B1",
        timestamp=future_time.isoformat(),
    )
    res = validator.validate_and_normalize(raw)
    assert res.status == "CONTRADICTION"
    assert res.contradiction.contradiction_type == "TEMPORAL_INVERSION"


def test_ingestion_spatial_teleportation_contradiction():
    validator = IngestionValidator()
    now = datetime.now(timezone.utc)
    # Train at NDL
    r1 = validator.validate_and_normalize(RawFeedPayload(
        feed_id="FEED-TEST-01", sequence_num=1, train_id="12625",
        event_type="STATION_ARRIVAL", location_id="NDL", timestamp=now.isoformat(),
    ))
    assert r1.status == "VALID"

    # Train suddenly reported arriving at distant VSN 2 seconds later
    r2 = validator.validate_and_normalize(RawFeedPayload(
        feed_id="FEED-TEST-01", sequence_num=2, train_id="12625",
        event_type="STATION_ARRIVAL", location_id="VSN", timestamp=(now + timedelta(seconds=2)).isoformat(),
    ))
    assert r2.status == "CONTRADICTION"
    assert r2.contradiction.contradiction_type == "SPATIAL_TELEPORTATION"


def test_ingestion_mutual_exclusion_contradiction():
    validator = IngestionValidator()
    now = datetime.now(timezone.utc)
    # Train 1 enters single line block B2
    r1 = validator.validate_and_normalize(RawFeedPayload(
        feed_id="FEED-TEST-01", sequence_num=1, train_id="12625",
        event_type="BLOCK_ENTRY", location_id="B2", timestamp=now.isoformat(),
    ))
    assert r1.status == "VALID"

    # Train 2 enters same block B2 simultaneously without Train 1 having exited
    r2 = validator.validate_and_normalize(RawFeedPayload(
        feed_id="FEED-TEST-01", sequence_num=2, train_id="51831",
        event_type="BLOCK_ENTRY", location_id="B2", timestamp=(now + timedelta(seconds=5)).isoformat(),
    ))
    assert r2.status == "CONTRADICTION"
    assert r2.contradiction.contradiction_type == "MUTUAL_EXCLUSION_VIOLATION"


def test_feed_manager_health_and_circuit_breaker():
    mgr = OperationalFeedManager(stale_threshold_sec=5.0, degraded_threshold_sec=2.0)
    health = mgr.get_feed_health("FEED-SIGNAL-01")
    assert health.status in {"HEALTHY", "DEGRADED", "STALE"}
    assert health.connected is True
    assert health.error_rate_pct == 0.0

    # Inject 10 consecutive contradictions to trip circuit breaker
    now = datetime.now(timezone.utc)
    for i in range(12):
        mgr.ingest_event(RawFeedPayload(
            feed_id="FEED-SIGNAL-01",
            sequence_num=100 + i,
            train_id="12625",
            event_type="SPEED_UPDATE",
            location_id="B1",
            timestamp=now.isoformat(),
            speed_kmph=300.0 + i,  # Invalid speed
        ))

    post_health = mgr.get_feed_health("FEED-SIGNAL-01")
    assert post_health.circuit_breaker_open is True
    assert post_health.status == "OFFLINE"

    # Reconnect resets circuit breaker
    reconnect_res = mgr.trigger_reconnect("FEED-SIGNAL-01")
    assert reconnect_res["success"] is True
    assert reconnect_res["status"] == "RECONNECTED"
    res_health = mgr.get_feed_health("FEED-SIGNAL-01")
    assert res_health.circuit_breaker_open is False


def test_api_ingestion_endpoints(client, section_headers):
    # Test GET /status
    res = client.get("/api/v1/ingestion/status", headers=section_headers)
    assert res.status_code == 200
    feeds = res.json()
    assert isinstance(feeds, list)
    assert len(feeds) >= 1
    assert "status" in feeds[0]

    # Test POST /events
    now = datetime.now(timezone.utc)
    ev_res = client.post(
        "/api/v1/ingestion/events",
        headers=section_headers,
        json={
            "feed_id": "FEED-SIGNAL-01",
            "sequence_num": 501,
            "train_id": "12625",
            "event_type": "BLOCK_ENTRY",
            "location_id": "B1",
            "timestamp": now.isoformat(),
            "speed_kmph": 80.0,
        },
    )
    assert ev_res.status_code == 200
    body = ev_res.json()
    assert body["status"] in {"VALID", "DUPLICATE"}

    # Test GET /events
    list_res = client.get("/api/v1/ingestion/events?limit=10", headers=section_headers)
    assert list_res.status_code == 200
    assert isinstance(list_res.json(), list)

    # Test GET /contradictions
    contr_res = client.get("/api/v1/ingestion/contradictions?limit=10", headers=section_headers)
    assert contr_res.status_code == 200
    assert isinstance(contr_res.json(), list)

    # Test POST /reconnect
    rec_res = client.post("/api/v1/ingestion/feeds/FEED-SIGNAL-01/reconnect", headers=section_headers)
    assert rec_res.status_code == 200
    assert rec_res.json()["success"] is True
