# RAILGORITHM v2.7 — Section Controller Control Office Specification

**Document Version:** 2.7.0  
**Effective Date:** 25 November 2026  
**Status:** Architecture & Engineering Specification  
**Authority:** Section Controller Decision-Support Platform  
**Target Console:** Desktop-First Control Office Workspace (`frontend/src/pages/Dashboard.tsx`)  

---

## 1. Executive Summary & Design Philosophy

In Indian Railways operating practice, the **Section Controller (SCR)** located in the Divisional Control Office exercises continuous operational supervision over train movements across all stations and block sections within their assigned control territory. The previous dashboard designs presented isolated station views or fragmented KPI cards, forcing controllers to toggle between screens and breaking situational awareness during peak traffic or degraded operations.

RAILGORITHM v2.7 redesigns the Section Controller interface into a **unified desktop-first Control Office Console**. The design principles are:
1. **Complete Territory Visibility:** The controller monitors the entire corridor (stations, block sections, bottlenecks, and berths) on a single high-density, professional visual canvas.
2. **Instant Station Inspection:** Clicking any station in the territory immediately opens an inline Electronic Interlocking (EI) yard inspection modal/drawer without losing corridor context.
3. **Master String Chart Centerpiece:** Dynamic time-distance graph tracking train trajectories against actual physical chainages ($0.0\text{ km}$ Nandpur to $60.0\text{ km}$ Vasanthpur) with single-line bottleneck shading, time panning, viewport scaling, and forecast toggles.
4. **Prioritized Urgency Triage:** Dedicated Operational Attention Panel categorizing safety constraint conflicts, infrastructure warnings, and communication alerts by severity with formal operator acknowledgement tracking.
5. **Advisory Decision Support:** AI recommendations (OR-Tools CP-SAT and PyTorch PPO) remain strictly advisory. Human controllers retain exclusive operational authority; no autonomous interlocking, route, or point control is permitted.

---

## 2. Console Architectural Regions (Regions A – E)

```
+---------------------------------------------------------------------------------------------------------+
| REGION A: SECTION CONTROLLER CONTROL OFFICE HEADER BAR                                                 |
| [Desk: SC-402] | Territory: NDL-VSN Mainline (5 Stations, 4 Sections) | Shift: Day 06:00-14:00           |
| Clocks: IST 07:00:00 | Sim Time: T+420m | Telemetry: HEALTHY (4.2s) | Unack Alerts: 0                  |
+---------------------------------------------------------------------------------------------------------+
| REGION B: OPERATIONAL SUMMARY (12 STANDARDIZED SECTION KPIS)                                            |
| [Active Trains] [Avg Delay] [Block Occupancy] [Throat Load] [Throughput] [DPI]                         |
| [Delayed Trains] [Conflicts] [Clearance Rate] [Running vs Berthed] [TSR/PSR] [Pending Decisions]      |
+---------------------------------------------------------------------------------------------------------+
| REGION C: MULTI-STATION TERRITORY CONTROL STRIP                                                         |
| [ NDL Card ] -----> [ KRN Card ] -----> [ MLG Card ] -----> [ SRP Card ] -----> [ VSN Card ]           |
| (Clicking any card opens inline Station Yard Interlocking & Platform Berths Inspection Console)         |
+---------------------------------------------------------------------------------------------------------+
| WORKSPACE NAVIGATOR TABS:                                                                               |
| [Master Console (All)] [Time-Distance Graph] [Corridor Blocks] [Train Ledger] [Regulation] [TSR] [Log] |
+---------------------------------------------------------------------------------------------------------+
| REGION D & E: MASTER TIME-DISTANCE GRAPH & OPERATIONAL ATTENTION PANEL                                 |
| - Time-Distance String Chart (Chainage km vs Time IST; Panning ◀ Center ▶; Viewport 2h/3h/6h/12h)      |
| - Operational Attention Panel (Critical/High/Medium/Info triage; Ack tracking; Rule references)       |
+---------------------------------------------------------------------------------------------------------+
| INTEGRATED CONTROL WORKSPACES:                                                                          |
| 1. Corridor Blocks, Bottlenecks & Schematics (RailwayCorridorDiagram + BlockOccupancyMatrix)           |
| 2. Section Train Movement & Regulation Ledger (Filterable movements + milestone progress timeline)      |
| 3. Crossing, Precedence & AI Regulation Workspace (CP-SAT vs PPO alternatives + Rule validation)       |
| 4. Operational Restrictions & Incidents Workspace (TSR, PSR, Engineering Blocks + Unusual Detentions) |
| 5. Control Office Coordination Diary & Shift Handover Console (Inter-departmental logs + Continuity)    |
+---------------------------------------------------------------------------------------------------------+
```

---

## 3. Detailed Region Specifications

### 3.1 Region A: Control Header Bar
- **Desk Identity:** Controller callsign (`SC-402`), Division/Subdivision identifier, and active shift window (`Day Shift 06:00–14:00 IST`).
- **Territory Selector:** Dropdown allowing seamless switching between assigned control sections:
  - `NDL-VSN Mainline Corridor (Southern Division)` (Default, 5 stations, 4 sections)
  - `MLG Junction Suburban Branch Loop`
  - `KRN-SRP Quad Track Freight Bypass`
- **Synchronized Clocks:**
  - Real-Time IST System Clock (`Asia/Kolkata` wall-clock reference).
  - Simulated Operational Clock (`07:00 IST`, elapsed simulation minutes `T+420m`).
- **Telemetry Integrity Indicator:** Real-time data stream status (`HEALTHY`, `DEGRADED`, `STALE`, `OFFLINE`) with heartbeat latency ($4.2\text{ s}$) and underlying feed source citations.
- **Unacknowledged Critical Alerts Pill:** Prominent visual badge reflecting the number of unresolved critical/high-severity conflicts requiring operator review.

### 3.2 Region B: Operational Summary (12 Standardized Section KPIs)
1. **Active Corridor Trains:** Total trains currently in transit or berthed on corridor tracks (`MEASURED`).
2. **Average Section Delay:** Mean delay across all active and completed trains on this corridor (`CALCULATED`).
3. **Block Occupancy Percentage:** Percentage of block sections occupied by moving or stationed trains (`MEASURED`).
4. **Junction Throat Load (MLG):** Capacity utilization of Malgaon diamond scissors crossing throat (limit: 2 parallel moves) (`CALCULATED`).
5. **Corridor Throughput:** Train movements completed per hour across section boundaries (`CALCULATED`).
6. **Delay Propagation Index (DPI):** Ratio of secondary knock-on delay minutes to primary initial schedule delay (`HEURISTIC`).
7. **Delayed Corridor Trains:** Count and percentage of trains exceeding the 5-minute punctuality threshold (`MEASURED`).
8. **Active Route Conflicts:** Number of active headway, opposing move, or platform occupancy conflicts (`MEASURED`).
9. **Recovery Clearance Rate:** Historical conflict clearance rate over the active session (`CALCULATED`).
10. **Running vs Berthed:** Instantaneous distribution of trains traversing block sections versus dwelling at station berths (`MEASURED`).
11. **Active Speed Restrictions:** Total active Permanent Speed Restrictions (PSR) and Temporary Speed Restrictions (TSR) (`MEASURED`).
12. **Pending Dispatch Decisions:** Count of candidate AI regulation proposals awaiting human authorization (`CALCULATED`).

### 3.3 Region C: Multi-Station Territory Control Strip
- Renders an interconnected horizontal strip of status cards representing every station along the territory: Nandpur (`NDL`), Karanpur (`KRN`), Malgaon Junction (`MLG`), Suryapur (`SRP`), and Vasanthpur (`VSN`).
- Each card displays:
  - Station code, station name, and junction indicator tag.
  - Movement counts: Approaching trains, berthed trains, and recently departed trains.
  - Delayed train count with color-coded severity tone (`good` = 0, `watch` > 0, `bad` = critical delay).
  - Platform availability: Free platforms versus total platform berths.
  - Active caution order indicators (e.g., PSR 30 km/h over turnout) or shunting activity.
- **Inline Yard Inspection Drawer:** Clicking any station card immediately opens a dedicated inspection workspace below the strip, rendering:
  - `<StationWorkingDiagram />`: Electronic Interlocking (EI) track layout, points, crossings, and signals.
  - `<StationPlatformBerths />`: Live occupancy slots for passenger and freight lines.
  - `<StationTrainBoard />`: Station arrival and departure timetable with dwell status.
  - Fast-action buttons: "Switch to Full Station Master View" and "Close Station Inspection ✕".

### 3.4 Region D: Master Time-Distance Graph Workspace (`TimeDistanceGraph.tsx`)
- High-resolution SVG vector string chart plotting station chainages on the Y-axis ($0.0\text{ km}$ at NDL to $60.0\text{ km}$ at VSN) against simulated operating time on the X-axis.
- **Dynamic Station Chainages:** Station offsets are derived dynamically from the network topology sections and lengths rather than hardcoded heuristics.
- **Interactive Panning Controls:**
  - `◀ -30m`: Pan viewport backward 30 minutes into historical movements.
  - `Center Now ⏱`: Snap viewport center directly to current simulated clock (`sim_time_min`).
  - `+30m ▶`: Pan viewport forward 30 minutes into projected operations.
- **Time Viewport Scaling:** Selectable operational zoom levels: $2\text{h}$, $3\text{h}$ (Default), $6\text{h}$, and $12\text{h}$.
- **Category & Forecast Toggles:**
  - Category filters: All Trains, Express / Passenger, Freight.
  - Toggle Forecast Trajectories: Show or hide projected future movements.
  - Toggle Timetable Baseline: Show or hide scheduled baseline paths.
- **Single-Line Bottleneck Shading:** Sections S1 (`NDL–KRN`) and S3 (`MLG–SRP`) are highlighted with distinct amber zebra-hatch pattern, visually indicating tokenless absolute block single-line territory where opposing moves are strictly prohibited.

### 3.5 Region E: Operational Attention Panel (`OperationalAttentionPanel.tsx`)
- Prioritized queue sorting operational safety constraints by severity:
  - `CRITICAL`: Immediate opposing move conflict on single line or zero-headway infringement.
  - `HIGH`: Station dwell extension causing platform berth conflict or throat saturation.
  - `MEDIUM`: Single-line bottleneck block occupied or knock-on propagation risk.
  - `INFORMATIONAL`: Engineering caution order in effect or routine token exchange.
- Each attention card displays:
  - Severity badge, title, detection timestamp, and affected trains.
  - Physical location (track block, station, or turnout).
  - Traceable constraint rules (e.g., Indian Railways General Rules 4.16 Headway Margin, 1.02(62) Wrong Line Movement, SEM Part II).
  - Suggested regulatory action (e.g., "Hold trailing freight at Karanpur loop line until Express clears block").
  - Operator acknowledgement button: Section Controller enters acknowledgement memo, recording duty controller callsign and timestamp.

---

## 4. The 6 Integrated Workspaces

The console provides quick-filter tabs allowing the Section Controller to focus on specific operational facets or view the complete master console:

| Tab ID | Workspace Title | Key Visual Components & Capabilities |
| :--- | :--- | :--- |
| `ALL` | **Master Console** | Complete simultaneous display of all 6 operational workspaces for ultra-wide control desk screens. |
| `GRAPH` | **Time-Distance Graph & Attention** | Centerpiece `<TimeDistanceGraph />` and `<OperationalAttentionPanel />` for movement tracking and conflict triage. |
| `BLOCKS` | **Corridor Blocks & Bottlenecks** | `<RailwayCorridorDiagram />`, `<BlockOccupancyMatrix />`, Malgaon diamond throat bottleneck monitor, and delay distribution charts. |
| `LEDGER` | **Train Movement Ledger** | `<TrainMovementLedger />` with real-time status filtering (Running, At Station, Waiting, Delayed, Stale), search, and milestone timeline drawer. |
| `REGULATION` | **Conflict & AI Regulation** | `<ConflictRegulationWorkspace />` evaluating candidate CP-SAT vs PPO regulation proposals, constraint validator outcomes, and human review links. |
| `RESTRICTIONS` | **TSR / PSR & Incidents** | `<RestrictionsAndIncidentsPanel />` tracking temporary/permanent speed restrictions, maintenance blocks, and operating incidents. |
| `HANDOVER` | **Coordination & Shift Handover** | `<CoordinationAndHandover />` inter-departmental control diary (SM, TPC, S&T, P-Way) and signed shift handover continuity protocol. |

---

## 5. Safety, Regulatory & Epistemic Boundaries

1. **Advisory-Only Boundary:** The Section Controller Console is strictly an advisory decision-support system. It has **no network or physical connection** to Electronic Interlockings, Relay Interlockings, Point Machines, or Wayside Signals. It is physically incapable of setting routes or clearing signals.
2. **Human Authorization Mandatory:** No candidate schedule adjustment, platform diversion, or precedence alteration may be executed autonomously. Every recommendation requires explicit confirmation (`confirm_apply: true`) by the authenticated human Section Controller.
3. **Regulatory Traceability:** All operational checks reference authentic Indian Railways operating documentation:
   - General Rules (GR) 1976 (Open Lines) & Subsidiary Rules (SR).
   - Signal Engineering Manual (SEM) Part II.
   - Operating Manual for Indian Railways.
4. **Transparent Telemetry Labeling:** Live operational feeds, historical playback, and synthetic simulations are strictly isolated and labeled with high-visibility banners. Telemetry data from track circuits and axle counters is distinguished from heuristic simulation predictions.
