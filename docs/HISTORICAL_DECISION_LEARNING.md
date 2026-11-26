# RAILGORITHM v2.9 — HISTORICAL DECISION & OUTCOME LEARNING

## 1. Background & Learning Objectives

Human-in-the-loop decision support systems require a continuous learning and evaluation loop. Operating staff develop operational instincts and local domain knowledge (e.g., local gradient difficulties, weather effects on adhesion, crew duty limits) that mathematical simulators may only approximate.

**RAILGORITHM v2.9** implements a complete **Historical Decision Capture, 3-Way Outcome Comparison, and Offline Model Governance Framework** (`backend/app/services/decision_service.py`).

---

## 2. Decision-Time Data Quality Capture

Whenever a Section Controller or Station Master records a decision (`APPROVE`, `MODIFY`, `REJECT`, `DEFER`, or `REQUEST_ALTERNATIVES`), the system captures a permanent, immutable snapshot of the operational data quality:

- `data_quality_at_decision`: Exact telemetry state (`HEALTHY`, `DEGRADED`, `STALE`, etc.) when the controller made the choice.
- `state_version`: The exact simulation state version pinned to the recommendation.
- `original_recommendation`: The full payload, candidate scores, and optimizer schedules.
- `controller_rationale`: Free-text justification (minimum 5 characters) explaining operational reasoning.
- `structured_rationale_tag`: Categorized reason code (e.g. `SCHEDULE_PRIORITY`, `CREW_DUTY_EXCEEDED`, `PLATFORM_MAINTENANCE`, `PASSENGER_CONNECTION`, `STATION_REQUEST`).

---

## 3. The 3-Way Outcome Evaluation Framework

After an action is applied or the simulation advances, the system performs a three-way comparative evaluation (`evaluate_decision_outcome`):

```
┌────────────────────────────────────────────────────────┐
│            3-WAY OUTCOME COMPARISON MODEL              │
├─────────────────────────┬──────────────────────────────┤
│ 1. AI PREDICTED OUTCOME │ Simulated estimate from AI   │
│ 2. HUMAN CHOSEN ACTION  │ Action selected by controller│
│ 3. OBSERVED OUTCOME     │ Ground-truth result in state │
└─────────────────────────┴──────────────────────────────┘
```

### 3.1 Dimensions of Comparison
1. **Action Concordance**:
   - `MATCHED_RECOMMENDATION`: Controller approved AI recommendation as proposed.
   - `HUMAN_OVERRIDE`: Controller modified parameters (e.g., reduced hold from 10 min to 5 min).
   - `HUMAN_REJECTION`: Controller rejected AI proposal in favor of local operational priority.
   - `DEFERRED`: Decision held pending situation stabilization.
2. **Delay Delta ($\Delta d$)**:
   $$\Delta d = d_{\text{observed}} - d_{\text{ai\_predicted}}$$
   - Quantifies whether reality performed better or worse than the AI simulation forecast.
3. **Conflict Resolution Success**:
   - Compares residual actionable conflicts observed after the horizon against the AI prediction ($\text{Conflicts}_{\text{observed}} \le \text{Conflicts}_{\text{predicted}}$).

---

## 4. Offline Model Governance & Deployment Gates

To prevent unvetted models from impacting live operational simulations, RAILGORITHM enforces strict offline evaluation governance (`evaluate_offline_model_candidates`):

### 4.1 Governance Criteria
Before any candidate model (PPO weights or heuristic solver) is promoted to active staging, it must run against the historical decision dataset and baseline scenarios:

1. **Zero Safety Violations ($V = 0$)**:
   - Candidate model must achieve zero hard constraint violations (HC-001 through HC-006). Any violation triggers immediate rejection.
2. **Policy Alignment Benchmark ($\ge 70.0\%$)**:
   - The candidate model's top-ranked choice must agree with historical human controller decisions on at least $70\%$ of accepted operational situations.
3. **Optimality Gap Threshold ($\le 5.0\%$)**:
   - Must not increase total weighted delay beyond the verified CP-SAT baseline schedule.

### 4.2 Gate Status Outputs
- **`APPROVED_FOR_STAGING`**: Meets all safety and alignment criteria; authorized for staging shadow runs.
- **`REQUIRES_REFINEMENT`**: Low policy alignment ($< 70\%$) or excessive delay degradation.
- **`REJECTED_UNSAFE`**: One or more constraint violations detected.
- **`INSUFFICIENT_DATA`**: Less than required sample size of recorded human decisions.
