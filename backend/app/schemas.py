"""Pydantic request/response schemas."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, field_validator


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    portal: str | None = Field(default=None, description="Optional portal restriction: STATION_MASTER | SECTION_CONTROLLER | ADMIN")


class UserOut(BaseModel):
    id: str
    username: str
    role: str
    display_name: str
    station_id: str | None
    section_id: str | None
    zone: str | None = None
    division: str | None = None
    control_area: str | None = None
    assigned_stations: list[str] = Field(default_factory=list)
    assigned_sections: list[str] = Field(default_factory=list)
    active: bool = True
    last_login_at: str | None = None


class PasswordChangeRequest(BaseModel):
    old_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(min_length=3, max_length=32)
    display_name: str = Field(min_length=3, max_length=120)
    station_id: str | None = None
    section_id: str | None = None
    zone: str | None = None
    division: str | None = None
    control_area: str | None = None
    assigned_stations: list[str] = Field(default_factory=list)
    assigned_sections: list[str] = Field(default_factory=list)


class UserUpdateRequest(BaseModel):
    display_name: str | None = None
    role: str | None = None
    active: bool | None = None
    station_id: str | None = None
    section_id: str | None = None
    zone: str | None = None
    division: str | None = None
    control_area: str | None = None
    assigned_stations: list[str] | None = None
    assigned_sections: list[str] | None = None
    password: str | None = None


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
    feedback_category: str | None = None
    structured_rationale_tag: str | None = None

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
