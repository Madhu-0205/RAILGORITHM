#!/usr/bin/env python3
"""Verification Script: Real Process Restart & Multi-Worker Token Revocation Gate.

Requirements tested:
1. Authenticate user and issue JWT.
2. Revoke token via /api/v1/auth/logout.
3. Stop backend process completely (SIGTERM / terminate and wait).
4. Start fresh backend process using the same persistent database.
5. Submit old token to protected /api/v1/auth/me endpoint.
6. Verify HTTP 401 Unauthorized (token revocation persisted durably in database).
7. Repeat with multiple backend workers (--workers 2) and verify concurrent rejection.
"""
from __future__ import annotations

import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
import json
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
PORT = 8999
BASE_URL = f"http://127.0.0.1:{PORT}"
VENV_PYTHON = str(REPO_ROOT / ".venv" / "bin" / "python3")


def wait_for_server(url: str, timeout_sec: float = 15.0) -> bool:
    start = time.time()
    while time.time() - start < timeout_sec:
        try:
            req = urllib.request.Request(f"{url}/api/v1/health")
            with urllib.request.urlopen(req, timeout=1.5) as res:
                if res.status == 200:
                    return True
        except Exception:
            time.sleep(0.3)
    return False


def http_post(url: str, data: dict, headers: dict | None = None) -> tuple[int, dict]:
    headers = headers or {}
    headers["Content-Type"] = "application/json"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        return exc.code, parsed


def http_get(url: str, headers: dict | None = None) -> tuple[int, dict]:
    headers = headers or {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=5.0) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = {"raw": raw}
        return exc.code, parsed


def kill_process_tree(proc: subprocess.Popen) -> None:
    if proc.poll() is None:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
        except Exception:
            proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
            except Exception:
                proc.kill()
            proc.wait(timeout=3)


def main() -> int:
    print("=" * 70)
    print("RAILGORITHM v2.8.1 — REAL RESTART TOKEN REVOCATION TEST")
    print("=" * 70)

    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "backend")

    # Step 1: Start initial backend process
    print("\n[Step 1] Starting initial backend instance (PID 1)...")
    log_file1 = open("/tmp/uvicorn_test_1.log", "w")
    proc1 = subprocess.Popen(
        [VENV_PYTHON, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(REPO_ROOT),
        env=env,
        preexec_fn=os.setsid,
        stdout=log_file1,
        stderr=subprocess.STDOUT,
    )
    print(f"  Launched Uvicorn Process 1 with PID {proc1.pid}")

    try:
        if not wait_for_server(BASE_URL, timeout_sec=12.0):
            with open("/tmp/uvicorn_test_1.log") as f:
                print(f"Uvicorn 1 log output:\n{f.read()}")
            assert False, "Initial server failed to reach healthy state"
        print("  Backend Instance 1 is online and healthy.")

        # Step 2: Authenticate user
        print("\n[Step 2] Authenticating Section Controller SC_NORTH_001...")
        status, login_body = http_post(
            f"{BASE_URL}/api/v1/auth/login",
            {"username": "SC_NORTH_001", "password": "Section@123"},
        )
        assert status == 200, f"Login failed with status {status}: {login_body}"
        token = login_body["access_token"]
        print(f"  Token acquired (length: {len(token)} chars, prefix: {token[:20]}...)")

        # Step 3: Verify token works
        print("\n[Step 3] Verifying token access on protected /api/v1/auth/me...")
        status, me_body = http_get(f"{BASE_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert status == 200, f"Protected endpoint access failed: {status}"
        assert me_body["username"] == "SC_NORTH_001"
        print(f"  Authentication verified: username={me_body['username']}, role={me_body['role']}")

        # Step 4: Revoke token via logout
        print("\n[Step 4] Revoking token via /api/v1/auth/logout...")
        status, logout_body = http_post(
            f"{BASE_URL}/api/v1/auth/logout",
            {},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert status == 200, f"Logout failed: {status}"
        assert logout_body["status"] == "LOGGED_OUT"
        print(f"  Logout reported success: {logout_body}")

    finally:
        # Step 5: Stop backend process completely
        print(f"\n[Step 5] Stopping backend instance 1 (PID {proc1.pid}) completely...")
        kill_process_tree(proc1)
        assert proc1.poll() is not None, "Process 1 failed to terminate"
        print("  Process 1 is completely stopped and no longer running in memory.")

    # Step 6: Start fresh backend process using the same persistent database
    print("\n[Step 6] Starting fresh backend instance 2 (brand new process & memory space)...")
    log_file2 = open("/tmp/uvicorn_test_2.log", "w")
    proc2 = subprocess.Popen(
        [VENV_PYTHON, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(PORT)],
        cwd=str(REPO_ROOT),
        env=env,
        preexec_fn=os.setsid,
        stdout=log_file2,
        stderr=subprocess.STDOUT,
    )
    print(f"  Launched Uvicorn Process 2 with PID {proc2.pid}")

    try:
        if not wait_for_server(BASE_URL, timeout_sec=12.0):
            with open("/tmp/uvicorn_test_2.log") as f:
                print(f"Uvicorn 2 log output:\n{f.read()}")
            assert False, "Fresh server failed to reach healthy state"
        print("  Backend Instance 2 is online and healthy.")

        # Step 7: Submit old token to protected endpoint
        print("\n[Step 7] Submitting old token to fresh Backend Instance 2...")
        status, err_body = http_get(f"{BASE_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
        print(f"  Response Status: HTTP {status}")
        print(f"  Response Detail: {err_body}")

        # Step 8: Assert HTTP 401
        assert status == 401, f"Security defect: expected HTTP 401, got HTTP {status}"
        assert "revoked" in str(err_body.get("detail", "")).lower(), "Expected detail to report revocation"
        print("  PASSED: Revocation persisted in database across complete process restart!")

    finally:
        print(f"\n[Step 8] Stopping backend instance 2 (PID {proc2.pid})...")
        kill_process_tree(proc2)
        assert proc2.poll() is not None

    # Step 9: Multi-worker verification
    print("\n[Step 9] Multi-worker verification: starting Uvicorn with --workers 2...")
    log_file3 = open("/tmp/uvicorn_test_3.log", "w")
    proc3 = subprocess.Popen(
        [VENV_PYTHON, "-m", "uvicorn", "backend.app.main:app", "--host", "127.0.0.1", "--port", str(PORT), "--workers", "2"],
        cwd=str(REPO_ROOT),
        env=env,
        preexec_fn=os.setsid,
        stdout=log_file3,
        stderr=subprocess.STDOUT,
    )
    print(f"  Launched Multi-Worker Uvicorn (Parent PID {proc3.pid})")

    try:
        if not wait_for_server(BASE_URL, timeout_sec=15.0):
            with open("/tmp/uvicorn_test_3.log") as f:
                print(f"Uvicorn 3 log output:\n{f.read()}")
            assert False, "Multi-worker server failed to start"
        print("  Multi-worker instance is online.")

        # Issue token on multi-worker cluster
        status, login_body = http_post(
            f"{BASE_URL}/api/v1/auth/login",
            {"username": "SM_NDL_001", "password": "Station@123"},
        )
        assert status == 200
        worker_token = login_body["access_token"]

        # Revoke token on cluster
        status, logout_body = http_post(
            f"{BASE_URL}/api/v1/auth/logout",
            {},
            headers={"Authorization": f"Bearer {worker_token}"},
        )
        assert status == 200

        # Submit 10 concurrent requests to test both workers
        print("  Submitting 10 concurrent requests with revoked token to multi-worker cluster...")
        def probe(_):
            return http_get(f"{BASE_URL}/api/v1/auth/me", headers={"Authorization": f"Bearer {worker_token}"})

        with ThreadPoolExecutor(max_workers=5) as pool:
            results = list(pool.map(probe, range(10)))

        statuses = [r[0] for r in results]
        print(f"  All 10 request statuses: {statuses}")
        assert all(s == 401 for s in statuses), f"Some requests did not return 401: {statuses}"
        print("  PASSED: All workers in multi-worker cluster consistently rejected revoked token with HTTP 401!")

    finally:
        print(f"\n[Step 10] Stopping multi-worker instance (PID {proc3.pid})...")
        kill_process_tree(proc3)
        assert proc3.poll() is not None
        print("  Multi-worker instance stopped.")

    print("\n" + "=" * 70)
    print("ALL REAL RESTART & MULTI-WORKER TOKEN REVOCATION TESTS PASSED (EXIT 0)")
    print("=" * 70)
    return 0


if __name__ == "__main__":
    sys.exit(main())
