"""System metadata: assumptions, constraint specification and deployment posture."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..config import settings
from ..deps import get_current_user
from ..domain.optimizer import OPTIMIZER_VERSION
from ..domain.ppo import metadata_summary
from ..domain.spec import (
    ASSUMPTION_SPEC_VERSION,
    CONSTRAINT_SPEC_VERSION,
    SIMULATION_MODEL_VERSION,
    assumption_manifest,
    constraint_manifest,
)
from ..domain.validator import VALIDATOR_VERSION
from ..models import User

router = APIRouter(prefix="/system", tags=["system"])


@router.get("/assumptions")
def assumptions() -> dict:
    return assumption_manifest()


@router.get("/constraints")
def constraints() -> dict:
    return constraint_manifest()


@router.get("/versions")
def versions() -> dict:
    ppo = metadata_summary()
    return {
        "simulation_model": SIMULATION_MODEL_VERSION,
        "assumptions": ASSUMPTION_SPEC_VERSION,
        "constraints": CONSTRAINT_SPEC_VERSION,
        "optimizer": OPTIMIZER_VERSION,
        "validator": VALIDATOR_VERSION,
        "ppo": {
            "version": ppo.get("model_version", "ppo-unavailable"),
            "trained": bool(ppo.get("trained")),
        },
        "label": "SYNTHETIC",
    }


@router.get("/deployment")
def deployment(user: User = Depends(get_current_user)) -> dict:
    """Expose non-secret deployment posture to an authenticated operator."""
    return {
        "environment": settings.environment,
        "deployment_profile": settings.deployment_profile,
        "live_railway_connection": False,
        "human_in_control": True,
        "demo_credentials_allowed": settings.allow_demo_credentials,
        "demo_seed_enabled": settings.seed_demo,
        "default_secret_in_use": settings.is_default_secret,
        "production_problems": settings.production_problems,
        "database_backend": settings.database_url.split(":", 1)[0],
        "requested_by": user.username,
        "label": "SYNTHETIC",
    }
