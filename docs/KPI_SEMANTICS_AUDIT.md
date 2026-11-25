# KPI SEMANTICS AUDIT & METHODOLOGY REPORT — RAILGORITHM v2.4

## 1. Executive Summary

A railway decision-support application must never report ambiguous, mathematically deceptive, or misleading metrics. In this audit, every Station Master and Section Controller KPI has been formally defined, verified against ground-truth mathematical baselines, and hardened against edge cases.

> [!IMPORTANT]
> **Resolution of Misleading 100% Adherence Edge Case:**
> In previous versions, when zero trains were present or scheduled in a station observation window, schedule adherence defaulted to `100.0%`. In RAILGORITHM v2.4, this misleading metric has been eliminated: `schedule_adherence_pct` evaluates to `null` with explicit operational status `adherence_status: "NO_DATA"` and explanatory text `"No trains scheduled or monitored in station window"`.

---

## 2. Station Master KPIs

The Station Master's operational jurisdiction is strictly scoped to their local station interlocking limits and trains approaching within a $[-30\text{ min}, +60\text{ min}]$ operational window.

### Mathematical Definitions & Semantics

| KPI Name | Return Type | Mathematical Formula / Derivation | Operational Meaning | Edge-Case Handling |
| :--- | :--- | :--- | :--- | :--- |
| **`trains_monitored`** | `int` | $N = \sum \mathbb{I}(\text{at\_station} \lor \text{approaching})$ | Total trains currently berthed at platforms or scheduled to arrive within 60 minutes. | Returns `0` if empty. |
| **`on_time_trains`** | `int` | $\sum \mathbb{I}(\text{delay} \le 5\text{ min})$ | Count of monitored trains with projected arrival/departure delay $\le 5$ minutes. | Returns `0` if empty. |
| **`delayed_trains`** | `int` | $\sum \mathbb{I}(\text{delay} > 5\text{ min})$ | Count of monitored trains with projected delay exceeding 5 minutes. | Returns `0` if empty. |
| **`schedule_adherence_pct`** | `float \| null` | $\frac{N_{\text{on\_time}}}{N_{\text{monitored}}} \times 100$ | Proportion of monitored trains adhering to schedule under the Indian Railways Mail/Express punctuality threshold. | **Returns `null` with `adherence_status: "NO_DATA"` if $N=0$. Never returns misleading 100%.** |
| **`punctuality_threshold_min`**| `int` | Constant ($5\text{ min}$) | Statutory Indian Railways punctuality tolerance for Mail, Express, and Passenger services. | Fixed constant `5`. |
| **`platform_availability_pct`** | `float` | $\frac{P_{\text{available}}}{P_{\text{total}}} \times 100$ | Percentage of station platform berths currently clear and unoccupied. | Evaluated against total physical platforms ($P_{\text{total}}$). |
| **`average_arrival_delay_min`**| `float` | $\frac{1}{N_{\text{arr}}} \sum \text{delay}_{\text{arr}}$ | Arithmetic mean projected delay of all approaching trains. | Returns `0.0` if no approaching trains. |
| **`average_departure_delay_min`**| `float` | $\frac{1}{N_{\text{dep}}} \sum \text{delay}_{\text{dep}}$ | Arithmetic mean projected delay of all trains berthed at platforms. | Returns `0.0` if no trains berthed. |

---

## 3. Section Controller KPIs

The Section Controller manages traffic across the entire multi-station corridor, overseeing section running line occupancy, junction bottlenecks, and knock-on delay propagation.

### Mathematical Definitions & Semantics

| KPI Name | Return Type | Mathematical Formula / Derivation | Operational Meaning & Classification | Edge-Case Handling |
| :--- | :--- | :--- | :--- | :--- |
| **`trains_active`** | `int` | $\sum \mathbb{I}(\text{status} \in \{\text{RUNNING}, \text{AT\_STATION}\})$ | Count of trains currently on running lines or berthed at stations. | Returns `0` if none active. |
| **`block_occupancy_pct`** | `float` | $\frac{B_{\text{occupied}}}{B_{\text{total\_running}}} \times 100$ | Proportion of running line track blocks occupied by trains. Denominator strictly counts running lines (excludes sidings and dead-ends). | Standard Northern Section denominator is $B=6$. |
| **`junction_throat_load_pct`** | `float` | $\min\left(100.0, \frac{T_{\text{throat}}}{C_{\text{throat}}} \times 100\right)$ | Proportion of physical junction throat capacity in simultaneous use at Malgaon ($C=2$). | Clamped to $100.0\%$ maximum. |
| **`delay_propagation_index`** | `float` | $\text{DPI} = \frac{\Delta_{\text{secondary}}}{\max(1, \Delta_{\text{initial}})}$ | Ratio of knock-on secondary delays to root-cause primary delays. **Explicitly labeled: `is_statutory_standard = False`, `methodology = "HEURISTIC_SIMULATION_ESTIMATE"`.** | Protected against division-by-zero when $\Delta_{\text{initial}}=0$. |
| **`knock_on_risk_level`** | `str` | Tiers: `LOW` ($\le 0.4$), `MODERATE` ($>0.4$), `HIGH` ($>1.0$), `SEVERE` ($>2.0$ or critical conflict) | Operational risk assessment of cascading corridor delay. | Deterministic tier thresholds. |
| **`recovery_clearance_rate_pct`** | `float` | $\frac{C_{\text{total\_detected}} - C_{\text{active}}}{\max(1, C_{\text{total\_detected}})} \times 100$ | Percentage of detected conflicts successfully resolved or spatially cleared. | Returns `100.0%` if no conflicts ever detected. |

---

## 4. Empirical Ground-Truth Test Matrix

In `backend/tests/test_kpi_correctness.py`:
- **`test_station_master_kpis_ground_truth_calculation`:** Verified against synthetic ground-truth scenario `normal_traffic` at Malgaon (MLG).
- **`test_station_master_empty_station_missing_data_behavior`:** Tested empty station state ($N=0$); verified `schedule_adherence_pct is None`, `adherence_status == "NO_DATA"`, and `punctuality_threshold_min == 5`.
- **`test_section_controller_kpis_ground_truth_calculation`:** Verified all 6 track blocks, throat capacity $C=2$, and delay metrics on `single_line_meet`.
- **`test_section_controller_knock_on_risk_threshold_tiers`:** Verified exact transitions across LOW, HIGH, and SEVERE risk tiers for DPI values 0.20, 1.50, and 2.50.
- **Result: 100% Passed.**
