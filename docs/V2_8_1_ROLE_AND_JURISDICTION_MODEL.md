# RAILGORITHM v2.8.1 — Role and Jurisdiction Architecture Specification

## 1. Executive Summary & Purpose

RAILGORITHM v2.8.1 establishes strict separation of duties, role-based access control (RBAC), and territorial jurisdiction boundaries across Indian Railways operational roles.

In previous releases, Station Master and Section Controller views were toggled client-side without strict server-side boundary enforcement. Release v2.8.1 replaces this with:
1. Independent user identities for Station Masters, Section Controllers, and System Administrators.
2. Server-side hierarchical jurisdiction enforcement across Zone, Division, Control Area, Section, and Station.
3. Client-side route and component guards preventing Station Masters from accessing section control tools or switching out of Station View.
4. Token revocation on logout, rate limiting, and password management.

---

## 2. Role Taxonomy & Authority Matrix

| Role Identifier | Operational Designation | Authority Scope | Typical Assignment | Permitted Operations | Restricted / Prohibited Operations |
|---|---|---|---|---|---|
| `STATION_MASTER` | Station Master (SM) | Single Station (or specific assigned stations) | Nandpur (`NDL`), Karanpur (`KRN`), Malgaon (`MLG`), Suryapur (`SRP`), Vasanthpur (`VSN`) | Monitor station train movements, berth status, local platform outages, review station-scoped recommendations | CANNOT switch to Section View; CANNOT view or decide corridor-level regulation recommendations; CANNOT view other stations' platform berths |
| `SECTION_CONTROLLER` / `SECTION_MASTER` | Section Controller (SC) / Chief Controller | Assigned Control Area or Entire Corridor | Northern Area (`S1`, `S2`), Southern Area (`S3`, `S4`), Full Corridor (`S1`–`S4`) | Monitor multi-station corridor, dispatch string chart (Master Control Graph), block occupancy matrix, conflict regulation workspace, decide corridor regulation recommendations | CANNOT access admin user management endpoints; decisions restricted to assigned control area |
| `ADMIN` | Security Administrator | System-wide administrative oversight | All zones, divisions, areas | User lifecycle management (create, update, activate/deactivate accounts), view all stations and sections | Advisory system administration only; no bypass of audit logging |

---

## 3. Jurisdiction Hierarchy & Data Model

The jurisdictional hierarchy is structured as follows:

```
Railway Zone (e.g., South Western Railway - SWR)
  └── Railway Division (e.g., Southern Division - SD)
        ├── Northern Control Area (NDL-MLG)
        │     ├── Section S1 (NDL ↔ KRN, km 0–25, Single Line)
        │     │     ├── Station NDL (Nandpur, km 0)
        │     │     └── Station KRN (Karanpur, km 25)
        │     └── Section S2 (KRN ↔ MLG, km 25–50, Double Line)
        │           └── Station MLG (Malgaon Junction, km 50)
        └── Southern Control Area (MLG-VSN)
              ├── Section S3 (MLG ↔ SRP, km 50–75, Single Line)
              │     └── Station SRP (Suryapur, km 75)
              └── Section S4 (SRP ↔ VSN, km 75–100, Double Line)
                    └── Station VSN (Vasanthpur, km 100)
```

### 3.1 User Schema & Jurisdiction Fields

In `backend/app/models.py`, the `User` entity includes:

```python
class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, default=generate_uuid)
    username = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="STATION_MASTER")
    display_name = Column(String, nullable=False)
    
    # Jurisdiction Model
    zone = Column(String, nullable=False, default="SWR")
    division = Column(String, nullable=False, default="Southern Division")
    control_area = Column(String, nullable=True)  # e.g. "NORTHERN_CONTROL_AREA", "SOUTHERN_CONTROL_AREA", "CORRIDOR"
    assigned_stations = Column(JSON, nullable=True)  # List of station codes: ["NDL"], ["MLG"], etc.
    assigned_sections = Column(JSON, nullable=True)  # List of section codes: ["S1", "S2"], etc.
    
    # Security & Audit
    active = Column(Boolean, nullable=False, default=True)
    last_login_at = Column(DateTime, nullable=True)
    password_changed_at = Column(DateTime, nullable=True)
```

### 3.2 Access Verification Methods

The `User` model defines deterministic helper methods for jurisdiction checks:

- `can_access_station(station_id: str) -> bool`:
  - Returns `True` if user is `ADMIN` or `SECTION_CONTROLLER` (with assigned station in territory).
  - Returns `True` for `STATION_MASTER` if and only if `station_id` matches `self.station_id` or is contained in `self.assigned_stations`.
  - Returns `False` otherwise.
- `can_access_section(section_id: str) -> bool`:
  - Returns `True` if user is `ADMIN` or `SECTION_CONTROLLER` whose territory encompasses `section_id`.
  - Returns `False` for `STATION_MASTER`.

---

## 4. Configured User Directory

| Username | Role | Display Name | Jurisdiction Area | Assigned Stations | Assigned Sections |
|---|---|---|---|---|---|
| `SC_CORRIDOR_001` | `SECTION_CONTROLLER` | Chief Controller (Corridor) | Entire Corridor | `NDL`, `KRN`, `MLG`, `SRP`, `VSN` | `S1`, `S2`, `S3`, `S4` |
| `SC_NORTH_001` | `SECTION_CONTROLLER` | Section Controller (North) | Northern Control Area | `NDL`, `KRN`, `MLG` | `S1`, `S2` |
| `SC_SOUTH_001` | `SECTION_CONTROLLER` | Section Controller (South) | Southern Control Area | `MLG`, `SRP`, `VSN` | `S3`, `S4` |
| `SM_NDL_001` | `STATION_MASTER` | SM Nandpur | Nandpur Station (km 0) | `NDL` | — |
| `SM_KRN_001` | `STATION_MASTER` | SM Karanpur | Karanpur Station (km 25) | `KRN` | — |
| `SM_MLG_001` | `STATION_MASTER` | SM Malgaon | Malgaon Junction (km 50) | `MLG` | — |
| `SM_SRP_001` | `STATION_MASTER` | SM Suryapur | Suryapur Station (km 75) | `SRP` | — |
| `SM_VSN_001` | `STATION_MASTER` | SM Vasanthpur | Vasanthpur Station (km 100) | `VSN` | — |
| `ADMIN_001` | `ADMIN` | Security Administrator | All Corridors | All | All |
| `section.master` | `SECTION_CONTROLLER` | Section Controller (Legacy) | Entire Corridor | All | All |
| `station.master` | `STATION_MASTER` | Station Master (Legacy) | Malgaon Station | `MLG` | — |

---

## 5. Server-Side Enforcement (FastAPI Dependencies)

### 5.1 Route Protection & Dependency Chaining

1. **`require_roles(*roles)`**:
   Validates bearer token, checks whether user is active, verifies token has not been revoked in `_REVOKED_TOKENS`, and verifies user role membership (treating `SECTION_MASTER` and `SECTION_CONTROLLER` as equivalent, and allowing `ADMIN`).
2. **`verify_station_access(station_id, user)`**:
   Enforces that Station Masters can only query analytics, platform states, or yard data for their assigned station. Throws `HTTPException(403, "Station access forbidden")` if unauthorized.
3. **`verify_section_access(section_id, user)`**:
   Enforces that users can only query section-specific control data if their jurisdiction includes the section.
4. **Recommendation Scoping**:
   - `GET /recommendations/{id}`: If the requesting user is a Station Master, the endpoint validates that `station_id in rec.affected_stations`. If outside jurisdiction, returns `403 Forbidden`.
   - `POST /recommendations/{id}/decide`: `_authorize_scope` in `decision_service.py` prevents Station Masters from deciding recommendations outside their station, and prevents area Section Controllers from deciding recommendations outside their control area.
5. **Dashboard Scoping**:
   `GET /simulations/{id}/dashboard` scopes the payload:
   - For a Station Master assigned to `NDL`, returns trains berthed or approaching `NDL`, platform outages at `NDL`, and returns an explicit `jurisdiction` object.
   - For a Section Controller, returns their assigned territory sections, trains, and blocks.

---

## 6. Client-Side Enforcement

1. **View Locking**:
   In `frontend/src/pages/Dashboard.tsx`, `isStationMaster` locks the interface to Station View. The role switcher button group is only visible to Section Controllers and Admins. Station Masters see an immutable badge: `STATION MASTER JURISDICTION`.
2. **Station Dropdown Scoping**:
   In Station View, the station selector dropdown is filtered to `authorizedStations`. For single-station Station Masters (`SM_NDL_001`), the selector is locked to `NDL`.
3. **Navigation Visibility**:
   In `frontend/src/components/Shell.tsx`, Section-only routes (`/disruptions`, `/audit`, `/simulation/new`) are hidden from Station Masters. The user chip displays the user's role, zone, division, and station/territory badge (e.g. `Scope: station NDL`).
