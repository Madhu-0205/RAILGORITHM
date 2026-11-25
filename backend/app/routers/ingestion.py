"""API endpoints for real-time data ingestion, feed health, contradiction tracking, and event recovery."""
from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..deps import get_current_user
from ..ingestion.event_processor import event_processor
from ..ingestion.feed_manager import feed_manager
from ..ingestion.models import (
    ContradictionRecord,
    EnvironmentMode,
    FeedHealthMetrics,
    IngestionValidationResult,
    NormalizedMovementEvent,
    RawFeedPayload,
)
from ..models import User

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


class ToggleFeedRequest(BaseModel):
    connected: bool


class IngestBatchRequest(BaseModel):
    events: list[RawFeedPayload]


class ProcessEventRequest(BaseModel):
    event: NormalizedMovementEvent
    state: dict[str, Any]
    recalculate_conflicts: bool = True


@router.get("/status", response_model=list[FeedHealthMetrics])
def get_all_feeds_status(
    environment: EnvironmentMode | None = Query(default=None),
    _user: User = Depends(get_current_user),
) -> list[FeedHealthMetrics]:
    """Retrieve operational status, freshness, and metrics for all railway feeds, optionally filtered by environment."""
    return feed_manager.get_all_feed_health(environment=environment)


@router.get("/feeds/{feed_id}", response_model=FeedHealthMetrics)
def get_feed_status(feed_id: str, _user: User = Depends(get_current_user)) -> FeedHealthMetrics:
    """Retrieve status and metrics for a specific feed."""
    try:
        return feed_manager.get_feed_health(feed_id)
    except KeyError:
        raise HTTPException(status_code=404, detail=f"Feed '{feed_id}' not found.")


@router.post("/events", response_model=IngestionValidationResult)
def ingest_single_event(payload: RawFeedPayload, _user: User = Depends(get_current_user)) -> IngestionValidationResult:
    """Ingest, validate, and normalize a single movement or sensor event."""
    return feed_manager.ingest_event(payload)


@router.post("/events/batch", response_model=list[IngestionValidationResult])
def ingest_event_batch(batch: IngestBatchRequest, _user: User = Depends(get_current_user)) -> list[IngestionValidationResult]:
    """Ingest a batch of movement events in rapid succession."""
    return feed_manager.ingest_batch(batch.events)


@router.post("/events/apply")
def apply_event_to_state(req: ProcessEventRequest, _user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Apply a validated event to operational state idempotently."""
    try:
        return event_processor.process_event(
            req.event,
            req.state,
            recalculate_conflicts=req.recalculate_conflicts,
        )
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/events", response_model=list[NormalizedMovementEvent])
def get_recent_events(
    limit: int = Query(default=50, ge=1, le=500),
    feed_id: str | None = None,
    environment: EnvironmentMode | None = None,
    _user: User = Depends(get_current_user),
) -> list[NormalizedMovementEvent]:
    """Query recent normalized operational movement events."""
    return feed_manager.get_recent_events(limit=limit, feed_id=feed_id, environment=environment)


@router.get("/events/recover", response_model=list[NormalizedMovementEvent])
def recover_event_stream(
    since_sequence_num: int = Query(default=0, ge=0),
    _user: User = Depends(get_current_user),
) -> list[NormalizedMovementEvent]:
    """Recover acknowledged events in sequence for replay and disaster recovery."""
    return feed_manager.recover_event_stream(since_sequence_num=since_sequence_num)


@router.get("/contradictions", response_model=list[ContradictionRecord])
def get_recent_contradictions(
    limit: int = Query(default=50, ge=1, le=200),
    _user: User = Depends(get_current_user),
) -> list[ContradictionRecord]:
    """Query recent physical, temporal, or spatial contradictions detected during ingestion."""
    return feed_manager.get_recent_contradictions(limit=limit)


@router.post("/feeds/{feed_id}/reconnect")
def reconnect_feed(feed_id: str, _user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Trigger feed reconnection with exponential backoff and circuit breaker reset."""
    res = feed_manager.trigger_reconnect(feed_id)
    if not res.get("success"):
        raise HTTPException(status_code=404, detail=res.get("message"))
    return res


@router.post("/feeds/{feed_id}/toggle")
def toggle_feed_connection(feed_id: str, req: ToggleFeedRequest, _user: User = Depends(get_current_user)) -> dict[str, Any]:
    """Manually disconnect or reconnect a feed for resilience and chaos testing."""
    if feed_id not in feed_manager._feeds:
        raise HTTPException(status_code=404, detail=f"Feed '{feed_id}' not found.")
    feed_manager.set_feed_connection(feed_id, req.connected)
    return {"feed_id": feed_id, "connected": req.connected}
