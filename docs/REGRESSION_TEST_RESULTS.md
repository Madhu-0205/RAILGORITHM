# RAILGORITHM 2.0 — Regression Test Results

**Date of Execution:** 25 November 2026  
**Environment:** Python 3.14.7, pytest 9.2.0, Node.js 26.3.0, Vitest 4.1.12, TypeScript 5.x, Vite 7.3.8  
**Total Automated Tests:** 212 tests (186 Backend + 26 Frontend)  
**Overall Verdict:** 100% PASSED — Zero Test Failures, Zero TypeScript Errors, Clean Production Build  

---

## 1. Test Suite Summary

| Test Domain | Framework | Files | Test Count | Result | Execution Time |
|---|---|---:|---:|---|---:|
| **Backend Suite** | `pytest` | 18 | 186 | **186 Passed** (1 warning) | 3.36 s |
| **Frontend Suite** | `vitest` | 6 | 26 | **26 Passed** | 2.13 s |
| **TypeScript Typecheck** | `tsc --noEmit` | — | — | **0 Errors** | ~0.7 s |
| **Production Build** | `vite build` | 61 modules | — | **Success** (348.6 kB gzip: 103.1 kB) | 0.81 s |
| **API End-to-End Matrix** | `TestClient` | 14 scenarios | 14 | **13 Applied, 1 Refused** | ~1.4 s |
| **Audit Verification** | SHA-256 Chain | — | 60 events | **Chain Valid, Head Valid** | < 10 ms |

---

## 2. Backend Test Breakdown (186 Tests)

| Test Module | Tests | Primary Scope Tested |
|---|---:|---|
| `test_v2_features.py` | 27 | Assumption/constraint manifests, v2 conflict taxonomy, overtaking, CP-SAT objective profiles, provenance, production guardrails, PostgreSQL portability, system endpoints. |
| `test_api_decisions.py` | 15 | Human decision lifecycle: approve, modify, reject, defer, request alternatives, staleness checks, scope gates, confirmation validation. |
| `test_api_simulations.py`| 15 | Simulation lifecycle: create, advance, pause, reset, what-if branching, disruption injection. |
| `test_scenarios.py` | 14 | Deterministic initialization and integrity across all scenario configurations. |
| `test_simulation.py` | 14 | Discrete-event step engine, speed factors, dwell logic, block progression. |
| `test_validator.py` | 11 | Independent constraint validator: block exclusivity, headway, closures, hold policy limits. |
| `test_api_rbac.py` | 9 | Role-based permissions, Station Master MLG scope constraints, anonymous access refusal. |
| `test_api_auth.py` | 8 | JWT issuance, password verification, login rate limiting, security headers, health endpoint. |
| `test_recommendation.py` | 9 | Hybrid pipeline candidate generation, CP-SAT integration, outcome evaluation, 10-point explanation. |
| `test_security.py` | 9 | Token tampering, invalid signatures, brute-force protection. |
| `test_network.py` | 7 | Synthetic topology graph, section connectivity, block mappings, throat capacities. |
| `test_conflicts.py` | 5 | Headway violations, single-line crossing conflicts, platform capacity overflows. |
| `test_optimizer.py` | 5 | CP-SAT model building, interval scheduling, cumulative platform and throat constraints. |
| `test_ppo.py` | 5 | Feature construction, policy inference, pre-validated candidate ranking. |
| `test_db.py` | 5 | SQLAlchemy models, relational foreign keys, SQLite immutability triggers. |
| `test_api_audit.py` | 4 | Append-only hash chain, tamper detection, tail truncation detection via chain head. |
| `test_api_analytics.py` | 4 | Real-time simulation KPIs, decision metrics, synthetic data labeling. |
| `test_api_models.py` | 2 | Scenarios catalog, model registry status reporting. |
| **Total** | **186** | |

---

## 3. Frontend Test Breakdown (26 Tests)

| Test Module | Tests | Primary Scope Tested |
|---|---:|---|
| `src/lib/format.test.ts` | 7 | Date, time, minute formatting, delay displays, badge styling. |
| `src/components/ui.test.tsx` | 5 | UI primitives: Button, Badge, Panel, Modal, Spinner, ErrorBanner. |
| `src/api.test.ts` | 5 | Bearer token injection, error handling, assumptions/constraints API client methods. |
| `src/components/Shell.test.tsx`| 4 | Section Master navigation (including Assumptions & Constraints link), Station Master scope banner, RBAC link visibility. |
| `src/pages/Login.test.tsx` | 4 | Login form validation, error message rendering, demo account selector. |
| `src/pages/Specifications.test.tsx`| 1 | Assumptions, constraints, version register, and override documentation rendering. |
| **Total** | **26** | |

---

## 4. Specific Regression Defect Protections

### Defect 1: Pre-Advance Conflict Window Coverage
- **Description:** Previously, candidate outcome evaluation projected conflicts only *after* advancing the simulation clock by the planning horizon, occasionally missing immediate block closures starting at the decision minute.
- **Protection:** `evaluate_candidate` in `validator.py` projects conflicts directly from the pre-advanced action state across the full horizon.
- **Regression Test:** `test_candidate_conflicts_cover_the_window_before_advancing`.

### Defect 2: Audit Tail Truncation Vulnerability
- **Description:** Standard hash chains verify that $H_k = \text{hash}(H_{k-1}, E_k)$, but an attacker with database access could delete events from the end of the table ($k \dots N$), leaving a shorter valid chain.
- **Protection:** Added `AuditChainHead` table recording $H_{last}$ and total event count $N$, protected by `audit_chain_head_no_delete` trigger.
- **Regression Tests:** `test_audit_chain_detects_tail_truncation`, `test_audit_chain_head_cannot_be_deleted`.

### Defect 3: Stale Recommendation Approval
- **Description:** If traffic conditions or time advanced between generating a recommendation and controller review, approving stale advice could apply invalid holds.
- **Protection:** Recommendations bind the simulation `state_version`. If the simulation version advances, the decision gate rejects approval with HTTP 409.
- **Regression Test:** `test_stale_recommendation_cannot_be_approved`.

### Defect 4: Station Master Scope Leakage
- **Description:** Station Masters must only view and act on conflicts and recommendations within their assigned station territory.
- **Protection:** Server-side filtering in recommendations and decision routers rejects out-of-scope interactions with HTTP 403.
- **Regression Tests:** `test_station_master_cannot_read_out_of_scope_recommendation`, `test_station_master_conflicts_are_scope_filtered`.
