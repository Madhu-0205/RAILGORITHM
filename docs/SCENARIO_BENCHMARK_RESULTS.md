# RAILGORITHM 2.0 — Scenario Benchmark Results

**Document Version:** 2.0.0  
**Date:** 25 November 2026  
**Scope:** 14 Deterministic Synthetic Scenarios  
**Evaluation Protocol:** Multi-seed evaluation, deterministic warm-up, end-to-end pipeline measurement.

---

## 1. Scenario Catalogue

RAILGORITHM 2.0 expands the scenario suite from 8 to 14 benchmark scenarios, covering high-density operations, multiple disruptions, overtaking, cascading delays, and junction contention.

| Scenario Key | Name | Trains | Disruptions | Tags | Description |
|---|---|---:|---:|---|---|
| `normal_traffic` | Normal Traffic | 4 | 0 | `normal`, `baseline` | Regular timetable with balanced bidirectional traffic. |
| `evening_peak` | Evening Peak Traffic | 7 | 0 | `peak`, `high_density` | High-frequency commuter and express services. |
| `single_line_meet` | Single Line Meet | 2 | 0 | `crossing`, `bottleneck` | Two opposing trains approaching single-line section S3. |
| `delayed_express` | Delayed Express Train | 3 | 0 | `delay`, `precedence` | Late-running Express competing with local passenger train. |
| `block_closure` | Block Closure | 3 | 1 | `closure`, `disruption` | Planned maintenance closure on single-line block B3. |
| `platform_outage` | Platform Outage | 3 | 1 | `outage`, `station` | Platform 2 out of service at junction station MLG. |
| `priority_train` | Freight vs Express | 3 | 0 | `priority`, `precedence` | High-priority Express approaching freight on same path. |
| `no_feasible_schedule` | No Feasible Schedule | 3 | 1 | `infeasible`, `adversarial` | Over-constrained closures making scheduling impossible. |
| `double_line_overtaking` | Double Line Overtaking | 4 | 0 | `overtaking`, `double_line` | Fast Express behind slow Freight on double-line S2. |
| `junction_congestion` | Junction Throat Congestion | 5 | 0 | `junction`, `throat` | Multiple trains converging simultaneously on MLG throat. |
| `maintenance_window` | Engineering Possession | 4 | 1 | `maintenance`, `possession`| Daytime 4-hour track renewal window on S3. |
| `cascading_delay` | Cascading Delay Propagation | 4 | 0 | `cascade`, `knock_on` | Upstream freight delay causing secondary passenger holds. |
| `disruption_recovery` | Multi-Disruption Recovery | 5 | 2 | `disruption`, `recovery` | Concurrent block closure and platform outage. |
| `time_varying_demand` | Time-Varying Traffic Surge | 5 | 0 | `surge`, `dynamic` | Mixed suburban and intercity traffic surge over 90 min. |

---

## 2. End-to-End Pipeline Performance Across Scenarios

Measurements reflect end-to-end execution: conflict detection $\to$ candidate generation $\to$ CP-SAT solve $\to$ independent cloned outcome validation $\to$ PPO ranking $\to$ explanation synthesis.

| Scenario | Sim Time | Evidence Status | CP-SAT Status | Pipeline (ms) | Candidates (Eligible / Total) | Recommended Source | Decision Applied |
|---|---:|---|---|---:|---:|---|---|
| `block_closure` | 06:05 | `VALIDATED` | `OPTIMAL` | 82.4 ms | 1 / 8 | `CP_SAT` | Applied (HTTP 200) |
| `cascading_delay` | 06:05 | `MODEL_DISAGREEMENT` | `OPTIMAL` | 18.2 ms | 8 / 8 | `HEURISTIC` | Applied (HTTP 200) |
| `delayed_express` | 06:05 | `MODEL_DISAGREEMENT` | `OPTIMAL` | 16.5 ms | 7 / 7 | `CP_SAT` | Applied (HTTP 200) |
| `disruption_recovery` | 06:05 | `VALIDATED` | `OPTIMAL` | 27.8 ms | 1 / 11 | `CP_SAT` | Applied (HTTP 200) |
| `double_line_overtaking`| 06:05 | `MODEL_DISAGREEMENT` | `OPTIMAL` | 17.1 ms | 11 / 11 | `CP_SAT` | Applied (HTTP 200) |
| `evening_peak` | 06:05 | `MODEL_DISAGREEMENT` | `OPTIMAL` | 21.4 ms | 12 / 12 | `CP_SAT` | Applied (HTTP 200) |
| `junction_congestion` | 06:05 | `MODEL_DISAGREEMENT` | `OPTIMAL` | 24.3 ms | 11 / 11 | `CP_SAT` | Applied (HTTP 200) |
| `maintenance_window` | 06:05 | `MODEL_DISAGREEMENT` | `OPTIMAL` | 22.0 ms | 11 / 11 | `CP_SAT` | Applied (HTTP 200) |
| `no_feasible_schedule` | 06:05 | `NO_FEASIBLE_SOLUTION` | `INFEASIBLE` | 9.8 ms | 0 / 7 | `NONE` | Refused (HTTP 409) |
| `normal_traffic` | 06:05 | `MODEL_DISAGREEMENT` | `OPTIMAL` | 16.0 ms | 12 / 12 | `HEURISTIC` | Applied (HTTP 200) |
| `platform_outage` | 06:05 | `MODEL_DISAGREEMENT` | `OPTIMAL` | 19.5 ms | 8 / 8 | `CP_SAT` | Applied (HTTP 200) |
| `priority_train` | 06:05 | `MODEL_DISAGREEMENT` | `OPTIMAL` | 17.8 ms | 7 / 7 | `CP_SAT` | Applied (HTTP 200) |
| `single_line_meet` | 06:05 | `MODEL_DISAGREEMENT` | `OPTIMAL` | 14.2 ms | 4 / 4 | `BASELINE` | Applied (HTTP 200) |
| `time_varying_demand` | 06:05 | `MODEL_DISAGREEMENT` | `OPTIMAL` | 23.6 ms | 11 / 11 | `CP_SAT` | Applied (HTTP 200) |

---

## 3. Key Observations and Validation Findings

1. **Safety Gate Effectiveness:**
   - In `block_closure` and `disruption_recovery`, 7 of 8 and 10 of 11 candidate actions were flagged as **ineligible** by the independent validator because they left unresolved critical closure conflicts. Only the validated CP-SAT schedule satisfied the spatial and temporal boundaries.
2. **Honest Infeasibility Handling:**
   - In `no_feasible_schedule`, CP-SAT proved infeasibility in **9.8 ms**. The pipeline generated `evidence_status: NO_FEASIBLE_SOLUTION`, with `recommended: null`. The human decision gate rejected approval attempts with HTTP 409 Conflict, declaring *"The system will not fabricate an executable action."*
3. **Model Disagreement Transparency:**
   - In 11 of 14 scenarios, PPO top-ranked candidate and CP-SAT candidate differed. The pipeline flagged `MODEL_DISAGREEMENT`, presented both candidates with measured comparative metrics, and selected the action minimizing measured weighted delay and residual conflicts.
