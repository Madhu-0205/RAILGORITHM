# RAILGORITHM 2.0 — Verification and Engineering Report

**Date:** 25 November 2026  
**Version:** 2.0.0  
**Scope:** Full-stack railway simulation, conflict detection, CP-SAT optimization, PPO ranking, and human-in-the-loop decision support system.  
**Classification:** Synthetic Simulation-Only Decision Support. No live railway connection.  
**Human Control:** Every operational action requires explicit human authorization and confirmation. Autonomous execution is strictly prohibited.

---

## 1. Executive Summary and Verdict

RAILGORITHM 2.0 represents a comprehensive engineering upgrade over the Version 1.0 baseline. The upgraded application has been fully implemented, rigorously tested, and empirically benchmarked across 14 deterministic synthetic scenarios.

### Verification Verdict: PASSED
- **Backend Test Suite:** **186 passed** (up from 141 in v1.0).
- **Frontend Test Suite:** **26 passed** across 6 test suites (up from 25 in v1.0).
- **TypeScript Typecheck:** Clean (0 errors).
- **Production Bundle:** Clean build (348.6 kB JS, 19.7 kB CSS).
- **14-Scenario API E2E Matrix:** **13 feasible scenarios approved and applied**, 1 infeasible scenario (`no_feasible_schedule`) **correctly refused approval with HTTP 409 Conflict**.
- **Cryptographic Audit Log:** SHA-256 hash chain verified valid across 60 events with tail truncation detection.
- **PPO Candidate Evaluation:** On 89 held-out decisions across 4 seeds, Top-1 match improved from **25.8% to 61.8%**, mean regret decreased from **16.20 to 15.26**, and residual conflicts dropped from **10.08 to 1.39** with **zero constraint violations**.
- **Model Checkpoints:** Baseline checkpoint `backend/ml/artifacts/ppo_policy.pt` protected and preserved; candidate stored in `backend/ml/artifacts/v2_candidate/`.

---

## 2. Baseline V1.0 vs Version 2.0 Comparative Matrix

| Evaluation Dimension | Baseline (Version 1.0) | Version 2.0 | Measurable Delta / Benefit |
|---|---|---|---|
| **Scenario Coverage** | 8 synthetic scenarios | **14 synthetic scenarios** | +6 scenarios (overtaking, junction congestion, maintenance, cascading delays, surge) |
| **Backend Tests** | 141 passed | **186 passed** | +45 tests (+31.9% test growth) |
| **Frontend Tests** | 25 passed | **26 passed** | +1 test suite (`Specifications.test.tsx`) |
| **Conflict Taxonomy** | 3 types (Headway, Crossing, Platform) | **13 formal types** (including Overtaking, Junction, Closures, Cascading Delay) | Comprehensive, deduplicated conflict evidence binding HC/SC constraint IDs |
| **CP-SAT Objectives** | Single fixed objective | **4 configurable profiles** (Balanced, Delay-focused, Priority-focused, Throughput) | Multi-criteria dispatching trade-offs with explicit lower bounds |
| **CP-SAT Mean Solve Time** | 0.057 seconds | **0.025 seconds** | 56% faster solve times through tightened interval bounds |
| **PPO Top-1 Match (Held-out)**| 25.84% | **61.80%** | **+35.96% improvement** in matching best measured candidate |
| **PPO Mean Regret (Held-out)**| 16.202 | **15.258** | **-0.944 lower regret** |
| **PPO Residual Conflicts** | 10.08 | **1.39** | **86.2% reduction** in unresolved operational conflicts |
| **PPO Violation Attempts** | 0 | **0** | Perfect hard-constraint filtering |
| **PPO Inference Latency** | ~0.05 ms | **0.058 ms mean (0.066 ms p95)** | Real-time candidate scoring (< 0.1 ms) |
| **Assumptions Transparency** | Constants scattered in code | **Centralized `ASSUMPTIONS` manifest** | All 15 assumptions versioned, typed, and inspectable via API and UI |
| **Constraint Formalization** | Implicit code checks | **13 Hard + 4 Soft Constraints** | Formal `CONSTRAINTS` specification bound to detector, solver, and validator |
| **Audit Log Integrity** | SHA-256 chain (tail vulnerable) | **SHA-256 chain + `AuditChainHead`** | Tail truncation detection; DB triggers blocking update/delete |
| **Security Posture** | Default secrets permitted | **Production Guardrails (`assert_safe_for_production`)** | Boot fails if demo creds, default secrets or SQLite used in production |
| **Database Portability** | SQLite only | **SQLite dev + PostgreSQL portability** | Schema compiles cleanly to PostgreSQL dialect without SQLite types |

---

## 3. Detailed Upgrade Verification Breakdown

### Upgrade 1: Railway Simulation Realism
- Implemented in `backend/app/domain/network.py`, `state.py`, `scenarios.py`, and `spec.py`.
- **Infrastructure:** Network features single-line bottlenecks (`NDL–KRN`, `MLG–SRP`), double-line unidirectional sections (`KRN–MLG`, `SRP–VSN`), station platforms (560m–720m), and junction throat capacities (2 simultaneous movements).
- **Traffic Realism:** 4 rolling stock categories (`EXPRESS`, `PASSENGER`, `MEMU`, `FREIGHT`) with category-specific speeds (75–130 km/h), speed factors (0.85–1.25), priority tiers (1 to 5), and station hold caps (20 to 45 min).
- **Verification Evidence:** `test_network.py` (7 tests), `test_scenarios.py` (14 tests), `test_simulation.py` (14 tests).

### Upgrade 2: Conflict Detection & Deduplication
- Implemented in `backend/app/domain/conflicts.py`.
- Taxonomy expanded to 13 types: `BLOCK_EXCLUSIVITY`, `HEADWAY`, `SINGLE_LINE_CROSSING`, `CROSSING_CONFLICT`, `ROUTE_CONFLICT`, `OVERTAKING_CONFLICT`, `PLATFORM_CAPACITY`, `JUNCTION_CONFLICT`, `BLOCK_CLOSURE`, `MAINTENANCE_CONFLICT`, `DISRUPTION_CONFLICT`, `CASCADING_DELAY`, `DELAY_RISK`.
- Every conflict binds a stable ID, affected trains, resources, time window, severity, explicit kinematic evidence, and linked constraint ID (`HC-001` through `HC-013`).
- Single-event canonicalization: multiple operational interpretations (e.g. single-line crossing is also a headway event) are grouped into `related_types` to eliminate duplicate conflict alerts.
- **Verification Evidence:** `test_conflicts.py` (5 tests), `test_v2_features.py` (conflict taxonomy tests).

### Upgrade 3: CP-SAT Optimization
- Implemented in `backend/app/domain/optimizer.py`.
- Models interval scheduling, block exclusivity (`AddNoOverlap`), headway spacing, platform capacity (`AddCumulative`), and junction throats (`AddCumulative`).
- Objective weights configurable across 4 profiles (`balanced`, `delay_focused`, `priority_focused`, `throughput_focused`).
- Solves accurately return `OPTIMAL`, `FEASIBLE`, or `INFEASIBLE`. Both `objective_value` and proven `objective_bound` are recorded.
- Supports alternative generation via `optimise_alternatives()`.
- **Verification Evidence:** `test_optimizer.py` (5 tests), `test_cpsat_reports_accurate_status_and_objective_fields`, `test_cpsat_alternative_profiles_are_reported_separately`.

### Upgrade 4: PPO Candidate Ranker
- Implemented in `backend/app/domain/ppo.py` and `backend/ml/train_ppo.py`.
- Evaluated on 6 held-out scenarios across 4 fixed seeds (`5000, 5001, 5002, 5003`).
- Strictly ranks pre-validated candidates; zero violation attempts.
- Baseline checkpoint `backend/ml/artifacts/ppo_policy.pt` protected.
- Preserves model disagreement and logs it explicitly.
- **Verification Evidence:** `test_ppo.py` (5 tests), `backend/ml/reports/v2_ppo_candidate_comparison.json`.

### Upgrade 5: Recommendation Intelligence & Provenance
- Implemented in `backend/app/domain/pipeline.py`.
- Every recommendation outputs recommendation ID, state version, timestamp, affected trains/blocks/sections/stations, conflict evidence, proposed action, alternatives, predicted delay/throughput/occupancy impacts, validation report, solver status, PPO evidence, uncertainty declarations, and calculated/predicted/assumed value tags.
- **Zero Fabricated Confidence:** `uncertainty.confidence_percentage` is explicitly `null`. Policy probabilities are declared as heuristic sampling scores.
- **Verification Evidence:** `test_recommendation.py` (9 tests), `test_recommendation_contains_provenance_and_honest_uncertainty`, `test_no_confidence_percentage_is_fabricated_anywhere`.

### Upgrade 6: Human-in-Control Workflow
- Implemented in `backend/app/routers/recommendations.py` and `backend/app/services/decision_service.py`.
- Non-negotiable principle: AI recommends, validator verifies, human decides, audit records.
- Approval requires `confirm_apply: true` and meaningful rationale (min 5 chars).
- Actions supported: `APPROVE`, `MODIFY`, `REJECT`, `DEFER`, `REQUEST_ALTERNATIVES`.
- Recommendations stored separately from human decisions. Re-validates state before applying.
- **Verification Evidence:** `test_api_decisions.py` (15 tests).

### Upgrade 7: Scenario Benchmark Framework
- Implemented in `backend/app/domain/scenarios.py` and `backend/ml/benchmark.py`.
- 14 deterministic scenarios reproducible by `(scenario_key, seed)`.
- **Verification Evidence:** `backend/ml/reports/v2_scenario.json`, `test_scenarios_endpoint`.

### Upgrade 8: Security & Scalability
- Implemented in `backend/app/config.py`, `app/main.py`, `app/routers/auth.py`, `app/services/audit.py`, and `app/db.py`.
- Login rate limiting (10 req/min).
- HTTP security headers (`nosniff`, `DENY`, `no-referrer`, `no-store`).
- Production boot assertion: blocks startup if defaults or SQLite are active in production.
- Audit integrity: append-only triggers plus `AuditChainHead` table to prevent tail truncation.
- PostgreSQL schema compatibility verified.
- **Verification Evidence:** `test_security.py` (9 tests), `test_api_audit.py` (4 tests), `test_production_configuration_rejects_default_secret_and_demo_credentials`.

### Upgrade 9: Testing & Verification
- 186 backend pytest tests passing in 3.36s.
- 26 frontend vitest tests passing in 2.13s.
- Clean TypeScript compilation and Vite production build.
- Full E2E matrix execution across all 14 scenarios.

---

## 4. API End-to-End 14-Scenario Matrix

Executed against a live API session logged in as `section.master`:

| Scenario | Evidence Status | CP-SAT Status | Eligible / Total | Action Decision | Recommended Source | Result |
|---|---|---|---:|---|---|---|
| `block_closure` | `VALIDATED` | `OPTIMAL` | 1 / 8 | APPROVE | `CP_SAT` | **200 APPLIED** |
| `cascading_delay` | `MODEL_DISAGREEMENT` | `OPTIMAL` | 8 / 8 | APPROVE | `HEURISTIC` | **200 APPLIED** |
| `delayed_express` | `MODEL_DISAGREEMENT` | `OPTIMAL` | 7 / 7 | APPROVE | `CP_SAT` | **200 APPLIED** |
| `disruption_recovery` | `VALIDATED` | `OPTIMAL` | 1 / 11 | APPROVE | `CP_SAT` | **200 APPLIED** |
| `double_line_overtaking`| `MODEL_DISAGREEMENT`| `OPTIMAL` | 11 / 11 | APPROVE | `CP_SAT` | **200 APPLIED** |
| `evening_peak` | `MODEL_DISAGREEMENT` | `OPTIMAL` | 12 / 12 | APPROVE | `CP_SAT` | **200 APPLIED** |
| `junction_congestion` | `MODEL_DISAGREEMENT` | `OPTIMAL` | 11 / 11 | APPROVE | `CP_SAT` | **200 APPLIED** |
| `maintenance_window` | `MODEL_DISAGREEMENT` | `OPTIMAL` | 11 / 11 | APPROVE | `CP_SAT` | **200 APPLIED** |
| `no_feasible_schedule` | `NO_FEASIBLE_SOLUTION`| `INFEASIBLE` | 0 / 7 | APPROVE | `NONE` | **409 REFUSED** |
| `normal_traffic` | `MODEL_DISAGREEMENT` | `OPTIMAL` | 12 / 12 | APPROVE | `HEURISTIC` | **200 APPLIED** |
| `platform_outage` | `MODEL_DISAGREEMENT` | `OPTIMAL` | 8 / 8 | APPROVE | `CP_SAT` | **200 APPLIED** |
| `priority_train` | `MODEL_DISAGREEMENT` | `OPTIMAL` | 7 / 7 | APPROVE | `CP_SAT` | **200 APPLIED** |
| `single_line_meet` | `MODEL_DISAGREEMENT` | `OPTIMAL` | 4 / 4 | APPROVE | `BASELINE` | **200 APPLIED** |
| `time_varying_demand` | `MODEL_DISAGREEMENT` | `OPTIMAL` | 11 / 11 | APPROVE | `CP_SAT` | **200 APPLIED** |

- **Audit Chain Verification:** `valid: True`, `events: 60`, `head_hash: 9338ff02b6c12b79...`.

---

## 5. Scope, Boundary and Known Limitations

1. **Simulation-Only Scope:** RAILGORITHM 2.0 is purely a simulation and human decision-support testbed. It is not connected to real Indian Railways signalling, interlocking or train management systems.
2. **Synthetic Data Disclaimer:** Timetables, topologies, train kinematics, and conflict models are synthetic representations. They do not constitute a validated digital twin of any physical railway network.
3. **PPO Role:** The neural policy is a ranking heuristic over pre-validated options; it does not guarantee global optimality or replace human cognitive assessment.
4. **CP-SAT Horizon:** Solves are bounded by configurable time limits (default 8s). While proven optimal for 13 of 14 synthetic scenarios, extreme combinatorial scenarios under tight limits may return feasible suboptimal or unknown statuses.
