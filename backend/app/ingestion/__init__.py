"""Data ingestion package for RAILGORITHM 2.3."""
from .adapters import BaseFeedAdapter, MockRailwayFeedAdapter
from .event_processor import EnvironmentIsolationError, OperationalEventProcessor, event_processor
from .feed_manager import OperationalFeedManager, feed_manager
from .models import (
    ContradictionRecord,
    ContradictionType,
    EnvironmentMode,
    EventType,
    FeedHealthMetrics,
    FeedStatus,
    IngestionValidationResult,
    NormalizedMovementEvent,
    RawFeedPayload,
    ValidationReasonCode,
)
from .validator import IngestionValidator

__all__ = [
    "BaseFeedAdapter",
    "MockRailwayFeedAdapter",
    "OperationalFeedManager",
    "feed_manager",
    "OperationalEventProcessor",
    "event_processor",
    "EnvironmentIsolationError",
    "ContradictionRecord",
    "ContradictionType",
    "EnvironmentMode",
    "EventType",
    "FeedHealthMetrics",
    "FeedStatus",
    "IngestionValidationResult",
    "NormalizedMovementEvent",
    "RawFeedPayload",
    "ValidationReasonCode",
    "IngestionValidator",
]
