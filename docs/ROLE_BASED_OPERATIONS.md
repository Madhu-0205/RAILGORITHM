# RAILGORITHM 2.2 — Role-Based Operations & KPI Intelligence

## 1. Operational Roles & Scope Separation

RAILGORITHM 2.2 enforces strict separation of responsibilities between two primary railway operating roles, aligned with Indian Railways operating procedures:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        ROLE SEPARATION HIERARCHY                       │
├───────────────────────────────────┬────────────────────────────────────┤
│       STATION MASTER (SM)         │      SECTION CONTROLLER (SC)       │
├───────────────────────────────────┼────────────────────────────────────┤
│ • Local station yard control      │ • Entire corridor dispatching      │
│ • Platform berthing allocations   │ • Mainline block occupancy         │
│ • Local dwell & dispatch monitoring│ • Junction throat bottlenecks (MLG)│
│ • Station-level conflict review   │ • Section-wide train priorities    │
│ • Monitored station trains (60m)  │ • Delay propagation & knock-on risk│
│ • Local scope: NDL/KRN/MLG/SRP/VSN│ • Global scope: Full 120 km line   │
└───────────────────────────────────┴────────────────────────────────────┘
```

---

## 2. Station Master Dashboard & Workflows

### 2.1 Station Master Screen Layout
The Station Master interface (`/dashboard` with Station View active) focuses on immediate station operations:
1. **Platform Berth Visualizer:** High-visibility, real-time berthing cards displaying every platform berth:
   - `AVAILABLE` (Green): Platform unoccupied, signalled, and ready for train reception.
   - `OCCUPIED` (Blue): Berthed train ID, current dwell status, and scheduled departure.
   - `OUTAGE` (Red): Maintenance closure, track circuit failure, or overhead line outage.
2. **Monitored Train Movements Table:** Rolling 60-minute window of approaching and berthed trains, detailing arrival/departure schedules, platform assignments, and delay deltas.
3. **Station Operational Alerts & Recommendations:** Filtered decision queue containing only recommendations and track alerts physically located at the Station Master's station.

### 2.2 Station Master Key Performance Indicators (KPIs)

| Metric Name | Mathematical Definition | Time Period | Target SLA |
| :--- | :--- | :--- | :--- |
| **Trains Monitored** | $N_{\text{monitored}} = \sum \mathbf{1}_{\{\text{train at station or arriving in window}\}}$ | Rolling 60 minutes | Informational |
| **Schedule Adherence** | $P_{\text{adherence}} = \frac{N_{\text{on-time}}}{N_{\text{monitored}}} \times 100 \quad (\text{delay} \le 5 \text{ min})$ | Rolling 60 minutes | $\ge 85.0\%$ |
| **Platform Availability** | $P_{\text{avail}} = \frac{N_{\text{platforms free}}}{N_{\text{platforms total}}} \times 100$ | Instantaneous snapshot | $\ge 25.0\%$ |
| **Average Arrival Delay** | $\bar{D}_{\text{arr}} = \frac{1}{|T_{\text{arr}}|} \sum_{i \in T_{\text{arr}}} \max(0, t_{\text{actual arr}, i} - t_{\text{sched arr}, i})$ | Approaching trains | $\le 5.0$ min |
| **Average Departure Delay**| $\bar{D}_{\text{dep}} = \frac{1}{|T_{\text{dep}}|} \sum_{i \in T_{\text{dep}}} \max(0, t_{\text{actual dep}, i} - t_{\text{sched dep}, i})$ | Stationed trains | $\le 5.0$ min |
| **Platform Outage Count** | $N_{\text{outage}} = \sum \mathbf{1}_{\{\text{platform status} = \text{OUTAGE}\}}$ | Current state | 0 |

---

## 3. Section Controller Corridor Dashboard & Workflows

### 3.1 Section Controller Screen Layout
The Section Controller interface provides full-corridor situation awareness across all 5 stations and 120 km of track:
1. **Corridor Movement Overview:** Live count of active trains running on the mainline, completed runs, and upcoming scheduled departures.
2. **Malgaon (MLG) Junction Throat Load Monitor:** Monitors the diamond crossing at Malgaon Junction. Displays active diamond movements vs throat capacity (2), junction queue length, and congestion level (`LOW`, `MODERATE`, `HIGH`, `SATURATED`).
3. **Single-Line Bottleneck Tracker:** Visual indicators for single-line blocks (B1, B2, B4, B5) indicating which train holds the exclusive token and remaining clearance time.
4. **Delay Propagation & Knock-On Analysis:** Highlights secondary delay escalation risks before they cause gridlock.
5. **Full Corridor Decision Queue:** Prioritized list of CP-SAT and PPO conflict resolutions requiring Section Controller authorization.

### 3.2 Section Controller Key Performance Indicators (KPIs)

| Metric Name | Mathematical Definition | Time Period | Target SLA |
| :--- | :--- | :--- | :--- |
| **Average Section Delay** | $\bar{D}_{\text{sec}} = \frac{1}{|T_{\text{active}}|} \sum_{i \in T_{\text{active}}} D_i$ | Current active trains | $\le 10.0$ min |
| **Block Occupancy Rate** | $R_{\text{block}} = \frac{N_{\text{blocks occupied}}}{N_{\text{blocks total}}} \times 100$ | Instantaneous corridor snapshot | $\le 60.0\%$ |
| **Junction Throat Load** | $L_{\text{throat}} = \frac{N_{\text{active diamond movements}}}{C_{\text{throat capacity}}} \times 100 \quad (C=2)$ | Instantaneous at Malgaon (MLG) | $\le 75.0\%$ |
| **Delay Propagation Index ($DPI$)** | $DPI = \frac{\sum \text{Secondary Delay Minutes}}{\sum \text{Initial Timetable Deviation Minutes}}$ | Rolling simulation window | $\le 0.50$ (Low risk) |
| **Knock-On Risk Level** | Derived from $DPI$: $\le 0.5 \implies \text{LOW}$, $0.5\text{--}1.0 \implies \text{MODERATE}$, $1.0\text{--}2.0 \implies \text{HIGH}$, $> 2.0 \implies \text{SEVERE}$ | Rolling simulation window | Low / Moderate |
| **Throughput Rate** | $Th = \frac{N_{\text{trains completed}}}{\Delta t_{\text{hours}}}$ | Corridor operating hour | Design capacity |
| **Recovery Clearance Rate**| $R_{\text{rec}} = \frac{N_{\text{conflicts resolved}}}{N_{\text{conflicts detected}}} \times 100$ | Active operational shift | $\ge 80.0\%$ |

---

## 4. Human Authority & Approval Workflow

RAILGORITHM is strictly an advisory decision-support system. All dispatch interventions follow a strict audit trail:

1. **System Computes Alternatives:** When conflicts or congestion arise, CP-SAT and PPO produce feasible resolution schedules.
2. **Independent Validation:** Every alternative schedule is independently verified against headway, block occupancy, route locking, and platform constraints.
3. **Recommendation Presentation:** Recommendations display full operational evidence:
   - Affected trains and resources
   - Projected delay impact and trade-offs
   - Mathematical constraint citations
   - Model consensus or disagreement details
   - Live telemetry freshness age
4. **Human Decision:** Only an authenticated Station Master (for station scope) or Section Controller (for section scope) can approve or reject a recommendation.
5. **Cryptographic Audit Chain:** Every human decision is appended to an immutable, hash-chained ledger storing:
   - User identity & role
   - UTC timestamp
   - Exact recommendation version
   - Validation signature
   - Human operator rationale text
   - Previous entry SHA-256 hash
