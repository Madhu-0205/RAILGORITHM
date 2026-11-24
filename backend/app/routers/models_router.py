"""Model registry endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import ModelVersion, User

router = APIRouter(prefix="/models", tags=["models"])


@router.get("")
def list_models(
    db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    records = db.execute(
        select(ModelVersion).order_by(ModelVersion.name, ModelVersion.created_at.desc())
    ).scalars().all()
    return {
        "models": [
            {
                "name": record.name,
                "version": record.version,
                "trained": record.trained,
                "status": record.status,
                "config": record.config,
                "metrics": record.metrics,
                "artifact_path": record.artifact_path,
                "created_at": record.created_at.isoformat(),
            }
            for record in records
        ],
        "disclaimer": (
            "PPO is reported as trained only when a completed training artifact and "
            "evaluation metadata exist. CP-SAT is a deterministic optimizer, not a "
            "trained model. The deterministic baseline is a fallback, not an AI model."
        ),
    }
