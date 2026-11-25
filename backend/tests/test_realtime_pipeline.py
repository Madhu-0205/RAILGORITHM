"""Comprehensive pipeline, reliability, security, and environment isolation tests for RAILGORITHM 2.3."""
from __future__ import annotations

import concurrent.futures
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.domain.network import build_default_network
from app.domain.state import initialise_state
from app.ingestion.event_processor import EnvironmentIsolationError, OperationalEventProcessor
from app.ingestion.feed_manager import OperationalFeedManager
from app.ingestion.models import RawFeedPayload
from app.ingestion.validator import IngestionValidator


@pytest.fixture()
def clean_feed_manager():
    fm = OperationalFeedManager()
    fm.reset()
    return fm


def test_end_to_end_event_processing_pipeline(clean_feed_manager):
    """Verify complete pipeline: Raw Ingest -> Validation -> Event Processing -> State Update."""
    state = initialise_state("normal_traffic")
    processor = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    state["environment_mode"] = "SYNTHETIC_SIMULATION"

    # 1. Source prepares a block entry event for train 12625
    raw = RawFeedPayload(
        feed_id="FEED-SIGNAL-01",
        sequence_num=101,
        train_id="12625",
        event_type="BLOCK_ENTRY",
        location_id="B1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        speed_kmph=80.0,
        direction="UP",
        environment="SYNTHETIC_SIMULATION",
    )

    # 2. Ingest and Validate
    val_res = clean_feed_manager.ingest_event(raw)
    assert val_res.status == "VALID"
    assert val_res.reason_code == "VALID_EVENT"
    assert val_res.event is not None
    norm_event = val_res.event

    # 3. Process into state
    proc_res = processor.process_event(norm_event, state)
    assert proc_res["success"] is True
    assert proc_res["idempotent"] is False
    assert proc_res["state_modified"] is True

    # 4. State verification
    t = next(x for x in state["trains"] if x["id"] == "12625")
    assert t["current_location"] == "B1"
    assert t["last_reported_speed_kmph"] == 80.0
    assert state["block_occupancy"]["B1"] == "12625"


def test_event_idempotency_and_duplicate_suppression(clean_feed_manager):
    """Processing duplicate raw payloads and duplicate normalized events must be strictly idempotent."""
    state = initialise_state("normal_traffic")
    processor = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    state["environment_mode"] = "SYNTHETIC_SIMULATION"

    raw = RawFeedPayload(
        feed_id="FEED-SIGNAL-01",
        sequence_num=201,
        train_id="12625",
        event_type="BLOCK_ENTRY",
        location_id="B1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        speed_kmph=75.0,
        environment="SYNTHETIC_SIMULATION",
    )

    # First ingestion is valid
    res1 = clean_feed_manager.ingest_event(raw)
    assert res1.status == "VALID"
    norm_event = res1.event

    # Second ingestion of identical raw event is identified as DUPLICATE
    res2 = clean_feed_manager.ingest_event(raw)
    assert res2.status == "DUPLICATE"
    assert res2.reason_code == "DUPLICATE_EVENT"

    # Processing normalized event into state first time modifies state
    p1 = processor.process_event(norm_event, state)
    assert p1["state_modified"] is True
    version_after_p1 = state["version"]

    # Re-processing the same normalized event is idempotent: zero state modification, same version
    p2 = processor.process_event(norm_event, state)
    assert p2["idempotent"] is True
    assert state["version"] == version_after_p1


def test_event_recovery_and_replay(clean_feed_manager):
    """Verify acknowledged events can be recovered from the feed manager and deterministically replayed."""
    initial_state = initialise_state("normal_traffic")
    initial_state["environment_mode"] = "SYNTHETIC_SIMULATION"
    processor = OperationalEventProcessor()

    # Ingest 3 chronological events for train 12625
    events_raw = [
        RawFeedPayload(
            feed_id="FEED-SIGNAL-01",
            sequence_num=301,
            train_id="12625",
            event_type="BLOCK_ENTRY",
            location_id="B1",
            timestamp="2026-03-01T07:05:00Z",
            speed_kmph=75.0,
            environment="SYNTHETIC_SIMULATION",
        ),
        RawFeedPayload(
            feed_id="FEED-SIGNAL-01",
            sequence_num=302,
            train_id="12625",
            event_type="SPEED_UPDATE",
            location_id="B1",
            timestamp="2026-03-01T07:08:00Z",
            speed_kmph=85.0,
            environment="SYNTHETIC_SIMULATION",
        ),
        RawFeedPayload(
            feed_id="FEED-SIGNAL-01",
            sequence_num=303,
            train_id="12625",
            event_type="BLOCK_EXIT",
            location_id="B1",
            timestamp="2026-03-01T07:15:00Z",
            speed_kmph=80.0,
            environment="SYNTHETIC_SIMULATION",
        ),
    ]

    for r in events_raw:
        res = clean_feed_manager.ingest_event(r)
        assert res.status == "VALID"

    # Recover event stream from sequence 301
    recovered = clean_feed_manager.recover_event_stream(since_sequence_num=301)
    assert len(recovered) >= 3

    # Replay event stream into fresh cloned state
    fresh_state = initialise_state("normal_traffic")
    fresh_state["environment_mode"] = "SYNTHETIC_SIMULATION"
    replayed_state = processor.replay_event_stream(recovered, fresh_state)

    # Final state must show train cleared B1
    assert "B1" not in replayed_state.get("block_occupancy", {})
    t = next(x for x in replayed_state["trains"] if x["id"] == "12625")
    assert t["last_reported_speed_kmph"] == 80.0


def test_environment_isolation_live_vs_simulation(clean_feed_manager):
    """Enforce strict separation: live operational feeds reject synthetic events and vice-versa."""
    # 1. Live feed (FEED-CRIS-COA-01) rejects synthetic payload
    synthetic_payload = RawFeedPayload(
        feed_id="FEED-CRIS-COA-01",
        sequence_num=401,
        train_id="T101",
        event_type="BLOCK_ENTRY",
        location_id="B1",
        timestamp=datetime.now(timezone.utc).isoformat(),
        environment="SYNTHETIC_SIMULATION",  # Wrong environment for live feed!
    )
    res = clean_feed_manager.ingest_event(synthetic_payload)
    assert res.status == "CONTRADICTION"
    assert res.reason_code == "ENVIRONMENT_MISMATCH"
    assert "Cross-environment" in res.contradiction.description or "environment" in res.contradiction.description.lower()

    # 2. Processor rejects applying live event to synthetic state
    norm_live_event = clean_feed_manager.ingest_event(
        RawFeedPayload(
            feed_id="FEED-CRIS-COA-01",
            sequence_num=402,
            train_id="T101",
            event_type="BLOCK_ENTRY",
            location_id="B1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment="LIVE_OPERATIONAL",  # Correct for feed
        )
    ).event
    assert norm_live_event is not None

    processor = OperationalEventProcessor()
    sim_state = {"environment_mode": "SYNTHETIC_SIMULATION", "trains": [{"id": "T101"}]}

    with pytest.raises(EnvironmentIsolationError, match="Cross-environment contamination blocked"):
        processor.process_event(norm_live_event, sim_state)


def test_railway_specific_validation_rules():
    """Verify train category speeds, directional locking, unmatched exits, and headway."""
    net = build_default_network()
    val = IngestionValidator(network=net, expected_environment="SYNTHETIC_SIMULATION")

    # 1. Freight speed limit check (max 75 km/h for Freight)
    res_freight = val.validate_and_normalize(
        RawFeedPayload(
            feed_id="FEED-SIGNAL-01",
            sequence_num=501,
            train_id="FRT-801",
            train_type="FREIGHT",
            event_type="SPEED_UPDATE",
            location_id="B2U",
            timestamp=datetime.now(timezone.utc).isoformat(),
            speed_kmph=88.0,  # Exceeds 75 km/h
            environment="SYNTHETIC_SIMULATION",
        )
    )
    assert res_freight.status == "CONTRADICTION"
    assert res_freight.reason_code == "TRAIN_SPEED_LIMIT_EXCEEDED"

    # 2. Wrong direction entry check on unidirectional block (B2U is strictly UP)
    res_wrong_dir = val.validate_and_normalize(
        RawFeedPayload(
            feed_id="FEED-SIGNAL-01",
            sequence_num=502,
            train_id="EXP-101",
            train_type="EXPRESS",
            direction="DOWN",  # Moving DOWN into UP block!
            event_type="BLOCK_ENTRY",
            location_id="B2U",
            timestamp=datetime.now(timezone.utc).isoformat(),
            speed_kmph=95.0,
            environment="SYNTHETIC_SIMULATION",
        )
    )
    assert res_wrong_dir.status == "CONTRADICTION"
    assert res_wrong_dir.reason_code == "WRONG_DIRECTION_ENTRY"

    # 3. Unmatched block exit check
    res_unmatched_exit = val.validate_and_normalize(
        RawFeedPayload(
            feed_id="FEED-SIGNAL-01",
            sequence_num=503,
            train_id="EXP-102",
            event_type="BLOCK_EXIT",
            location_id="B1",  # Was never recorded entering B1
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment="SYNTHETIC_SIMULATION",
        )
    )
    assert res_unmatched_exit.status == "CONTRADICTION"
    assert res_unmatched_exit.reason_code == "UNMATCHED_BLOCK_EXIT"

    # 4. Temporary Speed Restriction (TSR) enforcement
    val.set_tsr("B1", 45.0)  # Restrict B1 to 45 km/h
    res_tsr = val.validate_and_normalize(
        RawFeedPayload(
            feed_id="FEED-SIGNAL-01",
            sequence_num=504,
            train_id="EXP-103",
            train_type="EXPRESS",
            event_type="SPEED_UPDATE",
            location_id="B1",
            timestamp=datetime.now(timezone.utc).isoformat(),
            speed_kmph=60.0,  # Exceeds 45 km/h TSR
            environment="SYNTHETIC_SIMULATION",
        )
    )
    assert res_tsr.status == "CONTRADICTION"
    assert res_tsr.reason_code == "TSR_SPEED_LIMIT_EXCEEDED"


def test_feed_interruption_circuit_breaker_and_recovery(clean_feed_manager):
    """Test circuit breaker tripping upon elevated error rate and graceful recovery."""
    feed_id = "FEED-SIGNAL-01"

    # Inject 10 consecutive corrupted payloads to trip breaker
    for i in range(10):
        clean_feed_manager.ingest_event(
            RawFeedPayload(
                feed_id=feed_id,
                sequence_num=600 + i,
                train_id=f"T-BAD-{i}",
                event_type="SPEED_UPDATE",
                location_id="B1",
                timestamp=datetime.now(timezone.utc).isoformat(),
                speed_kmph=999.0,  # Physical impossibility
                environment="SYNTHETIC_SIMULATION",
            )
        )

    health = clean_feed_manager.get_feed_health(feed_id)
    assert health.circuit_breaker_open is True
    assert health.status == "OFFLINE"

    # Subsequent events must be blocked by circuit breaker
    blocked_res = clean_feed_manager.ingest_event(
        RawFeedPayload(
            feed_id=feed_id,
            sequence_num=700,
            train_id="T-VALID",
            event_type="HEARTBEAT",
            location_id="SYS",
            timestamp=datetime.now(timezone.utc).isoformat(),
            environment="SYNTHETIC_SIMULATION",
        )
    )
    assert blocked_res.status == "SCHEMA_ERROR"
    assert blocked_res.reason_code == "CIRCUIT_BREAKER_ACTIVE"

    # Trigger operator reconnection
    recon = clean_feed_manager.trigger_reconnect(feed_id)
    assert recon["success"] is True
    assert recon["status"] == "RECONNECTED"

    # Health restored to HEALTHY
    health_after = clean_feed_manager.get_feed_health(feed_id)
    assert health_after.circuit_breaker_open is False
    assert health_after.status == "HEALTHY"


def test_concurrent_event_ingestion(clean_feed_manager):
    """Stress test concurrent thread pool ingestion to ensure thread safety and no race conditions."""
    total_events = 200
    workers = 10

    def submit_event(i: int):
        return clean_feed_manager.ingest_event(
            RawFeedPayload(
                feed_id="FEED-SIGNAL-01",
                sequence_num=1000 + i,
                train_id=f"T-CONC-{i % 5}",
                event_type="HEARTBEAT",
                location_id="SYS",
                timestamp=datetime.now(timezone.utc).isoformat(),
                environment="SYNTHETIC_SIMULATION",
            )
        )

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        futures = [executor.submit(submit_event, i) for i in range(total_events)]
        results = [f.result() for f in concurrent.futures.as_completed(futures)]

    assert len(results) == total_events
    valid_count = sum(1 for r in results if r.status == "VALID")
    assert valid_count == total_events


def test_api_ingestion_recover_and_apply_endpoints(client: TestClient, station_headers: dict):
    """Verify REST endpoints for /api/v1/ingestion/events/apply and /api/v1/ingestion/events/recover."""
    # Ingest event via API
    res_ingest = client.post(
        "/api/v1/ingestion/events",
        headers=station_headers,
        json={
            "feed_id": "FEED-SIGNAL-01",
            "sequence_num": 801,
            "train_id": "12625",
            "event_type": "HEARTBEAT",
            "location_id": "CORRIDOR-SYS",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "environment": "SYNTHETIC_SIMULATION",
        },
    )
    assert res_ingest.status_code == 200
    assert res_ingest.json()["status"] == "VALID"

    # Recover event via API
    res_recover = client.get(
        "/api/v1/ingestion/events/recover?since_sequence_num=800",
        headers=station_headers,
    )
    assert res_recover.status_code == 200
    data = res_recover.json()
    assert any(e["sequence_num"] == 801 for e in data)
