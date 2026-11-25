# Section Controller Corridor Dashboard Specification

## 1. Overview & Operational Purpose

The **Section Controller Corridor Dashboard** provides macroscopic, corridor-wide traffic management and dispatching oversight across the entire railway division (Nandpur to Vasanthpur).

Designed for Section Controllers, Chief Controllers, and Dispatch Superintendents, this interface enables operating personnel to monitor track circuit occupancies, manage junction diamond crossing bottlenecks, evaluate secondary delay propagation, and resolve conflicting train paths across single-line and double-line sections.

---

## 2. Key Screen Components

### A. Operational Corridor Controls (Top Bar)
- **Simulation Progression Controls**: Dedicated controls enabling the Section Controller to advance the operational clock by `+5m`, `+15m`, or `+30m` to evaluate projected traffic flow.
- **Simulation Pause & Reset**: Fast control buttons to freeze the state or reset the scenario.
- **Scenario Management**: Direct entry point to launch new synthetic scenarios (`New simulation`).
- **Data Freshness Banner**: Live feed health monitor indicating heartbeat status, message rate, and clock drift.

---

### B. Standardized Corridor KPI Metrics

The Section Controller view displays **9 authoritative corridor KPIs**:

1. **Active Corridor Trains**: Count of all trains currently traversing the corridor or berthed at stations, with completed and scheduled counts in the hint.
2. **Average Section Delay**: Mean delay across all active and completed trains on this corridor in minutes, with total cumulative section delay.
3. **Block Occupancy**: Percentage of block sections currently occupied by trains (`blocks_occupied` / `blocks_total`), signaling corridor density.
4. **Junction Throat Load (MLG)**: Capacity utilization percentage of the critical Malgaon diamond crossing throat (capacity = 2 parallel movements), alongside queue length and congestion classification (`LOW`, `MODERATE`, `HIGH`, `SATURATED`).
5. **Corridor Throughput**: Realized train throughput in trains per hour (`tph`) over the operational window, with on-time adherence rate.
6. **Delay Propagation Index (DPI)**: Ratio of secondary knock-on delay minutes to initial primary delay minutes. Tagged as `HEURISTIC` simulation estimate.
7. **Delayed Corridor Trains**: Number of delayed active trains relative to total active trains.
8. **Active Route Conflicts**: Unresolved route, headway, or platform occupancy conflicts detected by the independent validator, with critical conflict breakdown.
9. **Recovery Clearance Rate**: Percentage of historical conflicts resolved within the active session. Guarded by `null` semantics (`"—"`) when no historical conflicts exist.

---

### C. Interactive Railway Corridor Schematic (`RailwayCorridorDiagram`)

A high-fidelity horizontal SVG schematic reflecting the actual configured physical network:

- **Stations**:
  - `NDL` — Nandpur (Station Node)
  - `KRN` — Karanpur (Station Node)
  - `MLG` — Malgaon Junction (Diamond Crossing Junction Node, capacity = 2)
  - `SRP` — Suryapur (Station Node)
  - `VSN` — Vasanthpur (Terminal Station Node)
- **Tracks & Block Sections**:
  - `S1` (`NDL–KRN`): Single-Line Bottleneck, Block `B1`, Absolute Block System.
  - `S2` (`KRN–MLG`): Double-Line Section, Blocks `B2U` (UP track) and `B2D` (DOWN track).
  - `S3` (`MLG–SRP`): Single-Line Bottleneck, Block `B3`, Absolute Block System.
  - `S4` (`SRP–VSN`): Double-Line Section, Blocks `B4U` (UP track) and `B4D` (DOWN track).
- **Dynamic Track States**:
  - Green (`#16A34A`): Clear and available block section.
  - Amber / Train Marker (`#D97706`): Block occupied by a train. Renders train marker badge with Train ID and direction arrow (`▶` for UP, `◀` for DN).
  - Red Dashed (`#DC2626`): Maintenance closure or track outage.
- **Conflict Warning Badges**: Overlaid warning markers indicating locations with detected headway or route conflicts.
- **Click-to-Inspect**: Clicking any station node immediately switches the dashboard to that station's detailed Station Master view.

---

### D. Visual Analytics: Corridor Delay & Junction Throat Bottlenecks

1. **Corridor Punctuality Status (`DelayDistributionChart`)**:
   - Visual progress distribution comparing active trains running on schedule versus delayed.
2. **Junction Congestion & Throat Bottlenecks Panel**:
   - Monitors the diamond crossing at Malgaon Junction (`MLG`).
   - Displays capacity (2 simultaneous parallel movements) and active transiting trains.
   - Lists occupied single-line bottleneck blocks (`B1`, `B2`, `B4`, `B5`) and the train occupying each.

---

### E. Corridor Active Trains Ledger

Comprehensive real-time ledger of all active trains in the corridor, detailing:
- `Train`: Train ID and Name.
- `Type / Priority`: Service category (e.g. Express P1, Freight P4).
- `Direction`: `UP` (Nandpur → Vasanthpur) or `DOWN` (Vasanthpur → Nandpur).
- `Track Location`: Specific block section or station platform currently occupied.
- `Delay`: Current projected delay minutes.
- `Waiting / Reason`: Explanation for hold (e.g., awaiting line clear, single-line meet).
- `Route Progress`: Origin station to destination station.

---

### F. Corridor Dispatch Decisions & Active Conflicts Resolution Queue

- **Pending Dispatch Decisions**: Advisory schedule adjustments (holds, precedence inversions, or crossing diversions) generated by the CP-SAT optimization engine.
  - Highlights model disagreements between CP-SAT and PPO ranking models.
  - Direct link to `Review & Decide` for human verification.
- **Active Corridor Conflicts**: Detailed list of all active constraints detected by the independent validator (headway violations, platform contention, or directional locking violations under GR 1.02(62) and GR 8.01).

---

## 3. Human Decision Protocol (Non-Autonomous)

RAILGORITHM strictly adheres to the principle of human-in-the-loop dispatching:
- **No autonomous interlocking control**: The system does not directly set points, clear signals, or command interlocking relays.
- **Advisory Decision Support**: AI recommendations are strictly advisory and require explicit operator review, rationale entry, and confirmation before being applied to the simulation schedule.
