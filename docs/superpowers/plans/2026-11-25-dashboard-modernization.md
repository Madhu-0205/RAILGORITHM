# RAILGORITHM v2.5 Dashboard Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Modernize the RAILGORITHM frontend into a high-density, professional, Indian Railways-familiar operational dashboard for Station Masters and Section Controllers with interactive SVG visualizations, traceable KPIs, and advisory AI decision support.

**Architecture:** Modern enterprise CSS design system (Deep Navy `#101B2B` navigation, Slate `#F1F5F9` workspace, White `#FFFFFF` cards, high contrast, WCAG 2.1 AA accessibility), modular SVG chart and corridor visualization components with zero external charting dependencies, strict null-safe KPI data rendering, role-scoped views, and independent recommendation validation display.

**Tech Stack:** React 19, TypeScript, React Router v7, Vitest, Testing Library, Native SVG Data Visualizations, CSS Container Queries & Custom Properties.

**Spec:** Modernization requirements in user prompt `RAILGORITHM v2.5 — Railway Operations Dashboard Modernization`.

## Global Constraints

- Do not rewrite the entire application or replace the backend.
- Maintain React, TypeScript, FastAPI, SQLAlchemy, OR-Tools CP-SAT, and PyTorch architecture.
- Maintain Station Master and Section Controller roles and existing access control.
- Maintain strict separation between `SYNTHETIC_SIMULATION`, `HISTORICAL_PLAYBACK`, and `LIVE_OPERATIONAL`.
- AI recommendations remain strictly advisory; no autonomous railway infrastructure control.
- Never show 0% when the correct result is `null` (`NO_DATA`).
- Do not fabricate operational data, KPI values, or confidence percentages.
- No new heavy charting dependencies; use lightweight, accessible native SVG components.
- Existing routes, permissions, and test suites must continue to pass without regression.

## Review Focus

1. **Null/Empty Observation Windows:** KPIs like `average_arrival_delay_min` and `recovery_clearance_rate_pct` return `null` when no trains/conflicts exist in the window; frontend must render `"—"` with informative tooltip, never `0 min` or `0%`.
2. **Role Authorization Scope:** Station Master must only see permitted navigation items and station-specific controls, while Section Controller retains corridor-wide controls and simulation progression buttons.
3. **Responsive Table Navigation:** Data tables must maintain horizontal scrollability with `role="region"` and `tabindex="0"`, keeping table headers sticky without breaking layout on smaller displays.
4. **Environment Disambiguation:** Simulation mode must be unmistakably flagged across the topbar and headers to prevent operator confusion with live operational data.
5. **Chart Accessibility:** All SVG charts and corridor schematics must provide semantic text equivalents, ARIA role attributes (`role="img"`), and title/description tags for screen reader accessibility.

---

### Task 1: Operational Design System & CSS Foundation

**Files:**
- Modify: `frontend/src/styles.css`
- Modify: `frontend/src/components/ui.tsx`
- Test: `frontend/src/components/ui.test.tsx`

**Interfaces:**
- Consumes: CSS variables for Deep Navy (`#101B2B`), Secondary Navy (`#17263B`), Slate Workspace (`#F1F5F9`), Surface (`#FFFFFF`), Borders (`#E2E8F0`), Status Green (`#16A34A`), Status Amber (`#D97706`), Status Red (`#DC2626`), Status Blue (`#2563EB`).
- Produces: Enhanced `KpiCard` with metadata, unit, period, data quality badge, and tooltip; modernized `Panel`, `Badge`, `StatusBadge`, and responsive `.table-wrapper`.

- [ ] **Step 1: Write tests for updated UI components**
- [ ] **Step 2: Run tests to verify failure/missing features**
- [ ] **Step 3: Update CSS variables, layout classes, and UI components in `styles.css` and `ui.tsx`**
- [ ] **Step 4: Run tests to verify they pass**
- [ ] **Step 5: Commit changes**

---

### Task 2: Modernized Application Shell & Operational Header

**Files:**
- Modify: `frontend/src/components/Shell.tsx`
- Test: `frontend/src/components/Shell.test.tsx`

**Interfaces:**
- Consumes: `useAuth()`, `useSimulation()`, `FeedHealthBanner`, `api`.
- Produces: Professional railway header with RTMS badge, environment pill, active simulation clock, data freshness status, active conflict severity pill, role-specific sidebar navigation, and simulation controls.

- [ ] **Step 1: Update `Shell.test.tsx` for new operational header elements while preserving existing navigation tests**
- [ ] **Step 2: Run tests to see test requirements**
- [ ] **Step 3: Implement modernized header, role badges, and sidebar in `Shell.tsx`**
- [ ] **Step 4: Run test suite on Shell**
- [ ] **Step 5: Commit changes**

---

### Task 3: Interactive SVG Railway Visualizations (Corridor & Charts)

**Files:**
- Create: `frontend/src/components/RailwayCorridorDiagram.tsx`
- Create: `frontend/src/components/StationPlatformBerths.tsx`
- Create: `frontend/src/components/HourlyMovementsChart.tsx`
- Create: `frontend/src/components/DelayDistributionChart.tsx`
- Create: `frontend/src/components/RailwayCorridorDiagram.test.tsx`

**Interfaces:**
- Consumes: Network data, `BlockOccupancy[]`, `Platform[]`, `Train[]`, `Conflict[]`.
- Produces: Accessible SVG corridor diagram with single/double track markers, diamond crossing throat, real-time train positions, and conflict alerts; platform berth visualizer; hourly arrival/departure distribution; delay breakdown chart.

- [ ] **Step 1: Write unit tests for `RailwayCorridorDiagram` and charts**
- [ ] **Step 2: Run tests to verify failure**
- [ ] **Step 3: Implement `RailwayCorridorDiagram.tsx`, `StationPlatformBerths.tsx`, `HourlyMovementsChart.tsx`, and `DelayDistributionChart.tsx`**
- [ ] **Step 4: Run tests to verify pass**
- [ ] **Step 5: Commit changes**

---

### Task 4: Station Master Dashboard Modernization

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Test: `frontend/src/pages/Dashboard.test.tsx`

**Interfaces:**
- Consumes: `api.stationKpis`, `api.dashboard`, `StationPlatformBerths`, `HourlyMovementsChart`, `DelayDistributionChart`.
- Produces: Modern Station Master operational screen with 8 standardized KPI cards, live platform berthing tracks, approaching/stationed train movement table with search and filters, local decision queue, and station conflict alerts.

- [ ] **Step 1: Update `Dashboard.test.tsx` to verify Station Master KPIs, movement table, and platform berths**
- [ ] **Step 2: Run tests to verify requirements**
- [ ] **Step 3: Implement Station Master section in `Dashboard.tsx` with all 8 KPIs, filters, and charts**
- [ ] **Step 4: Run test suite to verify pass**
- [ ] **Step 5: Commit changes**

---

### Task 5: Section Controller Dashboard Modernization

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`
- Test: `frontend/src/pages/Dashboard.test.tsx`

**Interfaces:**
- Consumes: `api.sectionKpis`, `api.dashboard`, `RailwayCorridorDiagram`, `api.conflicts`.
- Produces: Modern Section Controller corridor screen with 9 standardized corridor KPIs, interactive corridor schematic, single-line bottleneck occupancy, junction throat monitoring, corridor train timeline, and dispatch conflict resolution queue.

- [ ] **Step 1: Update `Dashboard.test.tsx` to verify Section Controller corridor schematic and KPIs**
- [ ] **Step 2: Run tests to verify requirements**
- [ ] **Step 3: Implement Section Controller view in `Dashboard.tsx`**
- [ ] **Step 4: Run test suite to verify pass**
- [ ] **Step 5: Commit changes**

---

### Task 6: Operational Documentation & Verification Reports

**Files:**
- Create: `docs/DASHBOARD_DESIGN_SYSTEM.md`
- Create: `docs/KPI_DEFINITIONS_AND_SEMANTICS.md`
- Create: `docs/STATION_MASTER_DASHBOARD.md`
- Create: `docs/SECTION_CONTROLLER_DASHBOARD.md`
- Create: `docs/FRONTEND_VERIFICATION.md`

**Interfaces:**
- Consumes: Implementation code, test results, design system tokens.
- Produces: 5 complete markdown technical documents fulfilling prompt Section 16 requirements.

- [ ] **Step 1: Create all 5 markdown specifications in `docs/`**
- [ ] **Step 2: Verify documentation consistency with implemented code and APIs**
- [ ] **Step 3: Commit documentation**

---

### Task 7: Full Regression Testing & Production Build

**Files:**
- Run full backend tests: `PYTHONPATH=backend .venv/bin/pytest backend/tests/`
- Run full frontend tests: `cd frontend && npm test -- --run`
- Run frontend production build: `cd frontend && npm run build`

- [ ] **Step 1: Execute backend and frontend test suites**
- [ ] **Step 2: Execute frontend production build**
- [ ] **Step 3: Verify zero regressions**
- [ ] **Step 4: Final commit and push**
