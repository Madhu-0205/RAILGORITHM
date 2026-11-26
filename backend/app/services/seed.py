"""Idempotent database seeding: users, model registry and a demo simulation."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..domain.optimizer import OPTIMIZER_VERSION
from ..domain.ppo import metadata_summary
from ..domain.state import initialise_state
from ..models import ModelVersion, Simulation, User
from ..security import hash_password
from .audit import append_audit

DEMO_USERS = [
    # Station Masters (Individual station jurisdiction)
    {
        "username": "SM_NDL_001",
        "password": "Station@123",
        "role": "STATION_MASTER",
        "display_name": "Station Master — Nandpur (NDL)",
        "station_id": "NDL",
        "section_id": "S1",
        "zone": "SWR",
        "division": "Southern Division",
        "control_area": "NORTHERN_CONTROL_AREA",
        "assigned_stations": ["NDL"],
        "assigned_sections": ["S1"],
    },
    {
        "username": "SM_KRN_001",
        "password": "Station@123",
        "role": "STATION_MASTER",
        "display_name": "Station Master — Karanpur (KRN)",
        "station_id": "KRN",
        "section_id": "S1",
        "zone": "SWR",
        "division": "Southern Division",
        "control_area": "NORTHERN_CONTROL_AREA",
        "assigned_stations": ["KRN"],
        "assigned_sections": ["S1", "S2"],
    },
    {
        "username": "SM_MLG_001",
        "password": "Station@123",
        "role": "STATION_MASTER",
        "display_name": "Station Master — Malgaon Junction (MLG)",
        "station_id": "MLG",
        "section_id": "S2",
        "zone": "SWR",
        "division": "Southern Division",
        "control_area": "CORRIDOR",
        "assigned_stations": ["MLG"],
        "assigned_sections": ["S2", "S3"],
    },
    {
        "username": "SM_SRP_001",
        "password": "Station@123",
        "role": "STATION_MASTER",
        "display_name": "Station Master — Suryapur (SRP)",
        "station_id": "SRP",
        "section_id": "S3",
        "zone": "SWR",
        "division": "Southern Division",
        "control_area": "SOUTHERN_CONTROL_AREA",
        "assigned_stations": ["SRP"],
        "assigned_sections": ["S3", "S4"],
    },
    {
        "username": "SM_VSN_001",
        "password": "Station@123",
        "role": "STATION_MASTER",
        "display_name": "Station Master — Vasanthpur (VSN)",
        "station_id": "VSN",
        "section_id": "S4",
        "zone": "SWR",
        "division": "Southern Division",
        "control_area": "SOUTHERN_CONTROL_AREA",
        "assigned_stations": ["VSN"],
        "assigned_sections": ["S4"],
    },
    # Section Controllers (Area and corridor jurisdiction)
    {
        "username": "SC_NORTH_001",
        "password": "Section@123",
        "role": "SECTION_CONTROLLER",
        "display_name": "Section Controller — Northern Area (NDL-MLG)",
        "station_id": None,
        "section_id": "S1",
        "zone": "SWR",
        "division": "Southern Division",
        "control_area": "NORTHERN_CONTROL_AREA",
        "assigned_stations": ["NDL", "KRN", "MLG"],
        "assigned_sections": ["S1", "S2"],
    },
    {
        "username": "SC_SOUTH_001",
        "password": "Section@123",
        "role": "SECTION_CONTROLLER",
        "display_name": "Section Controller — Southern Area (MLG-VSN)",
        "station_id": None,
        "section_id": "S3",
        "zone": "SWR",
        "division": "Southern Division",
        "control_area": "SOUTHERN_CONTROL_AREA",
        "assigned_stations": ["MLG", "SRP", "VSN"],
        "assigned_sections": ["S3", "S4"],
    },
    {
        "username": "SC_CORRIDOR_001",
        "password": "Section@123",
        "role": "SECTION_CONTROLLER",
        "display_name": "Chief Controller — Full Corridor (NDL-VSN)",
        "station_id": None,
        "section_id": "ALL",
        "zone": "SWR",
        "division": "Southern Division",
        "control_area": "CORRIDOR",
        "assigned_stations": ["NDL", "KRN", "MLG", "SRP", "VSN"],
        "assigned_sections": ["S1", "S2", "S3", "S4"],
    },
    # Administrator (System & User Management)
    {
        "username": "ADMIN_001",
        "password": "Admin@123",
        "role": "ADMIN",
        "display_name": "System Security Administrator",
        "station_id": None,
        "section_id": "ALL",
        "zone": "SWR",
        "division": "Southern Division",
        "control_area": "CORRIDOR",
        "assigned_stations": ["NDL", "KRN", "MLG", "SRP", "VSN"],
        "assigned_sections": ["S1", "S2", "S3", "S4"],
    },
    # Legacy Demo Accounts (Kept for automated backwards compatibility)
    {
        "username": "section.master",
        "password": "Section@123",
        "role": "SECTION_MASTER",
        "display_name": "Section Master — Northern Section (Demo)",
        "station_id": None,
        "section_id": "north-section",
        "zone": "SWR",
        "division": "Southern Division",
        "control_area": "CORRIDOR",
        "assigned_stations": ["NDL", "KRN", "MLG", "SRP", "VSN"],
        "assigned_sections": ["S1", "S2", "S3", "S4"],
    },
    {
        "username": "station.master",
        "password": "Station@123",
        "role": "STATION_MASTER",
        "display_name": "Station Master — Malgaon Junction (Demo)",
        "station_id": "MLG",
        "section_id": "north-section",
        "zone": "SWR",
        "division": "Southern Division",
        "control_area": "CORRIDOR",
        "assigned_stations": ["MLG"],
        "assigned_sections": ["S2", "S3"],
    },
]

DEMO_USERNAMES: set[str] = {u["username"] for u in DEMO_USERS}


def _bootstrap_users() -> list[dict]:
    """Optional production bootstrap user from environment variables.

    Demo credentials are only seeded when RAILGORITHM_ALLOW_DEMO_CREDENTIALS
    is enabled. Production deployments must supply an explicit bootstrap user
    and disable demo credentials.
    """
    username = os.getenv("RAILGORITHM_BOOTSTRAP_USERNAME")
    password = os.getenv("RAILGORITHM_BOOTSTRAP_PASSWORD")
    if not username or not password:
        return []
    return [
        {
            "username": username,
            "password": password,
            "role": os.getenv("RAILGORITHM_BOOTSTRAP_ROLE", "SECTION_CONTROLLER"),
            "display_name": os.getenv(
                "RAILGORITHM_BOOTSTRAP_DISPLAY_NAME", "Bootstrap Controller"
            ),
            "station_id": os.getenv("RAILGORITHM_BOOTSTRAP_STATION_ID") or None,
            "section_id": os.getenv("RAILGORITHM_BOOTSTRAP_SECTION_ID") or None,
            "zone": os.getenv("RAILGORITHM_BOOTSTRAP_ZONE") or "SWR",
            "division": os.getenv("RAILGORITHM_BOOTSTRAP_DIVISION") or "Southern Division",
            "control_area": os.getenv("RAILGORITHM_BOOTSTRAP_CONTROL_AREA") or "CORRIDOR",
            "assigned_stations": ["NDL", "KRN", "MLG", "SRP", "VSN"],
            "assigned_sections": ["S1", "S2", "S3", "S4"],
        }
    ]


def seed_users(db: Session) -> None:
    entries = []
    if settings.allow_demo_credentials and not settings.is_production:
        entries.extend(DEMO_USERS)
    entries.extend(_bootstrap_users())
    for entry in entries:
        existing = db.execute(
            select(User).where(User.username == entry["username"])
        ).scalar_one_or_none()
        if existing:
            # Update missing jurisdiction fields if necessary
            if entry.get("assigned_stations") and not existing.assigned_stations:
                existing.assigned_stations = entry["assigned_stations"]
            if entry.get("assigned_sections") and not existing.assigned_sections:
                existing.assigned_sections = entry["assigned_sections"]
            if entry.get("control_area") and not existing.control_area:
                existing.control_area = entry["control_area"]
            if entry.get("zone") and not existing.zone:
                existing.zone = entry["zone"]
            if entry.get("division") and not existing.division:
                existing.division = entry["division"]
            continue
        db.add(
            User(
                username=entry["username"],
                password_hash=hash_password(entry["password"]),
                role=entry["role"],
                display_name=entry["display_name"],
                station_id=entry.get("station_id"),
                section_id=entry.get("section_id"),
                zone=entry.get("zone"),
                division=entry.get("division"),
                control_area=entry.get("control_area"),
                assigned_stations=entry.get("assigned_stations"),
                assigned_sections=entry.get("assigned_sections"),
            )
        )
    db.commit()


def sync_model_registry(db: Session) -> None:
    summary = metadata_summary()
    version = summary.get("model_version", "ppo-v1")
    trained = bool(summary.get("trained"))
    existing = db.execute(
        select(ModelVersion).where(
            ModelVersion.name == "PPO", ModelVersion.version == version
        )
    ).scalar_one_or_none()
    status = (
        "TRAINED_AND_EVALUATED"
        if trained
        else summary.get("status", "UNTRAINED_DEVELOPMENT_COMPONENT")
    )
    if existing:
        existing.trained = trained
        existing.status = status
        existing.config = {
            "observation_space": summary.get("observation_space"),
            "action_space": summary.get("action_space"),
            "reward_design": summary.get("reward_design"),
        }
        existing.metrics = summary.get("evaluation", {})
        existing.artifact_path = str(settings.artifact_dir)
    else:
        db.add(
            ModelVersion(
                name="PPO",
                version=version,
                trained=trained,
                status=status,
                config={
                    "observation_space": summary.get("observation_space"),
                    "action_space": summary.get("action_space"),
                    "reward_design": summary.get("reward_design"),
                    "training_config": summary.get("training_config"),
                    "episodes": summary.get("episodes"),
                },
                metrics=summary.get("evaluation", {}),
                artifact_path=str(settings.artifact_dir),
            )
        )
    existing_opt = db.execute(
        select(ModelVersion).where(
            ModelVersion.name == "CP-SAT", ModelVersion.version == OPTIMIZER_VERSION
        )
    ).scalar_one_or_none()
    if not existing_opt:
        db.add(
            ModelVersion(
                name="CP-SAT",
                version=OPTIMIZER_VERSION,
                trained=False,
                status="DETERMINISTIC_OPTIMIZER",
                config={
                    "solver": "Google OR-Tools CP-SAT",
                    "time_limit_s": settings.cp_sat_time_limit_s,
                    "constraints": [
                        "block exclusivity",
                        "section headway",
                        "single-line ordering",
                        "platform cumulative capacity",
                        "junction throat capacity",
                        "temporary block closure",
                        "no early departure",
                        "dwell and route continuity",
                    ],
                },
                metrics={},
                artifact_path=None,
            )
        )
    existing_baseline = db.execute(
        select(ModelVersion).where(
            ModelVersion.name == "Baseline", ModelVersion.version == "baseline-1.0.0"
        )
    ).scalar_one_or_none()
    if not existing_baseline:
        db.add(
            ModelVersion(
                name="Baseline",
                version="baseline-1.0.0",
                trained=False,
                status="DETERMINISTIC_FALLBACK",
                config={"description": "Deterministic candidate preference ordering"},
                metrics={},
                artifact_path=None,
            )
        )
    db.commit()


def seed_default_simulation(db: Session) -> None:
    if not settings.seed_demo:
        return
    existing = db.execute(select(Simulation).limit(1)).scalar_one_or_none()
    if existing:
        return
    state = initialise_state("normal_traffic")
    state["scenario_date"] = datetime.now(timezone.utc).date().isoformat()
    simulation = Simulation(
        scenario_key="normal_traffic",
        name="Normal traffic — balanced timetable",
        seed=state["seed"],
        status="RUNNING",
        sim_time_min=state["sim_time_min"],
        state_version=state["version"],
        state=state,
        label="SYNTHETIC",
        created_by="system",
    )
    db.add(simulation)
    db.commit()
    append_audit(
        db,
        event_type="SIMULATION_CREATED",
        actor="system",
        actor_role="SYSTEM",
        simulation_id=simulation.id,
        payload={
            "scenario_key": simulation.scenario_key,
            "seed": simulation.seed,
            "label": "SYNTHETIC",
            "state_version": simulation.state_version,
        },
    )
    db.commit()
