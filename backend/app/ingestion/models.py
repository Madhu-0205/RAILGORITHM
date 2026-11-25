"""Data ingestion models and feed schemas for RAILGORITHM 2.3.

Defines schemas for normalized movement events, sensor signals, feed health metrics,
operational contradiction records, and environment isolation contracts.
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

FeedStatus = Literal["HEALTHY", "DEGRADED", "STALE", "OFFLINE", "DURABILITY_UNAVAILABLE", "REPLAY_UNCERTAIN"]

EnvironmentMode = Literal["LIVE_OPERATIONAL", "SYNTHETIC_SIMULATION", "HISTORICAL_PLAYBACK"]

ContradictionType = Literal[
    "PHYSICAL_IMPOSSIBILITY",
    "SPATIAL_TELEPORTATION",
    "MUTUAL_EXCLUSION_VIOLATION",
    "TEMPORAL_INVERSION",
    "SCHEMA_INVALID",
    "WRONG_DIRECTION_ENTRY",
    "UNMATCHED_BLOCK_EXIT",
    "SPEED_LIMIT_EXCEEDED",
    "HEADWAY_VIOLATION",
    "JUNCTION_THROAT_OVERFLOW",
    "ENVIRONMENT_MISMATCH",
]

ValidationReasonCode = Literal[
    "VALID_EVENT",
    "DUPLICATE_EVENT",
    "TIMESTAMP_FUTURE_DRIFT",
    "TIMESTAMP_MALFORMED",
    "TEMPORAL_INVERSION",
    "MISSING_REQUIRED_FIELD",
    "TRAIN_SPEED_LIMIT_EXCEEDED",
    "SECTION_SPEED_LIMIT_EXCEEDED",
    "TSR_SPEED_LIMIT_EXCEEDED",
    "PHYSICAL_IMPOSSIBILITY",
    "WRONG_DIRECTION_ENTRY",
    "UNMATCHED_BLOCK_EXIT",
    "SPATIAL_DISCONTINUITY",
    "SPATIAL_TELEPORTATION",
    "MUTUAL_EXCLUSION_COLLISION",
    "HEADWAY_VIOLATION",
    "JUNCTION_THROAT_OVERFLOW",
    "PLATFORM_CAPACITY_EXCEEDED",
    "PLATFORM_INCOMPATIBLE",
    "CIRCUIT_BREAKER_ACTIVE",
    "ENVIRONMENT_MISMATCH",
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
    train_type: str | None = None
    direction: Literal["UP", "DOWN", "BIDIRECTIONAL"] | None = None
    environment: EnvironmentMode = "SYNTHETIC_SIMULATION"
    source_timestamp: datetime | None = None
    receive_timestamp: datetime | None = None
    clock_skew_seconds: float = 0.0
    causal_dependencies: list[str] = Field(default_factory=list)
    causal_predecessors: list[str] = Field(default_factory=list)
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
    train_type: str | None = None
    direction: Literal["UP", "DOWN", "BIDIRECTIONAL"] | None = None
    environment: EnvironmentMode = "SYNTHETIC_SIMULATION"
    payload_hash: str | None = None
    source_timestamp: datetime | None = None
    receive_timestamp: datetime | None = None
    clock_skew_seconds: float = 0.0
    causal_dependencies: list[str] = Field(default_factory=list)
    causal_predecessors: list[str] = Field(default_factory=list)
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    label: Literal["OPERATIONAL_FEED", "SYNTHETIC_FEED"] = "SYNTHETIC_FEED"


class ContradictionRecord(BaseModel):
    """Record of an operational contradiction detected during data ingestion."""
    id: str
    contradiction_type: ContradictionType
    reason_code: ValidationReasonCode = "PHYSICAL_IMPOSSIBILITY"
    train_id: str | None
    feed_id: str
    description: str
    rule_reference: str = "OPERATIONAL-VALIDATION-RECORD"
    offending_payload: dict[str, Any]
    prior_state: dict[str, Any] | None = None
    detected_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    severity: Literal["WARNING", "CRITICAL"] = "CRITICAL"


class IngestionValidationResult(BaseModel):
    """Result of validating and normalizing an incoming feed event."""
    status: Literal["VALID", "DUPLICATE", "MISSING_SEQUENCE", "CONTRADICTION", "SCHEMA_ERROR"]
    reason_code: ValidationReasonCode = "VALID_EVENT"
    event: NormalizedMovementEvent | None = None
    message: str
    rule_reference: str = "TELEMETRY-VALID"
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
    environment: EnvironmentMode = "SYNTHETIC_SIMULATION"
    mode: Literal["AUTHORIZED_EXTERNAL_FEED", "SYNTHETIC_MOCK_FEED"] = "SYNTHETIC_MOCK_FEED"
    stale_threshold_seconds: float = 30.0
    degraded_threshold_seconds: float = 15.0
