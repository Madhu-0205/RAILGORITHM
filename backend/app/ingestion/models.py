"""Data ingestion models and feed schemas for RAILGORITHM 2.2.

Defines schemas for normalized movement events, sensor signals, feed health metrics,
and operational contradiction records.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal
from pydantic import BaseModel, Field


EventType = Literal[
    "BLOCK_ENTRY",
    "BLOCK_EXIT",
    "STATION_ARRIVAL",
    "STATION_DEPARTURE",
    "PLATFORM_OCCUPATION",
    "PLATFORM_VACATION",
    "SIGNAL_ASPECT",
    "SPEED_UPDATE",
    "HEARTBEAT",
]

FeedStatus = Literal["HEALTHY", "DEGRADED", "STALE", "OFFLINE"]

ContradictionType = Literal[
    "PHYSICAL_IMPOSSIBILITY",
    "SPATIAL_TELEPORTATION",
    "MUTUAL_EXCLUSION_VIOLATION",
    "TEMPORAL_INVERSION",
    "SCHEMA_INVALID",
]


class RawFeedPayload(BaseModel):
    """Raw payload received from external or mock railway data feeds."""
    feed_id: str
    event_id: str | None = None
    sequence_num: int
    train_id: str | None = None
    event_type: str
    location_id: str
    timestamp: str | datetime
    speed_kmph: float | None = None
    delay_min: float | None = None
    signal_aspect: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class NormalizedMovementEvent(BaseModel):
    """Normalized, validated railway operational event."""
    event_id: str
    feed_id: str
    sequence_num: int
    train_id: str
    event_type: EventType
    location_id: str
    timestamp: datetime
    ingested_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    speed_kmph: float | None = None
    delay_min: float | None = None
    signal_aspect: str | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    label: Literal["OPERATIONAL_FEED", "SYNTHETIC_FEED"] = "SYNTHETIC_FEED"


class ContradictionRecord(BaseModel):
    """Record of an operational contradiction detected during data ingestion."""
    id: str
    contradiction_type: ContradictionType
    train_id: str | None
    feed_id: str
    description: str
    offending_payload: dict[str, Any]
    prior_state: dict[str, Any] | None = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: Literal["WARNING", "CRITICAL"] = "CRITICAL"


class IngestionValidationResult(BaseModel):
    """Result of validating and normalizing an incoming feed event."""
    status: Literal["VALID", "DUPLICATE", "MISSING_SEQUENCE", "CONTRADICTION", "SCHEMA_ERROR"]
    event: NormalizedMovementEvent | None = None
    message: str
    contradiction: ContradictionRecord | None = None
    sequence_gap_detected: bool = False
    gap_size: int = 0
    processing_latency_ms: float = 0.0


class FeedHealthMetrics(BaseModel):
    """Real-time health, freshness, and performance metrics for an operational feed."""
    feed_id: str
    feed_name: str
    status: FeedStatus
    connected: bool
    last_heartbeat_at: datetime | None = None
    freshness_seconds: float = 0.0
    is_stale: bool = False
    events_received_total: int = 0
    events_valid_total: int = 0
    duplicates_detected_total: int = 0
    sequence_gaps_total: int = 0
    contradictions_detected_total: int = 0
    mean_ingestion_latency_ms: float = 0.0
    error_rate_pct: float = 0.0
    reconnection_attempts: int = 0
    circuit_breaker_open: bool = False
    mode: Literal["AUTHORIZED_EXTERNAL_FEED", "SYNTHETIC_MOCK_FEED"] = "SYNTHETIC_MOCK_FEED"
    stale_threshold_seconds: float = 30.0
    degraded_threshold_seconds: float = 15.0
