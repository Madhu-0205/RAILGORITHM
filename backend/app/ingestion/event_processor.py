"""Event processor: applies validated movement events to operational state idempotently.

Handles real-time operational state transitions, delay calculations, conflict engine
triggering, durable two-tier idempotency (memory LRU + SQLite persistent store),
strict simulation vs live environment isolation, payload tampering detection,
sequence collision guards, and multi-feed causal replay ordering.
"""
from __future__ import annotations

import copy
import hashlib
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..domain.conflicts import detect_conflicts
from ..domain.network import Network
from ..models import FeedCheckpointRecord, ProcessedEventRecord
from .models import EnvironmentMode, NormalizedMovementEvent


class EnvironmentIsolationError(ValueError):
    """Raised when an event from one environment attempts to modify state of another."""


class DurabilityUnavailableError(RuntimeError):
    """Raised in LIVE_OPERATIONAL mode when database persistence fails."""


class PayloadTamperingError(ValueError):
    """Raised when an event arrives with an existing event_id but different payload hash."""


class SequenceCollisionError(ValueError):
    """Raised when an event arrives with an existing (feed_id, sequence_num) but different event_id."""


def compute_payload_hash(event: NormalizedMovementEvent) -> str:
    """Computes a deterministic canonical payload hash for an event."""
    parts = [
        str(event.feed_id),
        str(event.sequence_num),
        str(event.event_id),
        str(event.train_id),
        str(event.event_type),
        str(event.location_id),
        event.timestamp.isoformat(),
        f"{event.speed_kmph:.2f}" if event.speed_kmph is not None else "NONE",
        f"{event.delay_min:.2f}" if event.delay_min is not None else "NONE",
        str(event.direction) if event.direction else "NONE",
        str(event.environment),
    ]
    return hashlib.sha256(":".join(parts).encode("utf-8")).hexdigest()


class OperationalEventProcessor:
    """Processes validated movement events into operational simulation and corridor states."""

    def __init__(self, expected_environment: EnvironmentMode = "SYNTHETIC_SIMULATION"):
        self.expected_environment = expected_environment
        # Tier 1 fast in-memory LRU cache: event_id -> dict with hash, feed_id, sequence_num, time
        self._processed_events: OrderedDict[str, dict[str, Any]] = OrderedDict()
        self._max_processed_cache = 10000
        self.durability_mode: str = "DURABLE_SQLITE"

    def _cache_processed(
        self,
        event_id: str,
        payload_hash: str | None = None,
        feed_id: str | None = None,
        sequence_num: int | None = None,
    ) -> None:
        self._processed_events[event_id] = {
            "hash": payload_hash,
            "feed_id": feed_id,
            "sequence_num": sequence_num,
            "time": time.time(),
        }
        if len(self._processed_events) > self._max_processed_cache:
            self._processed_events.popitem(last=False)

    def is_processed(self, event_id: str, db: Session | None = None, check_persistent: bool = True) -> bool:
        """Check whether an event has already been processed using 2-tier idempotency.
        
        Tier 1: High-throughput in-memory LRU cache.
        Tier 2: Persistent database records for survivability across server restarts & evictions.
        """
        # Tier 1: Check in-memory LRU cache
        if event_id in self._processed_events:
            return True

        if not check_persistent:
            return False

        # Tier 2: Check persistent storage
        try:
            if db is not None:
                rec = db.query(ProcessedEventRecord).filter(ProcessedEventRecord.event_id == event_id).first()
                if rec:
                    self._cache_processed(event_id, rec.payload_hash, rec.feed_id, rec.sequence_num)
                    return True
            else:
                with SessionLocal() as session:
                    rec = session.query(ProcessedEventRecord).filter(ProcessedEventRecord.event_id == event_id).first()
                    if rec:
                        self._cache_processed(event_id, rec.payload_hash, rec.feed_id, rec.sequence_num)
                        return True
        except Exception:
            if db is not None:
                try:
                    db.rollback()
                except Exception:
                    pass
            # Fallback to in-memory mode if DB is unavailable or degraded
            self.durability_mode = "DEGRADED_IN_MEMORY"

        return False

    def _mark_processed(
        self,
        event: NormalizedMovementEvent,
        state_version: int,
        db: Session | None = None,
        persist: bool = True,
    ) -> None:
        """Mark an event as processed in persistent SQLite store."""
        hash_val = event.payload_hash or compute_payload_hash(event)
        self._cache_processed(event.event_id, hash_val, event.feed_id, event.sequence_num)

        if not persist:
            return

        def _persist(session: Session) -> None:
            rec = ProcessedEventRecord(
                feed_id=event.feed_id,
                sequence_num=event.sequence_num,
                event_id=event.event_id,
                payload_hash=hash_val,
                state_version=state_version,
            )
            session.add(rec)
            session.flush()

            chk = session.query(FeedCheckpointRecord).filter(FeedCheckpointRecord.feed_id == event.feed_id).first()
            if not chk:
                chk = FeedCheckpointRecord(
                    feed_id=event.feed_id,
                    last_processed_sequence=event.sequence_num,
                    last_contiguous_sequence=event.sequence_num if event.sequence_num == 1 else 0,
                    highest_seen_sequence=event.sequence_num,
                    gap_count=0 if event.sequence_num == 1 else max(0, event.sequence_num - 1),
                    last_processed_timestamp=event.timestamp,
                    last_event_id=event.event_id,
                )
                session.add(chk)
            else:
                chk.highest_seen_sequence = max(chk.highest_seen_sequence, event.sequence_num)
                if event.sequence_num > chk.last_processed_sequence:
                    chk.last_processed_sequence = event.sequence_num
                chk.last_processed_timestamp = event.timestamp
                chk.last_event_id = event.event_id

                # Calculate contiguous watermark
                processed_seqs = {
                    s[0]
                    for s in session.query(ProcessedEventRecord.sequence_num)
                    .filter(ProcessedEventRecord.feed_id == event.feed_id)
                    .all()
                }
                curr = chk.last_contiguous_sequence
                while (curr + 1) in processed_seqs:
                    curr += 1
                chk.last_contiguous_sequence = curr
                chk.gap_count = max(0, chk.highest_seen_sequence - len(processed_seqs))

            session.commit()

        try:
            if db is not None:
                _persist(db)
            else:
                with SessionLocal() as session:
                    _persist(session)
            self.durability_mode = "DURABLE_SQLITE"
        except Exception:
            if db is not None:
                try:
                    db.rollback()
                except Exception:
                    pass
            self.durability_mode = "DEGRADED_IN_MEMORY"

    def process_event(
        self,
        event: NormalizedMovementEvent,
        state: dict[str, Any],
        recalculate_conflicts: bool = True,
        db: Session | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        """Apply a normalized movement event to an operational state dictionary.

        Guarantees:
        - Strict environment isolation (rejects cross-environment events).
        - Payload tampering detection (rejects same event_id with altered payload).
        - Sequence collision protection (rejects reuse of sequence_num on same feed).
        - Atomic state mutation: state is only permanently updated if durability commits.
        - In LIVE_OPERATIONAL mode, DB failure raises DurabilityUnavailableError without mutating state.
        - Transparent durability mode reporting.
        """
        # 1. Environment Isolation Check
        state_env = state.get("environment_mode", "SYNTHETIC_SIMULATION")
        if event.environment != state_env:
            raise EnvironmentIsolationError(
                f"Cross-environment contamination blocked: Event environment '{event.environment}' "
                f"cannot update state with environment '{state_env}'."
            )

        # 2. Canonical Payload Hash
        hash_val = event.payload_hash or compute_payload_hash(event)
        event.payload_hash = hash_val

        # 3. Tier 1 In-Memory Cache Check
        if event.event_id in self._processed_events:
            cached = self._processed_events[event.event_id]
            if isinstance(cached, dict) and cached.get("hash") and cached["hash"] != hash_val:
                raise PayloadTamperingError(
                    f"Payload tampering detected for event '{event.event_id}'. "
                    f"Cached hash: {cached['hash']}, incoming hash: {hash_val}."
                )
            return {
                "success": True,
                "idempotent": True,
                "event_id": event.event_id,
                "state_version": state.get("version", 1),
                "durability": self.durability_mode if persist else "IN_MEMORY_REPLAY",
                "message": f"Event '{event.event_id}' already applied; state unchanged.",
            }

        # 4. Tier 2 Persistent Database Idempotency & Conflict Check
        if persist:
            def _check_db(session: Session) -> tuple[bool, dict[str, Any] | None]:
                existing_event = session.query(ProcessedEventRecord).filter(
                    ProcessedEventRecord.event_id == event.event_id
                ).first()
                if existing_event:
                    if existing_event.payload_hash and existing_event.payload_hash != hash_val:
                        raise PayloadTamperingError(
                            f"Payload tampering detected for event '{event.event_id}'. "
                            f"Existing persisted hash: {existing_event.payload_hash}, incoming hash: {hash_val}."
                        )
                    self._cache_processed(event.event_id, hash_val, event.feed_id, event.sequence_num)
                    return True, {
                        "success": True,
                        "idempotent": True,
                        "event_id": event.event_id,
                        "state_version": state.get("version", 1),
                        "durability": self.durability_mode,
                        "message": f"Event '{event.event_id}' already applied in persistent store; state unchanged.",
                    }

                seq_collision = session.query(ProcessedEventRecord).filter(
                    ProcessedEventRecord.feed_id == event.feed_id,
                    ProcessedEventRecord.sequence_num == event.sequence_num,
                ).first()
                if seq_collision and seq_collision.event_id != event.event_id:
                    raise SequenceCollisionError(
                        f"Sequence collision on feed '{event.feed_id}': sequence {event.sequence_num} already committed "
                        f"for event '{seq_collision.event_id}', received conflicting event '{event.event_id}'."
                    )
                return False, None

            try:
                if db is not None:
                    is_dup, dup_res = _check_db(db)
                else:
                    with SessionLocal() as session:
                        is_dup, dup_res = _check_db(session)
                if is_dup and dup_res is not None:
                    return dup_res
            except (PayloadTamperingError, SequenceCollisionError):
                raise
            except Exception as exc:
                if event.environment == "LIVE_OPERATIONAL":
                    self.durability_mode = "DURABILITY_UNAVAILABLE"
                    raise DurabilityUnavailableError(
                        f"Database check failed in LIVE_OPERATIONAL mode for event '{event.event_id}': {exc}. "
                        "Cannot verify event idempotency; processing rejected."
                    )
                else:
                    self.durability_mode = "DEGRADED_IN_MEMORY"

        # 5. Atomic State Mutation on deepcopy working state
        working_state = copy.deepcopy(state)
        train_id = event.train_id
        train = next((t for t in working_state.get("trains", []) if t["id"] == train_id), None)
        
        event_time_min = event.timestamp.hour * 60 + event.timestamp.minute
        ev_type = event.event_type.upper()
        state_modified = False

        if train:
            train["last_reported_speed_kmph"] = event.speed_kmph
            train["last_telemetry_time"] = event.timestamp.isoformat()

            if ev_type in {"BLOCK_ENTRY", "PLATFORM_OCCUPATION"}:
                train["current_location"] = event.location_id
                train["location"] = event.location_id
                if "block_occupancy" not in working_state:
                    working_state["block_occupancy"] = {}
                working_state["block_occupancy"][event.location_id] = train_id
                state_modified = True

            elif ev_type in {"BLOCK_EXIT", "PLATFORM_VACATION"}:
                if working_state.get("block_occupancy", {}).get(event.location_id) == train_id:
                    working_state["block_occupancy"].pop(event.location_id, None)
                    state_modified = True

            elif ev_type == "STATION_ARRIVAL":
                train["current_location"] = event.location_id
                train["location"] = event.location_id
                train["actual_arrival_min"] = event_time_min
                sched_arr = train.get("scheduled_arrival_min")
                if sched_arr is not None:
                    train["delay_min"] = max(0, event_time_min - sched_arr)
                elif event.delay_min is not None:
                    train["delay_min"] = event.delay_min
                state_modified = True

            elif ev_type == "STATION_DEPARTURE":
                train["actual_departure_min"] = event_time_min
                sched_dep = train.get("scheduled_departure_min")
                if sched_dep is not None:
                    train["delay_min"] = max(0, event_time_min - sched_dep)
                elif event.delay_min is not None:
                    train["delay_min"] = event.delay_min
                state_modified = True

            elif ev_type == "SPEED_UPDATE":
                if event.speed_kmph is not None:
                    train["speed_kmph"] = event.speed_kmph
                    state_modified = True

        if "events" in working_state:
            working_state["events"].append({
                "time_min": event_time_min,
                "time": f"{event_time_min // 60:02d}:{event_time_min % 60:02d}",
                "type": ev_type,
                "message": f"Telemetry event {ev_type} for train {train_id} at {event.location_id}",
                "train_id": train_id,
                "location_id": event.location_id,
                "feed_id": event.feed_id,
                "sequence_num": event.sequence_num,
                "environment": event.environment,
            })
            if len(working_state["events"]) > 1000:
                working_state["events"] = working_state["events"][-1000:]

        conflicts = working_state.get("conflicts", [])
        if state_modified:
            working_state["version"] = working_state.get("version", 1) + 1
            if recalculate_conflicts:
                try:
                    conflicts = detect_conflicts(working_state)
                    working_state["conflicts"] = conflicts
                except Exception:
                    pass

        # 6. Transactional Persistence and Durability Commit
        if persist:
            def _persist_commit(session: Session) -> None:
                rec = ProcessedEventRecord(
                    feed_id=event.feed_id,
                    sequence_num=event.sequence_num,
                    event_id=event.event_id,
                    payload_hash=hash_val,
                    state_version=working_state.get("version", 1),
                )
                session.add(rec)
                session.flush()

                chk = session.query(FeedCheckpointRecord).filter(
                    FeedCheckpointRecord.feed_id == event.feed_id
                ).first()
                if not chk:
                    chk = FeedCheckpointRecord(
                        feed_id=event.feed_id,
                        last_processed_sequence=event.sequence_num,
                        last_contiguous_sequence=event.sequence_num if event.sequence_num == 1 else 0,
                        highest_seen_sequence=event.sequence_num,
                        gap_count=0 if event.sequence_num == 1 else max(0, event.sequence_num - 1),
                        last_processed_timestamp=event.timestamp,
                        last_event_id=event.event_id,
                    )
                    session.add(chk)
                else:
                    chk.highest_seen_sequence = max(chk.highest_seen_sequence, event.sequence_num)
                    if event.sequence_num > chk.last_processed_sequence:
                        chk.last_processed_sequence = event.sequence_num
                    chk.last_processed_timestamp = event.timestamp
                    chk.last_event_id = event.event_id

                    processed_seqs = {
                        s[0]
                        for s in session.query(ProcessedEventRecord.sequence_num)
                        .filter(ProcessedEventRecord.feed_id == event.feed_id)
                        .all()
                    }
                    curr = chk.last_contiguous_sequence
                    while (curr + 1) in processed_seqs:
                        curr += 1
                    chk.last_contiguous_sequence = curr
                    chk.gap_count = max(0, chk.highest_seen_sequence - len(processed_seqs))

                session.commit()

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    if db is not None:
                        _persist_commit(db)
                    else:
                        with SessionLocal() as session:
                            _persist_commit(session)
                    self.durability_mode = "DURABLE_SQLITE"
                    break
                except IntegrityError as exc:
                    if db is not None:
                        try:
                            db.rollback()
                        except Exception:
                            pass
                    # Check for concurrent race or sequence collision
                    try:
                        check_session = db if db is not None else SessionLocal()
                        try:
                            existing = check_session.query(ProcessedEventRecord).filter(
                                ProcessedEventRecord.event_id == event.event_id
                            ).first()
                            if existing:
                                if existing.payload_hash and existing.payload_hash != hash_val:
                                    raise PayloadTamperingError(
                                        f"Payload tampering detected during concurrent insert of event '{event.event_id}'."
                                    )
                                self._cache_processed(event.event_id, hash_val, event.feed_id, event.sequence_num)
                                return {
                                    "success": True,
                                    "idempotent": True,
                                    "event_id": event.event_id,
                                    "state_version": state.get("version", 1),
                                    "durability": "DURABLE_SQLITE",
                                    "message": f"Concurrent duplicate event '{event.event_id}' safely deduplicated via database constraint.",
                                }
                            coll = check_session.query(ProcessedEventRecord).filter(
                                ProcessedEventRecord.feed_id == event.feed_id,
                                ProcessedEventRecord.sequence_num == event.sequence_num,
                            ).first()
                            if coll:
                                raise SequenceCollisionError(
                                    f"Sequence collision on feed '{event.feed_id}': sequence {event.sequence_num} already committed by '{coll.event_id}'."
                                )
                        finally:
                            if db is None:
                                check_session.close()
                    except (PayloadTamperingError, SequenceCollisionError):
                        raise
                    except Exception:
                        pass
                    if event.environment == "LIVE_OPERATIONAL":
                        self.durability_mode = "DURABILITY_UNAVAILABLE"
                        raise DurabilityUnavailableError(
                            f"Database persistence failure in LIVE_OPERATIONAL mode for event '{event.event_id}': {exc}. "
                            "State mutation rolled back; event cannot be acknowledged."
                        )
                    self.durability_mode = "DEGRADED_IN_MEMORY"
                    break
                except Exception as exc:
                    if db is not None:
                        try:
                            db.rollback()
                        except Exception:
                            pass
                    # If database locked error and retries remain, back off briefly
                    if "locked" in str(exc).lower() and attempt < max_retries - 1:
                        time.sleep(0.05 * (attempt + 1))
                        # Check if event was committed while waiting
                        check_session = db if db is not None else SessionLocal()
                        try:
                            existing = check_session.query(ProcessedEventRecord).filter(
                                ProcessedEventRecord.event_id == event.event_id
                            ).first()
                            if existing:
                                self._cache_processed(event.event_id, hash_val, event.feed_id, event.sequence_num)
                                return {
                                    "success": True,
                                    "idempotent": True,
                                    "event_id": event.event_id,
                                    "state_version": state.get("version", 1),
                                    "durability": "DURABLE_SQLITE",
                                    "message": f"Concurrent duplicate event '{event.event_id}' safely deduplicated.",
                                }
                        finally:
                            if db is None:
                                check_session.close()
                        continue

                    if event.environment == "LIVE_OPERATIONAL":
                        self.durability_mode = "DURABILITY_UNAVAILABLE"
                        raise DurabilityUnavailableError(
                            f"Database persistence failure in LIVE_OPERATIONAL mode for event '{event.event_id}': {exc}. "
                            "State mutation rolled back; event cannot be acknowledged."
                        )
                    self.durability_mode = "DEGRADED_IN_MEMORY"
                    break

        # 7. Apply State Mutation on Successful Transaction
        state.clear()
        state.update(working_state)
        self._cache_processed(event.event_id, hash_val, event.feed_id, event.sequence_num)

        return {
            "success": True,
            "idempotent": False,
            "event_id": event.event_id,
            "state_version": state.get("version", 1),
            "state_modified": state_modified,
            "conflicts_detected": len(conflicts),
            "durability": self.durability_mode if persist else "IN_MEMORY_REPLAY",
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }

    def replay_event_stream(
        self,
        events: list[NormalizedMovementEvent],
        initial_state: dict[str, Any],
        persist_events: bool = False,
    ) -> dict[str, Any]:
        """Deterministically replay a sequence of normalized movement events to reconstruct state.
        
        Guarantees:
        - Deep copy of initial state prevents mutative side-effects on caller state.
        - Topological causal ordering respecting per-feed sequence numbers and explicit causal dependencies.
        - Timestamp inversion and clock skew anomaly detection.
        - Sets replay_status='REPLAY_UNCERTAIN' and is_authoritative_live=False if causal ambiguity or inversions are present.
        - Deterministic tie-breaking on (timestamp, feed_id, sequence_num, event_id) is an operational convention, NOT causal proof.
        """
        state = copy.deepcopy(initial_state)
        if not events:
            state["replay_status"] = "REPLAY_VERIFIED"
            state["ordering_uncertainty_reasons"] = []
            state["causal_integrity"] = "DETERMINISTIC_CAUSAL"
            state["is_authoritative_live"] = (state.get("environment_mode") == "LIVE_OPERATIONAL")
            return state

        uncertainty_reasons: list[str] = []
        event_map = {e.event_id: e for e in events}

        # 1. Dependency graph construction
        # in_deps[e_id] = set of e_ids that MUST precede e_id
        # out_edges[e_id] = set of e_ids that depend on e_id
        in_deps: dict[str, set[str]] = {e.event_id: set() for e in events}
        out_edges: dict[str, set[str]] = {e.event_id: set() for e in events}

        # A. Feed-local sequence ordering: for same feed, sequence_num defines ordering
        feed_events: dict[str, list[NormalizedMovementEvent]] = {}
        for e in events:
            feed_events.setdefault(e.feed_id, []).append(e)

        for feed_id, f_evs in feed_events.items():
            f_evs_sorted = sorted(f_evs, key=lambda x: x.sequence_num)
            for i in range(len(f_evs_sorted) - 1):
                pre = f_evs_sorted[i]
                nxt = f_evs_sorted[i + 1]
                in_deps[nxt.event_id].add(pre.event_id)
                out_edges[pre.event_id].add(nxt.event_id)

        # B. Explicit causal dependencies / predecessors
        for e in events:
            explicit_deps = set(e.causal_dependencies) | set(e.causal_predecessors)
            for dep_id in explicit_deps:
                if dep_id not in event_map:
                    uncertainty_reasons.append(
                        f"Unresolved causal dependency: event '{e.event_id}' depends on missing event '{dep_id}'."
                    )
                else:
                    in_deps[e.event_id].add(dep_id)
                    out_edges[dep_id].add(e.event_id)

        # C. Check timestamp inversions against causal dependencies
        for e in events:
            for pred_id in in_deps[e.event_id]:
                if pred_id in event_map:
                    pred = event_map[pred_id]
                    tolerance = timedelta(seconds=abs(e.clock_skew_seconds) + abs(pred.clock_skew_seconds) + 1.0)
                    if pred.timestamp > (e.timestamp + tolerance):
                        uncertainty_reasons.append(
                            f"Causal timestamp inversion: predecessor '{pred_id}' ({pred.timestamp.isoformat()}) "
                            f"is later than dependent '{e.event_id}' ({e.timestamp.isoformat()}) by "
                            f"{(pred.timestamp - e.timestamp).total_seconds():.1f}s."
                        )

        # 2. Cycle detection and topological sort using priority queue / deterministic ordering
        in_degree = {e_id: len(deps) for e_id, deps in in_deps.items()}
        ready = [event_map[e_id] for e_id, deg in in_degree.items() if deg == 0]

        sorted_order: list[NormalizedMovementEvent] = []

        while ready:
            # Deterministic tie-breaking among all causally ready events:
            # Sort by (timestamp, feed_id, sequence_num, event_id)
            ready.sort(key=lambda ev: (ev.timestamp, ev.feed_id, ev.sequence_num, ev.event_id))
            chosen = ready.pop(0)
            sorted_order.append(chosen)

            for dependent_id in out_edges[chosen.event_id]:
                in_degree[dependent_id] -= 1
                if in_degree[dependent_id] == 0:
                    ready.append(event_map[dependent_id])

        if len(sorted_order) < len(events):
            uncertainty_reasons.append(
                f"Cyclic causal dependencies detected: {len(events) - len(sorted_order)} events could not be topological sorted."
            )
            remaining_ids = set(event_map.keys()) - {ev.event_id for ev in sorted_order}
            remaining = [event_map[eid] for eid in remaining_ids]
            remaining.sort(key=lambda ev: (ev.timestamp, ev.feed_id, ev.sequence_num, ev.event_id))
            sorted_order.extend(remaining)

        # 3. Apply sorted events to state
        for ev in sorted_order:
            self.process_event(ev, state, recalculate_conflicts=False, persist=persist_events)

        # Final conflict recalculation at the end of replay
        try:
            state["conflicts"] = detect_conflicts(state)
        except Exception:
            pass

        # 4. Attach Causal Integrity Metadata
        if uncertainty_reasons:
            state["replay_status"] = "REPLAY_UNCERTAIN"
            state["ordering_uncertainty_reasons"] = uncertainty_reasons
            state["is_authoritative_live"] = False
            state["causal_integrity"] = "AMBIGUOUS"
        else:
            state["replay_status"] = "REPLAY_VERIFIED"
            state["ordering_uncertainty_reasons"] = []
            state["is_authoritative_live"] = (state.get("environment_mode") == "LIVE_OPERATIONAL")
            state["causal_integrity"] = "DETERMINISTIC_CAUSAL"

        return state


# Default singleton processor
event_processor = OperationalEventProcessor()
