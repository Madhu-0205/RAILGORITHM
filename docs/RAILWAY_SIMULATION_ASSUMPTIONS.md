# RAILGORITHM 2.0 — Railway Simulation Assumptions Specification

**Document Version:** 2.0.0  
**Specification Key:** `assumptions-2.0.0`  
**Classification:** Configured Synthetic Assumptions (Simulation-Only)  
**Safety Notice:** This system operates strictly on synthetic simulation models. None of the values, formulas or topologies herein represent verified rules or operating standards of Indian Railways or any real-world railway administration.

---

## 1. Scope and Design Philosophy

RAILGORITHM 2.0 eliminates buried constants by consolidating all operational, infrastructural and kinematic assumptions into an inspectable, version-controlled module (`backend/app/domain/spec.py`). Every assumption specifies:
- Unique identifier (`ASSUMPTION_ID`)
- Operational domain category
- Baseline synthetic value and physical unit
- Source attribution (declaring synthetic nature)
- Configuration override mechanism (via environment variables)
- Dependent subsystems (conflict detection, validator, CP-SAT optimizer, PPO policy)

---

## 2. Infrastructure Topology Assumptions

### NET-001: Synthetic Linear Network Topology
- **Category:** Network Topology
- **Baseline Value:** 5 stations (`NDL`, `KRN`, `MLG`, `SRP`, `VSN`), 4 sections, comprising 2 single-line bottlenecks and 2 double-line sections.
- **Physical Details:**
  - `NDL–KRN` (Section S1): Single-line bottleneck (Block `B1`), distance 14.0 km, max speed 90 km/h, run time 12 min.
  - `KRN–MLG` (Section S2): Double-line unidirectional (Blocks `B2U`, `B2D`), distance 18.0 km, max speed 110 km/h, run time 10 min.
  - `MLG–SRP` (Section S3): Single-line bottleneck (Block `B3`), distance 16.0 km, max speed 85 km/h, run time 14 min.
  - `SRP–VSN` (Section S4): Double-line unidirectional (Blocks `B4U`, `B4D`), distance 20.0 km, max speed 120 km/h, run time 10 min.
- **Subsystems Affected:** Routing, block occupancy tracking, crossing conflict detection, CP-SAT time-space discretization.

### NET-002: Junction Throat Capacity
- **Category:** Network / Interlocking
- **Baseline Value:** 2 concurrent movements across junction throats at `NDL` and `MLG`.
- **Configurable Via:** `RAILGORITHM_JUNCTION_THROAT_CAPACITY` (Integer, default `2`).
- **Subsystems Affected:** Junction conflict detection, CP-SAT cumulative capacity constraints (`AddCumulative`).

### NET-003: Platform Geometry and Dimensions
- **Category:** Station Infrastructure
- **Baseline Value:**
  - `NDL`: 3 platforms (`P1`, `P2`, `P3`), length 720 m
  - `KRN`: 2 platforms (`P1`, `P2`), length 580 m
  - `MLG`: 3 platforms (`P1`, `P2`, `P3`), length 650 m
  - `SRP`: 2 platforms (`P1`, `P2`), length 560 m
  - `VSN`: 2 platforms (`P1`, `P2`), length 600 m
- **Subsystems Affected:** Platform capacity conflict detection, train-to-platform assignment feasibility.

---

## 3. Rolling Stock and Operational Categories

### TRN-001: Train Categories and Priority Hierarchy
- **Category:** Rolling Stock
- **Baseline Classes:**
  1. `EXPRESS` (Priority 1): Premium passenger service, speed factor 0.85 (15% faster than nominal), max speed 130 km/h, default station dwell 1 min.
  2. `PASSENGER` (Priority 3): Ordinary passenger service, speed factor 1.00 (nominal), max speed 100 km/h, default station dwell 2 min.
  3. `MEMU` (Priority 4): Suburban commuter service, speed factor 1.00 (nominal), max speed 90 km/h, default station dwell 1 min.
  4. `FREIGHT` (Priority 5): Goods service, speed factor 1.25 (25% slower than nominal), max speed 75 km/h, default station dwell 2 min.
- **Subsystems Affected:** Weighted delay objective calculation, overtaking conflict projection, candidate precedence generation.

### TRN-002: Maximum Permissible Station Hold Policy
- **Category:** Operations
- **Baseline Thresholds:**
  - `EXPRESS`: 20 minutes maximum hold
  - `PASSENGER`: 30 minutes maximum hold
  - `MEMU`: 25 minutes maximum hold
  - `FREIGHT`: 45 minutes maximum hold
- **Subsystems Affected:** Independent validator (`HC-004`), candidate generation bounds, CP-SAT decision variable domains.

---

## 4. Headway and Signalling Assumptions

### SIG-001: Minimum Longitudinal Headway
- **Category:** Signalling
- **Baseline Values:**
  - Single-line sections (`S1`, `S3`): 4 minutes minimum separation
  - Double-line sections (`S2`, `S4`): 3 minutes minimum separation
- **Configurable Via:** Section-level parameter `headway_min`.
- **Subsystems Affected:** Headway conflict detection, CP-SAT precedence spacing constraints, validator trajectory verification.

### SIG-002: Running Train Non-Preemption
- **Category:** Safety Interlocking
- **Rule:** A train currently in motion inside a block cannot be held or stopped mid-block. Holds may only be scheduled at station platform tracks.
- **Subsystems Affected:** Validator action validation (`HC-008`), candidate generator filtering.

---

## 5. Temporal and Horizon Assumptions

### TIM-001: Recommendation Projection Horizon
- **Category:** Temporal
- **Baseline Value:** 75 minutes forward projection.
- **Configurable Via:** `RAILGORITHM_RECOMMENDATION_HORIZON` (default `75`).
- **Subsystems Affected:** Conflict projection, CP-SAT solve horizon, PPO feature generation.

### TIM-002: Decision Application Window
- **Category:** Temporal
- **Baseline Value:** 30 minutes post-approval simulated evaluation window.
- **Configurable Via:** `RAILGORITHM_DECISION_APPLY_MINUTES` (default `30`).
- **Subsystems Affected:** Simulation step on approval, audit metrics capture.

---

## 6. Disruption and Maintenance Assumptions

### DIS-001: Disruption Types and Invariants
- **Category:** Disruption Simulation
- **Supported Classes:**
  - `BLOCK_CLOSURE`: Complete unavailability of a block interval $[t_{start}, t_{end}]$.
  - `PLATFORM_OUTAGE`: Loss of specific platform track at a station $[t_{start}, t_{end}]$.
  - `TRAIN_DELAY`: Injected initial or intermediate schedule delay.
  - `SPEED_RESTRICTION`: Speed factor reduction across specific sections or blocks.
- **Invariance Rule:** A block closure cannot be scheduled on a block currently occupied by a train at the closure start time without generating a critical conflict.

---

## 7. Full Assumption Register

| ID | Category | Title | Value | Unit | Override Env Var |
|---|---|---|---|---|---|
| `NET-001` | Network | Linear Topology | 5 stations, 4 sections | topology | None (code-defined) |
| `NET-002` | Network | Junction Throat Capacity | 2 simultaneous | movements | `RAILGORITHM_JUNCTION_THROAT_CAPACITY` |
| `NET-003` | Network | Platform Dimensions | 560–720m | meters | None |
| `TRN-001` | Trains | Priority Classes | Exp:1, Pass:3, Memu:4, Fgt:5 | class | None |
| `TRN-002` | Trains | Max Hold Limits | Exp:20, Pass:30, Memu:25, Fgt:45 | min | None |
| `SIG-001` | Signalling| Minimum Headways | Single:4, Double:3 | min | None |
| `SIG-002` | Signalling| Non-Preemption | Stations only | policy | None |
| `TIM-001` | Temporal | Projection Horizon | 75 | min | `RAILGORITHM_RECOMMENDATION_HORIZON` |
| `TIM-002` | Temporal | Apply Horizon | 30 | min | `RAILGORITHM_DECISION_APPLY_MINUTES` |
| `OPT-001` | Optimizer| CP-SAT Time Limit | 8 | seconds | `RAILGORITHM_CP_SAT_TIME_LIMIT` |
| `OPT-002` | Optimizer| Deterministic Workers | 1 | thread | `RAILGORITHM_CP_SAT_WORKERS` |
| `OPT-003` | Optimizer| Balanced Weights | delay:1, max_delay:2, hold:3 | weights | `RAILGORITHM_OBJECTIVE_PROFILE` |
