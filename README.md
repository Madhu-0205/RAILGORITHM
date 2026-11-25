# RAILGORITHM 2.3 — Real-Time Integration & Reliability Audit

AI-assisted railway traffic monitoring, scheduling, and **human decision support** on a realistic, modular network. The system ingests and validates real-time operational telemetry, simulates train movements, detects projected conflicts, generates candidate control actions, checks feasibility with Google OR-Tools CP-SAT, independently validates every candidate against formal hard constraints, ranks them with a trained PPO policy, explains the evidence, and **waits for an authorised human controller or station master to decide**.

> **Advisory-Only Safety Guarantee:** RAILGORITHM is strictly an advisory decision-support system. It is never connected to live signalling interlockings, points, routes, or wayside infrastructure, and cannot execute autonomous control. Every operational recommendation requires explicit human confirmation (`confirm_apply: true`) and written rationale, cryptographically secured in an append-only SHA-256 audit chain.

---

## What's New in Version 2.3

- **Configurable Railway Domain Validation:** Replaced universal hardcoded assumptions with dynamic, configurable infrastructure and rolling stock rules:
  - **Train MPS Tiers:** Heavy Freight (75 km/h), MEMU/Suburban (90 km/h), Passenger (100 km/h), and Express/Superfast (130 km/h).
  - **Section Limits & TSRs:** Dynamic sectional speed enforcement and Temporary Speed Restrictions (TSRs).
  - **Directional Track Locking:** Strict unidirectional track circuit enforcement on double-line blocks (`B2U` strictly UP, `B2D` strictly DOWN) under `IR-G&SR-3.38`.
  - **Block Continuity & Headway:** Unmatched block exit prevention (`UNMATCHED_BLOCK_EXIT`) and 180s minimum headway verification (`HC-002`).
  - **Junction Diamond Throat Capacity:** Enforces maximum physical throat capacity ($C \le 2$) at Malgaon Junction (`HC-006`).
- **21 Standardized Traceable Reason Codes:** Every rejected telemetry event carries an explicit, machine-readable `ValidationReasonCode` and regulatory rule reference (e.g. `IR-G&SR-4.08`, `IR-G&SR-3.38`, `HC-002`).
- **Three-Tier Environment Isolation:** Complete separation across API, database, cache, and telemetry layers between `LIVE_OPERATIONAL`, `SYNTHETIC_SIMULATION`, and `HISTORICAL_PLAYBACK`. Cross-environment state mutations are strictly blocked.
- **Idempotent State Processor & Deterministic Replay:** `OperationalEventProcessor` guarantees zero duplicate mutations via a 10,000-entry LRU cache and provides `replay_event_stream` to reconstruct operational states from scratch with 100% bit-for-bit parity.
- **Audited KPI Mathematics:** Every Station Master and Section Controller KPI audited, documented with explicit formulas, reporting windows, and validated against independent ground-truth test matrices.
- **Live Integration Readiness:** Architecture specifications and modular adapters (`backend/app/ingestion/adapters.py`) ready for CRIS/COA, FOIS, and IoT Axle Counters (BPAC) with strict read-only contracts.
- **Comprehensive 8-Dimension Performance Benchmark:**
  - In-memory validation throughput: **71,707.0 events/second** (mean: **11.01 microseconds**).
  - Batch API ingestion throughput: **13,058.7 events/second** (effective: **0.0753 ms/event**).
  - End-to-end pipeline throughput: **7,404.7 events/second** (mean: **0.1312 ms**).
  - Database commit throughput: **2,978.8 tx/second** (mean: **0.3212 ms**).
  - Stream recovery latency: **28.76 microseconds** mean.
  - Role-specific dashboard latency: Station Master **0.87 ms**, Section Controller **1.73 ms**.
  - CP-SAT scheduling solve time: **~260 ms** mean across all 4 objective profiles (all OPTIMAL).
  - High-concurrency stress test: **230.7 QPS** across 20 workers with **0.0% error rate**.
- **264 Automated Tests Passing:** 229 backend pytest tests and 35 frontend vitest tests passing with 100% pass rate, clean TypeScript compilation, and production build.

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

## Version 2.3 Documentation & Audit Deliverables

Full architectural audits, mathematical derivations, benchmark reports, and regulatory specifications are available in `docs/`:

- [Real-Time Pipeline Audit Report](file:///Users/madhu/RAILGORITHM/docs/REALTIME_PIPELINE_AUDIT.md)
- [Railway Data Validation Specification](file:///Users/madhu/RAILGORITHM/docs/RAILWAY_DATA_VALIDATION_SPEC.md)
- [Operational KPI Accuracy Report](file:///Users/madhu/RAILGORITHM/docs/KPI_ACCURACY_REPORT.md)
- [End-to-End Performance Benchmark Report](file:///Users/madhu/RAILGORITHM/docs/END_TO_END_PERFORMANCE_REPORT.md)
- [Reliability & Failure Recovery Report](file:///Users/madhu/RAILGORITHM/docs/RELIABILITY_AND_RECOVERY_REPORT.md)
- [Live Integration Readiness Specification](file:///Users/madhu/RAILGORITHM/docs/LIVE_INTEGRATION_READINESS.md)
- [Verification & Operational Intelligence Report](file:///Users/madhu/RAILGORITHM/VERIFICATION.md)
- [Raw End-to-End Benchmark Artifact](file:///Users/madhu/RAILGORITHM/backend/ml/reports/e2e_benchmark_v2_3.json)
