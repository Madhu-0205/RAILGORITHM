"""Ingestion validation, normalization, duplicate detection, and contradiction analysis."""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any
from collections import OrderedDict

from .models import (
    ContradictionRecord,
    ContradictionType,
    IngestionValidationResult,
    NormalizedMovementEvent,
    RawFeedPayload,
)

MAX_TRAIN_SPEED_KMPH = 160.0
MAX_CLOCK_DRIFT_AHEAD_SECONDS = 60.0
MAX_DUPLICATE_CACHE_SIZE = 50000


class IngestionValidator:
    """Validates raw railway feed records against physical, temporal and spatial rules."""

    def __init__(self, cache_size: int = MAX_DUPLICATE_CACHE_SIZE):
        self._cache_size = cache_size
        # Fingerprint cache for duplicate detection (ordered for LRU eviction)
        self._seen_event_fingerprints: OrderedDict[str, float] = OrderedDict()
        # Sequence tracking: feed_id -> last_sequence_num
        self._feed_sequences: dict[str, int] = {}
        # Train movement tracking: train_id -> last_event_dict
        self._train_last_events: dict[str, dict[str, Any]] = {}
        # Resource occupancy tracking: location_id -> occupying_train_id
        self._active_occupancies: dict[str, str] = {}

    def _fingerprint(self, raw: RawFeedPayload) -> str:
        data = f"{raw.feed_id}:{raw.sequence_num}:{raw.train_id}:{raw.event_type}:{raw.location_id}:{raw.timestamp}"
        return hashlib.sha256(data.encode()).hexdigest()

    def _remember_fingerprint(self, fp: str) -> bool:
        if fp in self._seen_event_fingerprints:
            return True
        self._seen_event_fingerprints[fp] = time.time()
        if len(self._seen_event_fingerprints) > self._cache_size:
            self._seen_event_fingerprints.popitem(last=False)
        return False

    def reset(self) -> None:
        """Reset validation state (useful for tests and simulation resets)."""
        self._seen_event_fingerprints.clear()
        self._feed_sequences.clear()
        self._train_last_events.clear()
        self._active_occupancies.clear()

    def validate_and_normalize(self, raw: RawFeedPayload) -> IngestionValidationResult:
        t0 = time.perf_counter()
        now_utc = datetime.now(timezone.utc)

        # 1. Duplicate check
        fp = self._fingerprint(raw)
        if self._remember_fingerprint(fp):
            latency = (time.perf_counter() - t0) * 1000
            return IngestionValidationResult(
                status="DUPLICATE",
                message=f"Duplicate event ignored (fingerprint {fp[:12]}...)",
                processing_latency_ms=latency,
            )

        # 2. Parse timestamp
        if isinstance(raw.timestamp, datetime):
            event_dt = raw.timestamp
            if event_dt.tzinfo is None:
                event_dt = event_dt.replace(tzinfo=timezone.utc)
        else:
            try:
                event_dt = datetime.fromisoformat(str(raw.timestamp).replace("Z", "+00:00"))
                if event_dt.tzinfo is None:
                    event_dt = event_dt.replace(tzinfo=timezone.utc)
            except Exception as exc:
                latency = (time.perf_counter() - t0) * 1000
                contradiction = ContradictionRecord(
                    id=f"CONTR-TS-{int(time.time()*1000)}",
                    contradiction_type="SCHEMA_INVALID",
                    train_id=raw.train_id,
                    feed_id=raw.feed_id,
                    description=f"Invalid timestamp format '{raw.timestamp}': {exc}",
                    offending_payload=raw.model_dump(mode="json"),
                )
                return IngestionValidationResult(
                    status="SCHEMA_ERROR",
                    message=f"Invalid timestamp: {exc}",
                    contradiction=contradiction,
                    processing_latency_ms=latency,
                )

        # 3. Temporal inversion / Future timestamp check
        drift_seconds = (event_dt - now_utc).total_seconds()
        if drift_seconds > MAX_CLOCK_DRIFT_AHEAD_SECONDS:
            latency = (time.perf_counter() - t0) * 1000
            contradiction = ContradictionRecord(
                id=f"CONTR-TIME-FUT-{int(time.time()*1000)}",
                contradiction_type="TEMPORAL_INVERSION",
                train_id=raw.train_id,
                feed_id=raw.feed_id,
                description=f"Event timestamp {event_dt.isoformat()} is {drift_seconds:.1f}s in the future.",
                offending_payload=raw.model_dump(mode="json"),
            )
            return IngestionValidationResult(
                status="CONTRADICTION",
                message="Timestamp is in the future beyond allowable drift.",
                contradiction=contradiction,
                processing_latency_ms=latency,
            )

        # 4. Sequence gap detection
        last_seq = self._feed_sequences.get(raw.feed_id)
        gap_detected = False
        gap_size = 0
        if last_seq is not None:
            if raw.sequence_num > last_seq + 1:
                gap_detected = True
                gap_size = raw.sequence_num - (last_seq + 1)
        self._feed_sequences[raw.feed_id] = max(last_seq or 0, raw.sequence_num)

        # Heartbeat events need no further physical validation
        if raw.event_type.upper() == "HEARTBEAT":
            latency = (time.perf_counter() - t0) * 1000
            norm_event = NormalizedMovementEvent(
                event_id=raw.event_id or f"EVT-HB-{raw.feed_id}-{raw.sequence_num}",
                feed_id=raw.feed_id,
                sequence_num=raw.sequence_num,
                train_id=raw.train_id or "SYSTEM",
                event_type="HEARTBEAT",
                location_id=raw.location_id,
                timestamp=event_dt,
                ingested_at=now_utc,
                source_metadata=raw.extra,
            )
            return IngestionValidationResult(
                status="VALID",
                event=norm_event,
                message="Heartbeat verified",
                sequence_gap_detected=gap_detected,
                gap_size=gap_size,
                processing_latency_ms=latency,
            )

        # Train ID is mandatory for movement events
        if not raw.train_id:
            latency = (time.perf_counter() - t0) * 1000
            contradiction = ContradictionRecord(
                id=f"CONTR-NOTRAIN-{int(time.time()*1000)}",
                contradiction_type="SCHEMA_INVALID",
                train_id=None,
                feed_id=raw.feed_id,
                description=f"Event type '{raw.event_type}' requires a non-empty train_id.",
                offending_payload=raw.model_dump(mode="json"),
            )
            return IngestionValidationResult(
                status="SCHEMA_ERROR",
                message="Missing required train_id",
                contradiction=contradiction,
                processing_latency_ms=latency,
            )

        # 5. Speed plausibility check
        if raw.speed_kmph is not None and (raw.speed_kmph < 0 or raw.speed_kmph > MAX_TRAIN_SPEED_KMPH):
            latency = (time.perf_counter() - t0) * 1000
            contradiction = ContradictionRecord(
                id=f"CONTR-SPEED-{int(time.time()*1000)}",
                contradiction_type="PHYSICAL_IMPOSSIBILITY",
                train_id=raw.train_id,
                feed_id=raw.feed_id,
                description=f"Reported speed {raw.speed_kmph} km/h exceeds physical boundary [0, {MAX_TRAIN_SPEED_KMPH}].",
                offending_payload=raw.model_dump(mode="json"),
            )
            return IngestionValidationResult(
                status="CONTRADICTION",
                message=f"Physical speed impossibility: {raw.speed_kmph} km/h",
                contradiction=contradiction,
                processing_latency_ms=latency,
            )

        # 6. Physical and Spatial Contradictions against prior train state
        prior = self._train_last_events.get(raw.train_id)
        if prior:
            prior_dt = prior["timestamp"]
            prior_loc = prior["location_id"]
            delta_sec = (event_dt - prior_dt).total_seconds()

            # Time backwards check for the same train
            if delta_sec < -5.0:
                latency = (time.perf_counter() - t0) * 1000
                contradiction = ContradictionRecord(
                    id=f"CONTR-TIME-REV-{int(time.time()*1000)}",
                    contradiction_type="TEMPORAL_INVERSION",
                    train_id=raw.train_id,
                    feed_id=raw.feed_id,
                    description=(
                        f"Train {raw.train_id} moved backwards in time: prior event at "
                        f"{prior_dt.isoformat()}, incoming event at {event_dt.isoformat()} ({delta_sec:.1f}s)."
                    ),
                    offending_payload=raw.model_dump(mode="json"),
                    prior_state=prior,
                )
                return IngestionValidationResult(
                    status="CONTRADICTION",
                    message="Temporal inversion for train movement",
                    contradiction=contradiction,
                    processing_latency_ms=latency,
                )

            # Spatial teleportation check: train moves between disjoint distant locations in < 10 seconds
            if prior_loc != raw.location_id and delta_sec < 5.0 and raw.event_type in {"BLOCK_ENTRY", "STATION_ARRIVAL"}:
                # If locations are entirely different stations/blocks
                if not (prior_loc.startswith("B") and raw.location_id.startswith("B") and abs(int(prior_loc[1:2] or 0) - int(raw.location_id[1:2] or 0)) <= 1):
                    latency = (time.perf_counter() - t0) * 1000
                    contradiction = ContradictionRecord(
                        id=f"CONTR-TELE-{int(time.time()*1000)}",
                        contradiction_type="SPATIAL_TELEPORTATION",
                        train_id=raw.train_id,
                        feed_id=raw.feed_id,
                        description=(
                            f"Train {raw.train_id} teleported from {prior_loc} to {raw.location_id} in {delta_sec:.1f} seconds."
                        ),
                        offending_payload=raw.model_dump(mode="json"),
                        prior_state=prior,
                    )
                    return IngestionValidationResult(
                        status="CONTRADICTION",
                        message="Spatial teleportation contradiction detected",
                        contradiction=contradiction,
                        processing_latency_ms=latency,
                    )

        # 7. Mutual exclusion check on exclusive resources
        if raw.event_type in {"BLOCK_ENTRY", "PLATFORM_OCCUPATION"}:
            current_occupant = self._active_occupancies.get(raw.location_id)
            if current_occupant and current_occupant != raw.train_id:
                latency = (time.perf_counter() - t0) * 1000
                contradiction = ContradictionRecord(
                    id=f"CONTR-MUTEX-{int(time.time()*1000)}",
                    contradiction_type="MUTUAL_EXCLUSION_VIOLATION",
                    train_id=raw.train_id,
                    feed_id=raw.feed_id,
                    description=(
                        f"Resource {raw.location_id} is already occupied by {current_occupant}; "
                        f"incoming event reports {raw.train_id} entering without prior vacation."
                    ),
                    offending_payload=raw.model_dump(mode="json"),
                    prior_state={"occupying_train_id": current_occupant, "location_id": raw.location_id},
                )
                return IngestionValidationResult(
                    status="CONTRADICTION",
                    message="Mutual exclusion violation on single resource",
                    contradiction=contradiction,
                    processing_latency_ms=latency,
                )

        # Update tracking on valid movement
        if raw.event_type in {"BLOCK_ENTRY", "PLATFORM_OCCUPATION", "STATION_ARRIVAL"}:
            self._active_occupancies[raw.location_id] = raw.train_id
        elif raw.event_type in {"BLOCK_EXIT", "PLATFORM_VACATION", "STATION_DEPARTURE"}:
            if self._active_occupancies.get(raw.location_id) == raw.train_id:
                self._active_occupancies.pop(raw.location_id, None)

        self._train_last_events[raw.train_id] = {
            "location_id": raw.location_id,
            "event_type": raw.event_type,
            "timestamp": event_dt,
            "speed_kmph": raw.speed_kmph,
            "delay_min": raw.delay_min,
        }

        # Normalize into clean event
        event_id = raw.event_id or f"EVT-{raw.feed_id}-{raw.sequence_num}-{raw.train_id}"
        norm_event = NormalizedMovementEvent(
            event_id=event_id,
            feed_id=raw.feed_id,
            sequence_num=raw.sequence_num,
            train_id=raw.train_id,
            event_type=raw.event_type.upper(),  # type: ignore[arg-type]
            location_id=raw.location_id,
            timestamp=event_dt,
            ingested_at=now_utc,
            speed_kmph=raw.speed_kmph,
            delay_min=raw.delay_min,
            signal_aspect=raw.signal_aspect,
            source_metadata=raw.extra,
            label="SYNTHETIC_FEED",
        )

        latency = (time.perf_counter() - t0) * 1000
        return IngestionValidationResult(
            status="VALID",
            event=norm_event,
            message="Event validated and normalized successfully",
            sequence_gap_detected=gap_detected,
            gap_size=gap_size,
            processing_latency_ms=latency,
        )
