# RAILGORITHM v2.6 — Implementation Plan: Railway Operational Visualization & Interface Excellence

**Date:** 2026-11-25  
**Baseline Commit:** `ad273d4` (Tagged `v2.5`)  
**Target Branch:** `v2.6`  
**Mission:** Transform RAILGORITHM into a high-precision, authentic railway traffic control room visual interface adhering to Indian Railways operational conventions, without compromising data integrity, environment isolation, or advisory-only safety principles.

---

## 1. Core Visualizations & Components

### 1.1 Time-Distance Train Graph (`TimeDistanceGraph.tsx`)
- **Domain Purpose:** Master controller's chart / String chart used in Indian Railways Section Control Offices.
- **Axes:**
  - **Horizontal:** Time (00:00 to 24:00 IST, configurable 2h, 4h, 6h, or full day horizon). Displays current simulation time marker with vertical line and time label.
  - **Vertical:** Corridor Stations plotted strictly by physical chainage (km):
    - Nandpur (`NDL`, km 0.0)
    - Karanpur (`KRN`, km 14.0)
    - Malgaon Junction (`MLG`, km 32.0, diamond crossing)
    - Suryapur (`SRP`, km 48.0)
    - Vasanthpur (`VSN`, km 60.0)
- **Line Traces & Rendering:**
  - Scheduled Trajectory: Semi-transparent solid line (`#94A3B8`).
  - Actual Trajectory (history): Solid high-contrast line (`#1E293B` or color-coded by train priority/category: Express, Passenger, Freight).
  - Predicted / Projected Trajectory (future): Dashed line (`#2563EB` or `#F59E0B`).
  - Dwell / Halts: Horizontal line segments at station chainage lines.
  - Up Trains: Sloping from bottom-left to top-right (NDL -> VSN).
  - Down Trains: Sloping from top-left to bottom-right (VSN -> NDL).
  - Meets & Crossings: Displayed at station tracks; single-line sections (S1, S3) enforce no crosses outside station boundaries.
  - Conflicts: Warning markers (pulsing amber/red diamond icons) at conflict time and chainage.
- **Interactive Features:**
  - Time window range selector (2 hours, 4 hours, Full corridor window).
  - Direction filter (All, UP only, DOWN only).
  - Train hover tooltip with: Train ID, Name, Category, Scheduled vs Actual ETA, Current Delay (+Xm), Current Block/Station, Speed.
  - SVG canvas with crisp vector rendering, accessible aria labels and data table toggle.

### 1.2 Station Working Diagram (`StationWorkingDiagram.tsx`)
- **Domain Purpose:** Mimics Indian Railways Station Interlocking Yard Display / Electronic Interlocking (EI) VDU at Station Master's office.
- **Components for Selected Station:**
  - Up Main Line and Down Main Line (or single main line depending on section).
  - Loop Lines (Up Loop, Down Loop, Goods Siding).
  - Numbered Platforms (P1, P2, P3).
  - Points & Crossings: Turnouts into loops, diamond crossing at Malgaon Junction (`MLG`).
  - Signals: Home signals, Starter signals, Advance Starter signals.
  - Track circuits / Berths: Color-coded operational states:
    - **Clear / Available:** Green (`#16A34A` / `#22C55E`).
    - **Occupied:** Blue (`#2563EB`) or Amber (`#D97706`) with Train ID label and berthing elapsed timer.
    - **Maintenance / Block Outage:** Red (`#DC2626` / striped) with outage reason.
    - **Route Set / Locked:** Cyan / Yellow highlighting along switch path.
- **Interactive Inspection:**
  - Clicking any track segment or platform opens an inspection popover showing: Track ID, status, berthed train ID, name, arrival time, scheduled departure time, dwell remaining, and data source provenance (`MEASURED` via track circuits / axle counters).

### 1.3 Block Section Occupancy Matrix (`BlockOccupancyMatrix.tsx`)
- **Domain Purpose:** Real-time block state monitoring for Section Controllers across all corridor block sections:
  - `B1`: Nandpur – Karanpur (Single Line, Bidirectional, 14 km, Absolute Block)
  - `B2U`: Karanpur – Malgaon Up Line (Double Line, Direction UP, 18 km, Absolute Block)
  - `B2D`: Karanpur – Malgaon Down Line (Double Line, Direction DOWN, 18 km, Absolute Block)
  - `B3`: Malgaon – Suryapur (Single Line, Bidirectional, 16 km, Absolute Block)
  - `B4U`: Suryapur – Vasanthpur Up Line (Double Line, Direction UP, 12 km, Absolute Block)
  - `B4D`: Suryapur – Vasanthpur Down Line (Double Line, Direction DOWN, 12 km, Absolute Block)
- **Grid / Table Columns:**
  - Block ID & Section Name
  - Line Mode (Single / Double) & Permitted Direction
  - Track Circuit / Axle Counter Status (CLEAR / OCCUPIED / MAINTENANCE)
  - Occupying Train (ID, Name, Priority)
  - Entry Timestamp, Expected Exit Timestamp, Elapsed Transit Time vs Scheduled Run Time
  - Speed Restriction / Caution Order (if active)
  - Headway State (Normal / Critical)
  - Data Provenance (`MEASURED` via Axle Counter / Track Circuit)

### 1.4 Operational Station Train Board (`StationTrainBoard.tsx`)
- **Domain Purpose:** Familiar railway station electronic passenger & operational movement board.
- **Columns & Data:**
  - Train Number & Train Name
  - Category / Type (Express, Superfast, Passenger, Freight)
  - Direction (UP / DOWN)
  - Route (Origin → Destination)
  - Scheduled Arrival & Scheduled Departure
  - Expected / Actual Arrival & Expected / Actual Departure
  - Platform Allocation (P1, P2, P3)
  - Delay Status (+Xm / Right Time)
  - Status Tag: `APPROACHING`, `BERTHED`, `DEPARTED`, `DELAYED`
- **Filtering & Search:**
  - Filter tabs: All, Approaching, Berthed at Station, Departed, Delayed.
  - Search input for train number, name, or destination.

### 1.5 Formal KPI Registry (`kpiRegistry.ts`)
- TypeScript definition and registry metadata for every operational metric:
  - ID, canonical name, domain formula, unit, default time window, targets (good/watch/bad), provenance data source, epistemic classification (`MEASURED`, `CALCULATED`, `PREDICTED`, `HEURISTIC`, `NO_DATA`, `STALE`), and primary role.
  - Used in tooltips and KPI Traceability panels to guarantee zero ambiguity.

---

## 2. Dashboard Integration Strategy

### Station Master View:
1. Station Switcher & Station Working Status Header.
2. 8 Station Master Standardized KPI Cards.
3. **Station Working Diagram (`<StationWorkingDiagram />`)** with interactive track/platform popover.
4. **Station Train Arrival & Departure Board (`<StationTrainBoard />`)** with live search and status filters.
5. Station Platform Berthing Status & Hourly Movement Distribution.
6. Station Advisory Decisions & Active Platform Alerts.

### Section Controller View:
1. Corridor Operating Summary Header.
2. 9 Section Controller Standardized KPI Cards.
3. **Time-Distance Train Graph (`<TimeDistanceGraph />`)** as the primary central operational view with time controls and direction filtering.
4. Corridor Traffic & Movement Schematic (`<RailwayCorridorDiagram />`).
5. **Block Section Occupancy Matrix (`<BlockOccupancyMatrix />`)** showing complete corridor block state.
6. Corridor Punctuality & Junction Throat Analytics.
7. Active Corridor Trains Ledger & Dispatch Decision Queue.

---

## 3. Verification Plan
- Unit tests for `TimeDistanceGraph.test.tsx`.
- Unit tests for `StationWorkingDiagram.test.tsx`.
- Unit tests for `BlockOccupancyMatrix.test.tsx`.
- Unit tests for `StationTrainBoard.test.tsx`.
- Regression check on existing Dashboard and component tests (all 42+ frontend tests must pass).
- Full backend pytest run (all 244 backend tests must pass).
- Production build check (`npm run build` exits 0).
- Author documentation:
  - `docs/TIME_DISTANCE_GRAPH_SPEC.md`
  - `docs/STATION_WORKING_SPEC.md`
  - `docs/KPI_REGISTRY_V2_6.md`
  - `docs/V2_6_VERIFICATION_REPORT.md`
  - Update `README.md` and `VERIFICATION.md`.
