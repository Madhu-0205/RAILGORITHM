# RAILGORITHM v2.9 — AI DATA QUALITY & RECOMMENDATION ELIGIBILITY POLICY

## 1. Safety Directive: Garbage In, Silence Out

In railway operational management, bad data is significantly more dangerous than no data. Generating automated train regulation recommendations based on stale track circuits, disconnected locomotive telemetry, or contradictory train locations can lead to fatal dispatcher errors, signal violations, or network gridlock.

**RAILGORITHM v2.9** implements an uncompromising **Data Quality Eligibility Gate**:
> If telemetry inputs fail integrity, freshness, or consistency checks, the AI recommendation pipeline **refuses to issue recommendations** and returns an explicit, auditable refusal code.

---

## 2. Operational Quality State Taxonomy

Every input source is evaluated across a standardized quality taxonomy:

| Quality State | Criteria & Triggers | Recommendation Pipeline Eligibility |
| :--- | :--- | :--- |
| **`HEALTHY`** | All telemetry feeds fresh ($\le \text{TTL}$), train positions validated, topology complete. | **FULL ADVISORY ELIGIBLE** |
| **`SIMULATION`** | Internal synthetic testbed data; consistent and fresh. | **FULL ADVISORY ELIGIBLE** |
| **`DEGRADED`** | Non-critical feeds delayed or minor headway sensor jitter; safety limits intact. | **LIMITED ADVISORY** (Expanded Headways) |
| **`STALE`** | Telemetry exceeds source-specific freshness TTL. | **WITHHELD** (`STALE_DATA_WITHHELD`) |
| **`OFFLINE`** | Signalling or interlocking telemetry feed disconnected. | **BLOCKED** (`TELEMETRY_OFFLINE_GATED`) |
| **`CONTRADICTORY`** | Incompatible coordinates (e.g. running train without assigned block). | **BLOCKED** (`CONTRADICTORY_DATA_REFUSED`) |
| **`INCOMPLETE`** | Missing infrastructure topology, station geometry, or zero train positions. | **BLOCKED** (`INCOMPLETE_DATA`) |
| **`UNKNOWN`** | Telemetry provenance unverified. | **BLOCKED** (`UNKNOWN_DATA_PROVENANCE`) |

---

## 3. Configured Source-Specific Freshness TTLs

To prevent stale data from lingering in the decision engine, RAILGORITHM enforces strict Time-To-Live (TTL) thresholds by subsystem:

| Subsystem / Telemetry Stream | Freshness TTL | Rationale |
| :--- | :--- | :--- |
| **Signalling & Interlocking Feed** | **15 seconds** | Signals and point positions change rapidly during route setting. |
| **Track Circuit & Axle Counter Occupancy** | **10 seconds** | Physical track occupancy must be real-time for block clearance. |
| **GPS Locomotive Feed** | **30 seconds** | Speed and location coordinates for moving consists. |
| **Caution Orders & Temporary Speed Restrictions** | **30 minutes (1800s)** | Static speed boards and daily safety notices. |
| **Working Timetable (WTT)** | **24 hours (86400s)** | Published operational schedule baseline. |

---

## 4. Zero-Fabrication Confidence Policy

The railway operating industry is inundated with software asserting arbitrary confidence percentages (e.g., *"93.4% confident this hold is optimal"*). In safety-critical railway traffic management, uncalibrated statistical percentages are meaningless and hazardous.

### 4.1 Strict Policy Mandates
1. **No Fabricated Numerical Percentages**: Unless a formal empirical calibration pipeline (e.g. temperature scaling or isotonic regression on real historical data) is commissioned and verified, RAILGORITHM displays `display_percentage = null`.
2. **Categorical Disclosure**: The system reports `confidence_label = "Confidence: Not calibrated"`.
3. **Transparent Uncertainty Intervals**: Explicitly reports bounded mathematical uncertainty intervals ($\pm 4.0\text{ min}$) representing simulation variance.
4. **Independent Human Decision**: The Section Controller is explicitly notified that the system is an advisory tool; human authorization is mandatory before any simulation update.
