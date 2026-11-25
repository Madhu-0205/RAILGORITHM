"""Feed adapter implementations for external and simulated railway data sources."""
from __future__ import annotations

import abc
import time
from datetime import datetime, timezone
from typing import Any, Generator

from .models import RawFeedPayload


class BaseFeedAdapter(abc.ABC):
    """Abstract interface for external railway operational data feeds."""

    @abc.abstractmethod
    def poll_events(self) -> list[RawFeedPayload]:
        """Poll or receive incoming events from the upstream feed."""
        raise NotImplementedError

    @abc.abstractmethod
    def send_heartbeat(self) -> RawFeedPayload:
        """Construct a heartbeat payload to maintain feed freshness."""
        raise NotImplementedError


class MockRailwayFeedAdapter(BaseFeedAdapter):
    """Simulates realistic telemetry and movement events from track circuits and interlocking systems."""

    def __init__(self, feed_id: str = "FEED-SIGNAL-01"):
        self.feed_id = feed_id
        self._sequence = 1

    def send_heartbeat(self) -> RawFeedPayload:
        seq = self._sequence
        self._sequence += 1
        return RawFeedPayload(
            feed_id=self.feed_id,
            sequence_num=seq,
            train_id=None,
            event_type="HEARTBEAT",
            location_id="CORRIDOR-SYS",
            timestamp=datetime.now(timezone.utc).isoformat(),
            extra={"status": "ALIVE", "track_circuits_online": 32},
        )

    def create_movement_event(
        self,
        train_id: str,
        event_type: str,
        location_id: str,
        speed_kmph: float | None = None,
        delay_min: float | None = None,
        signal_aspect: str | None = None,
        timestamp: datetime | None = None,
    ) -> RawFeedPayload:
        seq = self._sequence
        self._sequence += 1
        ts = timestamp or datetime.now(timezone.utc)
        return RawFeedPayload(
            feed_id=self.feed_id,
            sequence_num=seq,
            train_id=train_id,
            event_type=event_type,
            location_id=location_id,
            timestamp=ts.isoformat(),
            speed_kmph=speed_kmph,
            delay_min=delay_min,
            signal_aspect=signal_aspect,
            extra={"source": "TRACK_CIRCUIT_AZLM"},
        )

    def poll_events(self) -> list[RawFeedPayload]:
        # Return a heartbeat by default on periodic poll
        return [self.send_heartbeat()]
