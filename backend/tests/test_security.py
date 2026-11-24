"""Authentication primitives: PBKDF2 hashing and HMAC-signed tokens."""
from __future__ import annotations

import time

import pytest

from app.security import (
    TokenError,
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)


def test_password_roundtrip():
    encoded = hash_password("Section@123")
    assert encoded.startswith("pbkdf2_sha256$")
    assert verify_password("Section@123", encoded)
    assert not verify_password("section@123", encoded)
    assert not verify_password("", encoded)


def test_password_hashes_are_salted():
    assert hash_password("Section@123") != hash_password("Section@123")


def test_password_minimum_length():
    with pytest.raises(ValueError):
        hash_password("short")


def test_malformed_hash_is_rejected():
    assert not verify_password("Section@123", "not-a-hash")
    assert not verify_password("Section@123", "md5$1$aa$bb")


def test_token_roundtrip():
    token = create_access_token("section.master", "SECTION_MASTER")
    payload = decode_access_token(token)
    assert payload["sub"] == "section.master"
    assert payload["role"] == "SECTION_MASTER"
    assert payload["iss"] == "railgorithm"
    assert payload["exp"] > payload["iat"]


def test_tampered_token_is_rejected():
    token = create_access_token("section.master", "SECTION_MASTER")
    header, body, signature = token.split(".")
    tampered = f"{header}.{body}.{'A' * len(signature)}"
    with pytest.raises(TokenError):
        decode_access_token(tampered)


def test_tampered_payload_is_rejected():
    token = create_access_token("section.master", "SECTION_MASTER")
    header, _, signature = token.split(".")
    fake_body = create_access_token("station.master", "SECTION_MASTER").split(".")[1]
    with pytest.raises(TokenError):
        decode_access_token(f"{header}.{fake_body}.{signature}")


def test_expired_token_is_rejected():
    token = create_access_token("section.master", "SECTION_MASTER", ttl_minutes=-1)
    with pytest.raises(TokenError, match="expired"):
        decode_access_token(token)


def test_malformed_token_is_rejected():
    with pytest.raises(TokenError):
        decode_access_token("only-one-part")
    with pytest.raises(TokenError):
        decode_access_token("a.b.c.d")
