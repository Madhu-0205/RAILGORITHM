# Regulatory Source Verification & Rule Interpretation — RAILGORITHM v2.5

## 1. Executive Summary & Purpose

A decision-support system in railway traffic management must maintain strict, scientifically traceable fidelity to authentic statutory operating rules. Fabricating regulatory rule citations or conflating different rules introduces unacceptable operational ambiguity.

This document records the formal verification of all railway regulatory rules referenced within RAILGORITHM v2.5 against the authentic statutory publications of the **Ministry of Railways (Government of India)**, the **General Rules 1976 (Open Lines)**, the **Indian Railways Schedule of Dimensions (SOD) 2004**, and verified **Working Time Table (WTT)** parameters.

---

## 2. P0 Regulatory Clarification: Correction of GR 3.38 Interpretation

In earlier development iterations, the rule identifier `IR-G&SR-3.38` was loosely cited for directional movement locking on double-line track sections. In RAILGORITHM v2.5, this interpretation has been rigorously audited and corrected.

### 2.1. Statutory Scope of General Rule 3.38
Under the **General Rules 1976 (Open Lines)**, **Rule 3.38** is titled:
> **"Points to be locked / Conditions for taking 'off' signals"**

**Statutory Mandate:** Rule 3.38 governs the mechanical and electrical conditions under which signals may be cleared:
1. Facing points over which the train is to pass must be securely locked and detected.
2. Trailing points in the route and overlap must be correctly set and locked.
3. Relevant isolation points and sand humps must be set to protect the route from conflicting movements.

**Finding:** **GR 3.38 governs point detection and signal interlocks; it does NOT define directional line clear on double lines.**

### 2.2. Governing Rules for Directional Movement Locking
Directional movement control on double-line sections is statutorily governed by:

1. **GR 1.02(62) — "Wrong Line":**
   Defines the line on a double-line or multi-line section on which trains run in the direction opposite to the established direction of traffic. Entry onto the "Wrong Line" without explicit written authority (e.g. Form T/D 602 for Single Line Working on Double Line) is prohibited.
2. **GR 8.01 — "Essentials of the Absolute Block System":**
   Mandates that no train shall be allowed to leave a block station until Line Clear has been received from the block station in advance.
3. **GR 8.03(1) — "Conditions for granting Line Clear on Double Line":**
   Statutorily requires that the line on which it is intended to receive the train is completely clear of all running trains and obstructions up to the adequate distance (overlap) in the designated direction of traffic.
4. **Station Working Rules (SWR):**
   Site-specific Station Working Rules (issued under GR 5.06) enforce electrical directional locking on block instruments (e.g., Daido / Kyosan tokenless block instruments).

**Implementation Update in v2.5:**
The rule identifier in `backend/app/ingestion/validator.py`, `docs/RAILWAY_RULE_TRACEABILITY.md`, and `docs/RAILWAY_DATA_VALIDATION_SPEC.md` has been corrected to:
`GR-1.02(62)-GR-8.01-DIRECTIONAL-LOCK`

---

## 3. Statutory Verification Matrix

| Rule Identifier | Authentic Source Document | Exact Statutory Clause | Verification Status | Operational Role in RAILGORITHM |
| :--- | :--- | :--- | :--- | :--- |
| **GR-4.08(1)-TRAIN-MPS** | General Rules 1976 (amended 2022) | Rule 4.08, Sub-rule (1) | **VERIFIED STATUTORY** | Enforces train-specific Maximum Permissible Speed (MPS) sanctioned by Commissioner of Railway Safety (CRS). |
| **GR-4.09-TSR-CAUTION-ORDER** | General Rules 1976 (amended 2020) | Rule 4.09 | **VERIFIED STATUTORY** | Enforces Temporary Speed Restrictions (TSRs) imposed via Caution Orders. Overrides sectional and train MPS. |
| **GR-1.02(62)-GR-8.01-DIRECTIONAL-LOCK** | General Rules 1976 & Operating Manual | GR 1.02(62), GR 8.01, GR 8.03(1) | **VERIFIED STATUTORY** | Rejects movement events where train direction opposes the unidirectional block designation on double lines. |
| **GR-8.01-ABSOLUTE-BLOCK-MUTEX** | General Rules 1976 | Rule 8.01 | **VERIFIED STATUTORY** | Mathematical mutual exclusion invariant: at most one train may occupy a block section between stations simultaneously. |
| **IR-SOD-TURNOUT-SPEED** | Schedule of Dimensions 2004 (amended 2023) | Chapter II, Item 5 (Turnouts) | **VERIFIED STATUTORY** | Restricts speed through station yard 1-in-12 and 1-in-8.5 turnouts to a maximum of $30\text{ km/h}$. |
| **BPAC-WHEEL-COUNT-CONTINUITY** | RDSO Specification | RDSO/SPN/177/2012 (Rev 3) | **VERIFIED STANDARD** | Block Proving by Axle Counters (BPAC): an exit event requires a prior verified entry event for wheel count balance. |
| **WTT-SECTIONAL-MPS** | Zonal Railway Working Time Table | Sectional Maximum Speed Table, Para 2.1 | **VERIFIED TIMETABLE** | Track infrastructure civil speed ceiling (e.g., $100\text{ km/h}$ on Section 1, $110\text{ km/h}$ on Section 2). |

---

## 4. Transparent Classification of Simulation Assumptions

Any heuristic parameter that is not directly codified in statutory General Rules is explicitly tagged with `SIM-ASSUMPTION-*`:

1. **`SIM-ASSUMPTION-HEADWAY` ($3.0\text{ min} / 180\text{ s}$):**
   - Macroscopic headway separation representing block signal spacing.
   - *Limitation:* Does not simulate microscopic four-aspect signal cascading (Green $\to$ Double Yellow $\to$ Yellow $\to$ Red).
2. **`SIM-ASSUMPTION-THROAT-CAPACITY` ($C=2$):**
   - Aggregate bottleneck heuristic at Malgaon Junction (MLG) diamond crossing.
   - *Limitation:* Represents physical route exclusivity across multiple yard tracks without modeling individual interlocking point levers.
3. **`SIM-ASSUMPTION-DRIFT-WINDOW` ($[-300\text{ s}, +60\text{ s}]$):**
   - Ingestion sanity filter accommodating GPS/NTP network drift while rejecting temporal hallucinations.
4. **`SIM-ASSUMPTION-TELEPORT-CAP` ($200\text{ km/h}$):**
   - Kinematic sanity filter blocking false telemetry jumps between discontinuous track circuits.

---

## 5. Non-Vital Advisory Scope

- **Simulation & Decision-Support Only:** RAILGORITHM is strictly an advisory scheduling and traffic monitoring platform.
- **No Vital Control:** The application has **zero writeback authority** to physical signalling relays, electronic interlockings, track circuits, or motorized points.
- **Human Authority:** All recommendations must be reviewed and approved by an authorized human Station Master or Section Controller before operational adoption.
