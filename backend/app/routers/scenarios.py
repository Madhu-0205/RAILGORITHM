"""Scenario catalogue endpoints."""
from __future__ import annotations

from fastapi import APIRouter, Depends

from ..domain.scenarios import scenario_catalogue
from ..models import User
from ..deps import get_current_user

router = APIRouter(prefix="/scenarios", tags=["scenarios"])


@router.get("")
def list_scenarios(user: User = Depends(get_current_user)) -> dict:
    return {
        "scenarios": scenario_catalogue(),
        "label": "SYNTHETIC",
        "note": "All scenarios are synthetic and reproducible with fixed seeds.",
    }
