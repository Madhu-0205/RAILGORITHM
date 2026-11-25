"""Comprehensive reliability, fault tolerance, and recovery verification tests for RAILGORITHM v2.4.

Tests:
1. Durable idempotency across simulated server restart.
2. Durable idempotency surviving in-memory LRU cache eviction.
3. Multi-feed deterministic replay ordering across feeds with independent sequences.
4. Database failure graceful degradation into in-memory mode without crashing.
5. Audit chain tail truncation detection via event count mismatch.
6. Audit chain head tampering detection via hash mismatch.
7. Rejection of stale recommendation approvals when state version has advanced.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.db import Base
from app.domain.state import initialise_state
from app.ingestion.event_processor import OperationalEventProcessor, EnvironmentIsolationError
from app.ingestion.models import NormalizedMovementEvent
from app.models import (
    AuditChainHead,
    AuditEvent,
    Decision,
    FeedCheckpointRecord,
    ProcessedEventRecord,
    Recommendation,
    Simulation,
    User,
)
from app.services.audit import append_audit, verify_audit_chain
from app.services.decision_service import submit_decision
from app.services.simulation_service import ServiceError


@pytest.fixture
def sqlite_db() -> Session:
    """Provides an isolated in-memory SQLite database session with all tables initialized."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    session = Session()
    yield session
    session.close()


def test_durable_idempotency_survives_restart(sqlite_db: Session):
    """Verify that an event processed by one processor instance is recognized as duplicate

    by a brand new processor instance (simulating cold server restart with empty RAM).
    """
    state = initialise_state("normal_traffic")
    event = NormalizedMovementEvent(
        event_id="EV-RESTART-001",
        feed_id="FEED-TEST-01",
        sequence_num=101,
        timestamp=datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 11, 25, 10, 0, 1, tzinfo=timezone.utc),
        train_id="12625",
        event_type="BLOCK_ENTRY",
        location_id="B2U",
        speed_kmph=80.0,
        environment="SYNTHETIC_SIMULATION",
    )

    # 1. First processor instance applies event
    proc1 = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    res1 = proc1.process_event(event, state, recalculate_conflicts=False, db=sqlite_db)

    assert res1["success"] is True
    assert res1["idempotent"] is False
    assert res1["state_modified"] is True
    version_after_first = state["version"]

    # Verify event and feed checkpoint were durably written to SQLite
    rec = sqlite_db.query(ProcessedEventRecord).filter_by(event_id="EV-RESTART-001").first()
    assert rec is not None
    assert rec.sequence_num == 101

    chk = sqlite_db.query(FeedCheckpointRecord).filter_by(feed_id="FEED-TEST-01").first()
    assert chk is not None
    assert chk.last_processed_sequence == 101

    # 2. Simulate cold restart: fresh processor instance with completely empty in-memory LRU
    proc2 = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    assert not proc2._processed_events  # RAM cache is empty

    res2 = proc2.process_event(event, state, recalculate_conflicts=False, db=sqlite_db)

    # Must be recognized as duplicate from DB without mutating state or incrementing version
    assert res2["success"] is True
    assert res2["idempotent"] is True
    assert state["version"] == version_after_first
    assert "already applied" in res2["message"]


def test_durable_idempotency_survives_lru_eviction(sqlite_db: Session):
    """Verify that when an event is evicted from the in-memory LRU cache,

    it is still recognized as duplicate via Tier 2 SQLite persistent storage.
    """
    state = initialise_state("normal_traffic")
    proc = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    proc._max_processed_cache = 2  # Artificially tiny cache to trigger eviction

    e1 = NormalizedMovementEvent(
        event_id="EV-LRU-1",
        feed_id="FEED-TEST-02",
        sequence_num=1,
        timestamp=datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 11, 25, 10, 0, 1, tzinfo=timezone.utc),
        train_id="12625",
        event_type="BLOCK_ENTRY",
        location_id="B2U",
        speed_kmph=75.0,
        environment="SYNTHETIC_SIMULATION",
    )
    e2 = NormalizedMovementEvent(
        event_id="EV-LRU-2",
        feed_id="FEED-TEST-02",
        sequence_num=2,
        timestamp=datetime(2026, 11, 25, 10, 1, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 11, 25, 10, 1, 1, tzinfo=timezone.utc),
        train_id="12625",
        event_type="SPEED_UPDATE",
        location_id="B2U",
        speed_kmph=85.0,
        environment="SYNTHETIC_SIMULATION",
    )
    e3 = NormalizedMovementEvent(
        event_id="EV-LRU-3",
        feed_id="FEED-TEST-02",
        sequence_num=3,
        timestamp=datetime(2026, 11, 25, 10, 2, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 11, 25, 10, 2, 1, tzinfo=timezone.utc),
        train_id="12625",
        event_type="BLOCK_EXIT",
        location_id="B2U",
        speed_kmph=85.0,
        environment="SYNTHETIC_SIMULATION",
    )

    proc.process_event(e1, state, recalculate_conflicts=False, db=sqlite_db)
    proc.process_event(e2, state, recalculate_conflicts=False, db=sqlite_db)
    proc.process_event(e3, state, recalculate_conflicts=False, db=sqlite_db)

    # e1 should have been evicted from RAM because capacity is 2
    assert "EV-LRU-1" not in proc._processed_events

    # Attempt to reapply evicted e1
    re_res = proc.process_event(e1, state, recalculate_conflicts=False, db=sqlite_db)
    assert re_res["idempotent"] is True
    assert "already applied" in re_res["message"]


def test_multi_feed_deterministic_replay_ordering():
    """Verify that multi-feed replay ordering handles independent sequence spaces

    by sorting deterministically on (timestamp, feed_id, sequence_num, event_id).
    """
    proc = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    initial_state = initialise_state("normal_traffic")

    # Construct events from Feed A and Feed B interleaved in real-world reception order
    base_time = datetime(2026, 11, 25, 8, 0, tzinfo=timezone.utc)
    ev_a1 = NormalizedMovementEvent(
        event_id="EV-A1", feed_id="FEED-A", sequence_num=1,
        timestamp=base_time + timedelta(minutes=5),
        ingested_at=base_time + timedelta(minutes=5, seconds=1),
        train_id="12625", event_type="SPEED_UPDATE", location_id="B2U", speed_kmph=70.0,
        environment="SYNTHETIC_SIMULATION",
    )
    ev_b1 = NormalizedMovementEvent(
        event_id="EV-B1", feed_id="FEED-B", sequence_num=1,
        timestamp=base_time + timedelta(minutes=2),
        ingested_at=base_time + timedelta(minutes=2, seconds=1),
        train_id="51831", event_type="SPEED_UPDATE", location_id="B2D", speed_kmph=60.0,
        environment="SYNTHETIC_SIMULATION",
    )
    ev_a2 = NormalizedMovementEvent(
        event_id="EV-A2", feed_id="FEED-A", sequence_num=2,
        timestamp=base_time + timedelta(minutes=8),
        ingested_at=base_time + timedelta(minutes=8, seconds=1),
        train_id="12625", event_type="SPEED_UPDATE", location_id="B2U", speed_kmph=80.0,
        environment="SYNTHETIC_SIMULATION",
    )
    ev_b2 = NormalizedMovementEvent(
        event_id="EV-B2", feed_id="FEED-B", sequence_num=2,
        timestamp=base_time + timedelta(minutes=4),
        ingested_at=base_time + timedelta(minutes=4, seconds=1),
        train_id="51831", event_type="SPEED_UPDATE", location_id="B2D", speed_kmph=75.0,
        environment="SYNTHETIC_SIMULATION",
    )

    events_list = [ev_a1, ev_b1, ev_a2, ev_b2]

    # Replay two different permutations on fresh processor instances (simulating independent node recoveries)
    proc1 = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    proc2 = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    state1 = proc1.replay_event_stream(events_list, initial_state)
    state2 = proc2.replay_event_stream(list(reversed(events_list)), initial_state)

    # State versions and event order in logs must be strictly identical
    assert state1["version"] == state2["version"]
    assert len(state1["events"]) == len(state2["events"])
    for logged1, logged2 in zip(state1["events"][-4:], state2["events"][-4:]):
        assert logged1["time_min"] == logged2["time_min"]
        assert logged1["train_id"] == logged2["train_id"]

    # Verify initial_state was not modified (deepcopy isolation)
    assert len(initial_state["events"]) == 1
    assert state1["version"] == initial_state["version"] + 4


def test_database_failure_graceful_degradation():
    """Verify that operational dispatching continues in degraded in-memory mode

    if SQLite raises an exception, ensuring dispatching never halts.
    """
    proc = OperationalEventProcessor(expected_environment="SYNTHETIC_SIMULATION")
    state = initialise_state("normal_traffic")

    mock_failing_db = MagicMock(spec=Session)
    mock_failing_db.query.side_effect = RuntimeError("Database disk I/O failure")
    mock_failing_db.merge.side_effect = RuntimeError("Database disk I/O failure")

    event = NormalizedMovementEvent(
        event_id="EV-DEGRADE-01",
        feed_id="FEED-FAIL-01",
        sequence_num=1,
        timestamp=datetime(2026, 11, 25, 10, 0, tzinfo=timezone.utc),
        ingested_at=datetime(2026, 11, 25, 10, 0, 1, tzinfo=timezone.utc),
        train_id="12625",
        event_type="SPEED_UPDATE",
        location_id="B2U",
        speed_kmph=88.0,
        environment="SYNTHETIC_SIMULATION",
    )

    # Must succeed without throwing RuntimeError
    res = proc.process_event(event, state, recalculate_conflicts=False, db=mock_failing_db)
    assert res["success"] is True
    assert res["durability"] == "DEGRADED_IN_MEMORY"
    assert proc.durability_mode == "DEGRADED_IN_MEMORY"


def test_audit_chain_tail_truncation_detection(sqlite_db: Session):
    """Verify that if an event is dropped from the end of the audit log,

    the chain head event_count mismatch detects the truncation.
    """
    head = AuditChainHead(id=1, head_hash="0" * 64, event_count=0)
    sqlite_db.add(head)
    sqlite_db.flush()

    append_audit(
        sqlite_db,
        event_type="SYSTEM_BOOT",
        actor="system",
        actor_role="SYSTEM",
        payload={"boot": True},
    )
    append_audit(
        sqlite_db,
        event_type="TELEMETRY_INGESTED",
        actor="feed.worker",
        actor_role="FEED_ADAPTER",
        payload={"count": 10},
    )
    e3 = append_audit(
        sqlite_db,
        event_type="DISPATCH_ADVISORY",
        actor="station.master",
        actor_role="STATION_MASTER",
        payload={"action": "HOLD"},
    )
    sqlite_db.commit()

    # Normal verification must pass
    verify_res = verify_audit_chain(sqlite_db)
    assert verify_res["valid"] is True
    assert verify_res["events"] == 3

    # Simulate truncation: directly delete the last event using SQL
    sqlite_db.execute(text("DELETE FROM audit_events WHERE id = :id"), {"id": e3.id})
    sqlite_db.commit()

    # Truncation verification must detect event_count mismatch
    trunc_res = verify_audit_chain(sqlite_db)
    assert trunc_res["valid"] is False
    assert "deleted from the tail" in trunc_res["detail"] or "does not match" in trunc_res["detail"]


def test_audit_chain_head_tampering_detection(sqlite_db: Session):
    """Verify that if the chain head hash is modified, verification fails."""
    head = AuditChainHead(id=1, head_hash="0" * 64, event_count=0)
    sqlite_db.add(head)
    sqlite_db.flush()

    append_audit(
        sqlite_db,
        event_type="SYSTEM_INIT",
        actor="admin",
        actor_role="SECTION_MASTER",
        payload={"init": True},
    )
    sqlite_db.commit()

    assert verify_audit_chain(sqlite_db)["valid"] is True

    # Tamper with the chain head hash
    head_record = sqlite_db.query(AuditChainHead).filter_by(id=1).first()
    head_record.head_hash = "deadbeef" * 8
    sqlite_db.commit()

    tamper_res = verify_audit_chain(sqlite_db)
    assert tamper_res["valid"] is False
    assert "deleted from the tail" in tamper_res["detail"] or "does not match" in tamper_res["detail"]


def test_stale_recommendation_approval_rejection(sqlite_db: Session):
    """Verify that approving a recommendation whose state version does not match

    the simulation's current state version is strictly rejected.
    """
    user = User(
        id="usr-sec-01",
        username="section.master",
        password_hash="fakehash",
        role="SECTION_MASTER",
        display_name="Section Controller",
    )
    sim = Simulation(
        id="sim-stale-test",
        name="Stale Test Corridor",
        scenario_key="normal_traffic",
        status="RUNNING",
        sim_time_min=480,
        state_version=1,
        seed=42,
        label="SYNTHETIC",
        created_by="section.master",
        state=initialise_state("normal_traffic"),
    )
    sqlite_db.add(user)
    sqlite_db.add(sim)
    sqlite_db.flush()

    # Add recommendation pegged to state_version 1
    rec = Recommendation(
        id="rec-stale-01",
        simulation_id=sim.id,
        state_version=1,
        status="PENDING",
        evidence_status="SUFFICIENT",
        model_version="ppo-v2.3",
        optimizer_version="cpsat-v2.3",
        created_by="section.master",
        payload={"recommended": {"label": "Proceed on Main Line", "action": "NO_OP"}, "affected_stations": []},
    )
    sqlite_db.add(rec)
    sqlite_db.commit()

    # Simulate operational state advance (state version increments to 2)
    sim.state_version = 2
    sqlite_db.commit()

    # Attempt to approve stale recommendation
    with pytest.raises(ServiceError) as exc_info:
        submit_decision(
            sqlite_db,
            user=user,
            simulation=sim,
            recommendation=rec,
            action="APPROVE",
            rationale="Approved after delay",
            modifications=None,
            confirm_apply=True,
        )

    assert "Recommendation is stale" in str(exc_info.value)

    # Verify recommendation was marked STALE
    sqlite_db.refresh(rec)
    assert rec.status == "STALE"
