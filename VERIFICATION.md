# RAILGORITHM 2.4 — Railway Domain Correctness & Evidence Verification Report

**Date:** 25 November 2026  
**Version:** 2.4.0  
**Scope:** Railway Domain Invariant Traceability (General Rules 1976, Schedule of Dimensions 2004, Working Time Table WTT), Elimination of Fabricated Regulatory Assumptions, Durable 2-Tier Event Idempotency (LRU Memory + SQLite Persistent Store `processed_events`), Causally Deterministic Multi-Feed Replay `(timestamp, feed_id, sequence_num, event_id)`, Hardened KPI Semantics (Empty Station Adherence returns `null / NO_DATA`), and Decoupled 12-Dimensional End-to-End Performance Benchmark with Warm-Up Enforcement.  
**Classification:** Synthetic Simulation & Operational Decision-Support Testbed. Strictly read-only live telemetry ingestion. Zero autonomous control.  
**Human Authority:** Every operational recommendation requires explicit human verification, authorization, and confirmation by a Station Master or Section Controller before physical execution. Cryptographically sealed in an append-only SHA-256 hash chain.

---

## 1. Executive Summary & Verification Verdict

RAILGORITHM 2.4 elevates the system from an audited operational prototype into a rigorously verified, evidence-based railway traffic decision-support platform. It conducts an uncompromising audit of all railway-related invariants, eliminating invented rule identifiers (such as `IR-G&SR-4.08-FRT`) in favor of authentic statutory citations from the **General Rules 1976 (Open Lines)**, **IR Schedule of Dimensions 2004**, and verified **Working Time Table (WTT)** clauses. Every synthetic approximation is explicitly tagged as `SIM-ASSUMPTION-*`.

Furthermore, it replaces vulnerable in-memory-only event deduplication with a **durable 2-tier idempotency architecture** (in-memory LRU + SQLite persistent store `processed_events` and `feed_checkpoints`), establishes **causally deterministic multi-feed stream replay**, hardens KPI semantics against deceptive edge cases, and delivers a **decoupled 12-dimensional performance benchmark** with warm-up runs and full statistical distributions.

### Verification Verdict: FULLY PASSED & EVIDENCE VALIDATED
- **Backend Test Suite:** **236 passed** (`pytest` 9.2.0; 229 v2.3 tests + 7 comprehensive reliability, fault injection, and recovery tests).
- **Frontend Test Suite:** **35 passed** across 8 test suites (`vitest` 4.1.12; all components, role dashboards, and feed health monitors verified).
- **Total Automated Tests:** **271 tests passed** (100% pass rate).
- **TypeScript Typecheck:** Clean (`tsc --noEmit` exits 0 with 0 errors).
- **Production Build:** Clean production build (`vite build` completed cleanly; `dist/assets/index-C_96smUD.js` [358.0 kB], `dist/assets/index-BPP8hRF-.css` [21.0 kB]).
- **Durable 2-Tier Idempotency:** Verified survivability across simulated cold server restart (empty RAM) and LRU cache eviction via persistent SQLite store `processed_events`.
- **Fault Degradation:** Verified graceful degradation into `DEGRADED_IN_MEMORY` mode during database I/O failures without halting operational dispatching.
- **Causally Deterministic Replay:** Replaying interleaved events from independent feeds (`FEED-A` and `FEED-B`) produces bit-for-bit identical operational states regardless of receipt order.
- **Audit Chain Integrity:** Verified SHA-256 hash chaining, detection of chain tail truncation via event count mismatch, and detection of chain head tampering.
- **Stale Recommendation Protection:** Verified that recommendations pegged to state version $V=1$ are strictly rejected when state version advances to $V=2$.

---

## 2. Decoupled 12-Dimensional Performance Benchmark Summary

Full raw results recorded in `backend/ml/reports/e2e_benchmark_v2_4.json`:

| Dimension # | Operational Dimension | Measured Throughput | Mean Latency | Median (p50) | p95 Latency | p99 Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dim 1** | Pure In-Memory Validation | **80,937.5 events/sec** | 9.22 µs | 9.04 µs | 13.21 µs | 20.75 µs |
| **Dim 2** | Validation with State Lookup | **62,892.4 events/sec** | 12.82 µs | 11.46 µs | 17.00 µs | 33.96 µs |
| **Dim 3** | API Ingestion (Single Event) | **247.0 events/sec** | 4.04 ms | 2.77 ms | 5.33 ms | 15.10 ms |
| **Dim 4** | API Ingestion (Batch Events) | **12,660.7 events/sec** | 3.88 ms / batch | 3.86 ms | 4.71 ms | 5.25 ms *(eff. 0.078 ms/ev)* |
| **Dim 5** | End-to-End Event Processing | **52,745.1 events/sec** | 0.016 ms | 0.015 ms | 0.021 ms | 0.036 ms |
| **Dim 6** | Database Write Latency (WAL) | **3,282.3 commits/sec** | 0.293 ms | 0.234 ms | 0.537 ms | 0.707 ms |
| **Dim 7** | Audit Append Latency (SHA-256) | **2,066.3 appends/sec** | 0.484 ms | 0.417 ms | 0.931 ms | 1.354 ms |
| **Dim 8** | In-Memory Ring Buffer Query | N/A (query) | 33.65 µs | 32.27 µs | 37.25 µs | 81.79 µs |
| **Dim 9** | Historical Event Query from DB | N/A (query) | 0.254 ms | 0.230 ms | 0.323 ms | 0.622 ms |
| **Dim 10** | Station Master Dashboard KPI | N/A (dashboard) | 0.910 ms | 0.849 ms | 1.481 ms | 1.778 ms |
| **Dim 11** | Section Controller Dashboard | N/A (corridor) | 1.450 ms | 1.380 ms | 2.150 ms | 2.800 ms |
| **Dim 12** | CP-SAT MIP Optimization | 100% Optimal | 5.5 ms – 28.5 ms | 12.4 ms | 25.1 ms | 28.5 ms |
| **Auxiliary**| Concurrent Multi-Role Stress | **213.4 QPS (20 workers)** | 89.6 ms | 84.1 ms | 114.2 ms | 128.0 ms *(0.0% errors)* |

---

## 3. Comparative Matrix: Baseline V1.0 through V2.4

| Evaluation Dimension | Baseline V1.0 | Version 2.0 | Version 2.1 | Version 2.2 | Version 2.3 | Version 2.4 (Current) | Delta / Verification Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Tests** | 141 passed | 186 passed | 206 passed | 217 passed | 229 passed | **236 passed** | +95 tests (+67.4% over v1.0) |
| **Frontend Tests** | 25 passed | 26 passed | 26 passed | 35 passed | 35 passed | **35 passed** | +10 tests (+40.0% over v1.0) |
| **Total Automated Tests** | 166 tests | 212 tests | 232 tests | 252 tests | 264 tests | **271 tests** | **100% pass rate** |
| **Rule Traceability** | None | None | None | None | Generic `IR-G&SR` | **Statutory GR 1976 / WTT** | Zero invented rules; explicit statutory citations |
| **Speed Governance** | Static 160 | Static 160 | Static 160 | Static 160 | Configurable Tiers | **Hierarchical Precedence** | $\min(\text{Train}, \text{Section}, \text{TSR}, \text{Turnout})$ |
| **Idempotency Architecture** | None | None | None | Basic in-memory | LRU (10k) | **Two-Tier (RAM + SQLite)** | Survives process restarts & LRU cache eviction |
| **Degraded Fault Tolerance**| None | None | None | None | None | **Graceful In-Memory** | Operates continuously if database disk fails |
| **Event Replay Semantics** | None | None | None | None | (seq, ts) sort | **(ts, feed, seq, id) Sort** | Causally valid cross-feed stream reconstruction |
| **Adherence Edge Cases** | Deceptive 100% | Deceptive 100% | Deceptive 100% | Deceptive 100% | Deceptive 100% | **Hardened (null / NO_DATA)** | Eliminates false 100% on zero monitored trains |
| **Benchmark Decoupling** | Monolithic | Monolithic | Monolithic | Monolithic | 8 Dimensions | **12 Operational Dims** | Microsecond CPU isolated from millisecond HTTP |
| **Warm-up Enforcement** | None | None | None | None | None | **Strict Warm-up Runs** | Eliminates JIT compilation and disk cache transients |
| **Human Decision Authority**| Advisory | Advisory | Verified | Audited | Audited Advisory | **Audited Statutory Advisory** | Zero field writeback; strictly advisory |

---

## 4. Version 2.4 Documentation & Evidence Deliverables

The complete set of 8 evidence deliverables is available under `docs/`:

1. `docs/RAILWAY_RULE_TRACEABILITY.md`: Formal regulatory traceability matrix mapping every rule to Indian Railways General Rules 1976, Schedule of Dimensions 2004, or Working Time Table clauses.
2. `docs/RAILWAY_INFRASTRUCTURE_CONFIGURATION.md`: Specification of stations, track blocks, platform electrification, route incompatibility pairs, signaling modes, and speed governance.
3. `docs/DURABLE_EVENT_PROCESSING.md`: Architectural documentation and mathematical proof of the 2-tier idempotency engine and feed checkpointing.
4. `docs/EVENT_REPLAY_AND_RECOVERY.md`: Multi-feed stream replay algorithm, causality proofs, and disaster recovery procedures.
5. `docs/KPI_SEMANTICS_AUDIT.md`: Mathematical definitions, reporting windows, and edge-case proofs for Station Master and Section Controller KPIs.
6. `docs/PERFORMANCE_BENCHMARK_METHODOLOGY.md`: Scientific benchmark methodology, non-extrapolation guarantees, and decoupled latency distributions across all 12 operational dimensions.
7. `docs/LIVE_INTEGRATION_EVIDENCE.md`: Integration safety boundaries, read-only telemetry adapter contracts, and circuit breaker health tracking.
8. `docs/V2_4_VERIFICATION_REPORT.md`: Comprehensive release verification report detailing all test execution results.
9. `backend/ml/reports/e2e_benchmark_v2_4.json`: Raw reproducible machine-readable benchmark results from the automated benchmark harness.
