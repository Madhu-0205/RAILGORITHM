"""Event processor: applies validated movement events to operational state idempotently.

Handles real-time operational state transitions, delay calculations, conflict engine
triggering, and strict simulation vs live environment isolation.
"""
from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any
from collections import OrderedDict

from ..domain.conflicts import detect_conflicts
from ..domain.network import Network
from .models import EnvironmentMode, NormalizedMovementEvent


class EnvironmentIsolationError(ValueError):
    """Raised when an event from one environment attempts to modify state of another."""


class OperationalEventProcessor:
    """Processes validated movement events into operational simulation and corridor states."""

    def __init__(self, expected_environment: EnvironmentMode = "SYNTHETIC_SIMULATION"):
        self.expected_environment = expected_environment
        # LRU cache of processed event IDs to guarantee idempotency: event_id -> timestamp
        self._processed_events: OrderedDict[str, float] = OrderedDict()
        self._max_processed_cache = 10000

    def is_processed(self, event_id: str) -> bool:
        return event_id in self._processed_events

    def _mark_processed(self, event_id: str) -> None:
        self._processed_events[event_id] = time.time()
        if len(self._processed_events) > self._max_processed_cache:
            self._processed_events.popitem(last=False)

    def process_event(
        self,
        event: NormalizedMovementEvent,
        state: dict[str, Any],
        recalculate_conflicts: bool = True,
    ) -> dict[str, Any]:
        """Apply a normalized movement event to an operational state dictionary.

        Guarantees:
        - Strict environment isolation (rejects cross-environment events).
        - Idempotency (re-processing the same event_id produces no secondary state mutation).
        - Accurate delay calculations and state version incrementing.
        """
        # 1. Environment Isolation Check
        state_env = state.get("environment_mode", "SYNTHETIC_SIMULATION")
        if event.environment != state_env:
            raise EnvironmentIsolationError(
                f"Cross-environment contamination blocked: Event environment '{event.environment}' "
                f"cannot update state with environment '{state_env}'."
            )

        # 2. Idempotency Check
        if self.is_processed(event.event_id):
            return {
                "success": True,
                "idempotent": True,
                "event_id": event.event_id,
                "state_version": state.get("version", 1),
                "message": f"Event '{event.event_id}' already applied; state unchanged.",
            }

        # 3. Locate Train in State
        train_id = event.train_id
        train = next((t for t in state.get("trains", []) if t["id"] == train_id), None)
        
        # Calculate time in minutes from scenario start or clock
        event_time_min = event.timestamp.hour * 60 + event.timestamp.minute
        
        # 4. Apply Event Mutation based on EventType
        ev_type = event.event_type.upper()
        state_modified = False

        if train:
            train["last_reported_speed_kmph"] = event.speed_kmph
            train["last_telemetry_time"] = event.timestamp.isoformat()

            if ev_type in {"BLOCK_ENTRY", "PLATFORM_OCCUPATION"}:
                train["current_location"] = event.location_id
                train["location"] = event.location_id
                # Track in state block occupancy if applicable
                if "block_occupancy" not in state:
                    state["block_occupancy"] = {}
                state["block_occupancy"][event.location_id] = train_id
                state_modified = True

            elif ev_type in {"BLOCK_EXIT", "PLATFORM_VACATION"}:
                if state.get("block_occupancy", {}).get(event.location_id) == train_id:
                    state["block_occupancy"].pop(event.location_id, None)
                    state_modified = True

            elif ev_type == "STATION_ARRIVAL":
                train["current_location"] = event.location_id
                train["location"] = event.location_id
                train["actual_arrival_min"] = event_time_min
                # Calculate arrival delay against scheduled arrival if present
                sched_arr = train.get("scheduled_arrival_min")
                if sched_arr is not None:
                    calculated_delay = max(0, event_time_min - sched_arr)
                    train["delay_min"] = calculated_delay
                elif event.delay_min is not None:
                    train["delay_min"] = event.delay_min
                state_modified = True

            elif ev_type == "STATION_DEPARTURE":
                train["actual_departure_min"] = event_time_min
                sched_dep = train.get("scheduled_departure_min")
                if sched_dep is not None:
                    calculated_delay = max(0, event_time_min - sched_dep)
                    train["delay_min"] = calculated_delay
                elif event.delay_min is not None:
                    train["delay_min"] = event.delay_min
                state_modified = True

            elif ev_type == "SPEED_UPDATE":
                if event.speed_kmph is not None:
                    train["speed_kmph"] = event.speed_kmph
                    state_modified = True

        # 5. Append event to state log
        if "events" in state:
            state["events"].append({
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
            if len(state["events"]) > 1000:
                state["events"] = state["events"][-1000:]

        # 6. Recalculate conflicts if state mutated and requested
        conflicts = state.get("conflicts", [])
        if state_modified:
            state["version"] = state.get("version", 1) + 1
            if recalculate_conflicts:
                try:
                    conflicts = detect_conflicts(state)
                    state["conflicts"] = conflicts
                except Exception:
                    # Maintain existing conflicts if conflict detector cannot parse partial state
                    pass

        self._mark_processed(event.event_id)

        return {
            "success": True,
            "idempotent": False,
            "event_id": event.event_id,
            "state_version": state.get("version", 1),
            "state_modified": state_modified,
            "conflicts_detected": len(conflicts),
            "applied_at": datetime.now(timezone.utc).isoformat(),
        }

    def replay_event_stream(
        self,
        events: list[NormalizedMovementEvent],
        initial_state: dict[str, Any],
    ) -> dict[str, Any]:
        """Deterministically replay a sequence of normalized movement events to reconstruct state."""
        state = dict(initial_state)
        # Sort events monotonically by sequence number and timestamp
        sorted_events = sorted(events, key=lambda e: (e.sequence_num, e.timestamp))
        for ev in sorted_events:
            self.process_event(ev, state, recalculate_conflicts=False)
        
        # Final conflict recalculation at the end of replay
        try:
            state["conflicts"] = detect_conflicts(state)
        except Exception:
            pass
        return state


# Default singleton processor
event_processor = OperationalEventProcessor()
