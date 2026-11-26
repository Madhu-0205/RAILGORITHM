# RAILGORITHM v2.8.1 — Authentication, Access Control & UI Filter Audit
**Document ID:** `V2_8_1_AUTHENTICATION_AND_ACCESS_AUDIT.md`  
**Date:** 2026-11-25  
**Version:** v2.8.1 Release Candidate Baseline  
**Classification:** Operational Security & Architecture Audit  

---

## 1. Executive Summary

An audit of RAILGORITHM v2.8 was conducted covering authentication, identity management, role authorization, operational jurisdiction enforcement, and UI filter components.

The audit revealed that while v2.8 features robust cryptographic hashing (PBKDF2-HMAC-SHA256) and signed JWT tokens:
1. **Frontend Role View Illusion:** In `Dashboard.tsx`, Station Masters and Section Controllers are provided client-side toggle buttons (`[Station View | Section View]`) and dropdowns that allow any authenticated Station Master to switch into the Section Controller corridor view, and inspect any station's operational platform and train data regardless of their assignment.
2. **Backend Jurisdiction Enforcement Gaps:** Key operational endpoints (`/simulations/{id}/dashboard`, `/trains`, `/network`, `/analytics/station-master`) do not enforce station or section territory boundaries at the query/service layer. An authenticated user can pass arbitrary query parameters (`?station_id=NDL`) to inspect another station's telemetry.
3. **Coarse Role Model & Shared Demo Accounts:** Only two shared demo accounts existed (`section.master` and `station.master`), lacking individual user identities for each station (`NDL`, `KRN`, `MLG`, `SRP`, `VSN`) and control area (`North`, `South`, `Corridor`).
4. **Master Control Graph UI Visibility Defect:** On `MasterControlGraphPage.tsx` and `TimeDistanceGraph.tsx`, filter buttons placed inside dark command panels (`#0F172A` / `#1E293B`) use `.button-ghost`, which inherits text color `var(--text)` (`#0F172A`), rendering buttons as blank dark outlined boxes with invisible text. Furthermore, essential operational filters (station filter, train search, operational overlays: single-line, engineering restrictions, station dwell, bottlenecks, reset/refresh) were either absent, disconnected, or split awkwardly between disparate toolbars.

---

## 2. Component-by-Component Security Audit

### 2.1 User Model & Database Schema (`backend/app/models.py`)
- **Current Structure:**
  - `id`: UUID (String 36).
  - `username`: String(80) unique.
  - `password_hash`: String(255) containing PBKDF2 parameters and digest.
  - `role`: String(32) — values `SECTION_MASTER`, `STATION_MASTER`.
  - `display_name`: String(120).
  - `station_id`: String(16) nullable. Single station ID (e.g., `MLG`).
  - `section_id`: String(32) nullable. Single section string (e.g., `north-section`).
  - `active`: Boolean flag.
  - `created_at`: DateTime UTC.
- **Identified Deficiencies:**
  - **No Jurisdiction Hierarchy:** Lacks zone, division, control area, and multi-station / multi-section assignment support. A Station Master cannot be authorized for a group of stations or junction loops; a Section Controller cannot have structured control territories (`NORTH`, `SOUTH`, `CORRIDOR`).
  - **No Last Login or Password Change Timestamp:** Missing `last_login_at` and `password_changed_at` fields necessary for session auditing and security lifecycle.
  - **Role Naming Inconsistency:** Uses `SECTION_MASTER` in DB/backend code instead of Indian Railways standard `SECTION_CONTROLLER`. (Must maintain backward compatibility while supporting `SECTION_CONTROLLER`).

### 2.2 Password Hashing & Security (`backend/app/security.py`)
- **Strengths:**
  - Standard library PBKDF2-HMAC-SHA256 with 240,000 iterations and 16-byte random salt.
  - Constant-time comparison (`hmac.compare_digest`).
  - Secure signed tokens using HMAC-SHA256 with timestamp verification (`iat`, `exp`).
- **Deficiencies:**
  - JWT token payload contains only `sub` and `role`. It does not contain `station_id`, `assigned_stations`, `control_area`, or `assigned_sections`.
  - No token revocation or session invalidation on logout.
  - Password change endpoint does not exist.

### 2.3 Authentication Endpoints (`backend/app/routers/auth.py`)
- **Strengths:**
  - In-process sliding-window rate limiting on `/login` (default 10 attempts/minute per IP).
  - Audit logging of `USER_LOGIN` events.
  - `/me` endpoint returns currently authenticated user details.
- **Deficiencies:**
  - No `/auth/change-password` endpoint.
  - No `/auth/logout` endpoint that invalidates tokens or logs out audit events.
  - No administrative user management endpoints (`/auth/users` for creating users, changing jurisdictions, activating/deactivating accounts).

### 2.4 Role & Jurisdiction Enforcement in Backend Routers

| Endpoint | Current Enforcement | Vulnerability / Gap |
| :--- | :--- | :--- |
| `POST /simulations` | `require_roles("SECTION_MASTER")` | Station Master correctly rejected (403). |
| `GET /simulations/{id}/dashboard` | `get_current_user` | Returns corridor-wide train movements, all platform berths, and all block sections. Only conflicts are filtered for Station Master. Station Master receives complete telemetry of all other stations. |
| `GET /simulations/{id}/trains` | `get_current_user` | Completely unscoped. Station Master sees all corridor trains. |
| `GET /simulations/{id}/network` | `get_current_user` | Completely unscoped. Station Master sees all sections and blocks across entire division. |
| `GET /simulations/{id}/conflicts` | `_scoped_conflicts` | Filters conflicts by station ID if `STATION_MASTER`. However, Section Controller has no area/territory boundary check. |
| `GET /simulations/{id}/analytics/station-master` | `get_current_user` | Accepts `station_id: str | None = None`. If an attacker passes `?station_id=NDL` while assigned to `MLG`, it returns Nandpur station KPIs without authorization check! |
| `GET /simulations/{id}/analytics/section-controller` | `get_current_user` | Unscoped; any Station Master can call this and receive corridor-level section controller KPIs. |
| `GET /recommendations/{id}` | `get_current_user` | Rejects Station Master if station not in `affected_stations`. But Section Controller territory boundary is not enforced. |
| `POST /recommendations/{id}/decision` | `submit_decision` | `_authorize_scope` checks that `affected_stations` is subset of `user.station_id` for Station Master. Section Controller is permitted without territory check. |
| `GET /audit` | `require_roles("SECTION_MASTER")` | Station Master correctly rejected (403). |

### 2.5 Frontend Route & State Security (`frontend/src/`)
- **Route Guards (`App.tsx`):**
  - Protected by `<RequireAuth>` and `<RequireRole>`.
  - While routes like `/graph`, `/blocks`, `/crossings`, `/restrictions`, `/incidents`, `/audit` are wrapped in `<RequireRole roles={["SECTION_MASTER"]}>`, `/` (Dashboard) is shared.
- **Dashboard Role Switching Defect (`Dashboard.tsx`):**
  - Lines 103–105 and 275–290: View mode is controlled by React local state `useState<"STATION" | "SECTION">`.
  - Buttons "Station View" and "Section View" are visible to all users. A Station Master can simply click "Section View" to render corridor dispatch, all section blocks, and crossing matrices.
  - The station selector dropdown (`NDL`, `KRN`, `MLG`, `SRP`, `VSN`) in Station View lets Station Masters switch to any station, triggering `api.stationKpis` for unauthorized stations.
  - **Required Fix:** Server-side enforced view mode based on authenticated user's assigned jurisdiction. Station Master must be locked to their authorized station(s). Section Controller must be locked to their assigned territory.

---

## 3. Master Control Graph Filter UI Defect Analysis

### 3.1 Defect Description
In `TimeDistanceGraph.tsx` and `MasterControlGraphPage.tsx`:
1. **Low Contrast / Invisible Text:**
   - Container has background `#0F172A` (dark navy).
   - Filter buttons use class `button-ghost`.
   - In `styles.css`, `.button-ghost` has `background: transparent; border-color: var(--border);` and inherits `color: var(--text)` (`#0F172A`).
   - Consequently, text inside the button has `#0F172A` color rendered directly on `#0F172A` background, rendering button labels invisible to the operator.
2. **Duplicated & Disconnected Toolbars:**
   - `MasterControlGraphPage.tsx` rendered a top toolbar with direction buttons, class dropdown, and conflict checkbox.
   - `TimeDistanceGraph.tsx` rendered an inner toolbar with direction buttons, category dropdown, time pan buttons, time window buttons, and trajectory checkboxes.
   - The two toolbars competed for space, duplicated direction filters, and left critical filters missing.
3. **Missing Critical Filters:**
   - **Station Filter:** Operator could not focus the graph on a specific station.
   - **Train Search / Selector:** Operator could not isolate a single train's string trajectory.
   - **Operational Overlays:** Missing toggles for single-line sections, engineering restrictions, station dwell bands, and bottlenecks.
   - **Reset & Refresh Controls:** Missing one-click "Reset Filters" and "Refresh Telemetry" actions.

---

## 4. Remediation Plan

1. **User Identity & Jurisdiction Hierarchy:**
   - Enhance `User` model with `zone`, `division`, `control_area`, `assigned_stations` (JSON list), `assigned_sections` (JSON list), `last_login_at`, and `password_changed_at`.
   - Seed independent simulation accounts:
     - `SM_NDL_001` (Nandpur), `SM_KRN_001` (Karanpur), `SM_MLG_001` (Malgaon Junction), `SM_SRP_001` (Suryapur), `SM_VSN_001` (Vasanthpur).
     - `SC_NORTH_001` (Northern Control Area: NDL, KRN, MLG), `SC_SOUTH_001` (Southern Control Area: MLG, SRP, VSN), `SC_CORRIDOR_001` (Full Corridor).
     - `ADMIN_001` (System Administrator).
   - Retain legacy demo credentials as explicitly labeled demo accounts for backwards compatibility with tests.
2. **Backend Server-Side Jurisdiction Enforcement:**
   - Update `deps.py` with `require_station_access(station_id)` and `require_section_access(section_id)`.
   - Filter `/dashboard`, `/trains`, `/network`, `/conflicts`, `/recommendations`, and `/analytics/station-master` to restrict data strictly to the user's authorized operational jurisdiction.
   - Reject unauthorized requests with HTTP 403 Forbidden.
3. **Account Management & Security Endpoints:**
   - Add `/auth/change-password`, `/auth/logout`, and admin user management `/auth/users`.
4. **Master Control Graph Filter Overhaul:**
   - Unify and redesign the filter toolbar with visible labels, high-contrast accessible styling, clear active states, and full operational filter capabilities (Direction, Category, Station, Train Search, Time Window, Trajectory Visibility, Overlays, Reset).
5. **Universal Filter Standardization:**
   - Ensure all list and graph views across RAILGORITHM adhere to consistent, accessible filter patterns.
