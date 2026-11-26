# RAILGORITHM v2.9 — EXPLAINABLE RECOMMENDATION REASONING & EVIDENCE SCHEMA

## 1. Operating Philosophy

In railway traffic management, a decision recommendation without clear, itemized provenance is unusable by train controllers. Section Controllers bear direct operational responsibility for train safety, passenger punctuality, and route clearing. An AI system that emits opaque confidence scores or cryptic advice will either be ignored or introduce severe operational risk.

**RAILGORITHM v2.9** implements an **11-Part Structured Operational Evidence Schema (Sections A through K)** alongside an explicit **Multi-Alternative Comparison Matrix**. Every claim, metric, and constraint is categorized into strict factual provenance classes.

---

## 2. The 11-Part Structured Evidence Schema

Each generated recommendation provides a complete, traceable operational explanation broken down into eleven standardized sections:

```
┌──────────────────────────────────────────────────────────────┐
│        11-PART OPERATIONAL EVIDENCE SCHEMA (SECTIONS A–K)    │
├────┬─────────────────────────────┬───────────────────────────┤
│ A  │ Current Situation & Posture │ Physical corridor context │
│ B  │ Conflict Detection Trigger  │ Time, location & geometry │
│ C  │ Itemized Evidence Items     │ Class-tagged factual facts│
│ D  │ Constraint Verification     │ Hard & soft check results │
│ E  │ Recommended Action Detail   │ Parameters & target train │
│ F  │ Expected Outcome Forecast   │ Delay, OTP & throughput   │
│ G  │ Alternative Actions Checked │ Validated alternatives    │
│ H  │ No-Action Consequence       │ Baseline impact if ignored│
│ I  │ Operational Trade-Offs      │ Gained vs sacrificed      │
│ J  │ Uncertainty & Limitations   │ Error bounds & caveats    │
│ K  │ Validity Window & Expiry    │ 15-min TTL & state version│
└────┴─────────────────────────────┴───────────────────────────┘
```

### Detailed Section Definitions:

#### Section A: Current Operational Situation & Posture
- **Purpose**: Establishes the real-time operational context of the corridor.
- **Evidence Class**: `OBSERVED`.
- **Fields**: Corridor state (e.g. `MODERATE_PEAK`), operational posture (`NORMAL_WORKING`, `REGULATED_HOLDING`, `DISRUPTED_RECOVERY`), active train counts, and primary stations involved.

#### Section B: Conflict Detection Mechanism & Problem Identification
- **Purpose**: Clarifies why the system alerted operating staff.
- **Evidence Class**: `PREDICTED`.
- **Fields**: Conflict identifier, type (e.g. `SINGLE_LINE_CROSSING`), location (station, block, section), earliest projected contention time, and time-to-act countdown.

#### Section C: Itemized Operational Evidence Table
- **Purpose**: Tabular audit trail of factual data supporting the recommendation.
- **Attributes per Evidence Item**:
  - `fact`: Factual statement describing the situation.
  - `category`: `TRAIN_MOVEMENT`, `SIGNALLING`, `INFRASTRUCTURE`, `PASSENGER_CONNECTION`.
  - `source`: Telemetry feed, WTT schedule, or physical block detection.
  - `evidence_class`: Explicit provenance tag (`OBSERVED`, `CALCULATED`, `PREDICTED`, `HEURISTIC`).

#### Section D: Constraints Checked & Feasibility Verification
- **Purpose**: Evidence that independent constraint validation verified the candidate schedule before advisory presentation.
- **Checks**:
  - **Hard Constraints (HC-001 through HC-006)**: Block exclusivity, minimum headway, single-line crossing exclusivity, absolute stop aspect observance, station platform capacity, and active line closures.
  - **Soft Constraints (SC-001 through SC-003)**: Timetable punctuality, train priority hierarchy, and maximum hold duration limits.

#### Section E: Recommended Operational Action & Parameters
- **Purpose**: Exact dispatch instruction for controller review.
- **Fields**: Action type (`HOLD`, `PLATFORM_REASSIGN`, `SCHEDULE`), target train ID and name, location, duration in minutes, and operational rationale.

#### Section F: Expected Quantitative Outcome
- **Purpose**: Simulated outcome metrics computed in a cloned simulation environment.
- **Metrics**: Total corridor delay (min), weighted delay score, on-time performance %, throughput (trains/hour), and residual critical conflicts after the horizon.

#### Section G: Feasible Alternative Actions Evaluated
- **Purpose**: Demonstrates that the optimizer explored multiple valid choices and did not arbitrarily latch onto a single option.
- **Content**: Summary of alternative crossing sequences, alternative crossing stations (e.g. `MLG`), and why each was ranked lower than the recommended choice.

#### Section H: No-Action Consequence Forecast
- **Purpose**: Answers: *"What happens if the Section Controller does nothing?"*
- **Outcome**: Forecast of compounding queueing, gridlock, and cascade delay resulting from unmanaged train movement.

#### Section I: Operational Trade-Offs (Gained vs. Sacrificed)
- **Purpose**: Explicit transparency on costs and benefits.
- **Gained**: Punctuality protected for high-priority express services; conflict resolved before block entry.
- **Sacrificed**: Detention imposed on lower-priority freight service (+8 min hold at loop siding).

#### Section J: Uncertainty, Data Quality & Model Limitations
- **Purpose**: Caveats ensuring controllers treat the system as advisory decision support.
- **Policy**: Explicitly confirms that no uncalibrated probability or fabricated percentage is displayed; reports dynamic uncertainty bounds ($\pm 4.0\text{ min}$).

#### Section K: Recommendation Validity Window & Expiry
- **Purpose**: Prevents execution of stale recommendations.
- **Parameters**: State version pinning (`v{version}`), 15-minute time-to-live (`valid_until_sim_time`), and list of revalidation triggers (clock advance, new TSR, manual override).

---

## 3. Data Provenance & Evidence Classes

To avoid blurring raw telemetry with mathematical model predictions, every evidence item is tagged with its formal class:

| Evidence Class | Operational Meaning | Reliability Level |
| :--- | :--- | :--- |
| **`OBSERVED`** | Direct sensor observation (track circuit occupancy, locomotive GPS, signal aspect). | Highest |
| **`CALCULATED`** | Deterministically derived from observations (speed from $\Delta x/\Delta t$, delay from scheduled time). | Mathematical Fact |
| **`PREDICTED`** | Forward projection from physical simulation or machine learning models. | Bounded Estimate |
| **`HEURISTIC`** | Domain operational rules of thumb (e.g. standard 5-minute passenger connect window). | Operational Guideline |
| **`UNKNOWN`** | Telemetry source cannot be cryptographically verified or provenance is unrecorded. | Unverified |
| **`STALE`** | Previously valid data that has exceeded its configured time-to-live (TTL). | Impaired |
| **`NO_DATA`** | Expected telemetry feed is offline or sensor record is missing. | Zero Evidence |

---

## 4. Multi-Alternative Comparison Matrix

In addition to sequential explanations, RAILGORITHM v2.9 generates a **7-Row Direct Comparative Matrix** evaluated across identical evaluation horizons (default: 75 min):

| Comparative Operational Attribute | Recommended Action (Option 1A) | Best Feasible Alternative (Option 1B) | No-Action Baseline | Operational Significance |
| :--- | :--- | :--- | :--- | :--- |
| **Target Train & Action** | Hold 12625 (Freight) at NDL (10m) | Hold 22692 (Express) at VSN (10m) | None (Do Nothing) | Regulation intervention point |
| **Projected Corridor Delay** | 15.0 min | 35.0 min | 65.0 min | Overall punctuality impact |
| **Residual Critical Conflicts** | 0 critical conflicts | 0 critical conflicts | 2 critical conflicts | Primary safety & operational conflict resolution |
| **On-Time Performance %** | 92.5% | 78.0% | 55.0% | Sectional punctuality metric |
| **Secondary Disruptions** | 0 downstream trains affected | 2 trailing passenger trains delayed | 4 trains gridlocked | Knock-on cascade containment |
| **Regulatory Safety Gate** | VALIDATED (HC-001 passed) | VALIDATED (HC-001 passed) | CRITICAL CONFLICT | Independent validator clearance |
| **Operational Feasibility** | Loop line capacity available | Platform siding occupied | Infeasible movement | Track and loop physical availability |

---

## 5. Backward Compatibility & Ten Required Questions

For audit and backwards compatibility with earlier RAILGORITHM releases, the system maintains complete support for the legacy ten operational review questions (`1_what_is_happening` through `10_what_if_the_controller_rejects`), ensuring existing automated parsers, audit logs, and frontend components continue to function without interruption.
