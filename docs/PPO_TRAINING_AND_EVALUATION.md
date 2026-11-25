# RAILGORITHM 2.0 — PPO Training and Evaluation Report

**Model Version:** `ppo-candidate-ranker-2.0.0` (Candidate) vs `ppo-candidate-ranker-1.0.0` (Baseline)  
**Status:** Evaluated and Preserved  
**Artifact Locations:**
- Baseline Checkpoint: `backend/ml/artifacts/ppo_policy.pt`
- Baseline Metrics: `backend/ml/artifacts/ppo_metrics.json`
- Candidate Checkpoint: `backend/ml/artifacts/v2_candidate/ppo_policy.pt`
- Candidate Comparison: `backend/ml/reports/v2_ppo_candidate_comparison.json`

---

## 1. Role of PPO in RAILGORITHM

In RAILGORITHM, Reinforcement Learning via Proximal Policy Optimization (PPO) is strictly constrained:
1. **PPO does not create arbitrary actions** from continuous or open combinatorial spaces.
2. **PPO cannot override the Independent Validator**. Ineligible candidates failing hard constraints are filtered out prior to PPO ranking (`violation_attempts = 0`).
3. **PPO acts as a contextual candidate ranker**: given $K$ pre-validated candidates (holds, precedence rules, platform reassignments, and CP-SAT schedules), PPO scores each candidate based on global simulation state features and candidate-specific attributes.
4. **Disagreements are preserved**: when PPO's top choice differs from CP-SAT, the system flags `MODEL_DISAGREEMENT` and presents both options with their measured trade-offs.

---

## 2. Neural Architecture and State-Action Representation

### Observation Space
The policy network processes a two-component observation tuple:
- **Global Feature Vector ($\mathbb{R}^{10}$)**:
  1. `sim_time_fraction`: Current time within the 24-hour cycle.
  2. `active_trains_scaled`: Number of trains currently active in the section.
  3. `total_projected_delay_scaled`: Sum of unmitigated delays across all trains.
  4. `max_projected_delay_scaled`: Maximum single train delay.
  5. `conflict_count_scaled`: Total number of active and projected conflicts.
  6. `primary_severity_scaled`: Highest conflict severity in horizon (CRITICAL=1.0, HIGH=0.75, MEDIUM=0.5, LOW=0.25).
  7. `block_occupancy_fraction`: Ratio of occupied blocks to total blocks.
  8. `platform_occupancy_fraction`: Ratio of occupied platform tracks.
  9. `completion_fraction`: Ratio of trains that have completed their journey.
  10. `horizon_fraction`: Proportion of planning horizon elapsed.

- **Candidate Feature Matrix ($\mathbb{R}^{K \times 28}$)**:
  - One-hot action encodings (hold, precedence, platform reassign, schedule, do nothing).
  - Target train kinematics and priority (express, freight, delay, speed factor, remaining legs).
  - Conflict interaction indicators (single-line crossing, headway, platform capacity, junction, closure, delay risk).
  - Source indicators (heuristic, baseline, CP-SAT schedule).

### Policy Architecture
- **Global Encoder**: 2-layer MLP ($10 \to 64 \to 32$, ReLU).
- **Candidate Encoder**: 2-layer MLP ($28 \to 64 \to 32$, ReLU).
- **Interaction Layer**: Concatenates global representation ($32$) with each candidate embedding ($32$), yielding $64$-dim candidate representations.
- **Actor Head**: Linear layer ($64 \to 1$) producing candidate selection logits $\pi(a_k \mid s)$.
- **Critic Head**: Linear layer pooled across candidates producing scalar state-value estimate $V(s)$.

---

## 3. Training Protocol and Data Leakage Prevention

To guarantee rigorous evaluation without benchmark contamination:
- **Disjoint Scenario Partitioning**:
  - **Training Scenarios (7 v1 Families):** `normal_traffic`, `evening_peak`, `single_line_meet`, `delayed_express`, `block_closure`, `platform_outage`, `priority_train`.
  - **Held-Out Evaluation Scenarios (6 v2 Families):** `double_line_overtaking`, `junction_congestion`, `maintenance_window`, `cascading_delay`, `disruption_recovery`, `time_varying_demand`.
  - `leakage_check.train_and_eval_disjoint: true`: Held-out scenarios are never seen during training, reward shaping, or hyperparameter tuning.
- **Random Seeds**:
  - Training seeds: `1000 + iteration*100 + episode`
  - Evaluation seeds: `[5000, 5001, 5002, 5003]` (multi-seed evaluation).
- **Reward Function**:
  $$R(s, a) = \frac{\Delta \text{Weighted Delay} + \lambda \Delta \text{Residual Conflicts}}{\sigma} - c_{\text{step}}$$
  Normalized against the "do nothing" baseline, penalizing residual critical conflicts.

---

## 4. Empirical Evaluation Results

### Multi-Seed Held-Out Evaluation (89 Decisions, 4 Seeds)

The candidate policy (`ppo-candidate-ranker-2.0.0`) was evaluated head-to-head against the baseline checkpoint (`ppo-candidate-ranker-1.0.0`) across identical held-out states.

| Metric | Baseline V1 Reference | Candidate V2 | Delta / Outcome |
|---|---:|---:|---|
| **Top-1 Match with Best Measured** | **25.84%** | **61.80%** | **+35.96% improvement** |
| **Mean Regret vs Best** | **16.202** | **15.258** | **-0.944 lower regret** |
| **Median Regret vs Best** | 6.000 | **0.000** | Strict median optimality |
| **Baseline Heuristic Regret** | 22.775 | 16.966 | Lower baseline regret |
| **CP-SAT Subset Regret** | 18.632 | 15.571 | Closely tracks CP-SAT |
| **Mean Residual Conflicts** | 10.08 | **1.39** | **86.2% conflict reduction** |
| **Mean Policy Reward** | -0.0095 | **+0.1634** | Positive policy utility |
| **Mean Eligible Candidates** | 8.10 | 8.18 | Comparable candidate sets |
| **Mean Inference Time** | 0.0522 ms | **0.0586 ms** | < 0.06 ms (ultra-fast) |
| **95th Percentile Inference Time** | 0.0715 ms | **0.0663 ms** | Predictable sub-millisecond |
| **Constraint Violation Attempts** | **0** | **0** | Zero violations (100% safe filter) |
| **Ineligible Candidates Filtered** | 8 | 8 | Pre-validation gate active |

### Breakdown by Held-Out Scenario Family

| Scenario | Decisions | Baseline Top-1% | Candidate Top-1% | Delta |
|---|---:|---:|---:|---:|
| `double_line_overtaking` | 16 | 31.25% | **93.75%** | +62.50% |
| `maintenance_window` | 16 | 0.00% | **100.00%** | +100.00% |
| `disruption_recovery` | 9 | 11.11% | **88.89%** | +77.78% |
| `cascading_delay` | 16 | 75.00% | 50.00% | -25.00% |
| `junction_congestion` | 16 | 31.25% | 18.75% | -12.50% |
| `time_varying_demand` | 16 | 0.00% | **31.25%** | +31.25% |

---

## 5. Checkpoint Protection and Promotion Status

In adherence to mission requirements:
- **Baseline Protection:** The verified baseline checkpoint `backend/ml/artifacts/ppo_policy.pt` has **not been overwritten**.
- **Candidate Storage:** The candidate model is versioned in `backend/ml/artifacts/v2_candidate/`.
- **Promotion Invariant:** The candidate demonstrated measurable improvement (Top-1 match increased from 25.8% to 61.8%, mean regret decreased from 16.20 to 15.26, residual conflicts decreased from 10.08 to 1.39). Both artifacts are preserved for full provenance.
