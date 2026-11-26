# RAILGORITHM — Role-Separated Railway Operations Redesign
## Phase 0: Baseline Audit & Technical Architecture Specification

**Document Version:** 1.0.0  
**Target Release:** Next Development Version (Role-Separated Operations Workspaces)  
**Branch:** `role-separated-redesign`  
**Classification:** Operational System Redesign / Human Decision Support  
**Safety Principle:** *AI RECOMMENDS → INDEPENDENT VALIDATOR CHECKS → HUMAN CONTROLLER DECIDES → SYSTEM RECORDS*  
**Operating Framework:** Purely advisory decision support; non-vital operations assistance. Not certified for vital interlocking or direct signalling control.

---

### 1. Executive Summary & Core Mission

RAILGORITHM is an AI-assisted railway traffic management and human decision-support system. While previous releases established CP-SAT optimization, PPO reinforcement learning, an independent safety constraint validator, and jurisdiction-based authentication, the operational presentation layer still relied on a shared dashboard with minor conditional toggles.

In operational reality, railway operations partition control into two fundamentally distinct roles with differing mental models, temporal horizons, and geographical scopes:
1. **Station Master (SM):** Station-centric spatial and operational responsibility. The SM manages the station yard, platform tracks, reception/dispatch lines, passenger boarding, local shunting, line-clear exchanges with block cabins, and immediate adjacent block entries/exits.
2. **Section Controller (SC):** Whole-section / territory-level temporal and corridor responsibility. The SC coordinates traffic across dozens of kilometers and multiple stations, resolves inter-station precedence and crossings, monitors headway, manages section bottlenecks, and balances corridor-wide throughput.

This audit establishes the baseline deficiencies of the pre-redesign system, inspects current components, details information leakage and usability defects, and specifies the technical blueprint for two purpose-built workspaces.

---

### 2. Pre-Redesign Baseline Review & Existing Assets

#### 2.1 Backend Architecture
- **Framework:** FastAPI with Python 3.11+.
- **Authentication:** JWT bearer tokens, role model (`station_master`, `section_controller`, `admin`), bcrypt password hashing, token revocation tracking (`revoked_tokens` table), and password change invalidation timestamp.
- **Data Model:** SQLite / PostgreSQL with SQLAlchemy ORM. Models include `User`, `Simulation`, `Station`, `BlockSection`, `Train`, `TrainMovement`, `DecisionAudit`, `OperationalIncident`.
- **Domain Engines:**
  - `optimizer.py`: Google OR-Tools CP-SAT discrete optimization for train scheduling and platform allocation.
  - `pipeline.py`: Recommendation generation pipeline integrating PPO policy evaluation and constraint checking.
  - `validator.py`: Independent constraint validator checking headway, line capacity, single-line conflict avoidance, and traction compatibility.
  - `data_quality.py`: Dynamic assessment of telemetry completeness, freshness, and sensor confidence.
  - `projection.py`: Predictive train movement calculation along corridor sections.

#### 2.2 Frontend Architecture
- **Framework:** React 18 with TypeScript, Vite bundler, Lucide React icons, and custom CSS design system.
- **Current Routing:** Shared routes (`/`, `/dashboard`, `/master-control-graph`, `/recommendations`, `/recommendations/:id`, `/analytics`, `/login`).
- **Existing Components:**
  - `TimeDistanceGraph.tsx`: SVG-based Master Control Graph (distance vs. time) supporting direction filters, station zoom, and delay projections.
  - `StationWorkingDiagram.tsx`: Basic SVG diagram depicting station platforms and occupancy blocks.
  - `TrainMovementLedger.tsx`: Tabular overview of trains, status, speed, and platform assignment.
  - `DecisionReviewModal.tsx`: Controller approval/rejection modal for advisory recommendations.

#### 2.3 Baseline Visual Records Captured
Prior to code modifications, visual baseline captures were verified and stored in `docs/screenshots/`:
- `pre-redesign-sm-1440px.png` (Station Master view at 1440px)
- `pre-redesign-sm-1920px.png` (Station Master view at 1920px)
- `pre-redesign-sc-1440px.png` (Section Controller view at 1440px)
- `pre-redesign-sc-1920px.png` (Section Controller view at 1920px)

---

### 3. Identified Deficiencies in Existing Baseline

#### 3.1 Station Master Operational Blindspots
1. **Absence of Adjacent Station Awareness:**
   - The Station Master had no visibility into trains approaching from the preceding block station or heading toward the succeeding station.
   - For single-line sections (e.g. Karanpur to Malgaon Junction), knowing if an opposing train has cleared the block section is essential for granting Line Clear; the previous UI omitted block line-clear state and direction of flow.
2. **Simplified Station Yard Layout:**
   - Station platforms were depicted as generic rectangles without distinction between Main Lines, Common Loop Lines, Goods Sidings, and Shunting Necks.
   - Track states lacked operational granularity: only basic occupied/free states were shown, ignoring `RESERVED`, `RESTRICTED`, `BLOCKED`, `STALE`, or `UNKNOWN`.
3. **Misleading Telemetry & KPI Calculations:**
   - If zero trains were currently active at a station, the system frequently displayed "100% Schedule Adherence" instead of explicitly communicating `NO_DATA` or `NO_ELIGIBLE_TRAINS`.
4. **Scope Creep & Irrelevant Data:**
   - Station Masters were shown whole-corridor metrics (e.g., total corridor active trains across all 5 stations) that diluted local yard focus and created clutter.

#### 3.2 Section Controller Console Fragmentation
1. **Disconnected Operational Tools:**
   - The Section Controller had to flip between `/dashboard`, `/master-control-graph`, and `/recommendations` across different browser pages.
   - There was no integrated single-pane control console where the Master Control Graph, Block Section Board, and Junction Crossing Manager coexisted.
2. **Lack of Junction Precedence & Crossing Workspace:**
   - Meeting and overtaking decisions require side-by-side evaluation of Train A vs. Train B (e.g., Express 12002 overtaking Freight F901 at Malgaon Junction).
   - Controllers had no interactive comparative interface displaying delay impacts, safety constraints, loop availability, and feasibility rationales.
3. **Block Section Board Deficit:**
   - The section controller lacked a consolidated real-time board showing all block sections, their signaling status, axle-counter telemetry freshness, and occupancy.

#### 3.3 Authorization & Jurisdiction Gaps
1. **Coarse-Grained Authorization:**
   - Existing checks checked `role == "station_master"` but did not formalize fine-grained operational permissions:
     - `VIEW_OWN_STATION`
     - `VIEW_ADJACENT_CONTEXT`
     - `VIEW_AUTHORIZED_SECTION`
     - `VIEW_TRAIN_MOVEMENTS`
     - `VIEW_BLOCK_SECTIONS`
     - `VIEW_RECOMMENDATIONS`
     - `SUBMIT_DECISION`
     - `APPLY_DECISION`
     - `MANAGE_STATION_LOCAL`
     - `MANAGE_SECTION_COORDINATION`
2. **Adjacent Context vs. Station Authority Separation:**
   - Station Masters must be able to view operational context of adjacent stations without being given management authority over those adjacent stations. The backend lacked dedicated projection endpoints providing read-only adjacent context.
3. **Section Controller Boundary Enforcement:**
   - Section Controllers must not be able to execute station-local decisions outside their designated jurisdiction (e.g., `SC_NORTH_001` vs `SC_SOUTH_001`).

---

### 4. Target Architecture & Technical Specification

```
                                      +------------------------------------+
                                      |        FASTAPI BACKEND CORE        |
                                      +------------------------------------+
                                                        |
                         +------------------------------+------------------------------+
                         |                                                             |
            +---------------------------+                                 +---------------------------+
            |  Station Master Endpoints  |                                 | Section Controller Endpoints|
            +---------------------------+                                 +---------------------------+
            | • /station-master/overview|                                 | • /section-controller/    |
            | • /station-master/layout  |                                 |   overview                |
            | • /station-master/        |                                 | • /section-controller/    |
            |   movement-board          |                                 |   topology                |
            | • /station-master/        |                                 | • /section-controller/    |
            |   adjacent-stations       |                                 |   train-ledger            |
            | • /station-master/alerts  |                                 | • /section-controller/    |
            +---------------------------+                                 |   block-board             |
                         |                                                | • /section-controller/    |
                         v                                                |   junction-workspace      |
            +---------------------------+                                 | • /section-controller/    |
            |     STATION MASTER UI     |                                 |   alerts                  |
            +---------------------------+                                 +---------------------------+
            | 1. Station Overview & KPIs|                                              |
            | 2. Physical Yard Diagram  |                                              v
            | 3. Train Movement Board   |                                 +---------------------------+
            | 4. Adjacent Station Board |                                 |   SECTION CONTROLLER UI   |
            | 5. Station Alerts & AI    |                                 +---------------------------+
            +---------------------------+                                 | 1. Corridor Overview KPIs |
                                                                          | 2. Master Control Graph   |
                                                                          | 3. Section Topology Strip |
                                                                          | 4. Block Section Board    |
                                                                          | 5. Junction & Precedence  |
                                                                          | 6. Section Train Ledger   |
                                                                          | 7. Alert & AI Rec Centre  |
                                                                          +---------------------------+
```

#### 4.1 Fine-Grained Permission Matrix

| Operation / Capability | Station Master | Section Controller | System Admin |
|:---|:---:|:---:|:---:|
| `VIEW_OWN_STATION` | **YES** (Assigned Station) | **YES** (All in Section) | **YES** |
| `VIEW_ADJACENT_CONTEXT` | **YES** (Previous/Next Only) | **YES** (Full Section) | **YES** |
| `VIEW_AUTHORIZED_SECTION` | **NO** | **YES** (Assigned Section) | **YES** |
| `VIEW_TRAIN_MOVEMENTS` | **YES** (Local Station Scope) | **YES** (Section Scope) | **YES** |
| `VIEW_BLOCK_SECTIONS` | **YES** (Adjacent Blocks) | **YES** (All Section Blocks) | **YES** |
| `VIEW_RECOMMENDATIONS` | **YES** (Station-Local Only) | **YES** (Section Regulation) | **YES** |
| `SUBMIT_DECISION` | **YES** (Station-Local) | **YES** (Section Regulation) | **YES** |
| `APPLY_DECISION` | **YES** (Local Platform/Route) | **YES** (Corridor Precedence)| **YES** |
| `MANAGE_STATION_LOCAL` | **YES** (Assigned Station) | **NO** (Advisory Only) | **YES** |
| `MANAGE_SECTION_COORDINATION` | **NO** | **YES** (Assigned Section) | **YES** |

#### 4.2 Endpoint Design

##### Station Master Endpoints (`/api/v1/simulations/{id}/station-master/`)
1. `GET /overview?station_id={station_id}`
   - Returns station operational state, total scheduled today, arriving in 30 min, departing in 30 min, through trains, delayed count, average delay, and data quality confidence score. Returns `NO_DATA` when 0 trains match.
2. `GET /layout?station_id={station_id}`
   - Returns full physical track topology: Main Line, Loop 1, Loop 2, Goods Siding 1, Shunting Neck. Tracks include states: `CLEAR`, `OCCUPIED`, `RESERVED`, `RESTRICTED`, `BLOCKED`, `STALE`, `UNKNOWN`, with occupied train id, route lock status, length (meters), and electrification.
3. `GET /movement-board?station_id={station_id}`
   - Returns all station train calls (Arriving, Departing, Through). Includes Train No, Name, Type, Source, Destination, Scheduled Time, Estimated Time, Platform assigned, Status (`ON_TIME`, `DELAYED`, `EARLY`), and Speed.
4. `GET /adjacent-stations?station_id={station_id}`
   - Returns upstream and downstream adjacent station operational summaries: previous station, next station, connected junction lines, block section status (`CLEAR`, `OCCUPIED`, `BLOCKED`, `CLOSED`), block direction (`UP`, `DOWN`, `REVERSIBLE`), train currently in block, and last telemetry update timestamp.
5. `GET /alerts?station_id={station_id}`
   - Filtered active conflicts and validated AI recommendations concerning the assigned station only.

##### Section Controller Endpoints (`/api/v1/simulations/{id}/section-controller/`)
1. `GET /overview`
   - Corridor-level status: Section Name, Division, Operating Boundaries (e.g., Nandpur to Vasanthpur, 120 km), Monitored Stations count, Active Trains, Delayed Trains, Punctuality %, Occupied Blocks count, Critical Conflicts count, Telemetry Health.
2. `GET /topology`
   - Complete section track strip: Station nodes, inter-station distances (km), single-line vs double-line track segments, crossovers, automatic block signalling territories, active speed restrictions (TSR/PSR).
3. `GET /train-ledger`
   - Section-wide train movement ledger with real-time locations, current speed, cumulative delay, priority class (Rajdhani/Superfast/Freight), crew hours, and projected section exit time.
4. `GET /block-board`
   - Real-time status of all block sections across the territory: Section code, from/to station, track type (Single/Double), signal aspect (Green/Double-Yellow/Yellow/Red), occupancy status, train ID occupying, headway time to next train, sensor confidence.
5. `GET /junction-workspace`
   - Dedicated junction and crossing resolution workspace: Identifies convergence bottlenecks (e.g., Malgaon Junction), conflicting movements (Train A vs Train B), precedence proposals, estimated delay impact, loop clearance feasibility, and validator constraint verification.
6. `GET /alerts`
   - Unified conflict and advisory regulation queue: Section-level conflicts, projected head-to-head collisions, crossing delays, speed restrictions, and CP-SAT/PPO optimization recommendations with explanation breakdown.

---

### 5. Implementation & Verification Plan

1. **Phase 1: Security & Permission Matrix Enforcement**
   - Update `backend/app/deps.py` and `backend/app/models.py` with explicit permission attributes.
   - Enforce authorization checks in all new and existing routes.
2. **Phase 2: Station Master Backend Endpoints**
   - Implement dedicated query routers in `backend/app/routers/station_master.py`.
   - Add unit tests validating station isolation and adjacent context visibility.
3. **Phase 3: Section Controller Backend Endpoints**
   - Implement dedicated query routers in `backend/app/routers/section_controller.py`.
   - Add unit tests validating corridor aggregation and junction conflict detection.
4. **Phase 4 & 5: Frontend Workspaces & Navigation Integration**
   - Build `frontend/src/pages/StationMasterWorkspace.tsx` and subcomponents.
   - Build `frontend/src/pages/SectionControllerWorkspace.tsx` and subcomponents.
   - Update `App.tsx` and `Shell.tsx` for seamless role-based landing and visual navigation.
   - Ensure high-contrast railway aesthetic, professional schematic SVGs, and responsive layouts (1366x768, 1440x900, 1920x1080).
5. **Phase 6 & 7: Comprehensive Test Suite & Visual Verification**
   - Implement 35+ test suite in `backend/tests/test_role_separated_workspaces.py`.
   - Capture post-redesign screenshots at 1440px and 1920px.
   - Author final delivery report.
