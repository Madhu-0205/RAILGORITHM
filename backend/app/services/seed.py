"""Idempotent database seeding: users, model registry and a demo simulation."""
from __future__ import annotations

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
    {
        "username": "section.master",
        "password": "Section@123",
        "role": "SECTION_MASTER",
        "display_name": "Section Master — Northern Section",
        "station_id": None,
        "section_id": "north-section",
    },
    {
        "username": "station.master",
        "password": "Station@123",
        "role": "STATION_MASTER",
        "display_name": "Station Master — Malgaon Junction",
        "station_id": "MLG",
        "section_id": "north-section",
    },
]


def seed_users(db: Session) -> None:
    for entry in DEMO_USERS:
        existing = db.execute(
            select(User).where(User.username == entry["username"])
        ).scalar_one_or_none()
        if existing:
            continue
        db.add(
            User(
                username=entry["username"],
                password_hash=hash_password(entry["password"]),
                role=entry["role"],
                display_name=entry["display_name"],
                station_id=entry["station_id"],
                section_id=entry["section_id"],
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
