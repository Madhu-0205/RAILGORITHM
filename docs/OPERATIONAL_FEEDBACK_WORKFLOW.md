# Operational Feedback & Decision Review Workflow (v2.8)

**Document ID:** WORKFLOW-V28-OF  
**Status:** Approved  
**Version:** 2.8.0  
**Scope:** Human-in-the-Loop Feedback & Controller Decision Lifecycle  

---

## 1. Operational Feedback Workflow

RAILGORITHM strictly adheres to the principle:
$$\text{AI RECOMMENDS} \longrightarrow \text{INDEPENDENT VALIDATOR CHECKS} \longrightarrow \text{HUMAN CONTROLLER DECIDES} \longrightarrow \text{SYSTEM RECORDS}$$

No recommendation can execute autonomously. The controller decision lifecycle in v2.8 operates through five formal stages:

```
┌─────────────────────────┐
│ 1. AI Recommendation    │ ───► Generated with 10-point reasoning & predictive timeline
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 2. Controller Review    │ ───► Evaluates situation, urgency window & knock-on impacts
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 3. Human Decision       │ ───► APPROVE / MODIFY / REJECT / DEFER / REQUEST_ALTERNATIVES
└───────────┬─────────────┘       (Captures feedback category & structured operational tag)
            │
            ▼
┌─────────────────────────┐
│ 4. Outcome Measurement  │ ───► Compares predicted vs actual delay & conflict resolution
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ 5. Offline ML Review    │ ───► Evaluates drift, acceptance patterns & model accuracy
└─────────────────────────┘
```

---

## 2. Decision Review Analytics

The Section Controller console (`/recommendations`) surfaces real-time decision review metrics via `GET /api/v1/recommendations/review/analytics`:
- **Acceptance Rate (%):** Percentage of generated recommendations approved without modification.
- **Modification Patterns:** Average hold adjustment in minutes (e.g., AI suggests 10 min, controller modifies to 8 min).
- **Mean Delay Error (min):** Difference between AI predicted total delay and actual delay measured after 30 minutes.
- **Resolution Success Rate (%):** Percentage of accepted recommendations that completely resolved the predicted conflict.

---

## 3. Dataset Export for Offline ML Evaluation

To support ongoing model refinement without risky real-time continuous learning, `GET /api/v1/recommendations/review/dataset` exports structured JSON records containing:
- `decision_id` & `simulation_id`
- Controller role and user ID
- Action taken (`APPROVE`, `MODIFY`, `REJECT`, etc.)
- Feedback category and structured rationale tag
- Predicted delay vs actual delay
- Resolution success indicator
- Optimizer version and PPO model version
