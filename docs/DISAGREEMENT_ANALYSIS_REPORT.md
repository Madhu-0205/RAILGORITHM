# RAILGORITHM 2.1 — Recommendation Disagreement Analysis Report

**Document ID:** `RAIL-DOC-21-DISAGREE`  
**Version:** 2.1.0  
**Date:** 2026-11-25  
**Status:** Validated  
**Scope:** Synthetic railway simulation and decision-support only. Zero live infrastructure control.

---

## 1. Architectural Philosophy: Preserving Disagreement

In railway traffic management, different optimization paradigms optimize for fundamentally different objectives:
- **CP-SAT (Global Constraint Programming):** Solves a global Mixed-Integer Scheduling formulation over the entire 75-minute planning horizon, finding mathematically optimal schedule shifts across all trains simultaneously.
- **PPO (Tactical Candidate Ranker):** Evaluates discrete tactical intervention candidates (holds, precedence overrides, platform reassignments) to resolve acute local bottlenecks while minimizing immediate disturbance to the wider network.

When CP-SAT and PPO recommend different operational interventions, **RAILGORITHM strictly preserves the disagreement rather than silently resolving it**. 

### The Six Mandatory Safety Rules
1. **Both model outputs remain completely visible** in the API payload and the frontend UI.
2. **The exact technical reason for disagreement is recorded** in `disagreement_detail` and the explanatory narrative.
3. **Only independently validated, hard-constraint feasible candidates** can ever be recommended or approved.
4. **The human dispatcher sees the quantitative trade-offs** (delays, throughput, residual conflicts) between both alternatives side-by-side.
5. **The system never automatically resolves disagreement** or executes an action autonomously.
6. **The human decision, selected option, and written rationale are immutably audited** in the append-only hash chain.

---

## 2. Review of `MODEL_DISAGREEMENT` Scenarios

Across the Version 2.0 benchmark runs and Version 2.1 held-out evaluations, 11 distinct recommendation states produced `MODEL_DISAGREEMENT` (`evidence_status: "MODEL_DISAGREEMENT"`). 

### Representative Case Studies

#### Case Study 1: `junction_congestion` (Malgaon Junction Throat Contention)
- **Situation:** Four trains (two expresses, one passenger, one freight) converge on Malgaon (MLG) where single-line sections merge with double-line sections.
- **CP-SAT Output:** Proposes a global `SCHEDULE` action with a 6-minute hold on Express 12625 at Nandpur, shifting its path so Freight FRT-701 clears the junction throat without stopping.
  - *Trade-off:* Minimizes total system delay (total delay: 18 min), but penalizes a premium passenger express.
- **PPO Output:** Ranks a localized `HOLD` candidate holding Freight FRT-701 at Karanpur (KRN) for 12 minutes.
  - *Trade-off:* Preserves Express 12625 punctuality (Express delay: 0 min), but incurs 12 minutes of freight delay (total system delay: 24 min).
- **System Behavior:**
  - Status set to `MODEL_DISAGREEMENT`.
  - Both candidates displayed with full quantitative trade-offs.
  - PPO policy probability (0.642) displayed as a sampling score with explicit disclaimer.
  - Human Section Master decides which commercial trade-off to approve.

#### Case Study 2: `cascading_delay` (Propagating Single-Line Meet)
- **Situation:** A 15-minute initial delay on an inbound passenger train causes overlapping block requests on the single-line section between Suryapur (SRP) and Vasanthpur (VSN).
- **CP-SAT Output:** Proposes full schedule reallocation that advances the outbound train and delays two following services.
- **PPO Output:** Selects a single `PRECEDENCE` override at Suryapur loop.
- **System Behavior:**
  - Both options pass independent constraint validation (HC-001 through HC-007).
  - Both alternatives made available for selection in the human decision interface.

---

## 3. Decision Support Interface & UI Visibility

The frontend application (`RecommendationDetail.tsx`) features a dedicated **"Model Disagreement" Panel** that renders whenever `data.disagreement === true`:

```tsx
<Panel title="Model disagreement" subtitle="Shown explicitly; never auto-resolved.">
  <dl className="grid-2">
    <div>
      <dt>Recommended (measured score)</dt>
      <dd>{labelFor(data, data.disagreement_detail.recommended_candidate_id)}</dd>
    </div>
    <div>
      <dt>PPO candidate</dt>
      <dd>{labelFor(data, data.disagreement_detail.ppo_top_candidate_id)}</dd>
    </div>
    <div>
      <dt>CP-SAT candidate</dt>
      <dd>{labelFor(data, data.disagreement_detail.cpsat_candidate_id)}</dd>
    </div>
    <div>
      <dt>Reason</dt>
      <dd>
        {data.disagreement_detail.ppo_vs_cpsat_disagreement
          ? "PPO and CP-SAT preferred different candidates. Review both before deciding."
          : "Heuristic and optimizer candidates differ."}
      </dd>
    </div>
  </dl>
  <p className="muted small">{data.disagreement_detail.selection_rule}</p>
</Panel>
```

### Banner & Badge Presentation
- Visual `badge badge-watch`: **`MODELS DISAGREE`**.
- Tone switched to `warning` to immediately alert the Section Master that the automated models have reached diverging conclusions.

---

## 4. Prohibition of Uncalibrated Confidence Percentages

A critical safety principle enforced in RAILGORITHM 2.1 is the **strict elimination of uncalibrated confidence percentages**:
- The API explicitly returns `uncertainty.confidence_percentage: null`.
- Policy logits represent softmax sampling weights over the candidate action space; they do **not** represent empirical probability of real-world operational success.
- Presenting a dispatcher with a label like "94% Confident" when the underlying policy is uncalibrated creates dangerous automation bias.
- Instead, RAILGORITHM provides **deterministic physical metrics**:
  - Predicted total delay minutes.
  - Count of remaining residual conflicts.
  - Section and platform utilization percentages.
  - Exact constraint checks passed and failed.

---

## 5. Human Decision Workflow & Immutable Auditing

When a human controller acts on a recommendation in a disagreement state:
1. **Explicit Confirmation Required:** The request payload must include `confirm_apply: true`.
2. **Mandatory Written Rationale:** The controller must submit a rationale of at least 5 characters (e.g., `"Approving PPO hold on freight to preserve express timetable during peak hour"`).
3. **RBAC Scope Check:** Station Masters can only approve decisions strictly confined to their station boundaries; Section Masters are required for multi-station and network-level actions.
4. **Append-Only Audit Recording:** The submission writes to the `decisions` table and appends a `DECISION_APPLIED` event to the cryptographic audit chain:
   ```json
   {
     "event_type": "DECISION_APPLIED",
     "actor": "section.master",
     "actor_role": "SECTION_MASTER",
     "recommendation_id": "REC-7701",
     "payload": {
       "action": "APPROVE",
       "selected_candidate": "CAND-02",
       "rationale": "Prioritize passenger express over freight in accordance with peak policy",
       "disagreement_present": true,
       "ppo_candidate": "CAND-02",
       "cpsat_candidate": "CAND-01"
     }
   }
   ```
5. **Non-Repudiation:** Once written, database triggers prevent any modification or deletion of the human decision record.
