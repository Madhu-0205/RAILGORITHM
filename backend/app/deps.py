"""Authentication and authorization dependencies."""
from __future__ import annotations

from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from .db import get_db
from .models import Simulation, User
from .security import TokenError, decode_access_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        payload = decode_access_token(credentials.credentials, db=db)
    except TokenError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    user = db.execute(
        select(User).where(User.username == payload["sub"])
    ).scalar_one_or_none()
    if not user or not user.active:
        raise HTTPException(status_code=401, detail="User is inactive or unknown")
    # Invalidate tokens with outdated token_version (monotonic security stamp)
    token_ver = payload.get("token_version")
    current_ver = user.token_version or 1
    if token_ver is not None and token_ver < current_ver:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalidated by password change. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    # Invalidate tokens issued prior to a password change (timestamp fallback)
    if user.password_changed_at and payload.get("iat", 0) < int(user.password_changed_at.timestamp()):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalidated by password change. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_role = payload.get("role")
    role_matches = (
        user.role == token_role
        or (user.role in {"SECTION_CONTROLLER", "SECTION_MASTER"} and token_role in {"SECTION_CONTROLLER", "SECTION_MASTER"})
        or user.role == "ADMIN"
    )
    if not role_matches:
        raise HTTPException(status_code=401, detail="Token role no longer matches user")
    return user


def require_roles(*roles: str) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        allowed = set(roles)
        if "SECTION_MASTER" in allowed:
            allowed.add("SECTION_CONTROLLER")
            allowed.add("ADMIN")
        if "SECTION_CONTROLLER" in allowed:
            allowed.add("SECTION_MASTER")
            allowed.add("ADMIN")
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {user.role} is not authorized for this operation",
            )
        return user

    return dependency


def require_permission(
    permission: str,
    target_station_param: str | None = None,
    target_section_param: str | None = None,
) -> Callable:
    def dependency(user: User = Depends(get_current_user)) -> User:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User '{user.username}' lacking required permission: {permission}",
            )
        return user

    return dependency


def require_admin(user: User = Depends(get_current_user)) -> User:
    if not user.is_admin():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative privileges required for this operation",
        )
    return user


def verify_station_access(user: User, station_id: str) -> None:
    if not user.can_access_station(station_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Station '{station_id}' is outside your authorized operational jurisdiction",
        )


def verify_adjacent_access(user: User, station_id: str, simulation: Simulation | None = None) -> None:
    state = simulation.state if simulation else None
    if not user.can_view_adjacent(station_id, state):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Station '{station_id}' is outside your authorized adjacent operational context",
        )


def verify_section_access(user: User, section_id: str) -> None:
    if not user.can_access_section(section_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Section '{section_id}' is outside your authorized operational jurisdiction",
        )


def get_simulation(simulation_id: str, db: Session = Depends(get_db)) -> Simulation:
    simulation = db.get(Simulation, simulation_id)
    if not simulation:
        raise HTTPException(status_code=404, detail="Simulation not found")
    return simulation
