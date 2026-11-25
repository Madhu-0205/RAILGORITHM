"""Operational feed manager: connection tracking, health metrics, and event buffering."""
from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any
from collections import deque

from .models import (
    ContradictionRecord,
    FeedHealthMetrics,
    FeedStatus,
    IngestionValidationResult,
    NormalizedMovementEvent,
    RawFeedPayload,
)
from .validator import IngestionValidator


class OperationalFeedManager:
    """Manages real-time railway data feeds, monitoring freshness, error rates and circuit breakers."""

    def __init__(self, stale_threshold_sec: float = 30.0, degraded_threshold_sec: float = 15.0):
        self.stale_threshold = stale_threshold_sec
        self.degraded_threshold = degraded_threshold_sec
        self.validator = IngestionValidator()

        # In-memory feeds state: feed_id -> dict
        self._feeds: dict[str, dict[str, Any]] = {}
        # Rolling event buffers
        self._event_buffer: deque[NormalizedMovementEvent] = deque(maxlen=2000)
        self._contradiction_buffer: deque[ContradictionRecord] = deque(maxlen=500)
        # Latency samples for rolling mean
        self._latency_samples: deque[float] = deque(maxlen=1000)

        # Register default operational feed
        self.register_feed(
            feed_id="FEED-SIGNAL-01",
            feed_name="Northern Corridor Signalling & Track Circuits",
            mode="SYNTHETIC_MOCK_FEED",
        )

    def register_feed(
        self,
        feed_id: str,
        feed_name: str,
        mode: str = "SYNTHETIC_MOCK_FEED",
    ) -> None:
        now = datetime.now(timezone.utc)
        self._feeds[feed_id] = {
            "feed_id": feed_id,
            "feed_name": feed_name,
            "connected": True,
            "last_heartbeat_at": now,
            "events_received": 0,
            "events_valid": 0,
            "duplicates": 0,
            "sequence_gaps": 0,
            "contradictions": 0,
            "errors": 0,
            "reconnect_attempts": 0,
            "circuit_breaker_open": False,
            "mode": mode,
            "consecutive_failures": 0,
        }

    def reset(self) -> None:
        """Reset all feed metrics and buffers."""
        self.validator.reset()
        self._event_buffer.clear()
        self._contradiction_buffer.clear()
        self._latency_samples.clear()
        now = datetime.now(timezone.utc)
        for feed in self._feeds.values():
            feed.update({
                "connected": True,
                "last_heartbeat_at": now,
                "events_received": 0,
                "events_valid": 0,
                "duplicates": 0,
                "sequence_gaps": 0,
                "contradictions": 0,
                "errors": 0,
                "reconnect_attempts": 0,
                "circuit_breaker_open": False,
                "consecutive_failures": 0,
            })

    def ingest_event(self, raw: RawFeedPayload) -> IngestionValidationResult:
        """Ingest, validate, and record a single raw event from a data feed."""
        feed_id = raw.feed_id
        if feed_id not in self._feeds:
            self.register_feed(feed_id=feed_id, feed_name=f"Dynamic Feed {feed_id}")

        feed = self._feeds[feed_id]
        feed["events_received"] += 1

        # Check circuit breaker
        if feed["circuit_breaker_open"]:
            now = datetime.now(timezone.utc)
            contradiction = ContradictionRecord(
                id=f"CONTR-CB-{int(time.time()*1000)}",
                contradiction_type="SCHEMA_INVALID",
                train_id=raw.train_id,
                feed_id=feed_id,
                description=f"Feed {feed_id} circuit breaker is OPEN due to elevated error rates.",
                offending_payload=raw.model_dump(mode="json"),
            )
            return IngestionValidationResult(
                status="SCHEMA_ERROR",
                message="Feed circuit breaker is open. Reconnection required.",
                contradiction=contradiction,
            )

        # Validate through IngestionValidator
        res = self.validator.validate_and_normalize(raw)
        self._latency_samples.append(res.processing_latency_ms)

        # Update feed stats
        if res.status == "VALID":
            feed["events_valid"] += 1
            feed["last_heartbeat_at"] = datetime.now(timezone.utc)
            feed["consecutive_failures"] = 0
            if res.event:
                self._event_buffer.append(res.event)
            if res.sequence_gap_detected:
                feed["sequence_gaps"] += 1

        elif res.status == "DUPLICATE":
            feed["duplicates"] += 1

        elif res.status in {"CONTRADICTION", "SCHEMA_ERROR"}:
            feed["errors"] += 1
            feed["consecutive_failures"] += 1
            if res.status == "CONTRADICTION":
                feed["contradictions"] += 1
            if res.contradiction:
                self._contradiction_buffer.append(res.contradiction)

            # Circuit breaker trip condition: 10 consecutive failures or error rate > 35% on > 30 events
            total = feed["events_received"]
            if feed["consecutive_failures"] >= 10 or (total >= 30 and (feed["errors"] / total) > 0.35):
                feed["circuit_breaker_open"] = True

        return res

    def ingest_batch(self, batch: list[RawFeedPayload]) -> list[IngestionValidationResult]:
        """Ingest a batch of raw feed events in sequence."""
        return [self.ingest_event(raw) for raw in batch]

    def set_feed_connection(self, feed_id: str, connected: bool) -> None:
        """Manually toggle feed connection state (e.g. for testing failover and recovery)."""
        if feed_id in self._feeds:
            self._feeds[feed_id]["connected"] = connected
            if not connected:
                self._feeds[feed_id]["consecutive_failures"] += 1

    def trigger_reconnect(self, feed_id: str) -> dict[str, Any]:
        """Attempt reconnection with exponential backoff simulation."""
        if feed_id not in self._feeds:
            return {"success": False, "message": f"Unknown feed '{feed_id}'"}

        feed = self._feeds[feed_id]
        feed["reconnect_attempts"] += 1
        attempts = feed["reconnect_attempts"]
        backoff_sec = min(30.0, 1.0 * math.pow(2.0, min(attempts - 1, 5)))

        # Reset circuit breaker on manual reconnect request
        feed["connected"] = True
        feed["circuit_breaker_open"] = False
        feed["consecutive_failures"] = 0
        feed["last_heartbeat_at"] = datetime.now(timezone.utc)

        return {
            "success": True,
            "feed_id": feed_id,
            "status": "RECONNECTED",
            "attempt": attempts,
            "backoff_seconds_simulated": backoff_sec,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

    def get_feed_health(self, feed_id: str) -> FeedHealthMetrics:
        """Calculate live status and health metrics for a feed."""
        if feed_id not in self._feeds:
            raise KeyError(f"Feed '{feed_id}' not found")

        feed = self._feeds[feed_id]
        now = datetime.now(timezone.utc)
        last_hb = feed["last_heartbeat_at"]

        freshness_sec = (now - last_hb).total_seconds() if last_hb else 999999.0
        connected = feed["connected"] and not feed["circuit_breaker_open"]

        if not connected:
            status: FeedStatus = "OFFLINE"
        elif freshness_sec > self.stale_threshold:
            status = "STALE"
        elif freshness_sec > self.degraded_threshold:
            status = "DEGRADED"
        else:
            status = "HEALTHY"

        total = feed["events_received"]
        err_rate = round(100.0 * feed["errors"] / max(1, total), 2)
        mean_lat = round(sum(self._latency_samples) / max(1, len(self._latency_samples)), 4)

        return FeedHealthMetrics(
            feed_id=feed_id,
            feed_name=feed["feed_name"],
            status=status,
            connected=connected,
            last_heartbeat_at=last_hb,
            freshness_seconds=round(freshness_sec, 2),
            is_stale=freshness_sec > self.stale_threshold,
            events_received_total=feed["events_received"],
            events_valid_total=feed["events_valid"],
            duplicates_detected_total=feed["duplicates"],
            sequence_gaps_total=feed["sequence_gaps"],
            contradictions_detected_total=feed["contradictions"],
            mean_ingestion_latency_ms=mean_lat,
            error_rate_pct=err_rate,
            reconnection_attempts=feed["reconnect_attempts"],
            circuit_breaker_open=feed["circuit_breaker_open"],
            mode=feed["mode"],
            stale_threshold_seconds=self.stale_threshold,
            degraded_threshold_seconds=self.degraded_threshold,
        )

    def get_all_feed_health(self) -> list[FeedHealthMetrics]:
        """Return health metrics for all registered operational feeds."""
        return [self.get_feed_health(fid) for fid in self._feeds]

    def get_recent_events(self, limit: int = 50, feed_id: str | None = None) -> list[NormalizedMovementEvent]:
        events = list(self._event_buffer)
        if feed_id:
            events = [e for e in events if e.feed_id == feed_id]
        return events[-limit:][::-1]

    def get_recent_contradictions(self, limit: int = 50) -> list[ContradictionRecord]:
        return list(self._contradiction_buffer)[-limit:][::-1]


# Global singleton instance
feed_manager = OperationalFeedManager()
