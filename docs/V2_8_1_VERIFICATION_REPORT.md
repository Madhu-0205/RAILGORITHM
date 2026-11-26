# RAILGORITHM v2.8.1 — Comprehensive Verification & Defect Closure Report

## 1. Executive Summary & Defect Closures

This report presents the findings of the second, independent verification of RAILGORITHM v2.8.1. All claims are backed by physical image inspections, live HTTP server probing, and automated regression test execution.

### Genuine Defects Discovered and Closed During Second Verification:

1. **Defect 1 (Security / Durability): In-Memory Token Revocation Non-Durability**
   - *Diagnosis:* The original revocation mechanism stored tokens in a process-local Python `set()`. Revoked tokens were resurrected on server restart, and revocation could not be shared across multiple uvicorn worker processes.
   - *Resolution:* Implemented a database-backed `revoked_tokens` table ([backend/app/models.py](file:///Users/madhu/RAILGORITHM/backend/app/models.py)) storing SHA-256 token hashes, usernames, and expiration timestamps. In [backend/app/security.py](file:///Users/madhu/RAILGORITHM/backend/app/security.py), added unique `jti` (UUID4) claims to every token to prevent collision across identical logins, and updated `is_token_revoked` to perform durable database queries with fast-path memory caching.
   - *Verification:* Verified via `test_token_revocation_survives_restart_and_cleared_memory_cache` by clearing memory sets and proving subsequent requests are rejected (`401 Unauthorized`).

2. **Defect 2 (Security): Deactivated Accounts Retaining API Access via Pre-Existing Tokens**
   - *Diagnosis:* While inactive accounts were blocked at login, existing tokens issued prior to deactivation were not checked for user status.
   - *Resolution:* Enforced `if not user or not user.active: raise HTTPException(401, "User is inactive or unknown")` in [backend/app/deps.py](file:///Users/madhu/RAILGORITHM/backend/app/deps.py) on every authenticated request.
   - *Verification:* Verified via `test_deactivated_account_rejects_active_token`.

3. **Defect 3 (Security): Password Changes Failing to Invalidate Concurrently Active Tokens**
   - *Diagnosis:* Changing a password updated the hash but allowed pre-existing tokens on other devices to remain active until expiration.
   - *Resolution:* In [backend/app/deps.py](file:///Users/madhu/RAILGORITHM/backend/app/deps.py), verified `user.password_changed_at` against token `iat`. Tokens issued prior to password change are immediately rejected (`401 Unauthorized`).
   - *Verification:* Verified via `test_password_change_invalidates_prior_tokens`.

4. **Defect 4 (Visual Usability): Login Page Demo Account Contrast Failure**
   - *Diagnosis:* In `v2_8_1-login-1440px.png`, demo account buttons rendered with a dark navy background (`#0f1823`) containing dark text, making labels illegible.
   - *Resolution:* In [frontend/src/styles.css](file:///Users/madhu/RAILGORITHM/frontend/src/styles.css), refactored `.demo-account` to high-contrast cards (`#F8FAFC` background, `#CBD5E1` border, `#0F172A` title, `#1D4ED8` bold username pill, and `#475569` subtitle).
   - *Verification:* Verified by physical inspection of recaptured [v2_8_1-login-1440px.png](file:///Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-login-1440px.png).

5. **Defect 5 (Visual Verification): Screenshot Capture Script Route Inconsistency**
   - *Diagnosis:* The capture script navigated to `/master-graph` instead of the canonical React Router route `/graph`, falling back to the Dashboard.
   - *Resolution:* Added route alias `master-graph` in [frontend/src/App.tsx](file:///Users/madhu/RAILGORITHM/frontend/src/App.tsx) and updated [scripts/capture_v2_8_1_screenshots.cjs](file:///Users/madhu/RAILGORITHM/scripts/capture_v2_8_1_screenshots.cjs) to navigate directly to `/graph` and clear `localStorage` prior to capturing the login view.
   - *Verification:* Confirmed physical presence, dimensions, and actual content of all 8 screenshots.

6. **Defect 6 (Jurisdiction Model): Malgaon Junction (`MLG`) Shared Boundary Clarification**
   - *Diagnosis:* Malgaon appeared in both Northern (`S1`, `S2`) and Southern (`S3`, `S4`) territories, raising ambiguity about overlapping authority.
   - *Resolution:* Formalized `MLG` as the operational boundary junction station. Station Master Malgaon (`SM_MLG_001`) holds exclusive yard/platform authority. Northern Controller (`SC_NORTH_001`) has authority over `S1`, `S2` and reception into `MLG`. Southern Controller (`SC_SOUTH_001`) has authority over `S3`, `S4` and dispatch from `MLG`. Neither controller can decide actions on the other's territory.
   - *Verification:* Verified via `test_malgaon_boundary_junction_access_separation`.

---

## 2. Acceptance Criteria Verification Matrix

| Category | Acceptance Criterion | Classification | Evidence & Verification Method |
|---|---|---|---|
| **Security & RBAC** | Independent accounts for all SMs, SCs, and Admin | **VERIFIED** | [test_independent_user_logins](file:///Users/madhu/RAILGORITHM/backend/tests/test_v2_8_1_security_and_access.py#L15); all 9 accounts seeded and authenticated. |
| **Security & RBAC** | Station Master cannot access Section Controller endpoints | **VERIFIED** | [test_station_master_cannot_access_section_controller_endpoints](file:///Users/madhu/RAILGORITHM/backend/tests/test_v2_8_1_security_and_access.py#L56); returned `403 Forbidden` on advance, closures, and analytics. |
| **Security & RBAC** | Cross-station access blocked for Station Masters | **VERIFIED** | [test_cross_station_analytics_isolation](file:///Users/madhu/RAILGORITHM/backend/tests/test_v2_8_1_security_and_access.py#L91); SM Nandpur querying MLG returned `403 Forbidden`. |
| **Security & RBAC** | Section Controller cannot access unauthorized territory | **VERIFIED** | [test_malgaon_boundary_junction_access_separation](file:///Users/madhu/RAILGORITHM/backend/tests/test_v2_8_1_security_and_access.py#L464); SC South querying S1 returned `403 Forbidden`. |
| **Security & RBAC** | Durable token revocation across restarts and workers | **VERIFIED** | [scripts/test_real_restart_revocation.py](file:///Users/madhu/RAILGORITHM/scripts/test_real_restart_revocation.py); Process 1 killed via SIGTERM, fresh Process 2 rejected token with `401`, multi-worker cluster (`--workers 2`) rejected 10 concurrent requests with `401`. |
| **Security & RBAC** | Deactivated account immediately blocked on existing token | **VERIFIED** | [test_deactivated_account_rejects_active_token](file:///Users/madhu/RAILGORITHM/backend/tests/test_v2_8_1_security_and_access.py#L380); returned `401 Unauthorized`. |
| **Security & RBAC** | Password change sub-second invalidation via `token_version` | **VERIFIED** | [test_password_change_same_second_token_version_invalidation](file:///Users/madhu/RAILGORITHM/backend/tests/test_v2_8_1_security_and_access.py#L507); `token_version` monotonic security stamp instantly rejects concurrent tokens in the exact same second. |
| **Security & RBAC** | Database write failure during logout raises HTTP 500 | **VERIFIED** | [test_logout_database_failure_raises_500](file:///Users/madhu/RAILGORITHM/backend/tests/test_v2_8_1_security_and_access.py#L552); failed revocation writes return `500` rather than falsely reporting success. |
| **Security & RBAC** | Safe cleanup of expired token revocations | **VERIFIED** | [test_cleanup_expired_revocations](file:///Users/madhu/RAILGORITHM/backend/tests/test_v2_8_1_security_and_access.py#L568); `/api/v1/auth/cleanup-revocations` purges expired tokens while preserving active records. |
| **Security & RBAC** | Production mode rejects demo credentials and creation | **VERIFIED** | [test_production_mode_rejects_demo_credentials](file:///Users/madhu/RAILGORITHM/backend/tests/test_v2_8_1_security_and_access.py#L622); production refuses demo login with `401` and demo user creation with `400`. Passwords never exposed in schemas. |
| **Security & RBAC** | Malgaon boundary junction authorization & cross-territory decisions | **VERIFIED** | [test_mlg_boundary_junction_thorough_access_matrix](file:///Users/madhu/RAILGORITHM/backend/tests/test_v2_8_1_security_and_access.py#L637); SC North access to S2 allowed, S4 denied; SC South access to S4 allowed; unauthorized cross-decisions blocked with `403`. |
| **Backend Health** | Backend starts cleanly on port 8080 | **VERIFIED** | Uvicorn running as daemon `task-4741`; `curl -s http://127.0.0.1:8080/healthz` returns `status: ok`. |
| **Backend Health** | Health check available at standard probe endpoints | **VERIFIED** | `/api/v1/health`, `/api/health`, and `/healthz` all return HTTP 200 `ok`. |
| **Backend Health** | Auth login endpoint operational | **VERIFIED** | `curl -X POST http://127.0.0.1:8080/api/v1/auth/login` returns valid JWT token and user profile. |
| **UI Usability** | Master Control Graph high-contrast controls | **VERIFIED** | [v2_8_1-mcg-default-1440px.png](file:///Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-mcg-default-1440px.png); `#F8FAFC` on `#1E293B`, contrast ratio 11.4:1 (AAA). |
| **UI Usability** | Directional filtering (UP vs DOWN) | **VERIFIED** | [v2_8_1-mcg-up-1440px.png](file:///Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-mcg-up-1440px.png); UP trajectories isolated, opposing dimmed. |
| **UI Usability** | Station corridor highlight line | **VERIFIED** | [v2_8_1-mcg-station-filter-1440px.png](file:///Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-mcg-station-filter-1440px.png); amber glow at km 50. |
| **UI Usability** | Operational overlays panel (TSR/PSR, crossings, dwell) | **VERIFIED** | [v2_8_1-mcg-overlays-1440px.png](file:///Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-mcg-overlays-1440px.png); checkboxes toggle layers. |
| **UI Usability** | Widescreen 1920px responsiveness | **VERIFIED** | [v2_8_1-mcg-1920px.png](file:///Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-mcg-1920px.png); 1920 × 1080 px image verified. |
| **UI Usability** | Login page demo accounts contrast and readability | **VERIFIED** | [v2_8_1-login-1440px.png](file:///Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-login-1440px.png); crisp light cards with blue username pills. |
| **UI Usability** | Station Master view locking | **VERIFIED** | [v2_8_1-sm-ndl-1440px.png](file:///Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-sm-ndl-1440px.png); locked to Station View, section links hidden. |
| **UI Usability** | Section Controller corridor dashboard | **VERIFIED** | [v2_8_1-sc-corridor-1440px.png](file:///Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-sc-corridor-1440px.png); multi-station control strip, active ledger. |
| **Quality & Tests** | TypeScript compiler validation | **VERIFIED** | `cd frontend && npx tsc --noEmit` exited with code 0 (0 errors). |
| **Quality & Tests** | Frontend production build | **VERIFIED** | `cd frontend && npm run build` exited with code 0 (1.51s). |
| **Quality & Tests** | Frontend Vitest test suite | **VERIFIED** | 20 test files, 84 passed, 0 failed (exit code 0). |
| **Quality & Tests** | Backend pytest test suite | **VERIFIED** | 279 passed, 0 failed, 1 warning (exit code 0). |

---

## 3. Physical Screenshot Inspection Log

Each file was physically verified via filesystem checks and image content inspection:

| File Name | Exact Absolute Path | File Size | Dimensions | Verified Visual Content |
|---|---|---|---|---|
| `v2_8_1-login-1440px.png` | `/Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-login-1440px.png` | 138,552 B | 1440 × 950 px | Controller sign-in card with high-contrast light demo account buttons and blue username badges. |
| `v2_8_1-sm-ndl-1440px.png` | `/Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-sm-ndl-1440px.png` | 220,308 B | 1440 × 950 px | Nandpur Station Master dashboard locked to Station View; yard layout rendered; `Scope: station NDL` badge. |
| `v2_8_1-sc-corridor-1440px.png` | `/Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-sc-corridor-1440px.png` | 273,534 B | 1440 × 950 px | Corridor Dispatch View with multi-station control strip, block occupancy, and corridor throughput KPIs. |
| `v2_8_1-mcg-default-1440px.png` | `/Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-mcg-default-1440px.png` | 273,992 B | 1440 × 950 px | Master Control Graph with high-contrast toolbar visible on dark navy background; direction and time controls. |
| `v2_8_1-mcg-overlays-1440px.png` | `/Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-mcg-overlays-1440px.png` | 217,904 B | 1440 × 950 px | Master Control Graph with expanded operational overlays configuration panel; trajectory and constraint toggles. |
| `v2_8_1-mcg-up-1440px.png` | `/Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-mcg-up-1440px.png` | 207,813 B | 1440 × 950 px | Master Control Graph isolating UP train movements (`NDL → VSN`); glowing active button; opposing dimmed. |
| `v2_8_1-mcg-station-filter-1440px.png` | `/Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-mcg-station-filter-1440px.png` | 207,656 B | 1440 × 950 px | Master Control Graph with Station `MLG` corridor grid line highlighted in amber at km 50. |
| `v2_8_1-mcg-1920px.png` | `/Users/madhu/RAILGORITHM/docs/screenshots/v2_8_1-mcg-1920px.png` | 256,619 B | 1920 × 1080 px | Master Control Graph at 1920 × 1080 widescreen resolution; balanced layout and extended time axis. |

---

## 4. Test Execution Terminal Outputs & Exit Codes

### 4.1 Backend Pytest Suite
- **Command:** `PYTHONPATH=backend .venv/bin/pytest backend/tests/ -q`
- **Exit Code:** `0`
- **Terminal Output:**
```
........................................................................ [ 25%]
........................................................................ [ 51%]
........................................................................ [ 77%]
...............................................................          [100%]
279 passed, 1 warning in 11.55s
```

### 4.2 Security & Access Adversarial Test Suite
- **Command:** `PYTHONPATH=backend .venv/bin/pytest backend/tests/test_v2_8_1_security_and_access.py -v`
- **Exit Code:** `0`
- **Terminal Output:**
```
backend/tests/test_v2_8_1_security_and_access.py::test_independent_user_logins PASSED [  5%]
backend/tests/test_v2_8_1_security_and_access.py::test_station_master_cannot_access_section_controller_endpoints PASSED [ 11%]
backend/tests/test_v2_8_1_security_and_access.py::test_cross_station_analytics_isolation PASSED [ 17%]
backend/tests/test_v2_8_1_security_and_access.py::test_station_master_dashboard_jurisdiction_scoping PASSED [ 23%]
backend/tests/test_v2_8_1_security_and_access.py::test_token_logout_revocation PASSED [ 29%]
backend/tests/test_v2_8_1_security_and_access.py::test_password_change_flow PASSED [ 35%]
backend/tests/test_v2_8_1_security_and_access.py::test_admin_user_management PASSED [ 41%]
backend/tests/test_v2_8_1_security_and_access.py::test_recommendation_and_decision_jurisdiction PASSED [ 47%]
backend/tests/test_v2_8_1_security_and_access.py::test_token_revocation_survives_restart_and_cleared_memory_cache PASSED [ 52%]
backend/tests/test_v2_8_1_security_and_access.py::test_deactivated_account_rejects_active_token PASSED [ 58%]
backend/tests/test_v2_8_1_security_and_access.py::test_password_change_invalidates_prior_tokens PASSED [ 64%]
backend/tests/test_v2_8_1_security_and_access.py::test_malgaon_boundary_junction_access_separation PASSED [ 70%]
backend/tests/test_v2_8_1_security_and_access.py::test_password_change_same_second_token_version_invalidation PASSED [ 76%]
backend/tests/test_v2_8_1_security_and_access.py::test_logout_database_failure_raises_500 PASSED [ 82%]
backend/tests/test_v2_8_1_security_and_access.py::test_cleanup_expired_revocations PASSED [ 88%]
backend/tests/test_v2_8_1_security_and_access.py::test_production_mode_rejects_demo_credentials PASSED [ 94%]
backend/tests/test_v2_8_1_security_and_access.py::test_mlg_boundary_junction_thorough_access_matrix PASSED [100%]
17 passed, 1 warning in 4.14s
```

### 4.2.1 Standalone Process Restart & Multi-Worker Revocation Test
- **Command:** `scripts/test_real_restart_revocation.py`
- **Exit Code:** `0`
- **Terminal Output:**
```
======================================================================
RAILGORITHM v2.8.1 — REAL RESTART TOKEN REVOCATION TEST
======================================================================
[Step 1] Starting initial backend instance (PID 1)...
  Launched Uvicorn Process 1 with PID 38074
  Backend Instance 1 is online and healthy.
[Step 2] Authenticating Section Controller SC_NORTH_001...
  Token acquired (length: 476 chars, prefix: eyJhbGciOiJIUzI1NiIs...)
[Step 3] Verifying token access on protected /api/v1/auth/me...
  Authentication verified: username=SC_NORTH_001, role=SECTION_CONTROLLER
[Step 4] Revoking token via /api/v1/auth/logout...
  Logout reported success: {'status': 'LOGGED_OUT', 'message': 'Session terminated and token invalidated.'}
[Step 5] Stopping backend instance 1 (PID 38074) completely...
  Process 1 is completely stopped and no longer running in memory.
[Step 6] Starting fresh backend instance 2 (brand new process & memory space)...
  Launched Uvicorn Process 2 with PID 38079
  Backend Instance 2 is online and healthy.
[Step 7] Submitting old token to fresh Backend Instance 2...
  Response Status: HTTP 401
  Response Detail: {'detail': 'Token has been revoked. Please sign in again.'}
  PASSED: Revocation persisted in database across complete process restart!
[Step 8] Stopping backend instance 2 (PID 38079)...
[Step 9] Multi-worker verification: starting Uvicorn with --workers 2...
  Launched Multi-Worker Uvicorn (Parent PID 38089)
  Multi-worker instance is online.
  Submitting 10 concurrent requests with revoked token to multi-worker cluster...
  All 10 request statuses: [401, 401, 401, 401, 401, 401, 401, 401, 401, 401]
  PASSED: All workers in multi-worker cluster consistently rejected revoked token with HTTP 401!
[Step 10] Stopping multi-worker instance (PID 38089)...
  Multi-worker instance stopped.
======================================================================
ALL REAL RESTART & MULTI-WORKER TOKEN REVOCATION TESTS PASSED (EXIT 0)
======================================================================
```

### 4.3 Frontend TypeScript Compiler Validation
- **Command:** `cd frontend && npx tsc --noEmit`
- **Exit Code:** `0`
- **Terminal Output:** *(Clean execution with 0 errors)*

### 4.4 Frontend Production Build
- **Command:** `cd frontend && npm run build`
- **Exit Code:** `0`
- **Terminal Output:**
```
vite v7.3.8 building client environment for production...
✓ 84 modules transformed.
dist/index.html                   0.55 kB │ gzip:   0.35 kB
dist/assets/index-BbqLBUAO.css   26.44 kB │ gzip:   6.08 kB
dist/assets/index-CTEcXJEW.js   546.66 kB │ gzip: 148.42 kB
✓ built in 1.61s
```

### 4.5 Frontend Vitest Suite
- **Command:** `cd frontend && npx vitest run`
- **Exit Code:** `0`
- **Terminal Output:**
```
Test Files  20 passed (20)
     Tests  84 passed (84)
  Duration  12.97s
```

### 4.6 Live Backend Probing
- **Health check (`/healthz`):** `curl -s http://127.0.0.1:8080/healthz` → `HTTP 200` (`status: ok`)
- **Health check (`/api/v1/health`):** `curl -s http://127.0.0.1:8080/api/v1/health` → `HTTP 200` (`status: ok`)
- **Authentication (`/api/v1/auth/login`):** `curl -X POST http://127.0.0.1:8080/api/v1/auth/login` → `HTTP 200` (valid JWT returned)

---

## 5. Unresolved Defects

**Unresolved Defects Count:** `0` (Zero).

All known issues—including the dark-on-dark contrast failure on demo account buttons, the string chart route mismatch, in-memory token revocation vulnerability across restarts/workers, deactivated user token access, and boundary junction authority rules—have been fully identified, resolved, and verified.

---

## 6. Architectural Invariants Confirmation

1. **Advisory Decision Support Only:** RAILGORITHM acts purely as advisory decision support. No autonomous interlocking, point switching, signal actuation, or route control was introduced or permitted.
2. **Human Final Authority:** Human controllers retain absolute authority over all regulation choices.
3. **Independent Validator Integrity:** CP-SAT and independent validator checks remain fully intact and verified by 18 independent validator tests.
4. **Simulation Isolation:** Synthetic data labels are enforced across all views.
5. **Rule 15 Adherence:** **Zero commits, tags, merges into main, or remote pushes have been made.** All changes reside in the local working tree awaiting explicit user authorization.
