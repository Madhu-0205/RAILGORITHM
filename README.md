# RAILGORITHM 2.2 — Real-Time Reliability & Operational Intelligence

AI-assisted railway traffic monitoring, scheduling, and **human decision support** on a realistic, modular network. The system ingests and validates real-time operational telemetry, simulates train movements, detects projected conflicts, generates candidate control actions, checks feasibility with Google OR-Tools CP-SAT, independently validates every candidate against formal hard constraints, ranks them with a trained PPO policy, explains the evidence, and **waits for an authorised human controller or station master to decide**.

> **Advisory-Only Safety Guarantee:** RAILGORITHM is strictly an advisory decision-support system. It is never connected to live signalling interlockings, points, routes, or wayside infrastructure, and cannot execute autonomous control. Every operational recommendation requires explicit human confirmation (`confirm_apply: true`) and written rationale, cryptographically secured in an append-only audit chain.

---

## What's New in Version 2.2

- **Modular Real-Time Data Ingestion:** Real-time ingestion engine (`backend/app/ingestion/`) supporting authorized railway telemetry feeds and partner APIs with continuous ingestion, data validation, and timestamp normalization.
- **Strict Ingestion Validation & Contradiction Protection:** 6-layer verification covering duplicate fingerprint caching (LRU), sequence gap tracking, physical velocity limits ($v \le 160$ km/h), temporal drift/inversion checks, spatial teleportation prevention, and single-line mutual exclusion.
- **Feed Health & Circuit Breakers:** Continuous health monitoring with freshness age classification (`HEALTHY`, `DEGRADED`, `STALE`, `OFFLINE`), automatic circuit breaker tripping on $>35\%$ error rates or 10 failures, exponential backoff reconnection, and clear stale-data UI indicators.
- **Role-Specific Operational Dashboards:**
  - **Station Master:** Station-scoped monitoring (NDL, KRN, MLG, SRP, VSN), platform berth visualizer (`OCCUPIED`, `AVAILABLE`, `OUTAGE`), rolling 60-minute train movements, schedule adherence %, and local station alerts.
  - **Section Controller:** Corridor-wide movements, average section delay, block occupancy, Malgaon (MLG) junction throat load % and queue length, Delay Propagation Index ($DPI$), knock-on risk levels, throughput, and dispatch decision queue.
- **Traceable Mathematical KPI Definitions:** Clear formulas, time periods, and source data citations displayed directly in the user interface for every operational metric.
- **Empirically Measured High Performance:**
  - Ingestion throughput: **72,446 events/second** (mean latency: **0.0055 ms**).
  - Concurrent API load: **197.8 QPS** across 20 workers with **0.0% error rate** (mean latency: **96.7 ms**).
  - Decision generation pipeline: **310.7 ms** mean latency under peak morning corridor traffic.
- **252 Automated Tests:** 217 backend pytest tests and 35 frontend vitest tests passing with 100% success rate, clean TypeScript compilation, and clean production build.

---

## Core Principles

1. **The human decides.** No recommendation is applied automatically. Approval requires explicit confirmation (`confirm_apply: true`) plus a written rationale (minimum 5 characters).
2. **Validation is independent of AI.** CP-SAT and PPO cannot make an invalid action executable. A separate hard-constraint validator checks topology, exclusivity, headway, closures, platform availability, hold policies, and junction throat capacities.
3. **The system admits uncertainty.** Infeasibility, model disagreement, stale advice, feed degradation, and candidate limitations are surfaced explicitly. Confidence percentages are never fabricated.
4. **Data integrity first.** Live telemetry is validated before entering the dispatch pipeline. Contradictory, impossible, or duplicate sensor packets are quarantined without corrupting simulation state.

---

## User Roles & Operational Scope

| Role | Scope | Key Capabilities |
| :--- | :--- | :--- |
| **Station Master** | Local Station (NDL / KRN / MLG / SRP / VSN) | Platform berthing lineup, dwell monitoring, local schedule adherence %, approaching trains (60m window), station-level recommendations. |
| **Section Controller** | Full Corridor (120 km mainline) | Corridow-wide train tracking, block occupancy, Malgaon junction throat load %, Delay Propagation Index ($DPI$), dispatch queue, conflict resolution. |

---

## Verification & Documentation

Full architectural specifications, benchmark test logs, and mathematical derivations are available in `docs/`:

- [Data Ingestion Architecture](file:///Users/madhu/RAILGORITHM/docs/INGESTION_ARCHITECTURE.md)
- [Role-Based Operations & KPI Intelligence](file:///Users/madhu/RAILGORITHM/docs/ROLE_BASED_OPERATIONS.md)
- [Performance, Concurrency & Load Benchmark Report](file:///Users/madhu/RAILGORITHM/docs/PERFORMANCE_AND_LOAD_TESTS.md)
- [Verification and Operational Intelligence Report](file:///Users/madhu/RAILGORITHM/VERIFICATION.md)
- [Raw Load Test Benchmark Report](file:///Users/madhu/RAILGORITHM/backend/ml/reports/load_test_v2_2.json)
