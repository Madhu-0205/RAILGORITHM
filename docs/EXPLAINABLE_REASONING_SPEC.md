# Explainable Recommendation Reasoning Specification (v2.8)

**Document ID:** SPEC-V28-ERR  
**Status:** Approved  
**Version:** 2.8.0  
**Scope:** Transparent Decision-Support & Structured Evidence Generation  

---

## 1. Principles of Railway Operational Explainability

Human operating personnel (Section Controllers and Station Masters) cannot safely accept black-box recommendations. If an AI system suggests holding an express train or altering precedence without clear, domain-accurate justification, the controller will rightly reject it.

RAILGORITHM v2.8 establishes the **10-Point Structured Operational Reasoning Standard** (`backend/app/domain/explanation.py`). Every generated recommendation includes a deterministic 10-point reasoning record compiled entirely from verified solver artifacts, constraint validator evaluations, and cloned simulation outcomes.

**Non-Negotiable Rule:** Explanations must NEVER fabricate facts, hallucinate unmodelled railway regulations, or claim certainty where none exists.

---

## 2. The 10-Point Structured Operational Reasoning Standard

| # | Element Key | Description & Operational Content |
|---|:---|:---|
| 1 | `1_operational_situation` | Current traffic state in Indian Railways operational terminology. Describes active train positions, block occupations, scheduled vs actual run times, and general sectional health. |
| 2 | `2_primary_problem` | The specific conflict or capacity bottleneck triggering intervention (e.g., single-line crossing at block BLK-3, platform berth shortage at junction station). |
| 3 | `3_recommended_action` | Explicit, executable advisory action with parameters (action type: `HOLD`, `PRECEDENCE`, `PLATFORM_REASSIGN`; train ID; station; exact hold duration in minutes). |
| 4 | `4_operational_reasoning` | Step-by-step logic explaining why this action was selected among all validated candidates. Explains weighted delay trade-offs and priority protection. |
| 5 | `5_railway_constraints_considered` | Exhaustive checklist of formal hard and soft constraints evaluated (`HC-001` through `HC-007`), detailing verification status for each. |
| 6 | `6_alternative_options_evaluated` | Minimum of 2 generated alternatives with explicit operational rejection reasons (e.g., rejected due to critical conflict residual, or not chosen due to higher delay penalty). |
| 7 | `7_expected_consequences` | Quantified outcome if action is approved: total delay change (min), average delay change, punctuality %, throughput (trains/hour), and conflict reduction. |
| 8 | `8_consequences_of_no_action` | Quantified outcome if controller continues without intervention: baseline delay accumulation, cascading knock-on effects, and residual critical conflicts. |
| 9 | `9_verified_evidence` | Traceability audit trail: simulation state version, timestamp, CP-SAT solver status (`OPTIMAL`/`FEASIBLE`), PPO model version, and validator check pass count. |
| 10 | `10_residual_uncertainty` | Frank statement of analysis boundaries: synthetic data boundary, uncalibrated confidence warning, unmodelled rolling stock breakdowns, or model disagreement. |

---

## 3. Mathematical Basis of Reasoning Synthesis

The operational reasoning does not rely on Large Language Model (LLM) text completion. It is deterministically synthesized from pipeline variables:

### Weighted Delay Score
$$\text{Score}(a) = \sum_{t \in \text{Trains}} w_t \cdot \text{Delay}_t(a) + \sum_{c \in \text{Conflicts}(a)} P_{\text{severity}}(c)$$

Where:
- $w_t = \max(1, 6 - \text{Priority}_t)$ (Priority 1 receives weight 5; Priority 5 receives weight 1).
- $P_{\text{CRITICAL}} = 100$, $P_{\text{HIGH}} = 5$, $P_{\text{MEDIUM}} = 2$, $P_{\text{LOW}} = 1$.

### Candidate Selection Rule
$$a^* = \arg\min_{a \in \mathcal{C}_{\text{eligible}}} \text{Score}(a)$$

Where $\mathcal{C}_{\text{eligible}} = \{a \in \mathcal{C} \mid \text{Validator}(a) = \text{PASS} \land \text{CriticalConflicts}(a) = 0\}$.

---

## 4. Constraint Checklist Traceability

Every recommendation records verification across all core constraints:
- **HC-001 (Block Exclusivity):** Only one train may occupy a physical block at any given time.
- **HC-002 (Headway Separation):** Following trains must maintain configured block spacing.
- **HC-003 (Single-Line Crossing):** Opposing movements on single-line sections must meet only at stations with loop capacity.
- **HC-005 (Platform Capacity):** Simultaneous berthing at a station must not exceed platform count.
- **HC-007 (Block & Platform Closures):** No movement permitted through active maintenance blocks or outage berths.
