# RAILGORITHM v2.7 — Implementation Plan: Section Controller Control Office Redesign

**Date:** 2026-11-25  
**Baseline Commit:** `05168b1` (Tagged `v2.6`)  
**Target Branch:** `v2.7`  
**Mission:** Transform the RAILGORITHM Section Controller interface into a desktop-first, multi-station railway traffic control office console adhering to Indian Railways operational realities, domain terminology, and human-in-the-loop decision-support safety boundaries.

---

## 1. Architectural Strategy & Design Principles

### 1.1 Five Principal Regions of the Control Console
1. **REGION A — Control Header & Territory Context:**
   - Control office branding: `RAILGORITHM Control Office · Section Controller Console`.
   - Controller identity & active role badge (`SECTION_CONTROLLER`).
   - Controlled section / territory selector: dynamically populated from configured network (e.g. `Northern Section (NDL–VSN) [60.0 km, 5 Stations, 6 Blocks]`).
   - Environment status: strictly transparent (`SYNTHETIC_SIMULATION` / `HISTORICAL_PLAYBACK` / `LIVE_OPERATIONAL`). Zero fabricated live connectivity.
   - Operational clocks: Current IST Time (`Asia/Kolkata`, 24h), Sim Time, Operational State Version.
   - Telemetry health: Feed status (`HEALTHY`, `DEGRADED`, `STALE`), heartbeat latency, unacknowledged critical alerts counter.
2. **REGION B — Section-Wide Operational Summary (Functional KPI Grid):**
   - 12 Functional KPIs with interactive filtering links:
     1. Monitored Trains (Total in horizon)
     2. Trains Running (Active in blocks)
     3. Trains at Stations (Berthed at platforms)
     4. Trains Awaiting Movement (Held / Pending line clear)
     5. Delayed Trains ($> 5\text{ min}$ deviation)
     6. Occupied Block Sections (Axle counter active)
     7. Confirmed Clear Block Sections (Line clear available)
     8. Unknown / Degraded Block States (Sensor offline or unconfirmed)
     9. Active Engineering Restrictions (Caution orders / Maintenance blocks)
     10. Active Route Conflicts (Headway / Platform / Crossing)
     11. Pending Regulation Decisions (Advisory options awaiting review)
     12. Trains with Missing/Stale Updates
   - Every KPI carries formal definition, unit, time window, data source, and epistemic quality badge (`MEASURED`, `CALCULATED`, `PREDICTED`, `HEURISTIC`, `NO_DATA`, `STALE`).
3. **REGION C — Multi-Station Territory Control Strip (`StationControlStrip.tsx`):**
   - Comprehensive horizontal or structured strip showing **every** configured station in the territory dynamically (`NDL`, `KRN`, `MLG`, `SRP`, `VSN`, or any configured network).
   - Per-station metrics: Code, Name, Role (Junction, Crossing, Terminal), Approaching Trains count, Berthed Trains count, Departed Trains count, Delayed Trains count, Platform utilization ($P_{\text{avail}} / P_{\text{total}}$), Active Local Alerts, Reported Restrictions, and Last Update timestamp.
   - Direct drill-down: Clicking any station expands an integrated drawer/modal displaying that station's Station Working Diagram, Platform Berth tracker, and Station Train Board without navigating away from the Section Controller console.
4. **REGION D — Master Time-Distance Control Graph (`TimeDistanceGraph.tsx`):**
   - Centerpiece primary operational workspace with enhanced multi-hour viewports ($2\text{h}$, $3\text{h}$, $6\text{h}$, $12\text{h}$, All Day).
   - Dynamic station chainage scaling derived directly from `network.stations` and `network.sections`.
   - Multi-layer trajectories: Scheduled baseline (faint grey), Actual observed running (solid color-coded by category), Forecast/projected paths (dashed).
   - Single-line bottleneck territory shading ($S_1$ `NDL–KRN` and $S_3$ `MLG–SRP`) highlighting single-line crossing constraints where meets must happen on loop lines.
   - Event annotations: Arrival, Departure, Station Dwell, Meet/Crossing, Precedence, and Engineering Block.
   - Interactive hover HUD displaying train details, schedule adherence, delay history, source freshness, and accessible tabular fallback.
5. **REGION E — Operational Attention & Incident Panel (`OperationalAttentionPanel.tsx`):**
   - Prioritized triage queue sorted by operational severity and urgency: Critical (Red), High (Amber), Medium (Blue), Informational (Slate).
   - Actionable incident cards: Event ID, affected train, station or block location, detection time, reason code, telemetry source, related safety constraint, and suggested operational next step.
   - Acknowledgement workflow: Tracks operator acknowledgement state with timestamp and user ID, maintaining strict distinction between *acknowledged* and *resolved*.

---

## 2. Integrated Workspaces & Sub-Panels

### 2.1 Block and Section Control Board (`BlockOccupancyMatrix.tsx`)
- Enhanced grid supporting 6 distinct operational states: `OCCUPIED`, `CONFIRMED CLEAR`, `UNKNOWN`, `STALE`, `DEGRADED`, `CLOSED / RESTRICTED`.
- Tracks: Block ID, Section territory, Mode (Single / Double), Permitted Direction, Line Clear instrument status, Occupying Train ID & Name, Entry/Exit times, Elapsed vs Nominal run time, Speed limits (MPS) & Caution orders, Signaling type, and Axle counter verification.
- Interactive filter: `All Blocks`, `Occupied Only`, `Single-Line Bottlenecks (B1, B3)`, `Degraded / Unknown`.

### 2.2 Train Movement & Regulation Workspace (`TrainMovementLedger.tsx`)
- Comprehensive real-time train movement register.
- Columns: Train ID, Train Name, Category/Type, Priority, Direction, Origin $\rightarrow$ Destination, Last Confirmed Location, Last Update Time, Scheduled vs Actual/Expected Times, Current Delay, Next Expected Station, Operational Status, and Data Quality.
- Interactive movement timeline: Clicking a train opens a detailed historical-to-projected milestone trace across every corridor station.
- Filters: `All Trains`, `Running`, `At Station`, `Waiting`, `Delayed`, `Stale Position`, `Priority Category`.

### 2.3 Crossing, Precedence & Conflict Regulation Workspace (`ConflictRegulationWorkspace.tsx`)
- Dedicated conflict analysis and regulation alternatives panel.
- Distinguishes: Detected Conflict, Potential Conflict, Confirmed Constraint Violation, Data Contradiction, Model Disagreement, and Resolved Conflict.
- AI Regulation Alternatives: Compares Baseline vs CP-SAT Schedule vs PPO Advisory.
- Displays: Current situation, affected trains, proposed arrangement, operational rationale, expected delays, knock-on impact, hard constraints checked, soft objectives evaluated, independent validator outcome, and human approval workflow.
- Explicitly renders `NO FEASIBLE SCHEDULE` if constraints cannot be satisfied.

### 2.4 Engineering Blocks & Operational Restrictions Panel (`RestrictionsAndIncidentsPanel.tsx`)
- Tracks engineering blocks (P-Way track renewals, machine tamping) and overhead traction (OHE) power blocks.
- Differentiates Temporary Speed Restrictions (TSR, Caution Orders) and Permanent Speed Restrictions (PSR).
- Fields: Restriction ID, Location (Station/Block), Section, Restriction Type, Speed Limit (km/h), Effective Start & End, Issuing Authority, Verification Status, and Operational Impact.

### 2.5 Control Office Coordination & Shift Handover Workspace (`CoordinationAndHandover.tsx`)
- **Coordination Record:** Structured message log between Section Controller and external departments: Station Masters, Traction Power Controller (TPC), Signal & Telecom (S&T), P-Way Engineering, Loco Running Shed, and Yard Master.
- **Shift Handover Console:** Summarizes active train positions, delayed trains, pending crossing/precedence decisions, active engineering restrictions, open incidents, and unresolved conflicts. Allows operator to record structured handover notes with cryptographic audit trail.

---

## 3. Component Architecture & File Layout

```
frontend/src/
├── components/
│   ├── StationControlStrip.tsx              [NEW: Multi-station operational overview strip]
│   ├── StationControlStrip.test.tsx         [NEW: Unit tests for station control strip]
│   ├── OperationalAttentionPanel.tsx        [NEW: Operational triage & alert management]
│   ├── OperationalAttentionPanel.test.tsx   [NEW: Unit tests for attention panel]
│   ├── TrainMovementLedger.tsx              [NEW: Comprehensive movement register & timeline]
│   ├── TrainMovementLedger.test.tsx         [NEW: Unit tests for movement ledger]
│   ├── ConflictRegulationWorkspace.tsx      [NEW: Crossing & precedence regulation panel]
│   ├── ConflictRegulationWorkspace.test.tsx [NEW: Unit tests for conflict workspace]
│   ├── RestrictionsAndIncidentsPanel.tsx    [NEW: Engineering blocks & speed restrictions]
│   ├── RestrictionsAndIncidentsPanel.test.tsx[NEW: Unit tests for restrictions]
│   ├── CoordinationAndHandover.tsx          [NEW: Control coordination & shift handover]
│   ├── CoordinationAndHandover.test.tsx     [NEW: Unit tests for handover]
│   ├── TimeDistanceGraph.tsx                [UPGRADE: Dynamic station chainage, pan/zoom, event markers]
│   ├── TimeDistanceGraph.test.tsx           [UPGRADE: Extended test coverage]
│   ├── BlockOccupancyMatrix.tsx             [UPGRADE: 6-state occupancy, event history]
│   ├── BlockOccupancyMatrix.test.tsx        [UPGRADE: Extended test coverage]
├── pages/
│   ├── Dashboard.tsx                        [UPGRADE: Integrated Section Controller console]
│   ├── Dashboard.test.tsx                   [UPGRADE: Full test coverage for new console]
```

---

## 4. Documentation Deliverables
- `docs/SECTION_CONTROLLER_CONSOLE_SPEC.md`: Exhaustive specification of the Section Controller control console.
- `docs/MULTI_STATION_OPERATIONS_SPEC.md`: Operational workflow specification for multi-station supervision.
- `docs/V2_7_VERIFICATION_REPORT.md`: Verification evidence covering all unit, integration, and performance tests.
- `README.md` and `VERIFICATION.md` updates.

---

## 5. Verification Gate
- All 244 existing backend pytest tests must pass without regression.
- All existing and new frontend vitest tests must pass (targeting 70+ tests across 18+ suites).
- TypeScript compile check (`tsc --noEmit`) must exit with 0 errors.
- Production build (`npm run build`) must succeed cleanly.
