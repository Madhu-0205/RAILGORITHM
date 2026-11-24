"""Authentication API."""
from __future__ import annotations


def test_login_returns_token_and_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "section.master", "password": "Section@123"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["role"] == "SECTION_MASTER"
    assert body["user"]["username"] == "section.master"


def test_login_rejects_wrong_password(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "section.master", "password": "WrongPassword1"},
    )
    assert response.status_code == 401


def test_login_rejects_unknown_user(client):
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "nobody", "password": "Whatever@123"},
    )
    assert response.status_code == 401


def test_login_validates_payload(client):
    response = client.post(
        "/api/v1/auth/login", json={"username": "ab", "password": "short"}
    )
    assert response.status_code == 422


def test_me_requires_authentication(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_bad_token(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-token"}
    )
    assert response.status_code == 401


def test_me_returns_current_user(client, station_headers):
    response = client.get("/api/v1/auth/me", headers=station_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["role"] == "STATION_MASTER"
    assert body["station_id"] == "MLG"


def test_health_is_public_and_declares_human_control(client):
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["human_in_control"] is True
    assert body["live_railway_connection"] is False
    assert body["data_label"] == "SYNTHETIC"
