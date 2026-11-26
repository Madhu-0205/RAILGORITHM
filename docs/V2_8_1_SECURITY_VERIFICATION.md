# RAILGORITHM v2.8.1 — Security & Access Control Verification Report

## 1. Executive Summary

This report documents the security audit, access control verification, and automated regression test suite executed for RAILGORITHM v2.8.1. All tests were executed against FastAPI endpoints and SQLAlchemy database models to confirm server-side role and jurisdiction boundary enforcement.

---

## 2. Test Execution Summary

- **Total Backend Security Tests:** 8 tests in `backend/tests/test_v2_8_1_security_and_access.py`
- **Total Backend Suite Tests:** 270 passed across 18 test files
- **Total Frontend Suite Tests:** 84 passed across 20 test files
- **Regression Count:** 0 regressions detected

---

## 3. Verified Security & Access Invariants

### 3.1 Independent User Authentication (`test_v2_8_1_independent_logins`)
- Verified that all newly provisioned Station Master accounts (`SM_NDL_001`, `SM_KRN_001`, `SM_MLG_001`, `SM_SRP_001`, `SM_VSN_001`), Section Controller accounts (`SC_NORTH_001`, `SC_SOUTH_001`, `SC_CORRIDOR_001`), and Security Administrator (`ADMIN_001`) authenticate successfully with their credentials.
- Verified that `last_login_at` timestamps are updated on login.
- Verified that JWT payloads embed the user's role, zone, division, and jurisdiction metadata.

### 3.2 Role Boundary Enforcement (`test_station_master_forbidden_on_section_endpoints`)
- **Station Masters attempting Section Controller Operations:**
  - `GET /api/v1/simulations/{id}/analytics/section-controller`: Returned `403 Forbidden` (`detail: Forbidden: role SECTION_MASTER required`).
  - `POST /api/v1/simulations/{id}/advance`: Returned `403 Forbidden` (`detail: Forbidden: role SECTION_MASTER required`).
  - `POST /api/v1/simulations/{id}/closures`: Returned `403 Forbidden` (`detail: Forbidden: role SECTION_MASTER required`).
- Confirms Station Masters cannot perform corridor-level regulation, simulation stepping, or block closure injection.

### 3.3 Cross-Station Boundary Enforcement (`test_station_master_cross_station_access_forbidden`)
- `SM_NDL_001` (assigned strictly to Nandpur `NDL`) attempted to query `GET /api/v1/simulations/{id}/analytics/station-master?station_id=MLG`.
- Server returned `403 Forbidden` (`detail: Station access forbidden`).
- `SM_NDL_001` queried their own station `station_id=NDL` and received `200 OK` with valid platform berthing and station delay KPIs.
- Section Controllers (`SC_CORRIDOR_001`, `SC_NORTH_001`) querying stations within their territory received `200 OK`.

### 3.4 Dashboard Scoping by Jurisdiction (`test_dashboard_scoping_by_jurisdiction`)
- `SM_NDL_001` queried `GET /api/v1/simulations/{id}/dashboard`:
  - Verified `payload["jurisdiction"]["scope"] == "STATION"`.
  - Verified `payload["jurisdiction"]["station_id"] == "NDL"`.
  - Verified all platforms returned belong to `NDL`.
  - Verified all closures/outages returned affect `NDL`.
- `SC_NORTH_001` queried `GET /api/v1/simulations/{id}/dashboard`:
  - Verified `payload["jurisdiction"]["scope"] == "SECTION"`.
  - Verified sections are scoped to Northern Area (`S1`, `S2`).
  - Verified stations are scoped to Northern Area (`NDL`, `KRN`, `MLG`).

### 3.5 Token Revocation on Logout (`test_token_revocation_on_logout`)
- User authenticated and obtained a valid bearer token.
- User invoked `POST /api/v1/auth/logout`.
- Server added token to `_REVOKED_TOKENS` registry and emitted an audit log entry.
- Subsequent request to `GET /api/v1/auth/me` with the logged-out token returned `401 Unauthorized` (`detail: Token has been revoked. Please sign in again.`).

### 3.6 Password Management & Verification (`test_password_change`)
- User authenticated with initial password.
- Invoked `POST /api/v1/auth/change-password` with incorrect old password: received `400 Bad Request` (`detail: Current password incorrect`).
- Invoked `POST /api/v1/auth/change-password` with valid old password and new password (min 8 chars): received `200 OK`.
- Old password failed authentication on subsequent login (`401 Unauthorized`).
- New password successfully authenticated (`200 OK`).

### 3.7 Administrator User Management (`test_admin_user_management_and_deactivation`)
- `POST /api/v1/auth/users`: `ADMIN_001` created a new user `SM_NEW_001` assigned to `KRN`.
- Non-admin user (`SC_NORTH_001`) attempting to access `GET /api/v1/auth/users` received `403 Forbidden`.
- `ADMIN_001` deactivated user `SM_NEW_001` via `PATCH /api/v1/auth/users/{user_id}` (`{"active": false}`).
- Deactivated user attempted login: received `403 Forbidden` (`detail: User account is inactive. Please contact your administrator.`).

### 3.8 Recommendation & Decision Jurisdiction (`test_recommendation_and_decision_jurisdiction`)
- A recommendation affecting only Malgaon Junction (`MLG`) was generated.
- `SM_NDL_001` attempted to query `GET /api/v1/simulations/{id}/recommendations/{rec_id}`: received `403 Forbidden` (`detail: Recommendation outside station jurisdiction`).
- `SM_NDL_001` attempted to decide the recommendation via `POST /api/v1/simulations/{id}/recommendations/{rec_id}/decide`: received `403 Forbidden` (`detail: Decision outside station jurisdiction`).
- `SM_MLG_001` and `SC_CORRIDOR_001` accessed the recommendation with `200 OK`.

---

## 4. Security Verification Verdict

**Status: PASSED (100% Invariants Verified)**

The architecture satisfies all requirements for role isolation, territorial jurisdiction, cryptographic session invalidation, and advisory decision boundaries.
