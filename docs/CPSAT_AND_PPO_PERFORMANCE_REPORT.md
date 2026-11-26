# CP-SAT and PPO Performance Report (v2.8)

**Document ID:** REPORT-V28-CPPO  
**Date:** 2026-11-25  
**Version:** 2.8.0  
**Test Suite:** `backend/ml/benchmark.py --all --label v2.8`  

---

## 1. Executive Summary

This report documents the empirical benchmark results of Google OR-Tools CP-SAT and the PyTorch PPO candidate ranker under the v2.8 AI Decision Intelligence and Predictive Regulation release.

Evaluation was performed on 14 deterministic synthetic scenarios across random seeds `5000` and `5001`. Generalization and regret metrics were evaluated strictly on 6 held-out scenarios never seen during policy training (`double_line_overtaking`, `junction_congestion`, `maintenance_window`, `cascading_delay`, `disruption_recovery`, `time_varying_demand`).

---

## 2. CP-SAT Solver Performance

- **Total Solves:** 28 solves across 14 scenarios and 2 random seeds.
- **Optimal Solves:** 26 (92.86%).
- **Infeasible Solves:** 2 (7.14%) — scenarios `no_feasible_schedule` intentionally construct unresolvable topological deadlock.
- **Mean Solve Time:** **0.032 seconds**.
- **Max Solve Time:** **0.430 seconds** (under evening peak with 8 trains).
- **Independent Validation Pass Rate:** 100% of generated schedules passed all hard constraints.

### Solve Time Distribution
| Scenario | Trains | Solver Status | Solve Time (s) | Objective Value |
|:---|:---:|:---:|:---:|:---:|
| `normal_traffic` | 4 | OPTIMAL | 0.013 | 14,069.0 |
| `evening_peak` | 8 | OPTIMAL | 0.360 | 87,294.0 |
| `single_line_meet` | 2 | OPTIMAL | 0.002 | 4,536.0 |
| `delayed_express` | 3 | OPTIMAL | 0.008 | 7,812.0 |
| `block_closure` | 3 | OPTIMAL | 0.009 | 8,920.0 |
| `platform_outage` | 4 | OPTIMAL | 0.015 | 16,420.0 |
| `no_feasible_schedule` | 4 | INFEASIBLE | 0.001 | — |
| `double_line_overtaking` | 4 | OPTIMAL | 0.018 | 19,104.0 |
| `cascading_delay` | 6 | OPTIMAL | 0.045 | 42,150.0 |

---

## 3. PPO Candidate Ranker Generalization & Regret

Evaluated across 44 decision steps on disjoint held-out scenarios:
- **Policy Top-1 Match against Measured Best:** **22.73%**.
- **Mean Regret vs. Best Measured Score:** **18.295** (Median: 5.5).
- **Baseline Heuristic Mean Regret:** **26.727**.
- **Mean Policy Total Delay:** 93.64 minutes.
- **Mean Policy Residual Conflicts:** 10.32.
- **Mean Inference Latency:** **0.74 ms** (p95: **0.65 ms**).
- **Constraint Violation Attempts:** **0** (Hard constraints strictly enforced by independent validator).

---

## 4. End-to-End Recommendation Pipeline Latency

- **Total Decisions Evaluated:** 56.
- **Mean Pipeline Latency:** **51.49 ms**.
- **Median Pipeline Latency:** **22.22 ms**.
- **Pipeline Components:**
  - Conflict Detection: ~1.2 ms
  - CP-SAT Optimization: ~32.0 ms
  - Independent Schedule Validation: ~2.5 ms
  - Dynamic Candidate Generation: ~1.8 ms
  - Cloned Simulation Evaluations: ~12.0 ms
  - PPO Inference: ~0.7 ms
  - Explanation & Predictive Timeline Synthesis: ~1.2 ms
