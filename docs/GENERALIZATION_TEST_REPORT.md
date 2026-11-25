# RAILGORITHM 2.1 — Unseen Scenario Generalization Report

**Document ID:** `RAIL-DOC-21-GEN-TEST`  
**Version:** 2.1.0  
**Date:** 2026-11-25  
**Status:** Validated  
**Scope:** Synthetic railway simulation and decision-support only. Zero live infrastructure control.

---

## 1. Generalization Test Objectives & Protocol

A fundamental requirement for trustworthy AI in railway dispatching is demonstrating **graceful degradation** and **generalization** to operational conditions outside the training distribution.

To evaluate this, three completely new scenario families were designed. These scenarios were **never included in the Version 1.0 training set** (`TRAIN_SCENARIOS`) and **never used in the Version 2.0 held-out evaluation** (`HELD_OUT_SCENARIOS`):
1. **`gen_freight_convoy_surge` (Unfamiliar Traffic Pattern & Speed Heterogeneity):**
   - Four slow, heavy freight trains (speed factor 1.25, low priority 5) and two premium intercity expresses (speed factor 0.85, high priority 1) converging on single-line sections.
   - Tests priority inversion, prolonged block occupancy, and loop siding overtaking.
2. **`gen_cascading_junction_gridlock` (Peak Traffic Density & Severe Resource Shortage):**
   - Seven trains converging on Malgaon Junction (MLG) within a 20-minute window during an active platform outage on Platform 1.
   - Platform capacity at the network's busiest junction is reduced by 50% while traffic density is at its maximum, stressing diamond crossing throats and platform queues.
3. **`gen_emergency_single_line_cross` (Unplanned Disruption & Reversed Crossing Sequence):**
   - An unplanned emergency overhead equipment inspection closes single-line block B2 from minute 368 to 386.
   - A 15-minute departure delay disruption is simultaneously injected into an opposing train, invalidating standard timetable crossing points and requiring non-standard holding sequences.

---

## 2. Multi-Seed Generalization Results

Evaluated across 4 independent random seeds (`[7001, 7002, 7003, 7004]`), yielding **24 total complex dispatch decisions**:

| Metric | Candidate V2 PPO | Baseline V1 PPO | Deterministic Baseline | Performance Delta (Cand vs Base) |
| :--- | :--- | :--- | :--- | :--- |
| **Top-1 Match %** | **41.67%** | 0.00% | — | **+41.67%** (Baseline failed to find best) |
| **Mean Regret vs Best** | **24.500** | 45.500 | 44.292 | **-21.000 (-46.2% regret)** |
| **Median Regret** | **15.000** | 16.000 | 22.000 | **-1.000** |
| **Regret Std Dev** | 28.776 | 46.401 | — | -38.0% variance reduction |
| **Mean Residual Conflicts** | **1.04** | 10.83 | — | **-9.79 (-90.4% conflict reduction)** |
| **Constraint Violations** | **0** | **0** | **0** | **100% hard constraint filter** |
| **Mean Inference Latency** | **0.0518 ms** | 0.0620 ms | < 0.01 ms | Sub-millisecond response |

---

## 3. Scenario-by-Scenario Breakdown

```
====================================================================================================
Scenario                           Candidate Top-1   Baseline Top-1   Candidate Regret   Baseline Regret   Cand Residual   Base Residual
====================================================================================================
gen_freight_convoy_surge               100.00%            0.00%             0.000            61.000            1.00            11.75
gen_cascading_junction_gridlock         25.00%            0.00%            40.750            60.500            2.12            18.25
gen_emergency_single_line_cross          0.00%            0.00%            32.750            15.000            0.00             2.50
====================================================================================================
```

### Key Behavioral Insights

#### 1. `gen_freight_convoy_surge` (Flawless Handling of Speed Heterogeneity)
- Candidate V2 achieved **100% Top-1 accuracy** and **0.000 regret** across all seeds.
- Baseline V1 suffered a severe failure mode: it repeatedly dispatched slow freight into single-line blocks immediately ahead of approaching express services, resulting in **11.75 residual conflicts** and **61.0 points of regret**.
- Candidate V2 correctly selected siding hold candidates at Nandpur and Suryapur, allowing express trains to overtake freight on double-line sections and clearing single-line blocks before slow freight entered.

#### 2. `gen_cascading_junction_gridlock` (Graceful Degradation Under Bottleneck Collapse)
- In the face of 7 trains and a 50% platform capacity reduction at Malgaon (MLG), Candidate V2 achieved a **25% Top-1 match** and reduced mean regret from **100.125** (Deterministic Baseline) down to **40.750**.
- Crucially, Candidate V2 prevented total junction gridlock: mean residual conflicts remained at **2.12**, compared to **18.25** under Baseline V1 (an **88.4% conflict reduction**).
- No simulated deadlocks or buffer overflows occurred.

#### 3. `gen_emergency_single_line_cross` (Conflict Elimination vs Delay Regret)
- Under emergency track closure, Candidate V2 prioritized safety and conflict elimination over greedy timetable adherence: it reduced residual conflicts to **0.00** (zero remaining conflicts), compared to **2.50** under Baseline V1.
- Because Candidate V2 elected to hold trains outside the closure zone for several extra minutes to guarantee conflict-free clearance, its delay regret was higher (32.75 vs 15.00). In a safety-critical railway system, eliminating active track conflicts is the correct operational behavior.

---

## 4. Verification of Graceful Degradation Criteria

1. **Zero Hard Constraint Violations:**
   - In 100% of decisions across all unseen scenarios, both models evaluated only actions that satisfied all hard constraints (HC-001 through HC-007). The hard-constraint filter never permitted an invalid candidate to be ranked.
2. **No Deadlock or State Corruption:**
   - Every simulation stepped smoothly through active disruptions and recovered to running/completed status without exception.
   - `validate_state_integrity` returned 0 structural defects across all stepped states.
3. **Sub-Millisecond Inference Maintained:**
   - Mean policy forward pass latency on novel inputs was **0.0518 ms**, proving that inference time does not degrade when evaluating unfamiliar network states.
