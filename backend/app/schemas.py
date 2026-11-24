"""Pydantic request/response schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)


class UserOut(BaseModel):
    id: str
    username: str
    role: str
    display_name: str
    station_id: str | None
    section_id: str | None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_minutes: int
    user: UserOut


class SimulationCreate(BaseModel):
    scenario_key: str = Field(min_length=2, max_length=64)
    seed: int | None = Field(default=None, ge=0, le=2_147_483_647)


class AdvanceRequest(BaseModel):
    minutes: int = Field(ge=1, le=180)


class PauseRequest(BaseModel):
    paused: bool = True


class DisruptionRequest(BaseModel):
    disruption_type: str
    payload: dict[str, Any] = Field(default_factory=dict)


class DecisionRequest(BaseModel):
    action: str
    rationale: str = Field(min_length=5, max_length=4000)
    modifications: dict[str, Any] | None = None
    confirm_apply: bool = False

    @field_validator("action")
    @classmethod
    def validate_action(cls, value: str) -> str:
        allowed = {"APPROVE", "REJECT", "MODIFY", "REQUEST_ALTERNATIVES", "DEFER"}
        upper = value.upper()
        if upper not in allowed:
            raise ValueError(f"action must be one of {sorted(allowed)}")
        return upper


class WhatIfRequest(BaseModel):
    action: dict[str, Any]
    minutes: int = Field(default=30, ge=5, le=120)


class GenerateRecommendationRequest(BaseModel):
    parent_recommendation_id: str | None = None
