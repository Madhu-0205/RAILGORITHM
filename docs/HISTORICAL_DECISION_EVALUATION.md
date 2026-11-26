# Historical Decision Evaluation & Outcome Tracking (v2.8)

**Document ID:** SPEC-V28-HDE  
**Status:** Approved  
**Version:** 2.8.0  
**Scope:** Human Controller Feedback, Decision Analytics & Offline Model Learning  

---

## 1. Principles of Operational Decision Feedback

Section Controllers make critical decisions during every shift: approving, modifying, or rejecting AI advisory recommendations. In v2.7 and earlier, these decisions were stored in an immutable audit ledger but never analyzed to measure whether the AI's predictions matched real operational outcomes.

RAILGORITHM v2.8 introduces **Decision Outcome Tracking & Review Analytics** (`backend/app/services/decision_service.py`):
1. Captures structured controller feedback categories and operational rationale tags.
2. Snapshots predicted operational outcomes at decision time.
3. Automatically measures actual operational outcomes as the simulation advances.
4. Computes prediction error distributions (delay error and conflict resolution success).
5. Provides aggregate review analytics and dataset export for offline ML evaluation.

**Strict Safety Principle:** RAILGORITHM NEVER performs online continuous learning or real-time neural network updates. Model feedback is strictly offline, validated, and evaluated on benchmark sets before redeployment.

---

## 2. Decision Feedback Taxonomy

When recording a decision (`POST /api/v1/recommendations/{id}/decision`), the controller specifies:

### Feedback Categories
- `ACCEPTED`: Controller approved the recommended action as proposed.
- `MODIFIED`: Controller adjusted action parameters (e.g., modified hold duration or platform).
- `REJECTED`: Controller rejected the recommendation and opted for alternative regulation.
- `NOT_APPLICABLE`: Operational situation changed before the decision could be executed.
- `SUPERSEDED`: Controller requested fresh alternatives due to emerging network changes.

### Structured Rationale Tags
- `SCHEDULE_PRIORITY`: Standard punctuality protection for premier passenger train.
- `CREW_DUTY_EXCEEDED`: Hours of Employment Regulation (HOER) constraint requires train clearance.
- `PLATFORM_MAINTENANCE`: Unscheduled track or platform obstruction at station.
- `PASSENGER_CONNECTION`: Holding train would break vital passenger connection at junction.
- `STATION_REQUEST`: Station Master requested regulation due to local yard congestion.
- `OTHER`: Exceptional operational circumstances documented in free text.

---

## 3. Predicted vs. Actual Outcome Evaluation

For every applied decision, the system records:

$$\text{PredictedOutcome} = \left\{\text{TotalDelay}_{\text{pred}}, \text{AvgDelay}_{\text{pred}}, \text{Conflicts}_{\text{pred}}\right\}$$

When the simulation clock advances, `evaluate_decision_outcome` records the actual outcome:

$$\text{ActualOutcome} = \left\{\text{TotalDelay}_{\text{actual}}, \text{AvgDelay}_{\text{actual}}, \text{Conflicts}_{\text{actual}}\right\}$$

### Prediction Error Metrics
- **Delay Error (min):** $\text{Error}_{\text{delay}} = \text{TotalDelay}_{\text{actual}} - \text{TotalDelay}_{\text{pred}}$
- **Conflict Error:** $\text{Error}_{\text{conflicts}} = \text{Conflicts}_{\text{actual}} - \text{Conflicts}_{\text{pred}}$
- **Resolution Success:** $\text{Success} = \mathbb{I}\left(\text{Conflicts}_{\text{actual}} \le \text{Conflicts}_{\text{pred}}\right)$

---

## 4. Decision Review Analytics Endpoints

RAILGORITHM exposes specialized review analytics:
- `GET /api/v1/recommendations/review/analytics`:
  Returns total decisions, acceptance rate %, action type breakdown, modification patterns (average hold adjustment in minutes), and mean delay prediction error.
- `GET /api/v1/recommendations/review/dataset`:
  Exports complete structured decision dataset for offline model benchmarking, drift detection, and heuristic recalibration.
