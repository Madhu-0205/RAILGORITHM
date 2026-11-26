"""Password hashing and signed access tokens.

Uses only the standard library for crypto primitives so that the authentication
surface has a small dependency footprint. Production deployments should supply
RAILGORITHM_JWT_SECRET from a secret manager.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from .config import settings

PBKDF2_ITERATIONS = 240_000
_REVOKED_TOKENS: set[str] = set()
_REVOKED_HASHES: set[str] = set()


class TokenError(Exception):
    pass


def compute_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("ascii", errors="replace")).hexdigest()


def revoke_token(token: str, db: Any = None, username: str = "") -> None:
    _REVOKED_TOKENS.add(token)
    th = compute_token_hash(token)
    _REVOKED_HASHES.add(th)

    exp_dt = None
    try:
        parts = token.split(".")
        if len(parts) == 3:
            payload = json.loads(_b64url_decode(parts[1]))
            if not username:
                username = payload.get("sub", "")
            exp_ts = payload.get("exp")
            if exp_ts:
                exp_dt = datetime.fromtimestamp(exp_ts, timezone.utc)
    except Exception:
        pass

    # Durable persistence in database
    close_db = False
    try:
        if db is None:
            from .db import SessionLocal
            db = SessionLocal()
            close_db = True

        from sqlalchemy import select
        from .models import RevokedToken

        existing = db.execute(
            select(RevokedToken).where(RevokedToken.token_hash == th)
        ).scalar_one_or_none()
        if not existing:
            rev = RevokedToken(
                token_hash=th,
                username=username or "unknown",
                expires_at=exp_dt,
            )
            db.add(rev)
            db.commit()
    except Exception as exc:
        if db:
            try:
                db.rollback()
            except Exception:
                pass
        _REVOKED_TOKENS.discard(token)
        _REVOKED_HASHES.discard(th)
        raise RuntimeError(f"Database error persisting token revocation: {exc}") from exc
    finally:
        if close_db and db:
            try:
                db.close()
            except Exception:
                pass


def cleanup_expired_revocations(db: Any = None) -> int:
    """Safely delete expired RevokedToken records where expires_at < utcnow()."""
    close_db = False
    try:
        if db is None:
            from .db import SessionLocal
            db = SessionLocal()
            close_db = True

        from sqlalchemy import delete
        from .models import RevokedToken, utcnow

        stmt = delete(RevokedToken).where(
            RevokedToken.expires_at.is_not(None),
            RevokedToken.expires_at < utcnow(),
        )
        res = db.execute(stmt)
        deleted_count = res.rowcount
        db.commit()
        return deleted_count
    except Exception:
        if db:
            try:
                db.rollback()
            except Exception:
                pass
        raise
    finally:
        if close_db and db:
            try:
                db.close()
            except Exception:
                pass


def is_token_revoked(token: str, db: Any = None) -> bool:
    if token in _REVOKED_TOKENS:
        return True
    th = compute_token_hash(token)
    if th in _REVOKED_HASHES:
        return True

    close_db = False
    try:
        if db is None:
            from .db import SessionLocal
            db = SessionLocal()
            close_db = True

        from sqlalchemy import select
        from .models import RevokedToken

        rev = db.execute(
            select(RevokedToken).where(RevokedToken.token_hash == th)
        ).scalar_one_or_none()
        if rev:
            _REVOKED_TOKENS.add(token)
            _REVOKED_HASHES.add(th)
            return True
        return False
    except Exception:
        return False
    finally:
        if close_db and db:
            try:
                db.close()
            except Exception:
                pass


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def hash_password(password: str, *, iterations: int = PBKDF2_ITERATIONS) -> str:
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters")
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    try:
        algorithm, iterations_raw, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        iterations = int(iterations_raw)
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(digest_hex)
    except (ValueError, TypeError):
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(actual, expected)


def create_access_token(
    subject: str,
    role: str,
    *,
    ttl_minutes: int | None = None,
    extra: dict[str, Any] | None = None,
) -> str:
    now = int(time.time())
    payload = {
        "jti": str(uuid.uuid4()),
        "sub": subject,
        "role": role,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": now + 60 * (ttl_minutes or settings.jwt_ttl_minutes),
    }
    if extra:
        payload.update(extra)
    header = {"alg": "HS256", "typ": "JWT"}
    encoded_header = _b64url_encode(json.dumps(header, separators=(",", ":")).encode())
    encoded_payload = _b64url_encode(json.dumps(payload, separators=(",", ":")).encode())
    signing_input = f"{encoded_header}.{encoded_payload}".encode("ascii")
    signature = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    return f"{encoded_header}.{encoded_payload}.{_b64url_encode(signature)}"


def decode_access_token(token: str, db: Any = None) -> dict[str, Any]:
    if is_token_revoked(token, db=db):
        raise TokenError("Token has been revoked. Please sign in again.")
    try:
        header_b64, payload_b64, signature_b64 = token.split(".")
    except ValueError as exc:
        raise TokenError("Malformed token") from exc
    signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
    expected = hmac.new(settings.jwt_secret.encode(), signing_input, hashlib.sha256).digest()
    try:
        provided = _b64url_decode(signature_b64)
    except ValueError as exc:
        raise TokenError("Malformed token signature") from exc
    if not hmac.compare_digest(expected, provided):
        raise TokenError("Invalid token signature")
    try:
        header = json.loads(_b64url_decode(header_b64))
        payload = json.loads(_b64url_decode(payload_b64))
    except (ValueError, json.JSONDecodeError) as exc:
        raise TokenError("Malformed token contents") from exc
    if header.get("alg") != "HS256":
        raise TokenError("Unsupported token algorithm")
    if payload.get("iss") != settings.jwt_issuer:
        raise TokenError("Invalid token issuer")
    if int(payload.get("exp", 0)) < int(time.time()):
        raise TokenError("Token expired")
    if not payload.get("sub") or not payload.get("role"):
        raise TokenError("Token is missing required claims")
    return payload
