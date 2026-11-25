# KPI Authority, Semantics & Null Handling — RAILGORITHM v2.5

## 1. Executive Summary & Purpose

Operational decision-support tools must communicate performance indicators with mathematical precision and regulatory clarity. Reporting arbitrary zeros or defaulting to 100% when data is absent misleads dispatchers and distorts historical safety audits.

RAILGORITHM v2.5 formalizes:
1. The regulatory authority and non-statutory nature of operational KPIs.
2. Formal null semantics for empty observation windows.
3. Explicit heuristic classification of predictive indices (Delay Propagation Index).
4. Six standardized operational health statuses.

---

## 2. Regulatory Authority & Configurable Punctuality

### 2.1. Statutory General Rules vs. Operational Guidelines
- **General Rules 1976 (Open Lines):** The statutory General Rules govern railway safety, signaling, train operation, and interlocking. **They do not define numerical punctuality percentages or delay thresholds.**
- **Railway Board Operating Directorate Circulars:** Punctuality monitoring thresholds are administrative guidelines issued periodically by the Railway Board Operating Directorate for Mail/Express performance reporting (typically 5 minutes for Mail/Express, 15 minutes for freight or suburban line punctuality).

### 2.2. Configurable Punctuality Threshold
In RAILGORITHM v2.5, the punctuality threshold is made explicitly configurable via the API parameter `punctuality_threshold_min` (default: 5 minutes):
$$\text{is\_on\_time}(t) \iff \text{projected\_delay\_min}(t) \le \text{punctuality\_threshold\_min}$$

Dispatchers and divisional controllers may configure this parameter dynamically based on the service pattern (e.g. 5 min for Mail/Express, 15 min for goods corridors).

---

## 3. Formal Null Semantics for Empty Observation Windows

When an observation window contains zero relevant trains or conflicts, calculating ratios creates mathematical indeterminacy ($0 / 0$). Reporting `0.0` or `100.0%` in such scenarios is factually misleading:
- Reporting `average_arrival_delay_min = 0.0` implies trains arrived perfectly on time, when in reality **no trains were approaching**.
- Reporting `schedule_adherence_pct = 100.0%` or `0.0%` falsely indicates flawless or catastrophic performance when **no trains were monitored**.
- Reporting `recovery_clearance_rate_pct = 100.0%` implies superior conflict recovery when **no conflicts ever occurred**.

### 3.1. Standardized Null Contract in v2.5

| KPI Identifier | Role Jurisdiction | Condition When Null | Return Value | Status Code / Explanation |
| :--- | :--- | :--- | :--- | :--- |
| **`schedule_adherence_pct`** | Station Master | 0 monitored trains in active window $[T-30\text{m}, T+60\text{m}]$ | `null` | `adherence_status: "NO_DATA"` |
| **`average_arrival_delay_min`** | Station Master | 0 approaching trains scheduled within lookahead | `null` | Displayed as `"—"` with hint `"no approaching trains"` |
| **`average_departure_delay_min`** | Station Master | 0 stationed trains currently berthed at station | `null` | Displayed as `"—"` with hint `"no stationed trains"` |
| **`recovery_clearance_rate_pct`** | Section Controller | 0 total conflicts ever detected in the scenario | `null` | Displayed as `"—"` with hint `"No historical conflicts recorded"` |

---

## 4. Heuristic Classification of Predictive Metrics

Certain metrics in the Section Controller dashboard represent predictive estimation models rather than physically measured quantities:

### 4.1. Delay Propagation Index (DPI)
$$\text{DPI} = \frac{\text{Secondary Knock-On Delay (min)}}{\max(1, \text{Initial Root Cause Delay (min)})}$$

- **`delay_propagation_is_statutory`**: `false`
- **`delay_propagation_methodology`**: `HEURISTIC_SIMULATION_ESTIMATE`
- **Knock-On Risk Tiers**:
  - `LOW`: $\text{DPI} \le 0.4$ and 0 critical/major conflicts.
  - `MODERATE`: $0.4 < \text{DPI} \le 1.0$.
  - `HIGH`: $1.0 < \text{DPI} \le 2.0$ or $>1$ major conflict.
  - `SEVERE`: $\text{DPI} > 2.0$ or $\ge 1$ critical conflict.

Both the API response and UI dashboard explicitly display these methodology tags to ensure dispatchers understand they are consulting heuristic decision-support estimates.

---

## 5. Honest Operational Status Definitions

To eliminate ambiguous or misleading "green" dashboard indicators, RAILGORITHM v2.5 defines six standardized operational health statuses across the backend and frontend:

| Status Code | Severity Tone | Operational Definition | Dispatcher Advisory |
| :--- | :--- | :--- | :--- |
| **`HEALTHY`** | Green (good) | Feed connected, telemetry received within degraded threshold ($\le 15\text{ s}$), zero circuit breaker or persistence errors. | Normal real-time advisory operations. |
| **`DEGRADED`** | Amber (watch) | Telemetry freshness exceeds degraded threshold ($> 15\text{ s}$) or error rate elevated ($> 15\%$). | Monitor feed; recommendations continue with freshness notice. |
| **`STALE`** | Amber (watch) | Telemetry freshness exceeds stale threshold ($> 30\text{ s}$). Live data is temporarily absent. | Advisory banner active; fallback to deterministic simulation. |
| **`OFFLINE`** | Red (bad) | Feed disconnected or circuit breaker opened due to sustained failure ($> 10$ consecutive errors). | Feed isolated; dispatcher reconnection required. |
| **`DURABILITY_UNAVAILABLE`** | Red (bad) | Database persistence failure in `LIVE_OPERATIONAL` mode. Transaction committed to disk has failed. | Event acknowledgements suspended; dispatchers alerted to disk write fault. |
| **`REPLAY_UNCERTAIN`** | Amber (watch) | Reconstructed event stream contains unresolved causal dependencies, cycles, or timestamp inversions. | Reconstructed state marked non-authoritative (`is_authoritative_live: false`). |
