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
from typing import Any

from .config import settings

PBKDF2_ITERATIONS = 240_000


class TokenError(Exception):
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


def decode_access_token(token: str) -> dict[str, Any]:
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
