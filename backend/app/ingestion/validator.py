"""Ingestion validation, normalization, duplicate detection, and railway-specific physical/operational rules."""
from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import Any
from collections import OrderedDict

from ..domain.network import Network, build_default_network
from ..domain.scenarios import TRAIN_TYPES
from .models import (
    ContradictionRecord,
    ContradictionType,
    EnvironmentMode,
    IngestionValidationResult,
    NormalizedMovementEvent,
    RawFeedPayload,
    ValidationReasonCode,
)

MAX_ABSOLUTE_TRAIN_SPEED_KMPH = 160.0
MAX_CLOCK_DRIFT_AHEAD_SECONDS = 60.0
MAX_DUPLICATE_CACHE_SIZE = 50000


class IngestionValidator:
    """Validates raw railway feed records against physical, temporal, spatial, and network operational rules."""

    def __init__(
        self,
        network: Network | None = None,
        train_type_specs: dict[str, dict[str, Any]] | None = None,
        temporary_speed_restrictions: dict[str, float] | None = None,
        cache_size: int = MAX_DUPLICATE_CACHE_SIZE,
        expected_environment: EnvironmentMode = "SYNTHETIC_SIMULATION",
    ):
        self._network = network or build_default_network()
        self._train_type_specs = train_type_specs or TRAIN_TYPES
        self._tsr_map: dict[str, float] = temporary_speed_restrictions or {}
        self._cache_size = cache_size
        self._expected_environment = expected_environment

        # LRU duplicate cache: fingerprint -> timestamp
        self._seen_event_fingerprints: OrderedDict[str, float] = OrderedDict()
        # Sequence tracking: feed_id -> last_sequence_num
        self._feed_sequences: dict[str, int] = {}
        # Train movement tracking: train_id -> last_event_dict
        self._train_last_events: dict[str, dict[str, Any]] = {}
        # Resource occupancy tracking: location_id -> occupying_train_id
        self._active_occupancies: dict[str, str] = {}
        # Block entry times: (location_id, direction) -> timestamp of last entering train
        self._block_entry_times: dict[str, datetime] = {}
        # Active throat transits at Malgaon Junction (MLG)
        self._active_throat_transits: set[str] = set()
        # Verified train Working Time Table (WTT) specifications
        self._train_wtt_specs: dict[str, dict[str, Any]] = {}

    def set_tsr(self, location_id: str, speed_limit_kmph: float) -> None:
        """Configure a Temporary Speed Restriction (TSR) for a block or section under GR 4.09."""
        self._tsr_map[location_id] = speed_limit_kmph

    def clear_tsr(self, location_id: str) -> None:
        """Clear a Temporary Speed Restriction."""
        self._tsr_map.pop(location_id, None)

    def register_train_wtt_mps(self, train_id: str, max_speed_kmph: float, source_reference: str = "WTT-TIMETABLE-MPS") -> None:
        """Register verified train Working Time Table (WTT) Maximum Permissible Speed."""
        self._train_wtt_specs[train_id] = {
            "max_speed_kmph": float(max_speed_kmph),
            "source": source_reference,
            "is_verified_wtt": True,
        }

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
        self._block_entry_times.clear()
        self._active_throat_transits.clear()
        self._train_wtt_specs.clear()

    def _get_train_max_speed(self, train_id: str, train_type: str | None) -> tuple[float, str]:
        """Determine permitted maximum speed and statutory/configuration source for a train.

        Derivation precedence:
        1. Explicit WTT train registration (timetable/config).
        2. Configured rolling-stock category specification from self._train_type_specs.
        3. Fallback unverified simulation assumption.
        """
        if train_id in self._train_wtt_specs:
            return float(self._train_wtt_specs[train_id]["max_speed_kmph"]), self._train_wtt_specs[train_id]["source"]

        if train_type and train_type in self._train_type_specs:
            mps = float(self._train_type_specs[train_type].get("max_speed_kmph", MAX_ABSOLUTE_TRAIN_SPEED_KMPH))
            return mps, f"CONFIG-ROLLING-STOCK-{train_type}"

        # Heuristic based on train ID prefix if train_type is not explicitly provided
        upper_id = train_id.upper()
        if upper_id.startswith("FRT") or upper_id.startswith("GOODS") or "FREIGHT" in upper_id:
            return float(self._train_type_specs.get("FREIGHT", {}).get("max_speed_kmph", 75.0)), "SIM-FALLBACK-FREIGHT-MPS"
        elif upper_id.startswith("MEMU") or upper_id.startswith("SUB"):
            return float(self._train_type_specs.get("MEMU", {}).get("max_speed_kmph", 90.0)), "SIM-FALLBACK-MEMU-MPS"
        elif upper_id.startswith("PAS") or upper_id.startswith("ORD"):
            return float(self._train_type_specs.get("PASSENGER", {}).get("max_speed_kmph", 100.0)), "SIM-FALLBACK-PASSENGER-MPS"
        elif upper_id.startswith("EXP") or upper_id.startswith("SF") or upper_id.startswith("RAJ"):
            return float(self._train_type_specs.get("EXPRESS", {}).get("max_speed_kmph", 130.0)), "SIM-FALLBACK-EXPRESS-MPS"

        return MAX_ABSOLUTE_TRAIN_SPEED_KMPH, "SIM-ASSUMPTION-MAX-CORRIDOR-CEILING"

    def _get_location_speed_limit(self, location_id: str) -> tuple[float, str, str]:
        """Determine permitted speed limit, reason code, and regulatory rule citation.

        Returns:
            (limit_kmph, reason_code, rule_reference)
        """
        # 1. Check Caution Order / TSR first (GR 4.09)
        if location_id in self._tsr_map:
            return self._tsr_map[location_id], "TSR_SPEED_LIMIT_EXCEEDED", "GR-4.09-TSR-CAUTION-ORDER"

        # 2. Check Section speed limit (WTT Sanctioned Sectional MPS)
        try:
            if location_id in self._network.block_map:
                sec = self._network.section_for_block(location_id)
                return float(sec.max_speed_kmph), "SECTION_SPEED_LIMIT_EXCEEDED", "WTT-SECTIONAL-MPS"
            elif location_id in self._network.section_map:
                sec = self._network.section_map[location_id]
                return float(sec.max_speed_kmph), "SECTION_SPEED_LIMIT_EXCEEDED", "WTT-SECTIONAL-MPS"
            elif location_id in self._network.station_map:
                # Station yard turnout speed limit under Schedule of Dimensions (SOD)
                return 30.0, "SECTION_SPEED_LIMIT_EXCEEDED", "IR-SOD-TURNOUT-SPEED"
        except Exception:
            pass

        return MAX_ABSOLUTE_TRAIN_SPEED_KMPH, "PHYSICAL_IMPOSSIBILITY", "SIM-ASSUMPTION-CORRIDOR-CEILING"

    def validate_and_normalize(self, raw: RawFeedPayload) -> IngestionValidationResult:
        t0 = time.perf_counter()
        now_utc = datetime.now(timezone.utc)

        # 0. Environment isolation check
        if raw.environment != self._expected_environment:
            latency = (time.perf_counter() - t0) * 1000
            contradiction = ContradictionRecord(
                id=f"CONTR-ENV-{int(time.time()*1000)}",
                contradiction_type="ENVIRONMENT_MISMATCH",
                reason_code="ENVIRONMENT_MISMATCH",
                train_id=raw.train_id,
                feed_id=raw.feed_id,
                description=(
                    f"Payload environment '{raw.environment}' does not match validator "
                    f"expected environment '{self._expected_environment}'."
                ),
                rule_reference="ENV-ISOLATION-001",
                offending_payload=raw.model_dump(mode="json"),
            )
            return IngestionValidationResult(
                status="CONTRADICTION",
                reason_code="ENVIRONMENT_MISMATCH",
                message="Environment mismatch: cross-environment data injection blocked",
                rule_reference="ENV-ISOLATION-001",
                contradiction=contradiction,
                processing_latency_ms=latency,
            )

        # 1. Duplicate check
        fp = self._fingerprint(raw)
        if self._remember_fingerprint(fp):
            latency = (time.perf_counter() - t0) * 1000
            return IngestionValidationResult(
                status="DUPLICATE",
                reason_code="DUPLICATE_EVENT",
                message=f"Duplicate event ignored (fingerprint {fp[:12]}...)",
                rule_reference="IR-TELEMETRY-DEDUP",
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
                    reason_code="TIMESTAMP_MALFORMED",
                    train_id=raw.train_id,
                    feed_id=raw.feed_id,
                    description=f"Invalid timestamp format '{raw.timestamp}': {exc}",
                    rule_reference="ISO-8601-UTC",
                    offending_payload=raw.model_dump(mode="json"),
                )
                return IngestionValidationResult(
                    status="SCHEMA_ERROR",
                    reason_code="TIMESTAMP_MALFORMED",
                    message=f"Invalid timestamp: {exc}",
                    rule_reference="ISO-8601-UTC",
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
                reason_code="TIMESTAMP_FUTURE_DRIFT",
                train_id=raw.train_id,
                feed_id=raw.feed_id,
                description=f"Event timestamp {event_dt.isoformat()} is {drift_seconds:.1f}s in future (limit {MAX_CLOCK_DRIFT_AHEAD_SECONDS}s).",
                rule_reference="IR-TELEMETRY-DRIFT-MAX60S",
                offending_payload=raw.model_dump(mode="json"),
            )
            return IngestionValidationResult(
                status="CONTRADICTION",
                reason_code="TIMESTAMP_FUTURE_DRIFT",
                message="Timestamp is in the future beyond allowable drift.",
                rule_reference="IR-TELEMETRY-DRIFT-MAX60S",
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
                environment=raw.environment,
                source_metadata=raw.extra,
                label="OPERATIONAL_FEED" if raw.environment == "LIVE_OPERATIONAL" else "SYNTHETIC_FEED",
            )
            return IngestionValidationResult(
                status="VALID",
                reason_code="VALID_EVENT",
                event=norm_event,
                message="Heartbeat verified",
                rule_reference="IR-TELEMETRY-HEARTBEAT",
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
                reason_code="MISSING_REQUIRED_FIELD",
                train_id=None,
                feed_id=raw.feed_id,
                description=f"Event type '{raw.event_type}' requires a non-empty train_id.",
                rule_reference="OPERATIONAL-IDENTIFIER-MANDATORY",
                offending_payload=raw.model_dump(mode="json"),
            )
            return IngestionValidationResult(
                status="SCHEMA_ERROR",
                reason_code="MISSING_REQUIRED_FIELD",
                message="Missing required train_id",
                rule_reference="OPERATIONAL-IDENTIFIER-MANDATORY",
                contradiction=contradiction,
                processing_latency_ms=latency,
            )

        # 5. Train-Specific & Section-Specific Speed Plausibility Checks
        if raw.speed_kmph is not None:
            if raw.speed_kmph < 0:
                latency = (time.perf_counter() - t0) * 1000
                contradiction = ContradictionRecord(
                    id=f"CONTR-SPEED-NEG-{int(time.time()*1000)}",
                    contradiction_type="PHYSICAL_IMPOSSIBILITY",
                    reason_code="PHYSICAL_IMPOSSIBILITY",
                    train_id=raw.train_id,
                    feed_id=raw.feed_id,
                    description=f"Reported negative speed {raw.speed_kmph} km/h.",
                    rule_reference="PHYS-VELOCITY-NON-NEGATIVE",
                    offending_payload=raw.model_dump(mode="json"),
                )
                return IngestionValidationResult(
                    status="CONTRADICTION",
                    reason_code="PHYSICAL_IMPOSSIBILITY",
                    message="Negative speed value is physically impossible",
                    rule_reference="PHYS-VELOCITY-NON-NEGATIVE",
                    contradiction=contradiction,
                    processing_latency_ms=latency,
                )

            # Check absolute ceiling
            if raw.speed_kmph > MAX_ABSOLUTE_TRAIN_SPEED_KMPH:
                latency = (time.perf_counter() - t0) * 1000
                contradiction = ContradictionRecord(
                    id=f"CONTR-SPEED-ABS-{int(time.time()*1000)}",
                    contradiction_type="PHYSICAL_IMPOSSIBILITY",
                    reason_code="PHYSICAL_IMPOSSIBILITY",
                    train_id=raw.train_id,
                    feed_id=raw.feed_id,
                    description=f"Reported speed {raw.speed_kmph} km/h exceeds corridor maximum {MAX_ABSOLUTE_TRAIN_SPEED_KMPH} km/h.",
                    rule_reference="WTT-SANCTIONED-CORRIDOR-MPS",
                    offending_payload=raw.model_dump(mode="json"),
                )
                return IngestionValidationResult(
                    status="CONTRADICTION",
                    reason_code="PHYSICAL_IMPOSSIBILITY",
                    message=f"Absolute speed ceiling exceeded: {raw.speed_kmph} km/h",
                    rule_reference="WTT-SANCTIONED-CORRIDOR-MPS",
                    contradiction=contradiction,
                    processing_latency_ms=latency,
                )

            # Check train-specific category speed derived from WTT or rolling-stock config
            train_max_speed, speed_rule_ref = self._get_train_max_speed(raw.train_id, raw.train_type)
            if raw.speed_kmph > train_max_speed:
                latency = (time.perf_counter() - t0) * 1000
                contradiction = ContradictionRecord(
                    id=f"CONTR-SPEED-TRN-{int(time.time()*1000)}",
                    contradiction_type="SPEED_LIMIT_EXCEEDED",
                    reason_code="TRAIN_SPEED_LIMIT_EXCEEDED",
                    train_id=raw.train_id,
                    feed_id=raw.feed_id,
                    description=(
                        f"Reported speed {raw.speed_kmph} km/h exceeds permitted limit {train_max_speed} km/h "
                        f"for train {raw.train_id} (governed by {speed_rule_ref})."
                    ),
                    rule_reference="GR-4.08(1)-TRAIN-MPS",
                    offending_payload=raw.model_dump(mode="json"),
                )
                return IngestionValidationResult(
                    status="CONTRADICTION",
                    reason_code="TRAIN_SPEED_LIMIT_EXCEEDED",
                    message=f"Train category speed limit exceeded: {raw.speed_kmph} > {train_max_speed} km/h",
                    rule_reference="GR-4.08(1)-TRAIN-MPS",
                    contradiction=contradiction,
                    processing_latency_ms=latency,
                )

            # Check location-specific speed limit or TSR
            loc_speed_limit, reason_code, loc_rule_ref = self._get_location_speed_limit(raw.location_id)
            if raw.speed_kmph > loc_speed_limit:
                latency = (time.perf_counter() - t0) * 1000
                contradiction = ContradictionRecord(
                    id=f"CONTR-SPEED-LOC-{int(time.time()*1000)}",
                    contradiction_type="SPEED_LIMIT_EXCEEDED",
                    reason_code=reason_code,  # type: ignore[arg-type]
                    train_id=raw.train_id,
                    feed_id=raw.feed_id,
                    description=(
                        f"Reported speed {raw.speed_kmph} km/h exceeds speed limit {loc_speed_limit} km/h "
                        f"at location {raw.location_id} (governed by {loc_rule_ref})."
                    ),
                    rule_reference=loc_rule_ref,
                    offending_payload=raw.model_dump(mode="json"),
                )
                return IngestionValidationResult(
                    status="CONTRADICTION",
                    reason_code=reason_code,  # type: ignore[arg-type]
                    message=f"Section/TSR speed limit exceeded at {raw.location_id}: {raw.speed_kmph} > {loc_speed_limit} km/h",
                    rule_reference=loc_rule_ref,
                    contradiction=contradiction,
                    processing_latency_ms=latency,
                )

        # 6. Directional Movement Check
        if raw.event_type == "BLOCK_ENTRY" and raw.location_id in self._network.block_map:
            blk = self._network.block_map[raw.location_id]
            if blk.direction in {"UP", "DOWN"}:
                # If direction is explicitly stated or inferred
                reported_dir = raw.direction
                if reported_dir and reported_dir != "BIDIRECTIONAL" and reported_dir != blk.direction:
                    latency = (time.perf_counter() - t0) * 1000
                    contradiction = ContradictionRecord(
                        id=f"CONTR-DIR-{int(time.time()*1000)}",
                        contradiction_type="WRONG_DIRECTION_ENTRY",
                        reason_code="WRONG_DIRECTION_ENTRY",
                        train_id=raw.train_id,
                        feed_id=raw.feed_id,
                        description=(
                            f"Train {raw.train_id} moving in direction {reported_dir} attempted to enter "
                            f"unidirectional block {raw.location_id} designated strictly for {blk.direction} movements."
                        ),
                        rule_reference="INFRA-DIRECTIONAL-LOCK",
                        offending_payload=raw.model_dump(mode="json"),
                    )
                    return IngestionValidationResult(
                        status="CONTRADICTION",
                        reason_code="WRONG_DIRECTION_ENTRY",
                        message=f"Wrong direction movement into unidirectional block {raw.location_id}",
                        rule_reference="INFRA-DIRECTIONAL-LOCK",
                        contradiction=contradiction,
                        processing_latency_ms=latency,
                    )

        # 7. Unmatched Block Exit Check
        if raw.event_type == "BLOCK_EXIT":
            occupant = self._active_occupancies.get(raw.location_id)
            if occupant != raw.train_id:
                latency = (time.perf_counter() - t0) * 1000
                contradiction = ContradictionRecord(
                    id=f"CONTR-EXIT-{int(time.time()*1000)}",
                    contradiction_type="UNMATCHED_BLOCK_EXIT",
                    reason_code="UNMATCHED_BLOCK_EXIT",
                    train_id=raw.train_id,
                    feed_id=raw.feed_id,
                    description=(
                        f"Train {raw.train_id} reported BLOCK_EXIT for block {raw.location_id}, "
                        f"but current recorded occupant is '{occupant}'."
                    ),
                    rule_reference="BPAC-WHEEL-COUNT-CONTINUITY",
                    offending_payload=raw.model_dump(mode="json"),
                )
                return IngestionValidationResult(
                    status="CONTRADICTION",
                    reason_code="UNMATCHED_BLOCK_EXIT",
                    message=f"Block exit without prior recorded entry for train {raw.train_id}",
                    rule_reference="BPAC-WHEEL-COUNT-CONTINUITY",
                    contradiction=contradiction,
                    processing_latency_ms=latency,
                )

        # 8. Physical and Spatial Contradictions against prior train state
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
                    reason_code="TEMPORAL_INVERSION",
                    train_id=raw.train_id,
                    feed_id=raw.feed_id,
                    description=(
                        f"Train {raw.train_id} moved backwards in time: prior event at "
                        f"{prior_dt.isoformat()}, incoming event at {event_dt.isoformat()} ({delta_sec:.1f}s)."
                    ),
                    rule_reference="PHYS-TIME-MONOTONIC",
                    offending_payload=raw.model_dump(mode="json"),
                    prior_state=prior,
                )
                return IngestionValidationResult(
                    status="CONTRADICTION",
                    reason_code="TEMPORAL_INVERSION",
                    message="Temporal inversion for train movement",
                    rule_reference="PHYS-TIME-MONOTONIC",
                    contradiction=contradiction,
                    processing_latency_ms=latency,
                )

            # Spatial teleportation check: train moves between disjoint distant locations in < 10 seconds
            if prior_loc != raw.location_id and delta_sec < 5.0 and raw.event_type in {"BLOCK_ENTRY", "STATION_ARRIVAL"}:
                # Topology check: are prior_loc and raw.location_id adjacent in the network?
                is_adjacent = False
                try:
                    if prior_loc in self._network.station_map and raw.location_id in self._network.block_map:
                        sec = self._network.section_for_block(raw.location_id)
                        if prior_loc in {sec.from_station, sec.to_station}:
                            is_adjacent = True
                    elif prior_loc in self._network.block_map and raw.location_id in self._network.station_map:
                        sec = self._network.section_for_block(prior_loc)
                        if raw.location_id in {sec.from_station, sec.to_station}:
                            is_adjacent = True
                    elif prior_loc in self._network.block_map and raw.location_id in self._network.block_map:
                        sec1 = self._network.section_for_block(prior_loc)
                        sec2 = self._network.section_for_block(raw.location_id)
                        if sec1.id == sec2.id:
                            is_adjacent = True
                except Exception:
                    pass

                if not is_adjacent:
                    latency = (time.perf_counter() - t0) * 1000
                    contradiction = ContradictionRecord(
                        id=f"CONTR-TELE-{int(time.time()*1000)}",
                        contradiction_type="SPATIAL_TELEPORTATION",
                        reason_code="SPATIAL_TELEPORTATION",
                        train_id=raw.train_id,
                        feed_id=raw.feed_id,
                        description=(
                            f"Train {raw.train_id} teleported from {prior_loc} to {raw.location_id} in {delta_sec:.1f} seconds."
                        ),
                        rule_reference="PHYS-SPATIAL-CONTINUITY",
                        offending_payload=raw.model_dump(mode="json"),
                        prior_state=prior,
                    )
                    return IngestionValidationResult(
                        status="CONTRADICTION",
                        reason_code="SPATIAL_TELEPORTATION",
                        message="Spatial teleportation contradiction detected",
                        rule_reference="PHYS-SPATIAL-CONTINUITY",
                        contradiction=contradiction,
                        processing_latency_ms=latency,
                    )

        # 9. Mutual exclusion check on exclusive resources (blocks and platforms)
        if raw.event_type in {"BLOCK_ENTRY", "PLATFORM_OCCUPATION"}:
            current_occupant = self._active_occupancies.get(raw.location_id)
            if current_occupant and current_occupant != raw.train_id:
                latency = (time.perf_counter() - t0) * 1000
                contradiction = ContradictionRecord(
                    id=f"CONTR-MUTEX-{int(time.time()*1000)}",
                    contradiction_type="MUTUAL_EXCLUSION_VIOLATION",
                    reason_code="MUTUAL_EXCLUSION_COLLISION",
                    train_id=raw.train_id,
                    feed_id=raw.feed_id,
                    description=(
                        f"Resource {raw.location_id} is already occupied by {current_occupant}; "
                        f"incoming event reports {raw.train_id} entering without prior vacation."
                    ),
                    rule_reference="GR-8.01-ABSOLUTE-BLOCK-MUTEX",
                    offending_payload=raw.model_dump(mode="json"),
                    prior_state={"occupying_train_id": current_occupant, "location_id": raw.location_id},
                )
                return IngestionValidationResult(
                    status="CONTRADICTION",
                    reason_code="MUTUAL_EXCLUSION_COLLISION",
                    message="Mutual exclusion violation on single resource",
                    rule_reference="GR-8.01-ABSOLUTE-BLOCK-MUTEX",
                    contradiction=contradiction,
                    processing_latency_ms=latency,
                )

        # 10. Headway Checking on Block Entry
        if raw.event_type == "BLOCK_ENTRY":
            last_entry = self._block_entry_times.get(raw.location_id)
            if last_entry:
                headway_elapsed_min = (event_dt - last_entry).total_seconds() / 60.0
                try:
                    sec = self._network.section_for_block(raw.location_id)
                    required_headway_min = float(sec.headway_min)
                except Exception:
                    required_headway_min = 3.0

                if headway_elapsed_min < (required_headway_min - 0.1):  # tolerance 6 seconds
                    latency = (time.perf_counter() - t0) * 1000
                    contradiction = ContradictionRecord(
                        id=f"CONTR-HDWY-{int(time.time()*1000)}",
                        contradiction_type="HEADWAY_VIOLATION",
                        reason_code="HEADWAY_VIOLATION",
                        train_id=raw.train_id,
                        feed_id=raw.feed_id,
                        description=(
                            f"Train {raw.train_id} entered block {raw.location_id} {headway_elapsed_min:.1f} min "
                            f"after prior train, violating minimum headway {required_headway_min:.1f} min."
                        ),
                        rule_reference="SIM-ASSUMPTION-HEADWAY",
                        offending_payload=raw.model_dump(mode="json"),
                    )
                    return IngestionValidationResult(
                        status="CONTRADICTION",
                        reason_code="HEADWAY_VIOLATION",
                        message=f"Minimum headway violation on {raw.location_id}",
                        rule_reference="SIM-ASSUMPTION-HEADWAY",
                        contradiction=contradiction,
                        processing_latency_ms=latency,
                    )
            self._block_entry_times[raw.location_id] = event_dt

        # 11. Malgaon Junction Throat Capacity Check (HC-006)
        if raw.location_id == "MLG" or raw.location_id.startswith("MLG-THROAT"):
            if raw.event_type in {"BLOCK_ENTRY", "STATION_ARRIVAL"}:
                if len(self._active_throat_transits) >= 2 and raw.train_id not in self._active_throat_transits:
                    latency = (time.perf_counter() - t0) * 1000
                    contradiction = ContradictionRecord(
                        id=f"CONTR-THROAT-{int(time.time()*1000)}",
                        contradiction_type="JUNCTION_THROAT_OVERFLOW",
                        reason_code="JUNCTION_THROAT_OVERFLOW",
                        train_id=raw.train_id,
                        feed_id=raw.feed_id,
                        description=(
                            f"Malgaon Junction throat capacity (2) exceeded. Current transits: "
                            f"{list(self._active_throat_transits)}. Train {raw.train_id} cannot enter simultaneously."
                        ),
                        rule_reference="SIM-ASSUMPTION-THROAT-CAPACITY",
                        offending_payload=raw.model_dump(mode="json"),
                    )
                    return IngestionValidationResult(
                        status="CONTRADICTION",
                        reason_code="JUNCTION_THROAT_OVERFLOW",
                        message="Junction throat capacity (2) exceeded at Malgaon",
                        rule_reference="SIM-ASSUMPTION-THROAT-CAPACITY",
                        contradiction=contradiction,
                        processing_latency_ms=latency,
                    )
                self._active_throat_transits.add(raw.train_id)
            elif raw.event_type in {"BLOCK_EXIT", "STATION_DEPARTURE"}:
                self._active_throat_transits.discard(raw.train_id)

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
            "direction": raw.direction,
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
            train_type=raw.train_type,
            direction=raw.direction,
            environment=raw.environment,
            source_metadata=raw.extra,
            label="OPERATIONAL_FEED" if raw.environment == "LIVE_OPERATIONAL" else "SYNTHETIC_FEED",
        )

        latency = (time.perf_counter() - t0) * 1000
        return IngestionValidationResult(
            status="VALID",
            reason_code="VALID_EVENT",
            event=norm_event,
            message="Event validated and normalized successfully",
            rule_reference="TELEMETRY-VALID",
            sequence_gap_detected=gap_detected,
            gap_size=gap_size,
            processing_latency_ms=latency,
        )
