# RAILGORITHM 2.4 — Railway Domain Correctness & Evidence Validation

AI-assisted railway traffic monitoring, scheduling, and **human decision support** on a realistic, modular network. The system ingests and validates real-time operational telemetry, simulates train movements, detects projected conflicts, generates candidate control actions, checks feasibility with Google OR-Tools CP-SAT, independently validates every candidate against formal hard constraints, ranks them with a trained PPO policy, explains the evidence, and **waits for an authorised human controller or station master to decide**.

> **Advisory-Only Safety Guarantee:** RAILGORITHM is strictly an advisory decision-support system. It is never connected to live signalling interlockings, points, routes, or wayside infrastructure, and cannot execute autonomous control. Every operational recommendation requires explicit human confirmation (`confirm_apply: true`) and written rationale, cryptographically secured in an append-only SHA-256 audit chain.

---

## What's New in Version 2.4

- **Railway Regulatory Traceability & Zero-Assumption Governance:**
  - Audited and eliminated all invented rule identifiers (such as `IR-G&SR-4.08-FRT`).
  - Mapped statutory invariants directly to the **General Rules 1976 (Open Lines)** issued by the Ministry of Railways, Government of India (`GR-4.08(1)-TRAIN-MPS`, `GR-4.09-TSR-CAUTION-ORDER`, `GR-1.02(62)`, `GR-3.38`, `GR-8.01`), **IR Schedule of Dimensions 2004** (`IR-SOD-TURNOUT-SPEED`), and verified **Working Time Table (WTT)** clauses.
  - Transparently marked all simulation approximations with `SIM-ASSUMPTION-*`.
- **Durable Two-Tier Event Idempotency:**
  - Backed in-memory deduplication with a persistent SQLite store (`processed_events` and `feed_checkpoints`).
  - Full idempotency survivability across process restarts and beyond bounded LRU cache evictions.
  - Graceful degradation to in-memory mode (`DEGRADED_IN_MEMORY`) if database disk I/O errors occur, ensuring dispatching never halts.
- **Causally Deterministic Multi-Feed Replay:**
  - Solved cross-feed causality by sorting multi-feed streams on `(timestamp, feed_id, sequence_num, event_id)` instead of independent per-feed sequence numbers.
  - Deep copy state isolation guarantees zero side-effects during historical playback or state reconstruction.
- **Hardened KPI Semantics:**
  - Corrected schedule adherence calculation: when zero trains are monitored in a station window, adherence evaluates to `null` with `adherence_status: "NO_DATA"`, eliminating misleading 100% adherence claims.
  - Documented statutory 5-minute punctuality tolerance (Indian Railways Mail/Express standard).
  - Explicitly labeled Delay Propagation Index (DPI) as a simulation heuristic (`HEURISTIC_SIMULATION_ESTIMATE`).
- **Decoupled 12-Dimensional Performance Benchmark:**
  - Decoupled pure in-memory microsecond validation from millisecond HTTP REST ingestion.
  - Enforced strict warm-up iterations and measured sample counts, p50, p95, and p99 distributions.
  - Documented full hardware metadata (Apple Silicon, 6 cores, macOS Darwin 27.2.0, Python 3.14.7).
- **271 Automated Tests Passing (100% Pass Rate):**
  - **236 backend tests passed** (`pytest`).
  - **35 frontend tests passed** across 8 test suites (`vitest`).
  - Clean TypeScript compilation (`tsc --noEmit`).
  - Successful production build (`vite build`).

---

## Core Principles

1. **The human decides.** No recommendation is applied automatically. Approval requires explicit confirmation (`confirm_apply: true`) plus a written rationale (minimum 5 characters).
2. **Validation is independent of AI.** CP-SAT and PPO cannot make an invalid action executable. A separate hard-constraint validator checks topology, exclusivity, headway, closures, platform availability, hold policies, and junction throat capacities.
3. **The system admits uncertainty.** Infeasibility, model disagreement, stale advice, feed degradation, and candidate limitations are surfaced explicitly. Confidence percentages are never fabricated.
4. **Data integrity first.** Live telemetry is validated against formal railway kinematic and interlocking invariants. Contradictory, impossible, or duplicate sensor packets are quarantined with traceable reason codes without corrupting state.
5. **Strict Environment Separation.** Simulation events never contaminate live operational state. Live feeds are strictly isolated and marked as advisory-only.

---

## User Roles & Operational Scope

| Role | Scope | Key Capabilities |
| :--- | :--- | :--- |
| **Station Master** | Local Station (NDL / KRN / MLG / SRP / VSN) | Platform berthing lineup, dwell monitoring, local schedule adherence %, approaching trains (60m window), station-level recommendations. |
| **Section Controller** | Full Corridor (120 km mainline) | Corridor-wide train tracking, block occupancy, Malgaon junction throat load %, Delay Propagation Index ($DPI$), dispatch queue, conflict resolution. |

---

## Version 2.4 Documentation & Evidence Deliverables

Full architectural audits, mathematical derivations, benchmark reports, and regulatory specifications are available in `docs/`:

- [Railway Rule Traceability Matrix](file:///Users/madhu/RAILGORITHM/docs/RAILWAY_RULE_TRACEABILITY.md)
- [Railway Infrastructure Configuration Specification](file:///Users/madhu/RAILGORITHM/docs/RAILWAY_INFRASTRUCTURE_CONFIGURATION.md)
- [Durable Event Processing & 2-Tier Idempotency](file:///Users/madhu/RAILGORITHM/docs/DURABLE_EVENT_PROCESSING.md)
- [Event Replay & Multi-Feed Recovery Specification](file:///Users/madhu/RAILGORITHM/docs/EVENT_REPLAY_AND_RECOVERY.md)
- [Operational KPI Semantics Audit Report](file:///Users/madhu/RAILGORITHM/docs/KPI_SEMANTICS_AUDIT.md)
- [Performance Benchmark Methodology & Decoupled Results](file:///Users/madhu/RAILGORITHM/docs/PERFORMANCE_BENCHMARK_METHODOLOGY.md)
- [Live Integration Readiness & Safety Evidence](file:///Users/madhu/RAILGORITHM/docs/LIVE_INTEGRATION_EVIDENCE.md)
- [Version 2.4 Verification & Release Report](file:///Users/madhu/RAILGORITHM/docs/V2_4_VERIFICATION_REPORT.md)
- [Master Verification Report](file:///Users/madhu/RAILGORITHM/VERIFICATION.md)
- [Raw End-to-End Benchmark Artifact](file:///Users/madhu/RAILGORITHM/backend/ml/reports/e2e_benchmark_v2_4.json)
