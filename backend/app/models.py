"""SQLAlchemy models.

Design notes:
- A simulation owns a full reproducible JSON state snapshot (network, trains,
  occupancy, counters). Recommendations are tied to the state_version they were
  generated from, so stale advice can be rejected rather than silently applied.
- Recommendations and decisions are stored separately. A decision never
  overwrites the original recommendation.
- Audit events and decisions are protected by SQLite triggers against
  UPDATE/DELETE and form a SHA-256 hash chain.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def new_id() -> str:
    return str(uuid.uuid4())


class RevokedToken(Base):
    __tablename__ = "revoked_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    username: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    revoked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    station_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    section_id: Mapped[str | None] = mapped_column(String(32), nullable=True)
    zone: Mapped[str | None] = mapped_column(String(64), nullable=True)
    division: Mapped[str | None] = mapped_column(String(64), nullable=True)
    control_area: Mapped[str | None] = mapped_column(String(64), nullable=True)
    assigned_stations: Mapped[list | None] = mapped_column(JSON, nullable=True)
    assigned_sections: Mapped[list | None] = mapped_column(JSON, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    token_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    password_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    def get_stations(self) -> list[str]:
        if self.assigned_stations and isinstance(self.assigned_stations, list):
            return list(self.assigned_stations)
        if self.station_id:
            return [self.station_id]
        if self.is_section_controller() or self.is_admin():
            if self.control_area == "NORTHERN_CONTROL_AREA":
                return ["NDL", "KRN", "MLG"]
            if self.control_area == "SOUTHERN_CONTROL_AREA":
                return ["MLG", "SRP", "VSN"]
            return ["NDL", "KRN", "MLG", "SRP", "VSN"]
        return []

    def get_sections(self) -> list[str]:
        if self.assigned_sections and isinstance(self.assigned_sections, list):
            return list(self.assigned_sections)
        if self.section_id:
            return [self.section_id]
        if self.is_section_controller() or self.is_admin():
            if self.control_area == "NORTHERN_CONTROL_AREA":
                return ["S1", "S2"]
            if self.control_area == "SOUTHERN_CONTROL_AREA":
                return ["S3", "S4"]
            return ["S1", "S2", "S3", "S4"]
        return []

    def is_section_controller(self) -> bool:
        return self.role in {"SECTION_CONTROLLER", "SECTION_MASTER", "ADMIN"}

    def is_station_master(self) -> bool:
        return self.role == "STATION_MASTER"

    def is_admin(self) -> bool:
        return self.role == "ADMIN"

    def can_access_station(self, target_station: str) -> bool:
        if self.is_admin():
            return True
        stations = self.get_stations()
        return target_station in stations

    def can_view_adjacent(self, target_station: str, simulation_state: dict | None = None) -> bool:
        if self.is_admin() or self.is_section_controller():
            return True
        user_stations = self.get_stations()
        if target_station in user_stations:
            return True
        if simulation_state and "network" in simulation_state:
            for sec in simulation_state["network"].get("sections", []):
                pair = {sec.get("from_station"), sec.get("to_station")}
                for st in user_stations:
                    if st in pair and target_station in pair:
                        return True
        adjacent_map = {
            "NDL": {"KRN"},
            "KRN": {"NDL", "MLG"},
            "MLG": {"KRN", "SRP"},
            "SRP": {"MLG", "VSN"},
            "VSN": {"SRP"},
        }
        for st in user_stations:
            if target_station in adjacent_map.get(st, set()):
                return True
        return False

    def get_permissions(self) -> set[str]:
        if self.is_admin():
            return {
                "VIEW_OWN_STATION",
                "VIEW_ADJACENT_CONTEXT",
                "VIEW_AUTHORIZED_SECTION",
                "VIEW_TRAIN_MOVEMENTS",
                "VIEW_BLOCK_SECTIONS",
                "VIEW_RECOMMENDATIONS",
                "SUBMIT_DECISION",
                "APPLY_DECISION",
                "MANAGE_STATION_LOCAL",
                "MANAGE_SECTION_COORDINATION",
            }
        if self.is_section_controller():
            return {
                "VIEW_AUTHORIZED_SECTION",
                "VIEW_TRAIN_MOVEMENTS",
                "VIEW_BLOCK_SECTIONS",
                "VIEW_RECOMMENDATIONS",
                "SUBMIT_DECISION",
                "APPLY_DECISION",
                "MANAGE_SECTION_COORDINATION",
            }
        if self.is_station_master():
            return {
                "VIEW_OWN_STATION",
                "VIEW_ADJACENT_CONTEXT",
                "VIEW_TRAIN_MOVEMENTS",
                "VIEW_BLOCK_SECTIONS",
                "VIEW_RECOMMENDATIONS",
                "SUBMIT_DECISION",
                "APPLY_DECISION",
                "MANAGE_STATION_LOCAL",
            }
        return set()

    def has_permission(
        self,
        permission: str,
        target_station: str | None = None,
        target_section: str | None = None,
    ) -> bool:
        if self.is_admin():
            return True
        perms = self.get_permissions()
        if permission not in perms:
            return False
        if permission == "VIEW_OWN_STATION" and target_station:
            return self.can_access_station(target_station)
        if permission == "VIEW_ADJACENT_CONTEXT" and target_station:
            return self.can_view_adjacent(target_station)
        if permission == "VIEW_AUTHORIZED_SECTION" and target_section:
            return self.can_access_section(target_section)
        if permission == "MANAGE_STATION_LOCAL" and target_station:
            return self.can_access_station(target_station)
        if permission == "MANAGE_SECTION_COORDINATION" and target_section:
            return self.can_access_section(target_section)
        return True

    def can_access_section(self, target_section: str) -> bool:
        if self.is_admin():
            return True
        sections = self.get_sections()
        if target_section in sections:
            return True
        # If user is station master, check if section borders their station
        # S1: NDL-KRN, S2: KRN-MLG, S3: MLG-SRP, S4: SRP-VSN
        station_section_map = {
            "NDL": {"S1"},
            "KRN": {"S1", "S2"},
            "MLG": {"S2", "S3"},
            "SRP": {"S3", "S4"},
            "VSN": {"S4"},
        }
        user_stations = self.get_stations()
        for st in user_stations:
            if target_section in station_section_map.get(st, set()):
                return True
        return False


class Simulation(Base):
    __tablename__ = "simulations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    scenario_key: Mapped[str] = mapped_column(String(64), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    seed: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="RUNNING", nullable=False)
    sim_time_min: Mapped[int] = mapped_column(Integer, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    state: Mapped[dict] = mapped_column(JSON, nullable=False)
    label: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    __table_args__ = (Index("ix_simulations_scenario", "scenario_key"),)


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    simulation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulations.id"), nullable=False
    )
    state_version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PENDING", nullable=False)
    evidence_status: Mapped[str] = mapped_column(String(40), nullable=False)
    disagreement: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    optimizer_version: Mapped[str] = mapped_column(String(64), nullable=False)
    created_by: Mapped[str] = mapped_column(String(80), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (
        Index("ix_recommendations_simulation", "simulation_id"),
        Index("ix_recommendations_status", "status"),
    )


class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    recommendation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("recommendations.id"), unique=True, nullable=False
    )
    simulation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("simulations.id"), nullable=False
    )
    action: Mapped[str] = mapped_column(String(32), nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    modifications: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    decided_by: Mapped[str] = mapped_column(String(80), nullable=False)
    decided_role: Mapped[str] = mapped_column(String(32), nullable=False)
    decided_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    applied: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    simulation_result: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    original_recommendation: Mapped[dict] = mapped_column(JSON, nullable=False)
    validation: Mapped[dict] = mapped_column(JSON, nullable=False)
    model_version: Mapped[str] = mapped_column(String(64), nullable=False)
    optimizer_version: Mapped[str] = mapped_column(String(64), nullable=False)
    feedback_category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    structured_rationale_tag: Mapped[str | None] = mapped_column(String(64), nullable=True)
    predicted_outcome: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    actual_outcome: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    prediction_error: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    data_quality: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    three_way_comparison: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (Index("ix_decisions_simulation", "simulation_id"),)


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    actor: Mapped[str] = mapped_column(String(80), nullable=False)
    actor_role: Mapped[str] = mapped_column(String(32), nullable=False)
    simulation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    recommendation_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (Index("ix_audit_event_type", "event_type"),)


class AuditChainHead(Base):
    """Single-row chain head used to detect tail truncation.

    The hash chain alone proves internal consistency, but deleting the final
    events would still leave a shorter valid chain. This row records the last
    hash and event count so truncation is detectable.
    """

    __tablename__ = "audit_chain_head"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)
    head_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    event_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )


class ModelVersion(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    trained: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    status: Mapped[str] = mapped_column(String(64), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, nullable=False)
    metrics: Mapped[dict] = mapped_column(JSON, nullable=False)
    artifact_path: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    __table_args__ = (UniqueConstraint("name", "version", name="uq_model_version"),)


class ProcessedEventRecord(Base):
    """Durable record of an acknowledged and applied movement event.

    Guarantees idempotency across process restarts and beyond bounded in-memory LRU eviction.
    """
    __tablename__ = "processed_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feed_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    sequence_num: Mapped[int] = mapped_column(Integer, nullable=False)
    event_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    processed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint("feed_id", "sequence_num", name="uq_feed_sequence"),
        Index("ix_processed_feed_seq", "feed_id", "sequence_num"),
    )


class FeedCheckpointRecord(Base):
    """Persistent sequence and watermark checkpoint per telemetry feed."""
    __tablename__ = "feed_checkpoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    feed_id: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    last_processed_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_contiguous_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    highest_seen_sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    gap_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_processed_timestamp: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, nullable=False)

