"""Authentication endpoints."""
from __future__ import annotations

import time
from collections import defaultdict, deque

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import settings
from ..db import get_db
from ..deps import bearer_scheme, get_current_user, require_admin
from ..models import User, new_id, utcnow
from ..schemas import (
    LoginRequest,
    PasswordChangeRequest,
    TokenResponse,
    UserCreateRequest,
    UserOut,
    UserUpdateRequest,
)
from ..security import (
    cleanup_expired_revocations,
    create_access_token,
    hash_password,
    revoke_token,
    verify_password,
)
from ..services.audit import append_audit
from ..services.seed import DEMO_USERNAMES
from fastapi.security import HTTPAuthorizationCredentials

router = APIRouter(prefix="/auth", tags=["auth"])

# Small in-process login throttle. This is deliberately simple and is not a
# substitute for a shared rate limiter in a multi-instance deployment.
_LOGIN_ATTEMPTS: dict[str, deque[float]] = defaultdict(deque)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _check_login_rate(request: Request) -> None:
    limit = max(1, int(settings.login_rate_limit_per_minute))
    now = time.monotonic()
    attempts = _LOGIN_ATTEMPTS[_client_key(request)]
    while attempts and now - attempts[0] > 60:
        attempts.popleft()
    if len(attempts) >= limit:
        raise HTTPException(
            status_code=429,
            detail="Too many login attempts. Try again in a minute.",
        )
    attempts.append(now)


def _user_out(user: User) -> UserOut:
    return UserOut(
        id=user.id,
        username=user.username,
        role=user.role,
        display_name=user.display_name,
        station_id=user.station_id,
        section_id=user.section_id,
        zone=user.zone,
        division=user.division,
        control_area=user.control_area,
        assigned_stations=user.get_stations(),
        assigned_sections=user.get_sections(),
        active=user.active,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
    )


@router.post("/login", response_model=TokenResponse)
def login(
    payload: LoginRequest, request: Request, db: Session = Depends(get_db)
) -> TokenResponse:
    _check_login_rate(request)
    user = db.execute(
        select(User).where(User.username == payload.username)
    ).scalar_one_or_none()
    if not user or not user.active or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid username or password")
    
    if settings.is_production and user.username in DEMO_USERNAMES:
        raise HTTPException(
            status_code=401,
            detail="Demo accounts are disabled in production environment.",
        )

    # Server-side role enforcement per portal gateway
    if payload.portal:
        portal_norm = payload.portal.strip().upper()
        if portal_norm == "STATION_MASTER":
            if user.role != "STATION_MASTER" and user.role != "ADMIN":
                raise HTTPException(
                    status_code=403,
                    detail=f"Portal Access Denied: Account '{user.username}' with role '{user.role}' cannot authenticate through the Station Master Portal. Please use the Section Controller Portal.",
                )
        elif portal_norm == "SECTION_CONTROLLER":
            if user.role not in {"SECTION_CONTROLLER", "SECTION_MASTER", "ADMIN"}:
                raise HTTPException(
                    status_code=403,
                    detail=f"Portal Access Denied: Account '{user.username}' with role '{user.role}' cannot authenticate through the Section Controller Portal. Please use the Station Master Portal.",
                )
        elif portal_norm == "ADMIN":
            if user.role != "ADMIN":
                raise HTTPException(
                    status_code=403,
                    detail=f"Portal Access Denied: Account '{user.username}' does not have Administrative privileges.",
                )

    user.last_login_at = utcnow()
    token = create_access_token(
        user.username,
        user.role,
        extra={
            "token_version": user.token_version or 1,
            "station_id": user.station_id,
            "control_area": user.control_area,
            "assigned_stations": user.get_stations(),
            "assigned_sections": user.get_sections(),
        },
    )
    append_audit(
        db,
        event_type="USER_LOGIN",
        actor=user.username,
        actor_role=user.role,
        payload={
            "role": user.role,
            "station_id": user.station_id,
            "control_area": user.control_area,
            "assigned_stations": user.get_stations(),
        },
    )
    db.commit()
    return TokenResponse(
        access_token=token,
        expires_in_minutes=settings.jwt_ttl_minutes,
        user=_user_out(user),
    )


@router.post("/login/station-master", response_model=TokenResponse)
def login_station_master(
    payload: LoginRequest, request: Request, db: Session = Depends(get_db)
) -> TokenResponse:
    payload.portal = "STATION_MASTER"
    return login(payload, request, db)


@router.post("/login/section-controller", response_model=TokenResponse)
def login_section_controller(
    payload: LoginRequest, request: Request, db: Session = Depends(get_db)
) -> TokenResponse:
    payload.portal = "SECTION_CONTROLLER"
    return login(payload, request, db)


@router.post("/logout")
def logout(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    try:
        if credentials and credentials.credentials:
            revoke_token(credentials.credentials, db=db, username=user.username)
        append_audit(
            db,
            event_type="USER_LOGOUT",
            actor=user.username,
            actor_role=user.role,
            payload={"username": user.username},
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database write error during logout: {exc}",
        ) from exc
    return {"status": "LOGGED_OUT", "message": "Session terminated and token invalidated."}


@router.post("/change-password")
def change_password(
    payload: PasswordChangeRequest,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict:
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Current password does not match.")
    try:
        user.password_hash = hash_password(payload.new_password)
        user.token_version = (user.token_version or 1) + 1
        user.password_changed_at = utcnow()
        if credentials and credentials.credentials:
            revoke_token(credentials.credentials, db=db, username=user.username)
        append_audit(
            db,
            event_type="PASSWORD_CHANGED",
            actor=user.username,
            actor_role=user.role,
            payload={"username": user.username},
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database write error during password change: {exc}",
        ) from exc
    return {"status": "SUCCESS", "message": "Password changed successfully."}


@router.get("/users", response_model=list[UserOut])
def list_users(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> list[UserOut]:
    users = db.execute(select(User).order_by(User.created_at.asc())).scalars().all()
    return [_user_out(u) for u in users]


@router.post("/users", response_model=UserOut)
def create_user(
    payload: UserCreateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserOut:
    if settings.is_production and payload.username in DEMO_USERNAMES:
        raise HTTPException(
            status_code=400,
            detail="Cannot create demo accounts in production environment.",
        )
    existing = db.execute(select(User).where(User.username == payload.username)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Username already exists.")
    
    new_user = User(
        id=new_id(),
        username=payload.username,
        password_hash=hash_password(payload.password),
        role=payload.role,
        display_name=payload.display_name,
        station_id=payload.station_id,
        section_id=payload.section_id,
        zone=payload.zone,
        division=payload.division,
        control_area=payload.control_area,
        assigned_stations=payload.assigned_stations or ([payload.station_id] if payload.station_id else []),
        assigned_sections=payload.assigned_sections or ([payload.section_id] if payload.section_id else []),
        active=True,
        token_version=1,
    )
    db.add(new_user)
    append_audit(
        db,
        event_type="USER_CREATED",
        actor=admin.username,
        actor_role=admin.role,
        payload={"created_username": payload.username, "role": payload.role},
    )
    db.commit()
    db.refresh(new_user)
    return _user_out(new_user)


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: str,
    payload: UserUpdateRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> UserOut:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if payload.display_name is not None:
        user.display_name = payload.display_name
    if payload.role is not None:
        user.role = payload.role
    if payload.active is not None:
        user.active = payload.active
    if payload.station_id is not None:
        user.station_id = payload.station_id
    if payload.section_id is not None:
        user.section_id = payload.section_id
    if payload.zone is not None:
        user.zone = payload.zone
    if payload.division is not None:
        user.division = payload.division
    if payload.control_area is not None:
        user.control_area = payload.control_area
    if payload.assigned_stations is not None:
        user.assigned_stations = payload.assigned_stations
    if payload.assigned_sections is not None:
        user.assigned_sections = payload.assigned_sections
    if payload.password:
        user.password_hash = hash_password(payload.password)
        user.token_version = (user.token_version or 1) + 1
        user.password_changed_at = utcnow()

    append_audit(
        db,
        event_type="USER_UPDATED",
        actor=admin.username,
        actor_role=admin.role,
        payload={"target_username": user.username, "updated_fields": payload.model_dump(exclude_unset=True, exclude={"password"})},
    )
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.post("/cleanup-revocations")
def cleanup_revocations(
    _admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    count = cleanup_expired_revocations(db=db)
    return {"status": "SUCCESS", "cleaned_count": count}
    db.commit()
    db.refresh(user)
    return _user_out(user)


@router.get("/me", response_model=UserOut)
def me(user: User = Depends(get_current_user)) -> UserOut:
    return _user_out(user)
