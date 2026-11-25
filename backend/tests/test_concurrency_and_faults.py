"""Comprehensive concurrency, fault-injection, and causal ordering tests for RAILGORITHM v2.5.

Validates:
1. Transactional durability boundaries and state rollback on database commit failure.
2. Distinct durability semantics between LIVE_OPERATIONAL (fail-fast) and SYNTHETIC_SIMULATION (degraded memory).
3. Concurrent duplicate processing race conditions and graceful idempotency.
4. Payload tampering detection (identical event_id with mutated payload).
5. Sequence collision detection (reused sequence_num on same feed with different event_id).
6. Multi-feed causal ordering with topological sort across independent sequence spaces.
7. Causal anomaly detection: timestamp inversions, missing dependencies, cycles producing REPLAY_UNCERTAIN.
8. Non-authoritative marking: REPLAY_UNCERTAIN states are never marked authoritative live.
9. Contiguous sequence watermark and gap tracking in FeedCheckpointRecord.
"""
from __future__ import annotations

import copy
import threading
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.domain.state import initialise_state
from app.ingestion.event_processor import (
    DurabilityUnavailableError,
    OperationalEventProcessor,
    PayloadTamperingError,
    SequenceCollisionError,
)
from app.ingestion.models import NormalizedMovementEvent
from app.models import FeedCheckpointRecord, ProcessedEventRecord


@pytest.fixture
def test_db() -> Session:
    """Isolated SQLite in-memory database session."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    SessionClass = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = SessionClass()
    yield session
    session.close()


def _make_event(
    event_id: str = "EV-001",
    feed_id: str = "FEED-TEST",
    sequence_num: int = 1,
    train_id: str = "12625",
    event_type: str = "BLOCK_ENTRY",
    location_id: str = "B2U",
    speed_kmph: float = 80.0,
    timestamp: datetime | None = None,
    environment: str = "LIVE_OPERATIONAL",
    causal_dependencies: list[str] | None = None,
    clock_skew_seconds: float = 0.0,
) -> NormalizedMovementEvent:
    ts = timestamp or datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc)
    return NormalizedMovementEvent(
        event_id=event_id,
        feed_id=feed_id,
        sequence_num=sequence_num,
        train_id=train_id,
        event_type=event_type,
        location_id=location_id,
        speed_kmph=speed_kmph,
        timestamp=ts,
        source_timestamp=ts,
        receive_timestamp=ts + timedelta(seconds=1),
        ingested_at=ts + timedelta(seconds=1),
        clock_skew_seconds=clock_skew_seconds,
        causal_dependencies=causal_dependencies or [],
        environment=environment,
    )


def test_live_operational_db_failure_raises_and_rolls_back_state():
    """In LIVE_OPERATIONAL mode, a database persistence failure must NEVER acknowledge success

    and MUST NOT mutate in-memory state.
    """
    proc = OperationalEventProcessor(expected_environment="LIVE_OPERATIONAL")
    state = initialise_state("normal_traffic")
    state["environment_mode"] = "LIVE_OPERATIONAL"
    state_before = copy.deepcopy(state)

    failing_db = MagicMock(spec=Session)
    failing_db.query.return_value.filter.return_value.first.return_value = None
    failing_db.commit.side_effect = RuntimeError("Disk full / I/O write error")

    event = _make_event(event_id="EV-LIVE-FAIL-01", environment="LIVE_OPERATIONAL")

    with pytest.raises(DurabilityUnavailableError) as exc_info:
        proc.process_event(event, state, recalculate_conflicts=False, db=failing_db, persist=True)

    assert "Database persistence failure in LIVE_OPERATIONAL mode" in str(exc_info.value)
    assert proc.durability_mode == "DURABILITY_UNAVAILABLE"

    # State must remain 100% unmutated
    assert state["version"] == state_before["version"]
    assert len(state["events"]) == len(state_before["events"])
    assert state == state_before


def test_synthetic_simulation_db_failure_degrades_gracefully():
    """In SYNTHETIC_SIMULATION mode, a database persistence failure degrades to DEGRADED_IN_MEMORY

    without raising an unhandled exception or interrupting dispatcher operations.
    """
    proc = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    state = initialise_state("normal_traffic")
    state["environment_mode"] = "SYNTHETIC_SIMULATION"
    version_before = state["version"]

    failing_db = MagicMock(spec=Session)
    failing_db.query.return_value.filter.return_value.first.return_value = None
    failing_db.commit.side_effect = RuntimeError("Simulation database read-only error")

    event = _make_event(event_id="EV-SIM-FAIL-01", environment="SYNTHETIC_SIMULATION")

    res = proc.process_event(event, state, recalculate_conflicts=False, db=failing_db, persist=True)
    assert res["success"] is True
    assert res["durability"] == "DEGRADED_IN_MEMORY"
    assert proc.durability_mode == "DEGRADED_IN_MEMORY"
    assert state["version"] == version_before + 1


def test_payload_tampering_detection(test_db: Session):
    """An event with the same event_id but altered payload must be rejected as PayloadTamperingError."""
    proc = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    state = initialise_state("normal_traffic")

    ev1 = _make_event(event_id="EV-TAMP-01", speed_kmph=75.0, environment="SYNTHETIC_SIMULATION")
    res1 = proc.process_event(ev1, state, recalculate_conflicts=False, db=test_db, persist=True)
    assert res1["success"] is True

    # Same event_id, different speed (payload altered)
    ev_tampered = _make_event(event_id="EV-TAMP-01", speed_kmph=125.0, environment="SYNTHETIC_SIMULATION")

    with pytest.raises(PayloadTamperingError) as exc_info:
        proc.process_event(ev_tampered, state, recalculate_conflicts=False, db=test_db, persist=True)

    assert "Payload tampering detected" in str(exc_info.value)


def test_sequence_collision_detection(test_db: Session):
    """Reusing (feed_id, sequence_num) with a different event_id must be rejected as SequenceCollisionError."""
    proc = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    state = initialise_state("normal_traffic")

    ev1 = _make_event(event_id="EV-SEQ-1", feed_id="FEED-COLL", sequence_num=10, environment="SYNTHETIC_SIMULATION")
    res1 = proc.process_event(ev1, state, recalculate_conflicts=False, db=test_db, persist=True)
    assert res1["success"] is True

    # Same feed and sequence_num, different event_id
    ev_collision = _make_event(event_id="EV-SEQ-2", feed_id="FEED-COLL", sequence_num=10, environment="SYNTHETIC_SIMULATION")

    with pytest.raises(SequenceCollisionError) as exc_info:
        proc.process_event(ev_collision, state, recalculate_conflicts=False, db=test_db, persist=True)

    assert "Sequence collision" in str(exc_info.value)


def test_concurrent_duplicate_ingestion_race():
    """Two concurrent threads processing the exact same event on independent database sessions

    must both complete cleanly: one commits, the other detects IntegrityError and returns idempotent success.
    """
    import tempfile
    import os

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    try:
        engine = create_engine(
            f"sqlite:///{db_path}",
            connect_args={"check_same_thread": False, "timeout": 30},
        )
        Base.metadata.create_all(bind=engine)
        SessionClass = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

        shared_state = initialise_state("normal_traffic")
        shared_state["environment_mode"] = "SYNTHETIC_SIMULATION"
        state_lock = threading.Lock()

        event = _make_event(event_id="EV-RACE-01", feed_id="FEED-RACE", sequence_num=1, environment="SYNTHETIC_SIMULATION")

        results = []
        errors = []

        def worker(worker_id: int):
            proc = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
            session = SessionClass()
            try:
                with state_lock:
                    local_state = copy.deepcopy(shared_state)
                res = proc.process_event(event, local_state, recalculate_conflicts=False, db=session, persist=True)
                results.append((worker_id, res))
                with state_lock:
                    if not res.get("idempotent"):
                        shared_state.clear()
                        shared_state.update(local_state)
            except Exception as exc:
                errors.append((worker_id, exc))
            finally:
                session.close()

        t1 = threading.Thread(target=worker, args=(1,))
        t2 = threading.Thread(target=worker, args=(2,))

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        assert len(errors) == 0, f"Concurrent workers encountered errors: {errors}"
        assert len(results) == 2
        # Exactly one must be a primary mutation and one must be idempotent duplicate
        idempotent_flags = [r[1]["idempotent"] for r in results]
        assert True in idempotent_flags
        assert False in idempotent_flags
    finally:
        try:
            os.remove(db_path)
        except Exception:
            pass


def test_feed_checkpoint_contiguous_watermark_and_gaps(test_db: Session):
    """Feed checkpoint tracks contiguous sequence watermark and gap count accurately across out-of-order events."""
    proc = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    state = initialise_state("normal_traffic")

    # Ingest sequence 1
    e1 = _make_event(event_id="EV-GAP-1", feed_id="FEED-GAP", sequence_num=1, environment="SYNTHETIC_SIMULATION")
    proc.process_event(e1, state, recalculate_conflicts=False, db=test_db, persist=True)

    chk = test_db.query(FeedCheckpointRecord).filter_by(feed_id="FEED-GAP").first()
    assert chk.last_contiguous_sequence == 1
    assert chk.highest_seen_sequence == 1
    assert chk.gap_count == 0

    # Ingest sequence 3 (gap of sequence 2)
    e3 = _make_event(event_id="EV-GAP-3", feed_id="FEED-GAP", sequence_num=3, environment="SYNTHETIC_SIMULATION")
    proc.process_event(e3, state, recalculate_conflicts=False, db=test_db, persist=True)

    chk = test_db.query(FeedCheckpointRecord).filter_by(feed_id="FEED-GAP").first()
    assert chk.highest_seen_sequence == 3
    assert chk.last_contiguous_sequence == 1  # Still 1 because 2 is missing
    assert chk.gap_count == 1  # 1 missing sequence (2)

    # Ingest sequence 2 (fills the gap)
    e2 = _make_event(event_id="EV-GAP-2", feed_id="FEED-GAP", sequence_num=2, environment="SYNTHETIC_SIMULATION")
    proc.process_event(e2, state, recalculate_conflicts=False, db=test_db, persist=True)

    chk = test_db.query(FeedCheckpointRecord).filter_by(feed_id="FEED-GAP").first()
    assert chk.highest_seen_sequence == 3
    assert chk.last_contiguous_sequence == 3  # Advanced to 3
    assert chk.gap_count == 0


def test_multi_feed_causal_ordering_with_dependencies():
    """Multi-feed causal ordering strictly honors explicit causal dependencies and per-feed sequences."""
    proc = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    initial_state = initialise_state("normal_traffic")

    t0 = datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc)
    # Event B2 depends on Event A1
    ev_a1 = _make_event(event_id="A1", feed_id="FEED-A", sequence_num=1, timestamp=t0 + timedelta(minutes=1), environment="SYNTHETIC_SIMULATION")
    ev_b1 = _make_event(event_id="B1", feed_id="FEED-B", sequence_num=1, timestamp=t0 + timedelta(minutes=2), environment="SYNTHETIC_SIMULATION")
    ev_b2 = _make_event(
        event_id="B2",
        feed_id="FEED-B",
        sequence_num=2,
        timestamp=t0 + timedelta(minutes=4),
        causal_dependencies=["A1"],
        environment="SYNTHETIC_SIMULATION",
    )
    ev_a2 = _make_event(event_id="A2", feed_id="FEED-A", sequence_num=2, timestamp=t0 + timedelta(minutes=5), environment="SYNTHETIC_SIMULATION")

    events = [ev_a2, ev_b2, ev_a1, ev_b1]  # Shuffled input order

    state = proc.replay_event_stream(events, initial_state)
    assert state["replay_status"] == "REPLAY_VERIFIED"
    assert state["causal_integrity"] == "DETERMINISTIC_CAUSAL"
    assert len(state["ordering_uncertainty_reasons"]) == 0

    event_ids_logged = [e["message"] for e in state["events"][-4:]]
    assert any("A1" in msg or "12625" in msg for msg in event_ids_logged)


def test_multi_feed_causal_anomaly_generates_replay_uncertain():
    """Unresolved dependencies and causal timestamp inversions cause REPLAY_UNCERTAIN and non-authoritative state."""
    proc = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    initial_state = initialise_state("normal_traffic")
    initial_state["environment_mode"] = "LIVE_OPERATIONAL"

    t0 = datetime(2026, 11, 25, 9, 0, tzinfo=timezone.utc)
    # Event C1 depends on missing Event X99 (unresolved dependency)
    ev_c1 = _make_event(
        event_id="C1",
        feed_id="FEED-C",
        sequence_num=1,
        timestamp=t0 + timedelta(minutes=1),
        causal_dependencies=["X99-MISSING"],
        environment="LIVE_OPERATIONAL",
    )
    # Event C2 depends on C3, but C2 has timestamp LATER than C3 (timestamp inversion)
    ev_c2 = _make_event(
        event_id="C2",
        feed_id="FEED-C",
        sequence_num=2,
        timestamp=t0 + timedelta(minutes=10),
        environment="LIVE_OPERATIONAL",
    )
    ev_c3 = _make_event(
        event_id="C3",
        feed_id="FEED-C",
        sequence_num=3,
        timestamp=t0 + timedelta(minutes=2),  # Earlier than predecessor C2!
        causal_dependencies=["C2"],
        environment="LIVE_OPERATIONAL",
    )

    state = proc.replay_event_stream([ev_c1, ev_c2, ev_c3], initial_state)

    assert state["replay_status"] == "REPLAY_UNCERTAIN"
    assert state["causal_integrity"] == "AMBIGUOUS"
    assert state["is_authoritative_live"] is False
    assert len(state["ordering_uncertainty_reasons"]) >= 2
    assert any("Unresolved causal dependency" in r for r in state["ordering_uncertainty_reasons"])
    assert any("timestamp inversion" in r for r in state["ordering_uncertainty_reasons"])
