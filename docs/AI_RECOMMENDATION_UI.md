# RAILGORITHM v2.9 — AI RECOMMENDATION WORKSPACE & DECISION CONSOLE

## 1. User Interface Design Philosophy

Railway control offices operate under high cognitive load. Controllers manage multiple telephone coordination lines, track diagrams, signal alerts, and timetable schedules concurrently. Visual clutter, dense paragraphs of text, or ambiguous indicators degrade operational efficiency.

**RAILGORITHM v2.9** redesigns the recommendation workspace (`Recommendations.tsx` and `RecommendationDetail.tsx`) around **Progressive Disclosure**, **Clear Provenance Indicators**, and **Role-Appropriate Jurisdiction Filtering**.

---

## 2. Key Interface Enhancements

### 2.1 Recommendation Queue & Priority Cards
- **Urgency Badges**:
  - `IMMEDIATE (<5m)`: Red pill indicator requiring urgent decision to prevent signal stop.
  - `NEAR-TERM (5–15m)`: Amber pill for upcoming crossing or loop overtake regulation.
  - `PLANNED (>15m)`: Green pill for proactive sectional spacing.
  - `MONITORING`: Slate badge for stable traffic with zero active contention.
- **Data Quality Gate Advisory Banner**:
  - Automatically displays when any telemetry feed is `DEGRADED`, `STALE`, or `OFFLINE`, warning controllers that recommendations may be gated or withheld.
- **Evidence Provenance Badges**:
  - Distinct badges for `VALIDATED`, `VALIDATED_WITH_ASSUMPTIONS`, `MODEL_DISAGREEMENT`, and `STALE`.

### 2.2 11-Part Structured Evidence Accordions
In the detail view, operational reasoning is presented in collapsible accordions (**Sections A through K**):
- Factual items display source pills (`OBSERVED`, `CALCULATED`, `PREDICTED`, `HEURISTIC`).
- Hard Safety Constraint results (HC-001 through HC-006) show distinct `PASS` / `FAIL` status tags.
- Trade-offs are split into clean two-column summaries: **Gained Benefits** (green) vs **Incurred Holds** (red).
- Validity window clearly indicates remaining time-to-live (15-min TTL) and pinned simulation state version.

### 2.3 Multi-Alternative Regulation Comparison Matrix
A dedicated comparison table allows Section Controllers to evaluate the **Recommended Action**, the **Best Feasible Alternative**, and the **No-Action Baseline** across seven operational dimensions:
1. Target Train & Action Type
2. Projected Corridor Delay (min)
3. Residual Critical Conflicts
4. Sectional On-Time Performance %
5. Secondary Downstream Disruptions
6. Regulatory Safety Gate Status
7. Track & Siding Physical Feasibility

### 2.4 Delay Propagation Graph Visualization
- Shows developing delays table with current delay, projected range, primary driver, and actionability status.
- Displays cascade propagation chains detailing initiating train, chain length, total accumulated delay, and downstream impacted trains.

### 2.5 3-Way Outcome Evaluation Table
Once a decision is recorded and evaluated:
- Displays side-by-side comparison: **AI Recommended Action** vs **Human Selected Action** vs **Observed Ground-Truth Outcome**.
- Highlights whether human modification achieved superior, equivalent, or degraded punctuality relative to the AI baseline.
