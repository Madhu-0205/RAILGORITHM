# RAILGORITHM 2.0 — CP-SAT Benchmarking Report

**Solver Engine:** Google OR-Tools CP-SAT (Version 9.15.6755)  
**Optimizer Specification:** `cpsat-2.0.0`  
**Worker Mode:** Single-threaded deterministic (`RAILGORITHM_CP_SAT_WORKERS=1`)  
**Time Limit:** 8.0 seconds (`RAILGORITHM_CP_SAT_TIME_LIMIT=8`)  

---

## 1. Mathematical Formulation

The CP-SAT model in RAILGORITHM 2.0 formulates railway dispatching as a Constraint Programming Scheduling problem over a time-space network.

### Decision Variables
- **Arrival Time ($A_{i,s}$)**: Integer variable $\in [0, T_{max}]$ for train $i$ arriving at station $s$.
- **Departure Time ($D_{i,s}$)**: Integer variable $\in [0, T_{max}]$ for train $i$ departing station $s$.
- **Block Interval ($I_{i,b}$)**: Fixed or flexible interval variable spanning $[entry_{i,b}, exit_{i,b})$ with duration $run\_time(i, b)$.
- **Station Platform Interval ($P_{i,s}$)**: Interval variable $[A_{i,s}, D_{i,s})$ with duration $dwell(i, s) + hold(i, s)$.
- **Station Throat Crossing Interval ($T_{i,s}$)**: Short interval $[D_{i,s} - 1, D_{i,s} + 1)$ representing transit across the interlocking throat.

### Hard Constraints Modeled
1. **Block Exclusivity:** `model.AddNoOverlap(intervals_on_block)` for every single-line block or single track.
2. **Headway Precedence:** For consecutive train intervals $I_1, I_2$ on block $b$:
   $$start(I_2) \ge end(I_1) + headway(b)$$
3. **Running Time & Speed Limits:** Duration of interval $I_{i,b} \ge run\_time_{nominal}(b) \times speed\_factor(i)$.
4. **Platform Capacity:** `model.AddCumulative(station_intervals, [1]*N, available_platforms)`.
5. **Junction Throat Capacity:** `model.AddCumulative(throat_intervals, [1]*N, throat_capacity)`.
6. **Block Closure Intervals:** Fixed synthetic intervals added to block interval collections during maintenance possessions.

---

## 2. Multi-Profile Objective Functions

RAILGORITHM 2.0 supports explicit, configurable objective profiles. Hard constraints are never relaxed or mixed into soft penalty terms.

$$\min Z = w_{\text{delay}} \sum_i \text{delay}_i + w_{\text{max}} \max_i \text{delay}_i + w_{\text{hold}} \sum_i \text{hold}_i + w_{\text{dwell}} \sum_i \Delta \text{dwell}_i$$

### Profile Configurations

| Profile | Total Delay Weight ($w_{\text{delay}}$) | Max Delay Weight ($w_{\text{max}}$) | Hold Weight ($w_{\text{hold}}$) | Throughput Weight | Focus |
|---|---:|---:|---:|---:|---|
| **Balanced** (Default) | 1 | 2 | 3 | 0 | Harmonious compromise across delay and holds |
| **Delay-Focused** | 5 | 1 | 2 | 0 | Aggressive minimization of total schedule delay |
| **Priority-Focused** | 1 (scaled by priority) | 4 | 2 | 0 | Strict protection of Express passenger trains |
| **Throughput-Focused** | 1 | 1 | 1 | -5 | Maximizing completed section exits |

---

## 3. Benchmarking Matrix Across All 14 Scenarios

Tested with 2 seeds (`5000, 5001`) under the deterministic single-worker configuration.

| Scenario | Mode | Solver Status | Is Optimal? | Objective Value | Objective Bound | Solve Time (s) | Schedule Valid? |
|---|---|---|---|---:|---:|---:|---|
| `block_closure` | Single | **OPTIMAL** | Yes | 148.0 | 148.0 | 0.082 | Validated |
| `cascading_delay` | Single | **OPTIMAL** | Yes | 148.0 | 148.0 | 0.016 | Validated |
| `delayed_express` | Single | **OPTIMAL** | Yes | 96.0 | 96.0 | 0.015 | Validated |
| `disruption_recovery` | Double | **OPTIMAL** | Yes | 196.0 | 196.0 | 0.027 | Validated |
| `double_line_overtaking`| Double | **OPTIMAL** | Yes | 148.0 | 148.0 | 0.016 | Validated |
| `evening_peak` | Mixed | **OPTIMAL** | Yes | 338.0 | 338.0 | 0.018 | Validated |
| `junction_congestion` | Junction | **OPTIMAL** | Yes | 170.0 | 170.0 | 0.024 | Validated |
| `maintenance_window` | Possess. | **OPTIMAL** | Yes | 196.0 | 196.0 | 0.021 | Validated |
| `no_feasible_schedule` | Over-con.| **INFEASIBLE**| No | None | None | 0.009 | Infeasible |
| `normal_traffic` | Normal | **OPTIMAL** | Yes | 100.0 | 100.0 | 0.015 | Validated |
| `platform_outage` | Outage | **OPTIMAL** | Yes | 120.0 | 120.0 | 0.019 | Validated |
| `priority_train` | Priority | **OPTIMAL** | Yes | 96.0 | 96.0 | 0.018 | Validated |
| `single_line_meet` | Meet | **OPTIMAL** | Yes | 48.0 | 48.0 | 0.014 | Validated |
| `time_varying_demand` | Peak | **OPTIMAL** | Yes | 196.0 | 196.0 | 0.022 | Validated |

### Summary Statistics
- **Total Solves:** 28 (14 scenarios $\times$ 2 seeds)
- **OPTIMAL Outcomes:** 26 / 28 (92.86%)
- **INFEASIBLE Outcomes:** 2 / 28 (7.14%) — solely in `no_feasible_schedule`
- **FEASIBLE (Suboptimal):** 0 / 28
- **UNKNOWN / Timeouts:** 0 / 28
- **Mean Solve Time:** **0.025 seconds** (25.1 ms)
- **Peak Solve Time:** **0.082 seconds** (`block_closure`)

---

## 4. Honest Status and Bound Reporting

In compliance with RAILGORITHM 2.0 requirements:
- The optimizer **never claims optimality when only a feasible solution is found**.
- Both `objective_value` (achieved solution cost) and `objective_bound` (best theoretical lower bound) are explicitly returned.
- In every OPTIMAL run, `objective_value == objective_bound` within floating-point tolerance ($10^{-6}$).
- For `no_feasible_schedule`, CP-SAT proves infeasibility in **9 ms**, and the system honestly refuses to fabricate a schedule, returning `status: "INFEASIBLE"` and `recommended: null`.
