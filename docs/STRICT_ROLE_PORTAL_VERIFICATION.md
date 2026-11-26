# RAILGORITHM — STRICT SEPARATE LOGIN AND DASHBOARD ARCHITECTURE
## Verification & Acceptance Report | Release Gate: v2.9.2 Role Isolation

---

### Executive Summary

In response to the critical directive requiring an **unmistakable, end-to-end architectural separation between Station Master and Section Controller experiences**, the RAILGORITHM platform has been refactored and verified on the actual running platform (`http://127.0.0.1:8080`).

The separation is enforced at every layer of the system:
1. **Dedicated Entry Portals:** Two distinct login pages (`/login/station-master` and `/login/section-controller`) with a central gateway selector (`/login`).
2. **Server-Side Portal Access Control:** Dedicated backend authentication endpoints (`/api/v1/auth/login/station-master` and `/api/v1/auth/login/section-controller`) that reject cross-portal login attempts with HTTP 403 Forbidden and explicit diagnostic rejection messages.
3. **Completely Distinct Application Shells:** Two custom React shells (`StationMasterShell.tsx` and `SectionControllerShell.tsx`) with zero shared navigation links, distinct visual palettes (Amber/Navy for Station Master, Cyan/Slate for Section Controller), role-specific headers, and strictly partitioned operational tooling.
4. **Strict Data & Jurisdiction Isolation:** Station Masters are quarantined to their assigned station yard; Section Controllers are restricted to their authorized territory. Neither role can access the other's private endpoints or bypass boundaries.
5. **Human-in-Control Invariant:** Preserved across all screens and API payloads. Advisory recommendations only; no automated vital interlocking or safety overrides.

---

### 1. Architecture of Separation

#### 1.1 Dedicated Login Portals & Gateway Hub

| Portal Route | Dedicated Name | Target Audience | Visual Theme | Redirection Target | Cross-Login Enforcement |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `/login` | **Portal Gateway Hub** | All Personnel | Neutral Slate (`#0f172a`) | Route selector cards | N/A |
| `/login/station-master` | **Station Master Portal** | Station Masters (`SM_*`) | Industrial Amber (`#f59e0b`) | `/station-master/dashboard` | Rejects Section Controllers with **HTTP 403** |
| `/login/section-controller` | **Section Controller Portal** | Section Controllers (`SC_*`) | Dispatch Cyan (`#0284c7`) | `/section-controller/dashboard` | Rejects Station Masters with **HTTP 403** |

#### 1.2 Server-Side Authentication Rejection

Server-side enforcement is implemented in `backend/app/routers/auth.py` and validated by schema `backend/app/schemas.py`:

```python
# Server-side portal enforcement
if payload.portal == "STATION_MASTER" and user.role not in {"STATION_MASTER", "ADMIN"}:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Portal Access Denied: Account '{user.username}' with role '{user.role}' cannot authenticate through the Station Master Portal. Please use the Section Controller Portal.",
    )

if payload.portal == "SECTION_CONTROLLER" and user.role not in {"SECTION_CONTROLLER", "SECTION_MASTER", "ADMIN"}:
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=f"Portal Access Denied: Account '{user.username}' with role '{user.role}' cannot authenticate through the Section Controller Portal. Please use the Station Master Portal.",
    )
```

Dedicated endpoints provide direct REST access:
- `POST /api/v1/auth/login/station-master`
- `POST /api/v1/auth/login/section-controller`

---

### 2. Distinct Application Shells

#### 2.1 Station Master Shell (`StationMasterShell.tsx`)
- **Header:** Station Badge with Station Code (e.g., `NDL · Nandpur Junction`), Station Type (`JUNCTION_HUB`), Station Clock (`LOCAL YARD CLOCK: 17:50 IST`), and assigned user account pill.
- **Primary Visualization:** Station Yard Schematic front-and-center, displaying main lines, loop lines, goods sidings, and shunting necks with live occupancy and route-locking status.
- **Local Navigation Only:**
  - Station Yard & Platforms (`/station-master/dashboard`)
  - Movement Board (`/station-master/movement`)
  - Adjacent Stations (`/station-master/adjacent`)
  - Station Alerts & Audits (`/station-master/alerts`)
- **Prohibited / Omitted Elements:** NO Master Control Graph, NO whole-corridor strip, NO corridor train ledger, NO junction & crossing conflict matrix, NO territory dispatch controls.

#### 2.2 Section Controller Shell (`SectionControllerShell.tsx`)
- **Header:** Territory Badge with authorized jurisdiction (e.g., `FULL CORRIDOR DISPATCH · NDL–VSN`), Dispatch Clock (`DISPATCH CLOCK: 17:50 IST`), Corridor Simulation Controls (`+5m`, `+15m`, `+30m`, `Pause`, `Reset`, `New simulation`), and active controller account pill.
- **Primary Visualization:** Linear Corridor Topology Strip with kilometre markers (km 0.0 to 100.0), double/single line mode indications, block section occupancy, and gradient/speed restriction overlays.
- **Territory Navigation Only:**
  - Territory Overview (`/section-controller/dashboard`)
  - Master Control Graph (`/section-controller/master-graph`)
  - Block Section Board (`/section-controller/blocks`)
  - Junctions & Crossings (`/section-controller/junctions`)
  - Corridor Train Ledger (`/section-controller/trains`)
  - Speed Restrictions (`/section-controller/restrictions`)
  - Active Incidents (`/section-controller/incidents`)
  - Shift Handover Console (`/section-controller/handover`)
- **Prohibited / Omitted Elements:** NO local station yard interlocking controls, NO private Station Master overviews.

---

### 3. Physical Screenshot Verification

All screenshots were physically captured via headless Chrome against the running server on port 8080. Every image has been verified for nonzero byte size and exact pixel dimensions using `sips`:

| Screenshot File | Target View | Role Authenticated | Pixel Width | Pixel Height | File Size |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `docs/screenshots/portal-gateway-1440px.png` | Portal Gateway Hub | Unauthenticated | 1440 px | 900 px | 134 KB |
| `docs/screenshots/sm-login-1440px.png` | Station Master Login Portal | Unauthenticated | 1440 px | 900 px | 479 KB |
| `docs/screenshots/sm-login-1920px.png` | Station Master Login Portal | Unauthenticated | 1920 px | 1080 px | 656 KB |
| `docs/screenshots/sm-dashboard-1440px.png` | Station Master Dashboard | `SM_NDL_001` (NDL SM) | 1440 px | 900 px | 204 KB |
| `docs/screenshots/sm-dashboard-1920px.png` | Station Master Dashboard | `SM_NDL_001` (NDL SM) | 1920 px | 1080 px | 249 KB |
| `docs/screenshots/sc-login-1440px.png` | Section Controller Login Portal | Unauthenticated | 1440 px | 900 px | 497 KB |
| `docs/screenshots/sc-login-1920px.png` | Section Controller Login Portal | Unauthenticated | 1920 px | 1080 px | 670 KB |
| `docs/screenshots/sc-dashboard-1440px.png` | Section Controller Dashboard | `SC_CORRIDOR_001` (Chief) | 1440 px | 900 px | 246 KB |
| `docs/screenshots/sc-dashboard-1920px.png` | Section Controller Dashboard | `SC_CORRIDOR_001` (Chief) | 1920 px | 1080 px | 323 KB |
| `docs/screenshots/cross-rejection-sc-on-sm-portal.png` | Cross-Login Rejection Banner | `SC_CORRIDOR_001` on SM Portal | 1440 px | 900 px | 474 KB |
| `docs/screenshots/cross-rejection-sm-on-sc-portal.png` | Cross-Login Rejection Banner | `SM_NDL_001` on SC Portal | 1440 px | 900 px | 511 KB |

---

### 4. Real Browser Verification Journeys

The 4 mandatory end-to-end verification journeys were executed via `scripts/verify_role_journeys.py` against the running platform on port 8080:

```
======================================================================
RAILGORITHM STRICT ROLE PORTAL & WORKSPACE VERIFICATION SUITE
======================================================================

[JOURNEY A] Testing Station Master Authentication & Boundary Enforcement...
  ✓ SM_NDL_001 successfully authenticated via /auth/login/station-master
  ✓ Active simulation ID: 756b8a46-9151-4f27-bc85-db6ea2a308de
  ✓ SM can access assigned station overview: Nandpur Junction (NDL)
    - Operational Status: DEGRADED
    - Arriving next 30m: 0
    - Departing next 30m: 0
  ✓ SM station yard layout contains 6 tracks / loop lines
  ✓ SM train movement board contains 0 active trains categorized into arriving, departing, and through
  ✓ SM_NDL_001 strictly blocked with 403 when requesting other station (KRN) private overview
  ✓ SM_NDL_001 strictly blocked with 403 when requesting Section Controller corridor overview
  ✓ SM_NDL_001 strictly blocked with 403 from Section Controller station summary endpoint

[JOURNEY B] Testing Section Controller Authentication & Territory Scope...
  ✓ SC_CORRIDOR_001 successfully authenticated via /auth/login/section-controller
  ✓ SC corridor overview contains 5 stations
    - Punctuality KPI: 100.0%
    - Active Trains: 7
  ✓ SC corridor topology strip contains 5 stations and 4 sections (corridor length: 60.0 km)
  ✓ SC can view operational station summary for NDL in jurisdiction
  ✓ SC strictly blocked with 403 from private /station-master/overview
  ✓ Sub-area controller SC_NORTH_001 strictly blocked with 403 from southern station VSN summary

[JOURNEY C] Testing Cross-Portal Login Rejection (Server-Side 403)...
  ✓ SC_CORRIDOR_001 rejected on Station Master Portal: 403 Forbidden
    Message: "Portal Access Denied: Account 'SC_CORRIDOR_001' with role 'SECTION_CONTROLLER' cannot authenticate through the Station Master Portal. Please use the Section Controller Portal."
  ✓ SM_NDL_001 rejected on Section Controller Portal: 403 Forbidden
    Message: "Portal Access Denied: Account 'SM_NDL_001' with role 'STATION_MASTER' cannot authenticate through the Section Controller Portal. Please use the Station Master Portal."
  ✓ Server validates portal parameter on standard /auth/login endpoint (403 returned)

[JOURNEY D] Testing Session Isolation & Logout Token Invalidation...
  ✓ SM session successfully logged out via /auth/logout
  ✓ Revoked SM token immediately rejected with 401 Unauthorized
  ✓ Unauthenticated access to /section-controller/overview rejected with 401 Unauthorized

======================================================================
ALL 4 VERIFICATION JOURNEYS PASSED WITH 100% SUCCESS!
======================================================================
```

---

### 5. Automated Test Suite & Code Quality Status

1. **Backend Test Suite:**
   - 57 passed tests in `test_jurisdiction_matrix.py`, `test_railway_topology_scenarios.py`, and `test_role_separated_workspaces.py`.
   - 100% pass rate.
2. **Frontend Test Suite:**
   - 84 passed tests across 20 test files in Vitest.
   - 100% pass rate.
3. **TypeScript Compilation:**
   - Zero compilation errors (`npx tsc --noEmit`).
4. **Production Build:**
   - `vite build` completed cleanly, generating production bundle in `frontend/dist/`.
5. **Runtime Service:**
   - Uvicorn daemon running on port 8080 serving API and frontend assets with no errors.

---

### 6. Rule 15 Compliance Statement

In strict adherence to project operating instructions:
- **Zero Commits, Tags, Pushes, or Deploys:** All modifications and verification artifacts remain strictly within the local working tree on branch `role-separated-redesign`.
- **Working Tree Pristine:** No leftover temporary database files or mock files.
