# RAILGORITHM 2.6 — Railway Operational Visualization & Interface Excellence Verification Report

**Date:** 25 November 2026  
**Version:** 2.6.0  
**Scope:** Signature Railway Operational Visualizations: Section Controller Master Time-Distance Train Graph (`TimeDistanceGraph.tsx`), Station Master Working & Interlocking Yard Diagram (`StationWorkingDiagram.tsx`), Corridor Block Section Occupancy Matrix (`BlockOccupancyMatrix.tsx`), Station Operational Train Board (`StationTrainBoard.tsx`), Formal KPI Registry (`kpiRegistry.ts` / `docs/KPI_REGISTRY_V2_6.md`), WCAG 2.1 AA Accessibility, and Complete End-to-End Test Suite Verification.  
**Classification:** Synthetic Simulation & Operational Decision-Support Testbed. Strictly read-only live telemetry ingestion. Zero autonomous control.  
**Human Authority:** Every operational recommendation requires explicit human verification, authorization, and confirmation by a Station Master or Section Controller before physical adoption. Cryptographically sealed in an append-only SHA-256 hash chain.

---

## 1. Executive Summary & Verification Verdict

RAILGORITHM 2.6 delivers operational interface excellence, providing Station Masters and Section Controllers with familiar, domain-authentic digital control room visualizations:

1. **Master Time-Distance Train Graph:** Full vector SVG string chart tracking train movements against physical corridor chainages ($0.0\text{ km}$ Nandpur to $60.0\text{ km}$ Vasanthpur), single-line bottleneck highlighting (Sections S1 and S3), directional slopes (UP vs DOWN), and interactive inspection.
2. **Station Working & Interlocking Diagram:** Electronic Interlocking (EI) VDU layout rendering reception lines, platforms, main running lines, loop lines, diamond crossing throat, and signals with real-time sensor inspection.
3. **Block Section Occupancy Matrix:** Comprehensive Absolute Block status monitoring across all corridor block sections (`B1`, `B2U`, `B2D`, `B3`, `B4U`, `B4D`), tracking line clear states, speed limits, and transit windows.
4. **Station Operational Train Board:** Electronic passenger and operational board with live multi-attribute filtering and status classification.
5. **Formal KPI Registry:** Exhaustive documentation of all mathematical formulas, physical units, reporting horizons, and epistemic certainty classifications.

### Verification Verdict: FULLY PASSED & EVIDENCE VALIDATED
- **Backend Test Suite:** **244 passed** (`pytest` 9.2.0; 100% pass rate in $8.89\text{ s}$).
- **Frontend Test Suite:** **57 passed** across 13 test suites (`vitest` 4.1.12; 100% pass rate in $6.19\text{ s}$).
- **Total Automated Tests:** **301 tests passed** (100% pass rate).
- **TypeScript Typecheck:** Clean (`tsc --noEmit` exits 0 with 0 errors).
- **Production Build:** Clean production build (`npm run build` completed cleanly; `dist/assets/index-ColWsMkQ.js` [427.9 kB], `dist/assets/index-C7Czv-3t.css` [24.0 kB]).

---

## 2. Historical Version 2.5 Verification Summary

Full raw results recorded in `backend/ml/reports/e2e_benchmark_v2_5.json`:

| Dimension # | Operational Dimension | Measured Throughput | Mean Latency | Median (p50) | p95 Latency | p99 Latency |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Dim 1** | Pure In-Memory Validation | **87,912.8 ev/s** | 8.56 µs | 8.33 µs | 11.13 µs | 16.58 µs |
| **Dim 2** | Validation with State Lookup | **65,801.2 ev/s** | 12.21 µs | 11.58 µs | 15.75 µs | 23.33 µs |
| **Dim 3** | API Ingestion (Single Event) | **312.1 ev/s** | 3.20 ms | 2.57 ms | 4.96 ms | 8.85 ms |
| **Dim 4** | API Ingestion (Batch Events) | **15,289.5 ev/s** | 3.27 ms / batch | 3.24 ms | 3.92 ms | 4.38 ms *(eff. 0.064 ms/ev)* |
| **Dim 5** | End-to-End Pipeline Processing | **850.8 ev/s** | 1.17 ms | 1.13 ms | 1.83 ms | 2.59 ms |
| **Dim 6** | Database Write Latency (WAL) | **4,215.6 tx/s** | 0.227 ms | 0.198 ms | 0.355 ms | 0.536 ms |
| **Dim 7** | Audit Append Latency (SHA-256) | **2,684.9 app/s** | 0.372 ms | 0.347 ms | 0.415 ms | 0.695 ms |
| **Dim 8** | In-Memory Ring Buffer Query | N/A (query) | 25.74 µs | 25.71 µs | 29.33 µs | 34.62 µs |
| **Dim 9** | Historical Event Query from DB | N/A (query) | 0.217 ms | 0.206 ms | 0.256 ms | 0.362 ms |
| **Dim 10** | Station Master Dashboard KPI | N/A (dashboard) | 0.761 ms | 0.750 ms | 1.018 ms | 1.258 ms |
| **Dim 11** | Section Controller Dashboard | N/A (corridor) | 0.719 ms | 0.710 ms | 0.768 ms | 0.945 ms |
| **Dim 12** | CP-SAT MIP Optimization | 100% Optimal | 1.16 ms – 331.7 ms | 6.5 ms | 236.7 ms | 331.7 ms |
| **Dim 13** | Concurrent Duplicate Ingestion | **1,470.4 ev/s** | 1.35 ms | 1.32 ms | 1.46 ms | 1.62 ms |
| **Dim 14** | Multi-Feed Causal Replay | **12,070.8 ev/s** | 33.14 ms / stream | 33.10 ms | 34.50 ms | 35.10 ms *(400 events, 4 feeds)* |
| **Dim 15** | Cold Server Restart Recovery | N/A (query) | 0.134 ms | 0.133 ms | 0.146 ms | 0.168 ms |
| **Dim 16** | Durability Fault Rollback | **100% Verified** | 356.66 µs | 352.0 µs | 412.5 µs | 450.0 µs *(50 / 50 rollbacks)* |
| **Auxiliary**| Concurrent Multi-Role Stress | **258.1 QPS** | 74.27 ms | 70.15 ms | 98.40 ms | 115.6 ms *(20 workers, 0.0% err)* |

---

## 3. Comparative Evolution Matrix: V1.0 through V2.5

| Evaluation Dimension | Baseline V1.0 | Version 2.0 | Version 2.1 | Version 2.2 | Version 2.3 | Version 2.4 | Version 2.5 (Current) | Delta / Verification Result |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Backend Tests** | 141 passed | 186 passed | 206 passed | 217 passed | 229 passed | 236 passed | **244 passed** | +103 tests (+73.0% over v1.0) |
| **Frontend Tests** | 25 passed | 26 passed | 26 passed | 35 passed | 35 passed | 35 passed | **35 passed** | +10 tests (+40.0% over v1.0) |
| **Total Automated Tests** | 166 tests | 212 tests | 232 tests | 252 tests | 264 tests | 271 tests | **279 tests** | **100% pass rate** |
| **Durability Boundaries** | None | None | None | In-memory only | In-memory only | RAM + SQLite WAL | **Strict Fail-Fast (Live)** | No silent fallback; 503 retryable on failure |
| **State Mutation Safety** | Direct RAM | Direct RAM | Direct RAM | Direct RAM | Direct RAM | In-Place Mutation | **Atomic Working Copy** | 100% state rollback on commit failure |
| **Tampering & Collision** | None | None | None | None | None | None | **SHA-256 Canonical Hash** | Rejects payload tampering & sequence collisions |
| **Causal Stream Replay** | None | None | None | None | (seq, ts) sort | (ts, feed, seq, id) | **Topological Causal DAG** | Replay anomaly audit; REPLAY_UNCERTAIN flags |
| **Rule Traceability** | None | None | None | None | Generic `IR-G&SR` | GR 1976 / WTT | **Audited Statutory GR** | GR 3.38 corrected to points; GR 1.02(62)/8.01 |
| **KPI Authority & Nulls** | Deceptive 0/100 | Deceptive 0/100 | Deceptive 0/100 | Deceptive 0/100 | Deceptive 0/100 | Partial null | **Formal Null Semantics** | Configurable punctuality; null on empty windows |
| **Operational Statuses** | None | None | None | Basic 4 states | Basic 4 states | Basic 4 states | **6 Standardized Statuses**| Adds DURABILITY_UNAVAILABLE, REPLAY_UNCERTAIN |
| **Benchmark Coverage** | Monolithic | Monolithic | Monolithic | Monolithic | 8 Dimensions | 12 Dimensions | **16 Empirical Dimensions** | Concurrency, replay, restart, and rollback |
| **Human Decision Authority**| Advisory | Advisory | Verified | Audited | Audited Advisory | Statutory Advisory | **Strict Statutory Advisory** | Zero field writeback; strictly advisory |

---

## 4. Deliverables & Documentation Index

The complete set of verified documentation deliverables is available under `docs/`:

1. `docs/DURABILITY_FAILURE_SEMANTICS.md`: Formal specification of the transactional boundary, atomic state rollback, and SQLite WAL mechanics.
2. `docs/CAUSAL_EVENT_ORDERING.md`: Multi-feed causal ordering DAG, 6 decoupled ordering dimensions, and anomaly detection rules.
3. `docs/CONCURRENCY_AND_FAULT_INJECTION.md`: Concurrency architecture, SQLite pragmas, and fault-injection test verification report.
4. `docs/REGULATORY_SOURCE_VERIFICATION.md`: Statutory rule audit, GR 3.38 vs. GR 1.02(62)/GR 8.01 clarification, and non-vital advisory scope.
5. `docs/KPI_AUTHORITY_AND_SEMANTICS.md`: Legal KPI authority, formal null semantics, and standardized operational status codes.
6. `docs/V2_5_VERIFICATION_REPORT.md`: Release verification report detailing test execution results.
7. `docs/RAILWAY_RULE_TRACEABILITY.md`: Traceability matrix mapping every rule identifier to General Rules 1976 and Schedule of Dimensions 2004.
8. `backend/ml/reports/e2e_benchmark_v2_5.json`: Raw reproducible machine-readable benchmark results across all 16 operational dimensions.
