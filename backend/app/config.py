"""Application configuration.

Secrets are read from the environment. Development defaults are clearly
labelled and must be overridden in any shared or production deployment.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_DIR = BACKEND_DIR.parent


def _env_flag(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str = "RAILGORITHM"
    api_prefix: str = "/api/v1"
    environment: str = os.getenv("RAILGORITHM_ENV", "development").strip().lower()
    deployment_profile: str = os.getenv(
        "RAILGORITHM_DEPLOYMENT_PROFILE", "simulation-only"
    )
    database_url: str = os.getenv(
        "RAILGORITHM_DATABASE_URL", f"sqlite:///{BACKEND_DIR / 'railgorithm.db'}"
    )
    jwt_secret: str = os.getenv(
        "RAILGORITHM_JWT_SECRET", "railgorithm-dev-only-secret-change-me"
    )
    jwt_ttl_minutes: int = int(os.getenv("RAILGORITHM_JWT_TTL_MINUTES", "480"))
    jwt_issuer: str = "railgorithm"
    cors_origins: tuple[str, ...] = tuple(
        origin.strip()
        for origin in os.getenv(
            "RAILGORITHM_CORS_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173",
        ).split(",")
        if origin.strip()
    )
    cp_sat_time_limit_s: float = float(
        os.getenv("RAILGORITHM_CP_SAT_TIME_LIMIT", "8")
    )
    cp_sat_workers: int = int(os.getenv("RAILGORITHM_CP_SAT_WORKERS", "1"))
    recommendation_horizon_min: int = int(
        os.getenv("RAILGORITHM_RECOMMENDATION_HORIZON", "75")
    )
    evaluation_horizon_min: int = int(
        os.getenv("RAILGORITHM_EVALUATION_HORIZON", "75")
    )
    decision_apply_minutes: int = int(
        os.getenv("RAILGORITHM_DECISION_APPLY_MINUTES", "30")
    )
    max_events: int = 600
    objective_profile: str = os.getenv("RAILGORITHM_OBJECTIVE_PROFILE", "balanced")
    junction_throat_capacity: int = int(
        os.getenv("RAILGORITHM_JUNCTION_THROAT_CAPACITY", "2")
    )
    seed_demo: bool = _env_flag("RAILGORITHM_SEED_DEMO", True)
    allow_demo_credentials: bool = _env_flag(
        "RAILGORITHM_ALLOW_DEMO_CREDENTIALS", True
    )
    login_rate_limit_per_minute: int = int(
        os.getenv("RAILGORITHM_LOGIN_RATE_LIMIT", "10")
    )
    artifact_dir: Path = field(
        default_factory=lambda: Path(
            os.getenv("RAILGORITHM_ARTIFACT_DIR", str(BACKEND_DIR / "ml" / "artifacts"))
        )
    )
    timezone_label: str = "Asia/Kolkata (IST)"
    data_label: str = "SYNTHETIC — NOT REAL INDIAN RAILWAYS DATA"

    @property
    def is_default_secret(self) -> bool:
        return self.jwt_secret.startswith("railgorithm-dev-only")

    @property
    def is_production(self) -> bool:
        return self.environment in {"production", "prod"}

    @property
    def production_problems(self) -> list[str]:
        """Configuration problems that make a production deployment unsafe."""
        problems: list[str] = []
        if self.is_production and self.is_default_secret:
            problems.append(
                "RAILGORITHM_JWT_SECRET must be set to a strong non-default value in production"
            )
        if self.is_production and self.allow_demo_credentials:
            problems.append(
                "RAILGORITHM_ALLOW_DEMO_CREDENTIALS must be disabled in production"
            )
        if self.is_production and self.seed_demo:
            problems.append("RAILGORITHM_SEED_DEMO must be disabled in production")
        if self.is_production and self.database_url.startswith("sqlite"):
            problems.append(
                "SQLite is not a supported production database; configure PostgreSQL"
            )
        return problems

    def assert_safe_for_production(self) -> None:
        if self.production_problems:
            raise RuntimeError(
                "Unsafe production configuration: " + "; ".join(self.production_problems)
            )


settings = Settings()
