"""Shared pytest fixtures.

The database URL is forced to a disposable SQLite file *before* importing the
application so that tests never touch a developer database. Every test module
uses the same client; individual tests create their own simulations so state
does not leak between assertions.
"""
from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

import pytest

_TMP_DIR = Path(tempfile.mkdtemp(prefix="railgorithm-tests-"))
_DB_PATH = _TMP_DIR / "test.db"

os.environ["RAILGORITHM_DATABASE_URL"] = f"sqlite:///{_DB_PATH}"
os.environ["RAILGORITHM_SEED_DEMO"] = "1"
os.environ["RAILGORITHM_JWT_SECRET"] = "test-only-secret-please-change"
os.environ["RAILGORITHM_CP_SAT_TIME_LIMIT"] = "8"

from fastapi.testclient import TestClient  # noqa: E402

from app.db import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client
    shutil.rmtree(_TMP_DIR, ignore_errors=True)


def _login(client: TestClient, username: str, password: str) -> str:
    response = client.post(
        "/api/v1/auth/login", json={"username": username, "password": password}
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


@pytest.fixture(scope="session")
def section_token(client: TestClient) -> str:
    return _login(client, "section.master", "Section@123")


@pytest.fixture(scope="session")
def station_token(client: TestClient) -> str:
    return _login(client, "station.master", "Station@123")


@pytest.fixture(scope="session")
def section_headers(section_token: str) -> dict:
    return {"Authorization": f"Bearer {section_token}"}


@pytest.fixture(scope="session")
def station_headers(station_token: str) -> dict:
    return {"Authorization": f"Bearer {station_token}"}


@pytest.fixture()
def simulation(client: TestClient, section_headers: dict) -> dict:
    response = client.post(
        "/api/v1/simulations",
        headers=section_headers,
        json={"scenario_key": "single_line_meet"},
    )
    assert response.status_code == 200, response.text
    return response.json()


@pytest.fixture()
def db_session(client: TestClient):
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
