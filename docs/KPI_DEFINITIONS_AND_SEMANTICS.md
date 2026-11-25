# RAILGORITHM KPI Definitions & Mathematical Semantics

## 1. Principles of Operational Accuracy

Every operational metric presented in RAILGORITHM must adhere to strict mathematical integrity:

1. **Backend Authoritative**: The backend is the single source of truth for all mathematical calculations. The frontend must never silently recalculate or approximate operational values.
2. **Strict Null Semantics (`NO_DATA`)**: An unobserved window or empty dataset must **never** be coerced into `0` or `100%`. If no trains traversed a station within a time window, the average arrival delay is `null` (`"—"`), not `0.0 min`. If no conflicts have ever occurred, the conflict recovery clearance rate is `null` (`"—"`), not `100.0%`.
3. **Statutory vs Administrative Traceability**: Operational thresholds (such as the 5-minute punctuality criterion) are documented under their true authority (e.g. Railway Board Operating Directorate guidelines for Mail/Express monitoring), and are never falsely cited as statutory General Rules.
4. **Transparent Classification**: Every metric is explicitly tagged as `MEASURED`, `CALCULATED`, `PREDICTED`, `HEURISTIC`, or `NO_DATA`.

---

## 2. Station Master KPI Registry

| Metric Name | Classification | Formula / Mathematical Definition | Unit | Reporting Window | Data Source | Missing Data Semantics |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Trains Monitored** | `MEASURED` | $\sum \mathbb{I}(\text{train scheduled in window})$ | count | Rolling 60m / Horizon | Station Working Timetable & Movement Ledger | `0` if no trains scheduled |
| **Schedule Adherence** | `CALCULATED` | $\frac{\text{Trains with delay} \le T_{\text{punctual}}}{\text{Trains Monitored}} \times 100\%$ | % | Rolling 60m ($T = 5\text{ min}$) | Railway Board 5-Min Punctuality Criterion | `null` (`"—"`) if zero monitored trains |
| **Platform Availability** | `MEASURED` | $\frac{\text{Platforms Available}}{\text{Platforms Total}} \times 100\%$ | % | Current Instant | Station Interlocking & Berthing State | Exact measured fraction ($0.0\%$ to $100.0\%$) |
| **Average Arrival Delay** | `CALCULATED` | $\frac{1}{|A|} \sum_{t \in A} \max(0, \text{delay}_t)$ where $A = \text{approaching trains}$ | min | Rolling 60m | Section Block Tracking & Radar | `null` (`"—"`) if no approaching trains ($|A| = 0$) |
| **Average Departure Delay**| `CALCULATED` | $\frac{1}{|D|} \sum_{t \in D} \max(0, \text{delay}_t)$ where $D = \text{stationed departures}$ | min | Rolling 60m | Platform Berthing Ledger | `null` (`"—"`) if no stationed departures ($|D| = 0$) |
| **On-Time Trains** | `MEASURED` | Count of trains with arrival delay $\le 5\text{ min}$ | count | Rolling 60m | Timetable Adherence Ledger | `0` if no on-time arrivals |
| **Station Alerts & Recs** | `MEASURED` | Active local conflicts + pending station decisions | count | Active Planning Horizon | Independent Validator & CP-SAT Engine | `0` if station operating normally |
| **Pending Decisions** | `CALCULATED` | Local advisory recommendations awaiting SM review | count | Queue | CP-SAT / PPO Advisory Engine | `0` if queue is empty |

---

## 3. Section Controller KPI Registry

| Metric Name | Classification | Formula / Mathematical Definition | Unit | Reporting Window | Data Source | Missing Data Semantics |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Active Corridor Trains** | `MEASURED` | Trains currently running or berthed on corridor tracks | count | Current Instant | Block Section Transits | `0` if corridor is empty |
| **Average Section Delay** | `CALCULATED` | $\frac{1}{|T_{\text{active}}|} \sum_{t \in T_{\text{active}}} \text{delay}_t$ | min | Corridor Operational Horizon | Station Master Train Registers | `0.0 min` if all trains on time; `null` if no trains |
| **Block Occupancy** | `MEASURED` | $\frac{\text{Occupied Blocks}}{\text{Total Configured Blocks}} \times 100\%$ | % | Current Instant | Axle Counters & Track Circuits | Exact measured fraction |
| **Junction Throat Load** | `CALCULATED` | $\frac{\text{Active Transits}}{\text{Throat Capacity}} \times 100\%$ (Capacity = 2 for MLG) | % | Simulated Planning Horizon | Diamond Crossing Interlocking Model | $0.0\%$ to $100.0\%$ |
| **Corridor Throughput** | `CALCULATED` | $\frac{\text{Completed Transits}}{\text{Elapsed Hours}}$ | tph | Rolling 60m | Movement Realization | `0.0 tph` if no completed transits |
| **Delay Propagation (DPI)**| `HEURISTIC` | $\frac{\text{Secondary Knock-On Delay Min}}{\text{Primary Schedule Delay Min}}$ | x | Knock-On Horizon | Advisory Secondary Delay Model | `0.0x` if no secondary delays; labeled HEURISTIC |
| **Delayed Corridor Trains** | `MEASURED` | Count of active trains with projected delay $> 0\text{ min}$ | count | Rolling 60m | Section OS Data | `0` if all trains on time |
| **Active Route Conflicts** | `MEASURED` | Unresolved headway, platform, or direction violations | count | Active Window | Independent Constraint Validator | `0` if corridor is clear of conflicts |
| **Recovery Clearance Rate**| `CALCULATED` | $\frac{\text{Resolved Conflicts}}{\text{Total Recorded Conflicts}} \times 100\%$ | % | Cumulative Session | Append-Only Audit Trail | `null` (`"—"`) if zero conflicts have ever occurred |

---

## 4. Statutory vs Administrative Clarification

### A. Line Clear & Directional Safety (Statutory)
- **General Rule 1.02(62)**: Defines "Wrong Line" operations on double-line block sections. Moving a train against normal direction without authoritative Line Clear constitutes a statutory violation.
- **General Rule 8.01 & 8.03(1)**: Absolute Block System conditions for granting Line Clear. No train may enter a block section until the preceding train has completely cleared the adequate distance.
- **Enforcement**: Hard safety constraint in `backend/app/domain/validator.py`. A violation cannot be overridden by AI recommendations or operator preference.

### B. Punctuality Monitoring Standard (Administrative)
- **Authority**: Railway Board Operating Directorate Circulars for Mail/Express punctuality monitoring.
- **Definition**: A passenger service is classified as on-time if its arrival delay at the reporting station is within **5 minutes** of the working timetable.
- **Enforcement**: Administrative guideline exposed via the configurable parameter `punctuality_threshold_min: int = 5` in analytics and KPI APIs.
