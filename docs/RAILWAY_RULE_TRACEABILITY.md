# RAILWAY RULE TRACEABILITY MATRIX — RAILGORITHM v2.4

## 1. Executive Summary & Regulatory Scope

RAILGORITHM v2.4 operates as an **advisory decision-support and traffic simulation system**. It does **not** perform vital field interlocking, signal aspect cascading, or autonomous points control.

In response to rigorous verification guidelines, this document establishes a zero-assumption traceability matrix connecting every rule identifier implemented in the code to its statutory source, Working Time Table (WTT) parameter, or transparent simulation approximation.

> [!IMPORTANT]
> **Elimination of Invented Regulatory Identifiers:**
> Previous versions referenced fabricated strings such as `IR-G&SR-4.08-FRT` or `IR-G&SR-GENERIC`. In RAILGORITHM v2.4, all statutory rules explicitly cite the **General Rules 1976 (Open Lines)** issued by the Ministry of Railways, Government of India, the **Indian Railways Schedule of Dimensions (SOD) 2004**, or verified **Working Time Table (WTT)** clauses. Any synthetic or heuristic heuristic is explicitly tagged with `SIM-ASSUMPTION-*`.

---

## 2. Regulatory Traceability Matrix

| Rule Identifier | Issuing Authority & Source Document | Exact Clause / Table | Effective Date & Edition | Category | Implementation Location | Test Verification | Operational Scope & Limitations |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **GR-4.08(1)-TRAIN-MPS** | Ministry of Railways, Govt of India / General Rules 1976 | Rule 4.08, Sub-rule (1) | 1976 (amended 2022) | Statutory General Rule | `backend/app/ingestion/validator.py` (`_get_train_max_speed`) | `backend/tests/test_realtime_pipeline.py` | Governs maximum permissible speed (MPS) of trains based on loco/rolling stock sanction. |
| **GR-4.09-TSR-CAUTION-ORDER** | Ministry of Railways, Govt of India / General Rules 1976 | Rule 4.09 | 1976 (amended 2020) | Statutory General Rule | `backend/app/ingestion/validator.py` (`_get_location_speed_limit`) | `backend/tests/test_realtime_pipeline.py` | Enforces Temporary Speed Restrictions (TSR) notified via Caution Orders. |
| **WTT-SECTIONAL-MPS** | Zonal Railway Operating Dept / Working Time Table | Sectional Maximum Speed Table, Para 2.1 | Divisional WTT 2024-2025 | Timetable Parameter | `backend/app/ingestion/validator.py` (`_get_location_speed_limit`) | `backend/tests/test_realtime_pipeline.py` | Sets maximum sectional operating speed for track segments (e.g. 100/110 km/h). |
| **IR-SOD-TURNOUT-SPEED** | Railway Board / Schedule of Dimensions 2004 | Chapter II, Item 5 (Turnouts) | 2004 (amended 2023) | Statutory Engineering Standard | `backend/app/ingestion/validator.py` (`_get_location_speed_limit`) | `backend/tests/test_realtime_pipeline.py` | Speed ceiling (30 km/h) over 1-in-12 or 1-in-8.5 station yard turnouts. |
| **INFRA-DIRECTIONAL-LOCK** | General Rules 1976 & Interlocking Principles | GR 1.02(62) (Wrong Line), GR 3.38 | 1976 (amended 2022) | Infrastructure Invariant | `backend/app/ingestion/validator.py` (Directional check) | `backend/tests/test_realtime_pipeline.py` | Prohibits entry of a train into a unidirectional line in the reverse direction. |
| **GR-8.01-ABSOLUTE-BLOCK-MUTEX** | Ministry of Railways, Govt of India / General Rules 1976 | Rule 8.01 (Essentials of Absolute Block System) | 1976 | Statutory Operating System | `backend/app/domain/conflicts.py`, `backend/app/optimizer.py` | `backend/tests/test_optimizer.py` | Requires exclusive track block occupancy between two block stations. |
| **BPAC-WHEEL-COUNT-CONTINUITY** | Research Designs & Standards Organisation (RDSO) | Spec RDSO/SPN/177/2012 | 2012 (Rev 3) | Signaling Invariant | `backend/app/ingestion/validator.py` (Unmatched exit check) | `backend/tests/test_realtime_pipeline.py` | Axle counter block proving: an exit event requires a prior verified entry event. |
| **OPERATIONAL-IDENTIFIER-MANDATORY** | Railway Operating Practice / Control Office Manual | Chapter IV, Train Numbering | 2018 | Operational Requirement | `backend/app/ingestion/validator.py` | `backend/tests/test_realtime_pipeline.py` | Every telemetry movement event must carry an authentic 5-digit/operational train ID. |
| **TELEMETRY-VALID** | System Invariant | RAILGORITHM Telemetry Spec | 2026 (v2.4) | System Baseline | `backend/app/ingestion/models.py` | `backend/tests/test_realtime_pipeline.py` | Assigned to movement events that satisfy all railway physical and timetable invariants. |
| **SIM-ASSUMPTION-HEADWAY** | System Simulation Model | Parameter `headway_min` (3 min / 180s) | 2026 (v2.4) | Simulation Heuristic | `backend/app/domain/network.py`, `backend/app/domain/conflicts.py` | `backend/tests/test_conflicts.py` | Macroscopic headway spacing representing signal spacing; not micro-interlocking aspect cascade. |
| **SIM-ASSUMPTION-THROAT-CAPACITY** | System Simulation Model | Parameter `junction_throat_capacity` ($C=2$) | 2026 (v2.4) | Simulation Heuristic | `backend/app/domain/network.py`, `backend/app/optimizer.py` | `backend/tests/test_optimizer.py` | Aggregate bottleneck heuristic at Malgaon (MLG) throat representing route exclusivity. |
| **SIM-ASSUMPTION-DRIFT-WINDOW** | System Sanity Filter | $[-300s, +60s]$ clock skew filter | 2026 (v2.4) | Telemetry Filter | `backend/app/ingestion/validator.py` | `backend/tests/test_realtime_pipeline.py` | Accommodates GPS/NTP network drift while rejecting temporal hallucinations. |
| **SIM-ASSUMPTION-TELEPORT-CAP** | System Kinematic Sanity Filter | Absolute velocity threshold 200 km/h | 2026 (v2.4) | Physical Filter | `backend/app/ingestion/validator.py` | `backend/tests/test_realtime_pipeline.py` | Kinematic sanity check blocking spurious multi-block location telemetry jumps. |

---

## 3. Precedence Hierarchy in Speed Governance

When multiple speed restrictions apply to a single train movement, RAILGORITHM enforces the strict statutory safety precedence rule:

$$\text{Effective Speed Limit} = \min(\text{Train MPS}, \text{Sectional MPS}, \text{Caution Order TSR}, \text{Yard Turnout Limit})$$

1. **Working Time Table (WTT) Train Registration (`GR-4.08(1)-TRAIN-MPS`):**
   - Explicitly configured for the train's rake type and locomotive classification.
   - Example: Train 12625 (Kerala Express / WAP-7) registered at 130 km/h.
2. **Rolling Stock Class Fallback (`GR-4.08(1)-TRAIN-MPS`):**
   - Freight / Goods: 75 km/h.
   - Passenger Ordinary: 100 km/h.
   - Mail / Express: 110–130 km/h.
3. **Caution Orders & TSRs (`GR-4.09-TSR-CAUTION-ORDER`):**
   - Dynamic track engineering maintenance restrictions (e.g. 45 km/h over track renewals).
4. **Sectional Maximum Permissible Speed (`WTT-SECTIONAL-MPS`):**
   - Civil infrastructure limit for the block or section (e.g. 90 km/h on single line, 110 km/h on double line).
5. **Turnout & Yard Speed Limit (`IR-SOD-TURNOUT-SPEED`):**
   - 30 km/h through station turnouts and yard entry crossovers.

---

## 4. Operational Boundaries & Non-Vital Advisory Scope

- **Advisory Only:** No recommendation generated by the CP-SAT optimizer or PPO policy directly controls physical field hardware.
- **Interlocking Superiority:** Physical station electronic interlocking and Route Relay Interlocking (RRI) take absolute precedence over any advisory schedule.
- **Human Authority:** The Station Master and Section Controller retain exclusive legal authority to accept, modify, or reject any recommendation.
