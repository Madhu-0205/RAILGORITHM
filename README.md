# RAILGORITHM 2.5 — Durable Operations & Causal Integrity

AI-assisted railway traffic monitoring, scheduling, and **human decision support** on a realistic, modular network. The system ingests and validates real-time operational telemetry, simulates train movements, detects projected conflicts, generates candidate control actions, checks feasibility with Google OR-Tools CP-SAT, independently validates every candidate against formal hard constraints, ranks them with a trained PPO policy, explains the evidence, and **waits for an authorised human controller or station master to decide**.

> **Advisory-Only Safety Guarantee:** RAILGORITHM is strictly an advisory decision-support system. It is never connected to live signalling interlockings, points, routes, or wayside infrastructure, and cannot execute autonomous control. Every operational recommendation requires explicit human confirmation (`confirm_apply: true`) and written rationale, cryptographically secured in an append-only SHA-256 audit chain.

---

## What's New in Version 2.5

- **Fail-Fast Durability Boundaries:**
  - In `LIVE_OPERATIONAL` mode, database persistence failures **never** acknowledge success and never mutate in-memory state. The system raises `DurabilityUnavailableError` (mapped to HTTP 503 Service Unavailable with `retryable: True`).
  - Atomic state mutation: mutations are evaluated on a candidate snapshot copy and atomically swapped into active state only upon confirmed SQLite WAL transaction commit.
- **Payload Tampering & Sequence Collision Protection:**
  - SHA-256 canonical event payload hashing detects and rejects payload tampering on identical `event_id` (`PayloadTamperingError`).
  - Strict uniqueness constraints on `(feed_id, sequence_num)` prevent sequence reuse on the same feed (`SequenceCollisionError`).
- **Multi-Feed Causal Topological Replay:**
  - Implemented Directed Acyclic Graph (DAG) topological sorting across independent feeds with explicit `causal_dependencies`.
  - Distinguishes between source timestamps, server ingestion time, feed sequence, event IDs, clock skew, and causal dependencies.
  - Anomaly detection: unresolved dependencies, cycles, and timestamp inversions flag the stream as `replay_status: "REPLAY_UNCERTAIN"` and `causal_integrity: "AMBIGUOUS"`.
  - Non-authoritative invariant: uncertain replays can **never** become authoritative live operational states (`is_authoritative_live: false`).
  - Explicitly documents that deterministic tie-breaking on `(timestamp, feed_id, sequence_num, event_id)` is an operational convention, **not** mathematical proof of physical causality.
- **P0 Regulatory Traceability Correction (GR 3.38):**
  - Audited against authentic General Rules 1976 (Open Lines). Corrected the rule interpretation: **GR 3.38** statutorily governs *Points to be locked / Conditions for taking 'off' signals* (facing point detection and route locking), while directional movement locking on double lines is governed by **GR 1.02(62) ("Wrong Line" on double line)** and **GR 8.01 / GR 8.03(1) (Absolute Block System: Line Clear condition)**.
  - Tagged all simulation heuristics (`SIM-ASSUMPTION-*`) transparently.
- **KPI Authority, Null Semantics & Honest Operational Status:**
  - Punctuality threshold is made configurable via `punctuality_threshold_min` (default: 5 min) and documented as an administrative guideline (Railway Board Operating Directorate circulars for Mail/Express), not a statutory General Rule.
  - Formal null (`NO_DATA`) semantics for `schedule_adherence_pct`, `average_arrival_delay_min`, `average_departure_delay_min`, and `recovery_clearance_rate_pct` when observation windows contain 0 trains or 0 historical conflicts.
  - Standardized six operational health statuses across backend and frontend: `HEALTHY`, `DEGRADED`, `STALE`, `OFFLINE`, `DURABILITY_UNAVAILABLE`, `REPLAY_UNCERTAIN`.
- **Railway Operations Dashboard Modernization:**
  - Modern enterprise control-center design system: Deep Navy (`#101B2B` / `#17263B`) primary navigation, clean slate workspace (`#F1F5F9`), and pure white cards (`#FFFFFF`).
  - Standardized Station Master 8-KPI dashboard with live platform berth tracks (`StationPlatformBerths`), hourly movements chart (`HourlyMovementsChart`), and delay tier distribution (`DelayDistributionChart`).
  - Standardized Section Controller 9-KPI dashboard with interactive horizontal SVG railway corridor schematic (`RailwayCorridorDiagram`), Malgaon diamond crossing throat monitoring, and corridor active trains ledger.
  - Strict WCAG 2.1 AA accessibility and responsive table wrappers (`role="region"`, `tabIndex={0}`).
- **286 Automated Tests Passing (100% Pass Rate):**
  - **244 backend tests passed** (`pytest`).
  - **42 frontend tests passed** across 9 test suites (`vitest`).
  - Clean TypeScript compilation (`tsc --noEmit`).
  - Successful production build (`vite build`).
- **16-Dimensional Performance & Reliability Benchmark:**
  - Expanded benchmark from 12 to 16 empirical operational dimensions, measuring concurrent duplicate races (1,470.4 ev/s), multi-feed causal replay (12,070.8 ev/s), cold restart recovery (0.134 ms), and durability fault state rollbacks (100% verified). Output persisted to `backend/ml/reports/e2e_benchmark_v2_5.json`.

---

## Core Principles

1. **The human decides.** No recommendation is applied automatically. Approval requires explicit confirmation (`confirm_apply: true`) plus a written rationale (minimum 5 characters).
2. **Validation is independent of AI.** CP-SAT and PPO cannot make an invalid action executable. A separate hard-constraint validator checks topology, exclusivity, headway, closures, platform availability, hold policies, and junction throat capacities.
3. **The system admits uncertainty.** Infeasibility, model disagreement, stale advice, feed degradation, persistence unavailability, and causal ambiguities are surfaced explicitly. Confidence percentages are never fabricated.
4. **Data integrity first.** Live telemetry is validated against formal railway kinematic and interlocking invariants. Contradictory, impossible, tampered, or duplicate sensor packets are quarantined with traceable reason codes without corrupting state.
5. **Strict Environment Separation.** Simulation events never contaminate live operational state. Live feeds are strictly isolated and marked as advisory-only.

---

## User Roles & Operational Scope

| Role | Scope | Key Capabilities |
| :--- | :--- | :--- |
| **Station Master** | Local Station (NDL / KRN / MLG / SRP / VSN) | Platform berthing lineup, dwell monitoring, local schedule adherence %, approaching trains (60m window), station-level recommendations. |
| **Section Controller** | Full Corridor (120 km mainline) | Corridor-wide train tracking, block occupancy, Malgaon junction throat load %, Delay Propagation Index ($DPI$), dispatch queue, conflict resolution. |

---

## Version 2.5 Documentation & Evidence Deliverables

Full architectural specifications, fault-injection reports, mathematical derivations, and regulatory matrices are available in `docs/`:

- [Dashboard Design System Specification](file:///Users/madhu/RAILGORITHM/docs/DASHBOARD_DESIGN_SYSTEM.md)
- [KPI Definitions & Mathematical Semantics](file:///Users/madhu/RAILGORITHM/docs/KPI_DEFINITIONS_AND_SEMANTICS.md)
- [Station Master Dashboard Specification](file:///Users/madhu/RAILGORITHM/docs/STATION_MASTER_DASHBOARD.md)
- [Section Controller Dashboard Specification](file:///Users/madhu/RAILGORITHM/docs/SECTION_CONTROLLER_DASHBOARD.md)
- [Frontend Modernization & Verification Report](file:///Users/madhu/RAILGORITHM/docs/FRONTEND_VERIFICATION.md)
- [Durability & Failure Semantics Specification](file:///Users/madhu/RAILGORITHM/docs/DURABILITY_FAILURE_SEMANTICS.md)
- [Multi-Feed Causal Event Ordering Specification](file:///Users/madhu/RAILGORITHM/docs/CAUSAL_EVENT_ORDERING.md)
- [Concurrency & Fault Injection Engineering Report](file:///Users/madhu/RAILGORITHM/docs/CONCURRENCY_AND_FAULT_INJECTION.md)
- [Regulatory Source Verification & Rule Interpretation](file:///Users/madhu/RAILGORITHM/docs/REGULATORY_SOURCE_VERIFICATION.md)
- [KPI Authority, Semantics & Null Handling](file:///Users/madhu/RAILGORITHM/docs/KPI_AUTHORITY_AND_SEMANTICS.md)
- [Version 2.5 Verification & Reliability Report](file:///Users/madhu/RAILGORITHM/docs/V2_5_VERIFICATION_REPORT.md)
- [Railway Rule Traceability Matrix](file:///Users/madhu/RAILGORITHM/docs/RAILWAY_RULE_TRACEABILITY.md)
- [Master Verification Report](file:///Users/madhu/RAILGORITHM/VERIFICATION.md)
- [Raw End-to-End Benchmark Artifact](file:///Users/madhu/RAILGORITHM/backend/ml/reports/e2e_benchmark_v2_5.json)
