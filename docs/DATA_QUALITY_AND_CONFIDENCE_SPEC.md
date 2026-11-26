# Data Quality and Calibrated Confidence Specification (v2.8)

**Document ID:** SPEC-V28-DQC  
**Status:** Approved  
**Version:** 2.8.0  
**Scope:** Data Provenance, Quality Gatekeeping & Honest Confidence Disclosure  

---

## 1. First Principle: Data Quality Before Confidence

In safety-critical railway traffic management, uncalibrated confidence percentages (e.g., "87% confident") are dangerous. If the underlying signalling feed is stale or train speed reports are contradictory, presenting an AI recommendation with high confidence misleads operating personnel.

RAILGORITHM v2.8 implements the **Data Quality & Calibrated Confidence Architecture** (`backend/app/domain/data_quality.py`).

---

## 2. Data Quality Taxonomy

Every telemetry input and simulation variable is tagged with an explicit quality state:

| Quality State | Definition & Operational Provenance |
|:---|:---|
| `VERIFIED_SOURCE_DATA` | Direct, cryptographically signed or hardware-validated telemetry from signalling relays, track circuits, or GPS. |
| `OBSERVED` | Direct telemetry observation without redundant cross-checking. |
| `CALCULATED` | Derived deterministically from observed data (e.g., speed calculated from block entry/exit). |
| `PREDICTED` | Output of forward trajectory projection or statistical model. |
| `SIMULATION` | Generated within the synthetic simulation testbed. |
| `HEURISTIC` | Derived from operational rules of thumb or default timetable buffers. |
| `UNKNOWN` | Data provenance cannot be established. |
| `STALE` | Data was valid but exceeds freshness time-to-live (TTL). |
| `CONFLICTING` | Multiple independent sources report contradictory readings (e.g., train reported on two blocks simultaneously). |
| `NO_DATA` | Required telemetry is completely missing. |

---

## 3. Recommendation Eligibility Gates

Before generating any operational recommendation, the pipeline executes `evaluate_data_quality`:

```
Input Telemetry Checked
       │
       ├─► Any Critical Telemetry NO_DATA or CONFLICTING? ──► HALT: Return NO_VALID_RECOMMENDATION
       │
       ├─► Any Critical Telemetry STALE? ───────────────────► WARN: Flag STALE_INPUT (Manual verification required)
       │
       └─► All Quality Gates Passed ────────────────────────► PROCEED: Generate Validated Recommendations
```

### Gate Failure Behavior
- If train location telemetry is contradictory or missing: The pipeline halts and returns `evidence_status = "INCOMPLETE_DATA"` (with `quality_state = "NO_DATA"` or `"CONFLICTING"`). It will never fabricate an action on corrupt input.

---

## 4. Calibrated Confidence Policy

RAILGORITHM enforces a strict non-deceptive confidence policy:
1. **Uncalibrated Policy:** When confidence has not been empirically calibrated against observed historical outcomes, the system explicitly displays:
   `Confidence: Not calibrated`
2. **Safety Disclosure:** Accompanied by:
   *"RAILGORITHM does not display uncalibrated confidence percentages. Recommendations are evaluated based on categorical evidence status, formal constraint satisfaction, and cloned simulation outcomes."*
3. **Calibrated Models:** A percentage is only displayed if mathematical calibration metrics (Expected Calibration Error $< 0.05$ and verified Brier Score) are documented and verified.
