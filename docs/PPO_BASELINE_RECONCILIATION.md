# RAILGORITHM 2.1 — PPO Baseline Reconciliation Report

**Document ID:** `RAIL-DOC-21-PPO-RECON`  
**Version:** 2.1.0  
**Date:** 2026-11-25  
**Status:** Validated  
**Scope:** Synthetic railway simulation and decision-support only. Zero live infrastructure control.

---

## 1. Executive Summary & Root Cause Analysis

A central objective of the RAILGORITHM 2.1 verification mission was investigating the discrepancy between historical baseline numbers reported in Version 1.0 and Version 2.0 evaluation artifacts:

| Report Source | Partition Evaluated | Top-1 Match % | Mean Regret vs Measured Best | Baseline Regret |
| :--- | :--- | :--- | :--- | :--- |
| **Historical Version 1.0 Report** (`v1`) | 7 Training Scenarios (*In-Distribution*) | **55.88%** | **19.510** | 21.420 |
| **Version 2.0 Baseline Benchmark** (`v2`) | 6 Held-Out Scenarios (*Out-of-Distribution*) | **25.84%** | **16.202** | 22.775 |
| **Version 2.0 Candidate Benchmark** (`v2`) | 6 Held-Out Scenarios (*Out-of-Distribution*) | **61.80%** | **15.258** | 22.775 |

### The Root Cause
A thorough code and artifact investigation into `backend/ml/train_ppo.py`, `backend/ml/artifacts/ppo_metrics.json`, and `backend/ml/reports/` revealed the exact cause of this numerical divergence:

1. **Scenario Partition Mismatch:**
   - The **Version 1.0 historical evaluation** was conducted exclusively on the **7 training scenario families** (`normal_traffic`, `evening_peak`, `single_line_meet`, `delayed_express`, `block_closure`, `platform_outage`, `priority_train`). This represented an **in-distribution evaluation** on scenarios that the policy network had already seen during its training loop.
   - The **Version 2.0 baseline benchmark** evaluated the Version 1.0 baseline checkpoint against the **6 newly introduced held-out scenarios** (`double_line_overtaking`, `junction_congestion`, `maintenance_window`, `cascading_delay`, `disruption_recovery`, `time_varying_demand`). This was an **out-of-distribution generalization test**.
   - Comparing the historical 55.88% (in-distribution) against 61.80% (out-of-distribution) as if they were measured on identical test sets is scientifically invalid.

2. **Simulation Evaluation Bugfix in Candidate Ranking:**
   - In Version 1.0, candidate evaluation in `evaluate_candidate` did not strictly simulate post-conflict propagation over the full lookahead horizon when calculating residual conflict penalties.
   - In Version 2.0, candidate evaluation was hardened to detect multi-stage cascading conflicts, and hard constraint validation was enforced strictly before candidate scoring.
   - When the Version 1.0 baseline model is evaluated on the 7 in-distribution training scenarios under the hardened Version 2.0 evaluation pipeline, its Top-1 match is **24.47%** and its mean regret is **21.298**.

---

## 2. Controlled Re-Evaluation Under Identical Conditions

To establish true, scientifically valid comparisons, both the original Version 1.0 baseline checkpoint (`backend/ml/artifacts/ppo_policy.pt`) and the Version 2.0 candidate checkpoint (`backend/ml/artifacts/v2_candidate/ppo_policy.pt`) were re-evaluated across identical evaluation states, identical seeds, identical action spaces, and identical candidate scoring functions.

### A. In-Distribution Evaluation (7 Training Scenario Families)
*Seeds:* `[5000, 5001]` — 94 total decisions evaluated:

| Metric | Baseline V1 Model | Candidate V2 Model | Absolute Delta | Relative Change |
| :--- | :--- | :--- | :--- | :--- |
| **Top-1 Match %** | 24.47% | **73.40%** | +48.93% | **+200.0%** |
| **Mean Regret vs Best** | 21.298 | **8.138** | -13.160 | **-61.8%** |
| **Median Regret** | 8.000 | **0.000** | -8.000 | -100.0% |
| **Mean Residual Conflicts** | 8.42 | **0.86** | -7.56 | **-89.8%** |
| **Constraint Violations** | 0 | 0 | 0 | 100% Valid |

### B. Out-of-Distribution Evaluation (6 Held-Out Scenario Families)
*Seeds:* 8 independent seeds (`[5000, 5001, 5002, 5003, 6000, 6001, 6002, 6003]`) — 178 total decisions evaluated:

| Metric | Baseline V1 Model | Candidate V2 Model | Absolute Delta | Relative Change |
| :--- | :--- | :--- | :--- | :--- |
| **Top-1 Match %** | 25.84% | **61.80%** | +35.96% | **+139.2%** |
| **Mean Regret vs Best** | 16.202 | **15.258** | -0.944 | **-5.8%** |
| **Median Regret** | 6.000 | **0.000** | -6.000 | -100.0% |
| **Mean Residual Conflicts** | 10.08 | **1.39** | -8.69 | **-86.2%** |
| **Deterministic Baseline Regret** | 22.775 | 22.775 | — | — |
| **CP-SAT Candidate Mean Regret** | 18.632 | 18.632 | — | — |
| **Constraint Violations** | 0 | 0 | 0 | 100% Valid |

---

## 3. Discrepancy Breakdown Table

| Evaluation Setting | V1 Baseline Model | V2 Candidate Model | Why the Comparison Differs |
| :--- | :--- | :--- | :--- |
| **Historical V1 Report** (In-dist, v1 env) | Top-1: 55.88%<br>Regret: 19.510 | N/A (Not yet created) | Evaluated on training scenarios with unhardened candidate simulation. |
| **Re-evaluated V1 vs V2** (In-dist, v2 env) | Top-1: 24.47%<br>Regret: 21.298 | Top-1: 73.40%<br>Regret: 8.138 | Identical in-distribution states; candidate exhibits marked superiority. |
| **Reported V2 Benchmark** (Held-out, v2 env) | Top-1: 25.84%<br>Regret: 16.202 | Top-1: 61.80%<br>Regret: 15.258 | Identical held-out states; candidate exhibits strong Top-1 and conflict reduction. |

---

## 4. Key Takeaways for RAILGORITHM 2.1

1. **Direct comparison between Historical V1 (55.88%) and Candidate V2 (61.80%) is scientifically invalid** because they were evaluated on entirely different sets of scenarios.
2. **On identical held-out scenarios**, Candidate V2 achieves **61.80% Top-1 match** versus Baseline V1's **25.84%**, representing a true, statistically significant 35.96% gain ($\chi^2 = 46.74, p < 10^{-11}$).
3. **Residual conflict reduction is the most significant operational improvement**: Candidate V2 reduces residual conflicts by **86.2%** (from 10.08 down to 1.39) on held-out scenarios, and by **89.8%** on in-distribution scenarios.
4. **Hard-constraint filtering is 100% effective**: In both models across all evaluation states, zero constraint violations occurred because candidates are filtered by the independent domain validator prior to policy ranking.
