"""Data ingestion package for RAILGORITHM 2.2."""
from .adapters import BaseFeedAdapter, MockRailwayFeedAdapter
from .feed_manager import OperationalFeedManager, feed_manager
from .models import (
    ContradictionRecord,
    ContradictionType,
    EventType,
    FeedHealthMetrics,
    FeedStatus,
    IngestionValidationResult,
    NormalizedMovementEvent,
    RawFeedPayload,
)
from .validator import IngestionValidator

__all__ = [
    "BaseFeedAdapter",
    "MockRailwayFeedAdapter",
    "OperationalFeedManager",
    "feed_manager",
    "ContradictionRecord",
    "ContradictionType",
    "EventType",
    "FeedHealthMetrics",
    "FeedStatus",
    "IngestionValidationResult",
    "NormalizedMovementEvent",
    "RawFeedPayload",
    "IngestionValidator",
]
