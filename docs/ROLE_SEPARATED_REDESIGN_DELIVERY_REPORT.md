# RAILGORITHM — Role-Separated Railway Operations Redesign
## Final Engineering Verification & Delivery Report

**Document Version:** 1.0.0  
**Target Release:** Role-Separated Operations Workspaces  
**Active Git Branch:** `role-separated-redesign`  
**Classification:** Core Operations Architectural Transformation  
**Safety Mandate:** *AI RECOMMENDS → INDEPENDENT VALIDATOR CHECKS → HUMAN CONTROLLER DECIDES → SYSTEM RECORDS*  
**Operational Status:** Purely advisory human decision support; synthetic simulation environment. Not certified for vital interlocking or direct signal execution.

---

### 1. Executive Summary & Purpose of the Redesign

In railway operations, managing a railway yard and regulating traffic across an entire territorial corridor require fundamentally different operational awareness, temporal horizons, and decision responsibilities:
1. **Station Master (SM):**
   - **Operational Focus:** Yard-centric and spatial.
   - **Key Responsibilities:** Managing platform lines, loop reception/dispatch lines, passenger berthing, freight siding staging, route locking, shunting operations, and point-to-point Line Clear communication with block cabins at adjacent stations.
   - **Core Need:** A station-focused console providing local yard layout status, arriving/departing/through train boards, and critical adjacent block awareness (what trains are approaching or leaving toward adjacent stations).
2. **Section Controller (SC):**
   - **Operational Focus:** Corridor-wide and temporal.
   - **Key Responsibilities:** Coordinating traffic over multi-station sections (60+ km), resolving single-line meet-and-cross conflicts, managing junction bottlenecks (e.g. Malgaon Junction), optimizing corridor throughput, and overseeing overall section punctuality.
   - **Core Need:** An integrated single-pane control console combining the Master Control Graph (time-distance chart), section topology strip, live block section board, junction precedence workspace, and territory-wide train ledger.

Prior to this redesign, both roles shared a generic dashboard with minor conditional toggles, causing significant operational deficiencies:
- Station Masters lacked visibility into adjacent station blocks and approaching trains, creating blindspots for Line Clear granting.
- Station layouts were portrayed as basic generic boxes without distinction between Main Lines, Loops, Goods Sidings, and Shunting Necks.
- Schedule adherence misleadingly showed 100% when 0 trains were active.
- Section Controllers had to switch between fragmented browser pages to consult the Master Control Graph, block occupancy, and junction regulations.
- Operational visibility was conflated with execution authority.

This release successfully transforms RAILGORITHM into two dedicated, professional, visually distinct railway operations workspaces backed by fine-grained jurisdiction authorization, robust domain endpoints, and an extensive 35+ test suite.

---

### 2. Architecture & Code Changes

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           FASTAPI BACKEND CORE                              │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
        ┌──────────────────────────────┴──────────────────────────────┐
        ▼                                                             ▼
┌────────────────────────────────┐            ┌────────────────────────────────┐
│   STATION MASTER ENDPOINTS     │            │  SECTION CONTROLLER ENDPOINTS  │
│  (routers/station_master.py)   │            │(routers/section_controller.py) │
├────────────────────────────────┤            ├────────────────────────────────┤
│ • GET /overview                │            │ • GET /overview                │
│ • GET /layout                  │            │ • GET /topology                │
│ • GET /movement-board          │            │ • GET /train-ledger            │
│ • GET /adjacent-stations       │            │ • GET /block-board             │
│ • GET /alerts                  │            │ • GET /junction-workspace      │
│                                │            │ • GET /alerts                  │
└────────────────────────────────┘            └────────────────────────────────┘
        │                                                             │
        ▼                                                             ▼
┌────────────────────────────────┐            ┌────────────────────────────────┐
│      STATION MASTER UI         │            │    SECTION CONTROLLER UI       │
│(pages/StationMasterWorkspace)  │            │(pages/SectionControllerWorkspace│
├────────────────────────────────┤            ├────────────────────────────────┤
│ 1. Station Yard Working Diagram│            │ 1. Territory Overview KPIs     │
│ 2. Real-Time Movement Board    │            │ 2. Section Topology Strip      │
│ 3. Adjacent Station Awareness  │            │ 3. Embedded Time-Distance Graph│
│ 4. Local Interlocking Alerts   │            │ 4. Corridor Block Board        │
│ 5. Clean NO_DATA KPI Badging   │            │ 5. Junction & Precedence WS    │
│                                │            │ 6. Section Train Ledger        │
└────────────────────────────────┘            └────────────────────────────────┘
```

#### 2.1 Backend Implementation
1. **Fine-Grained Permission Enforcement (`backend/app/models.py` & `backend/app/deps.py`):**
   - Added explicit permissions: `VIEW_OWN_STATION`, `VIEW_ADJACENT_CONTEXT`, `VIEW_AUTHORIZED_SECTION`, `VIEW_TRAIN_MOVEMENTS`, `VIEW_BLOCK_SECTIONS`, `VIEW_RECOMMENDATIONS`, `SUBMIT_DECISION`, `APPLY_DECISION`, `MANAGE_STATION_LOCAL`, `MANAGE_SECTION_COORDINATION`.
   - Separated **visibility** from **execution authority**: Station Masters can view adjacent operational context (`can_view_adjacent()`) without gaining administrative access to adjacent station accounts.
   - Enforced that Section Controllers coordinate territory regulation (`MANAGE_SECTION_COORDINATION`) while station yard execution remains with the Station Master (`MANAGE_STATION_LOCAL`).
2. **Dedicated Station Master Router (`backend/app/routers/station_master.py`):**
   - `GET /overview`: Returns station status, summary counts (arriving, departing, through, berthed), platform occupancy, data quality, and schedule adherence (with explicit `NO_DATA` handling when 0 trains match).
   - `GET /layout`: Returns complete station yard lines (Main Lines, Loop Lines, Platforms, Goods Sidings, Shunting Neck) with operational states (`CLEAR`, `OCCUPIED`, `RESERVED`, `RESTRICTED`, `BLOCKED`), route locking, and speed restrictions.
   - `GET /movement-board`: Returns tabular trains categorized into Arriving, Departing, Through, and Recent History with line clear communication status.
   - `GET /adjacent-stations`: Returns upstream (rear station) and downstream (advance station) block section states, line clear token status, approaching trains, and connected junction branches.
   - `GET /alerts`: Returns conflicts and recommendations strictly scoped to the assigned station.
3. **Dedicated Section Controller Router (`backend/app/routers/section_controller.py`):**
   - `GET /overview`: Corridor overview, operating boundaries, monitored stations summary, active/delayed trains, occupied blocks, critical bottlenecks, punctuality, and delay propagation index.
   - `GET /topology`: Linear corridor strip covering 60 km, station nodes, single/double line segments, and engineering speed restrictions (TSR/PSR).
   - `GET /train-ledger`: Real-time section ledger with positions (km), speed, delay, priority class, crew duty hours, and projected exit time.
   - `GET /block-board`: Real-time board of all corridor blocks (`B1`, `B2U`, `B2D`, `B3`, `B4U`, `B4D`), signal aspects (Green/Yellow/Red), and axle-counter health.
   - `GET /junction-workspace`: Convergence bottleneck resolution (e.g. Malgaon Junction), side-by-side comparative analysis of Train A vs Train B, delay impacts, net corridor savings, and G&SR rule verification.
   - `GET /alerts`: Corridor-wide conflicts and CP-SAT / PPO optimization advisories.

#### 2.2 Frontend Implementation
1. **Station Yard Working Diagram (`frontend/src/components/StationYardDiagram.tsx`):**
   - High-contrast interactive SVG diagram rendering platform lines, main lines, common loops, goods siding, and shunting neck.
   - Railway color coding (Green: Clear, Red: Occupied, Amber: Restricted/Outage, Cyan: Reserved Route).
   - Interactive track selection displaying length, electrification, maximum speed, route lock status, and occupant details.
2. **Adjacent Station Operational Awareness Panel (`frontend/src/components/AdjacentStationAwareness.tsx`):**
   - Visual upstream and downstream station cards showing connecting section mode (Single vs Double), block states, line-clear token indicators, approaching train telemetry, and connected junction branches.
3. **Section Topology Strip (`frontend/src/components/SectionTopologyStrip.tsx`):**
   - Linear 60 km section strip rendering station nodes, double lines, single-line bottleneck segments, occupied block indicators, and temporary speed restriction (TSR) markers.
4. **Junction Crossing & Precedence Management Workspace (`frontend/src/components/JunctionWorkspace.tsx`):**
   - Purpose-built decision-support interface for Section Controllers to evaluate conflicting train movements (e.g., Shatabdi Express overtaking Container Freight at Malgaon Junction).
   - Compares AI Recommended Resolution vs Alternative Option with net corridor time savings and safety constraints.
5. **Workspaces & Shell Integration (`frontend/src/pages/`, `frontend/src/App.tsx`, `frontend/src/components/Shell.tsx`):**
   - `StationMasterWorkspace.tsx`: Comprehensive yard control workspace.
   - `SectionControllerWorkspace.tsx`: Integrated multi-station console embedding the Master Control Graph (`TimeDistanceGraph.tsx`).
   - Seamless role-based routing (`/` automatically lands Station Masters on `/station-master` and Section Controllers on `/section-controller`).

---

### 3. Permission & Jurisdiction Access Matrix

| Operation / Endpoint | Station Master | Section Controller | Administrator |
|:---|:---:|:---:|:---:|
| `GET /station-master/overview` (Own Station) | **ALLOWED** | **ALLOWED** (In Area) | **ALLOWED** |
| `GET /station-master/overview` (Other Station) | **403 FORBIDDEN** | **403 FORBIDDEN** (Outside Area) | **ALLOWED** |
| `GET /station-master/layout` (Own Station) | **ALLOWED** | **ALLOWED** (In Area) | **ALLOWED** |
| `GET /station-master/movement-board` | **ALLOWED** (Own Station) | **ALLOWED** (In Area) | **ALLOWED** |
| `GET /station-master/adjacent-stations` (Bordering) | **ALLOWED** | **ALLOWED** | **ALLOWED** |
| `GET /station-master/adjacent-stations` (Non-Bordering)| **403 FORBIDDEN** | **ALLOWED** | **ALLOWED** |
| `GET /section-controller/overview` | **403 FORBIDDEN** | **ALLOWED** | **ALLOWED** |
| `GET /section-controller/topology` | **403 FORBIDDEN** | **ALLOWED** | **ALLOWED** |
| `GET /section-controller/block-board` | **403 FORBIDDEN** | **ALLOWED** | **ALLOWED** |
| `GET /section-controller/junction-workspace` | **403 FORBIDDEN** | **ALLOWED** | **ALLOWED** |
| `GET /section-controller/train-ledger` | **403 FORBIDDEN** | **ALLOWED** | **ALLOWED** |
| `POST /simulations` (Create Simulation) | **403 FORBIDDEN** | **ALLOWED** | **ALLOWED** |
| `POST /recommendations/{id}/decide` (Local Action) | **ALLOWED** (Own Station) | **ALLOWED** (Section Level) | **ALLOWED** |

---

### 4. Physical Screenshot Verification

All 8 screenshots physically exist on disk in `docs/screenshots/`, have nonzero file sizes, and were verified for correct dimensions (1440x900 and 1920x1080) and operational contents:

| Screenshot File | Resolution | Size | Role / Subject | Operational Verification Details |
|:---|:---:|:---:|:---:|:---|
| `docs/screenshots/pre-redesign-sm-1440px.png` | 1440x900 | 203 KB | Station Master (Baseline) | Pre-redesign baseline dashboard; lacked adjacent station awareness and yard lines. |
| `docs/screenshots/pre-redesign-sm-1920px.png` | 1920x1080 | 222 KB | Station Master (Baseline) | High-res pre-redesign baseline; showed whole-corridor metrics leaked to SM. |
| `docs/screenshots/pre-redesign-sc-1440px.png` | 1440x900 | 250 KB | Section Controller (Baseline)| Pre-redesign baseline; Master Control Graph disconnected from block board. |
| `docs/screenshots/pre-redesign-sc-1920px.png` | 1920x1080 | 315 KB | Section Controller (Baseline)| Pre-redesign baseline; lacked junction crossing decision workspace. |
| `docs/screenshots/post-redesign-sm-1440px.png` | 1440x900 | 218 KB | Station Master (Redesigned)| **Verified**: Station yard diagram (Main/Loop/Siding), Adjacent Station board, clean NO_DATA adherence. |
| `docs/screenshots/post-redesign-sm-1920px.png` | 1920x1080 | 259 KB | Station Master (Redesigned)| **Verified**: Full 1920px widescreen layout, Movement Board with Line Clear communication tokens. |
| `docs/screenshots/post-redesign-sc-1440px.png` | 1440x900 | 241 KB | Section Controller (Redesigned)| **Verified**: Territory Overview, Section Topology Strip, Block Section Board, Junction Precedence WS. |
| `docs/screenshots/post-redesign-sc-1920px.png` | 1920x1080 | 322 KB | Section Controller (Redesigned)| **Verified**: Embedded Master Control Graph, live train ledger, delay propagation index. |

---

### 5. Automated Verification & Test Suite Results

#### 5.1 New Role-Separated Workspaces Test Suite (35 Tests)
All 35 tests in `backend/tests/test_role_separated_workspaces.py` passed with 100% success rate:
- **Category 1: Role Isolation & Access Control (Tests 1–10):**
  - `test_01_station_master_can_view_own_station`: PASSED
  - `test_02_station_master_cannot_view_other_station_overview`: PASSED
  - `test_03_station_master_cannot_access_section_controller_overview`: PASSED
  - `test_04_station_master_can_view_adjacent_station_context`: PASSED
  - `test_05_station_master_cannot_view_non_adjacent_station_context`: PASSED
  - `test_06_section_controller_can_view_territory_overview`: PASSED
  - `test_07_section_controller_can_view_jurisdiction_stations`: PASSED
  - `test_08_section_controller_cannot_view_station_outside_jurisdiction`: PASSED
  - `test_09_section_controller_lacks_manage_station_local`: PASSED
  - `test_10_admin_has_universal_access`: PASSED
- **Category 2: Station Master Functionality & Domain Model (Tests 11–18):**
  - `test_11_station_overview_metrics_structure`: PASSED
  - `test_12_station_adherence_handles_no_data_cleanly`: PASSED
  - `test_13_station_layout_tracks_and_sidings`: PASSED
  - `test_14_station_layout_occupancy_and_route_locking`: PASSED
  - `test_15_station_layout_speed_restrictions`: PASSED
  - `test_16_train_movement_board_categorization`: PASSED
  - `test_17_adjacent_station_awareness_data`: PASSED
  - `test_18_station_alerts_scoped_strictly`: PASSED
- **Category 3: Section Controller Functionality & Domain Model (Tests 19–28):**
  - `test_19_section_controller_corridor_kpis`: PASSED
  - `test_20_section_controller_monitored_stations`: PASSED
  - `test_21_section_topology_strip`: PASSED
  - `test_22_section_train_ledger`: PASSED
  - `test_23_section_block_board_aspects`: PASSED
  - `test_24_single_line_bottleneck_detection`: PASSED
  - `test_25_junction_workspace_scenarios`: PASSED
  - `test_26_junction_workspace_alternative_delays`: PASSED
  - `test_27_section_alerts_severity_breakdown`: PASSED
  - `test_28_section_alerts_evidence_status`: PASSED
- **Category 4: AI Decision Support & Safety Invariants (Tests 29–35):**
  - `test_29_ai_recommendations_advisory_status`: PASSED
  - `test_30_independent_validator_safety_checks`: PASSED
  - `test_31_human_decision_audit_trail`: PASSED
  - `test_32_decision_records_immutable`: PASSED
  - `test_33_non_vital_disclaimer_present`: PASSED
  - `test_34_data_quality_confidence_scores`: PASSED
  - `test_35_token_revocation_blocks_outdated_tokens`: PASSED

#### 5.2 Full Test Suite Regressions Status
- **Backend Tests:** 338 of 338 passed (`PYTHONPATH=backend .venv/bin/pytest backend/tests/ -q`) in 14.81s.
- **Frontend Tests:** 84 of 84 passed (`cd frontend && npx vitest run`) in 12.16s.
- **Frontend Build:** Succeeded with zero errors (`cd frontend && npm run build`).

---

### 6. Operational Principles & Non-Vital Safety Boundary

1. **Advisory Decision Support Only:**
   - RAILGORITHM operates under the strict principle: `AI RECOMMENDS → INDEPENDENT VALIDATOR CHECKS → HUMAN CONTROLLER DECIDES → SYSTEM RECORDS`.
   - The platform produces advisory schedules, crossing proposals, and berthing recommendations. It never directly controls signals, points, or routes.
2. **Synthetic Demonstration Boundary:**
   - All scenarios and topologies are simulated. The application does not claim operational integration or formal certification by Indian Railways or the Commissioner of Railway Safety (CRS).
3. **Rule 15 Working Tree Compliance:**
   - In accordance with project instructions, all code modifications, test files, and screenshot assets remain uncommitted in the local working tree on dedicated feature branch `role-separated-redesign`.
   - No commits, tags, merges into main, pushes, or remote deployments were performed.
