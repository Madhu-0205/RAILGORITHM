# RAILGORITHM 2.1 — CP-SAT Objective & Constraint Audit

**Document ID:** `RAIL-DOC-21-CPSAT-AUDIT`  
**Version:** 2.1.0  
**Date:** 2026-11-25  
**Status:** Validated  
**Scope:** Synthetic railway simulation and decision-support only. Zero live infrastructure control.

---

## 1. Mathematical Formulation & Decision Variables

The RAILGORITHM CP-SAT optimizer models railway dispatching and rescheduling as a Constraint Integer Programming (CIP) problem over discrete integer minutes using Google OR-Tools CP-SAT (`ortools.sat.python.cp_model`).

### Explicit Decision Variables
For each train $t \in T$ and scheduled segment/block $b \in B_t$:
- $\text{arr}_{t,b} \in [\text{sched\_arr}_{t,b}, \text{sched\_arr}_{t,b} + \text{max\_delay}]$: Integer minute train $t$ enters block $b$.
- $\text{dep}_{t,b} \in [\text{sched\_dep}_{t,b}, \text{sched\_dep}_{t,b} + \text{max\_delay}]$: Integer minute train $t$ exits block $b$.
- $\text{interval}_{t,b} = \text{NewIntervalVar}(\text{arr}_{t,b}, \text{run}_{t,b}, \text{dep}_{t,b})$: Optional/fixed interval variable for resource reservation.
- $\text{hold}_{t,s} \in [0, \text{max\_hold}_t]$: Explicit hold minutes applied at station $s$.
- $\text{prec}_{t_1, t_2, b} \in \{0, 1\}$: Precedence boolean indicating whether train $t_1$ traverses block $b$ before train $t_2$.

---

## 2. Strict Separation: Hard Constraints vs. Soft Objectives

A core architectural principle of RAILGORITHM is that **hard constraints are never relaxed or mixed into soft penalty terms**. If a constraint cannot be satisfied, the solver strictly returns `INFEASIBLE` rather than presenting an unsafe schedule with a penalty.

### Hard Constraints (Enforced in MIP Formulation & Independently Re-Checked)
1. **HC-001 (Exclusive Resource Occupancy):**
   - Single-line blocks enforce mutual exclusion between opposing and following movements:
     $$\forall t_1 \neq t_2 \text{ sharing block } b, \quad \text{dep}_{t_1, b} \le \text{arr}_{t_2, b} \quad \lor \quad \text{dep}_{t_2, b} \le \text{arr}_{t_1, b}$$
   - Modeled via `model.AddNoOverlap([interval_{t_1, b}, interval_{t_2, b}, \dots])`.
2. **HC-002 (Minimum Safety Headway):**
   - Same-direction movements across common boundaries require at least $H = 3$ minutes headway:
     $$\text{arr}_{t_2, b} \ge \text{arr}_{t_1, b} + H_{\text{track}}$$
     $$\text{dep}_{t_2, b} \ge \text{dep}_{t_1, b} + H_{\text{station}}$$
3. **HC-003 (Platform Capacity):**
   - At station $s$, total concurrent train dwell intervals cannot exceed physical platform count $C_s$:
     $$\sum_{t \in T} \mathbb{I}(\text{at station } s \text{ at time } \tau) \le C_s - \text{active\_outages}(s, \tau) \quad \forall \tau$$
   - Modeled via cumulative interval constraints: `model.AddCumulative(station_intervals, demands, capacity)`.
4. **HC-004 (Maintenance & Block Closure Exclusion):**
   - For any active planned closure or emergency disruption on block $b$ during $[\tau_{\text{start}}, \tau_{\text{end}}]$:
     $$\text{dep}_{t, b} \le \tau_{\text{start}} \quad \lor \quad \text{arr}_{t, b} \ge \tau_{\text{end}} \quad \forall t$$
5. **HC-005 (Maximum Hold Limits):**
   - Train holding at stations cannot exceed operational crew/comfort limits:
     $$\text{hold}_{t, s} \le \text{max\_hold}_t \quad (\text{Express: } 20\text{ min, Freight: } 45\text{ min, Passenger: } 30\text{ min})$$
6. **HC-006 (Junction Throat Capacity):**
   - Concurrent diamond crossings and switch transits through station throats (e.g. Malgaon MLG) cannot exceed throat limits:
     $$\sum_{t \in T} \mathbb{I}(\text{transiting throat } j \text{ at time } \tau) \le \text{throat\_capacity}_j$$
7. **HC-007 (Dwell & Traversal Physics):**
   - Traversal times must respect minimum physical run times and station dwell times:
     $$\text{dep}_{t, b} - \text{arr}_{t, b} \ge \text{min\_run}_{t, b}$$
     $$\text{dep}_{t, s} - \text{arr}_{t, s} \ge \text{dwell}_{t, s} + \text{hold}_{t, s}$$

---

## 3. Configurable Objective Profiles

The CP-SAT model supports four discrete objective profiles. Soft objectives are mapped to a linear integer minimization function:

$$\min \quad W_{\text{delay}} \sum_t \text{delay}_t + W_{\text{max}} \max_t \text{delay}_t + W_{\text{prio}} \sum_t P_t \cdot \text{delay}_t + W_{\text{dev}} \sum_t |\text{sched\_dev}_t| - W_{\text{thru}} \cdot N_{\text{completed}}$$

| Objective Profile | $W_{\text{delay}}$ (Total Delay) | $W_{\text{max}}$ (Max Delay) | $W_{\text{dev}}$ (Deviation) | $W_{\text{thru}}$ (Throughput) | $W_{\text{prio}}$ (Priority) | $W_{\text{util}}$ (Utilization) | Primary Operational Use Case |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **`balanced`** (Default) | 4 | 3 | 2 | 10 | 6 | 1 | Normal operations balancing punctuality and throughput. |
| **`delay_focused`** | 10 | 6 | 4 | 2 | 2 | 0 | Severe disruption recovery to minimize passenger delay-minutes. |
| **`priority_focused`** | 3 | 3 | 2 | 4 | 12 | 0 | Peak hours with high-priority premium express trains. |
| **`throughput_focused`** | 2 | 1 | 1 | 14 | 3 | 3 | Bottleneck clearance and heavy freight corridor flow. |

---

## 4. Explanation of the 26 Feasible Benchmark Solves

In the benchmark report `backend/ml/reports/v2_cpsat.json`, exactly **26 feasible solves** are recorded. The origin and exact scenario coverage of these 26 solves is documented below:

- **Scenario Catalogue Size:** 14 synthetic scenarios total:
  - 13 Feasible scenarios (`normal_traffic`, `evening_peak`, `single_line_meet`, `delayed_express`, `block_closure`, `platform_outage`, `priority_train`, `double_line_overtaking`, `junction_congestion`, `maintenance_window`, `cascading_delay`, `disruption_recovery`, `time_varying_demand`).
  - 1 Intentionally Infeasible scenario (`infeasible_capacity_overload`).
- **Benchmark Execution Matrix:**
  - Evaluated across 2 random seeds (`5000, 5001`) under the default `balanced` profile:
  - $13 \text{ feasible scenarios} \times 2 \text{ seeds} = \mathbf{26} \text{ feasible solves}$.
  - $1 \text{ infeasible scenario} \times 2 \text{ seeds} = \mathbf{2} \text{ infeasible solves}$.
  - Total solve records in `v2_cpsat.json` $= 26 + 2 = \mathbf{28} \text{ solves}$.
- **Optimality Breakdown:**
  - 24 of the 26 feasible solves achieved proved mathematical **`OPTIMAL`** status within the 8.0-second time limit.
  - 2 solves reached **`FEASIBLE`** status (valid, conflict-free solutions found with non-zero optimality gap at time-out).
  - The solver accurately reports `is_optimal: false` whenever a time-out occurs with a feasible solution.

---

## 5. Adversarial Stress Testing Results

To verify robustness against solver failure modes and ensure that the optimizer and validator remain resilient under extreme conditions, 8 dedicated adversarial tests were executed (`backend/tests/test_cpsat_adversarial.py`):

1. **Timeout Handling (`test_adversarial_timeout_handling`):**
   - High-density scenario evaluated under a tiny 0.05-second time limit.
   - Result: Solver terminates cleanly returning status `FEASIBLE` (or `UNKNOWN` if no initial heuristic solution is found) with explicit solve time and bound, without raising uncaught exceptions.
2. **Infeasible Schedule Rejection (`test_adversarial_infeasible_schedule_rejection`):**
   - Impossible constraint injected (forcing a train to travel faster than the laws of physics or arrive before departing).
   - Result: Solver strictly returns `INFEASIBLE` with `schedule: None`.
3. **All 4 Objective Profiles (`test_adversarial_all_objective_profiles`):**
   - Each profile (`balanced`, `delay_focused`, `priority_focused`, `throughput_focused`) solved on `evening_peak`.
   - Result: All 4 profiles return valid schedules that pass independent validation.
4. **Tampered Headway Rejection (`test_adversarial_validator_rejects_tampered_headway`):**
   - An adversary tampers with the optimizer output schedule to compress headway from 3 min to 1 min.
   - Result: Independent validator intercepts and rejects the schedule (`FAIL` on HC-002 check `block_headway`).
5. **Tampered Platform Overflow (`test_adversarial_validator_rejects_tampered_platform_overflow`):**
   - An adversary schedules 3 concurrent trains onto a 2-platform station.
   - Result: Independent validator intercepts and rejects the schedule (`FAIL` on HC-003 `platform_capacity`).
6. **Closure Encroachment Rejection (`test_adversarial_validator_rejects_closure_encroachment`):**
   - An adversary routes a train through a block during an active maintenance window.
   - Result: Independent validator intercepts and rejects the schedule (`FAIL` on HC-004 `block_closure`).
7. **Junction Throat Overflow Rejection (`test_adversarial_validator_rejects_throat_overflow`):**
   - An adversary schedules 3 concurrent trains into a single-capacity junction throat at Malgaon (MLG).
   - Result: Independent validator intercepts and rejects the schedule (`FAIL` on HC-006 `junction_throat_capacity`).
8. **Multi-Conflict Surge Stress (`test_adversarial_multi_conflict_surge`):**
   - 8 trains simultaneously contending for blocks and platforms.
   - Result: CP-SAT resolves the multi-conflict burst cleanly in < 1.5 seconds with zero residual hard-constraint violations.

---

## 6. Independent Validator Rigor

The RAILGORITHM independent validator (`app/domain/validator.py`) does **not** rely on CP-SAT variables or solver internal assertions. Instead, it reconstructs physical time-space trajectories from scratch:
- Builds explicit occupancy intervals $[t_{\text{entry}}, t_{\text{exit}}]$ for every train and block.
- Evaluates pairwise intervals across all trains sharing track resources.
- Verifies station platform slot allocation second-by-second.
- Any discrepancy between optimizer claims and physical constraints results in immediate rejection of the schedule.
