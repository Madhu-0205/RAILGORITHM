# RAILGORITHM 2.1 — Trustworthy Intelligence & Benchmark Validation

AI-assisted railway traffic management and **human decision support** on a deterministic, synthetic network. The system simulates train movements, detects projected conflicts, generates candidate control actions, checks feasibility with Google OR-Tools CP-SAT, independently validates every candidate against formal hard constraints, ranks them with a trained PPO policy, explains the evidence, and **waits for an authorised human controller to decide**.

> **Synthetic data only.** This is a simulation testbed and is not connected to Indian Railways or any live signalling, interlocking, or control system. It is not a validated digital twin. Every screen, API response and report labels the data as synthetic.

---

## What's New in Version 2.1

- **PPO Baseline Reconciliation:** Reconciled historical 55.88% in-distribution training figure with the 25.84% held-out baseline, explaining dataset partition mismatch and candidate simulation bugfixes.
- **8-Seed Multi-Seed Statistical Evaluation:** 178 decisions across held-out scenarios; Candidate V2 achieves **61.80% Top-1 match** ($\chi^2 = 46.74, p = 8.12 \times 10^{-12}$, statistically significant) and **86.2% residual conflict reduction** (1.39 vs 10.08); mean regret difference (15.258 vs 16.202) is honestly reported as not statistically significant ($p = 0.731$).
- **CP-SAT Objective & Constraint Audit:** Formally audited 4 objective profiles, verified decision variables and mathematical lower bounds, explained the 26 feasible benchmark solves in `v2_cpsat.json`, and added 8 adversarial solver stress tests.
- **Recommendation Disagreement Handling:** Formally audited 11 `MODEL_DISAGREEMENT` cases, verified dual-model visibility, trade-offs presentation, absence of auto-resolution, immutable human audit, and strict prohibition of uncalibrated confidence percentages.
- **Unseen Scenario Generalization Testing:** Evaluated 3 novel unseen scenarios (`gen_freight_convoy_surge`, `gen_cascading_junction_gridlock`, `gen_emergency_single_line_cross`) across 4 seeds; Candidate V2 achieves **41.67% Top-1 match** (vs Baseline 0.0%), **46.2% regret reduction** (24.50 vs 45.50), **90.4% residual conflict reduction** (1.04 vs 10.83), and **zero constraint violations**.
- **Adversarial Security & Audit Verification:** Verified SQLite triggers blocking `UPDATE` and `DELETE`, hash-chain tampering detection, tail truncation detection via `audit_chain_head`, head tampering detection, concurrent decision race condition handling (`[200, 409]`), RBAC station scoping, and stale recommendation rejection.
- **232 Automated Tests:** 206 backend tests (`pytest`) and 26 frontend tests (`vitest`) passing with 100% success rate, clean TypeScript compilation, and clean production build.

---

## Core Principles

1. **The human decides.** No recommendation is applied automatically. Approval requires explicit confirmation (`confirm_apply: true`) plus a written rationale (minimum 5 characters).
2. **Validation is independent of AI.** CP-SAT and PPO cannot make an invalid action executable. A separate hard-constraint validator checks topology, exclusivity, headway, closures, platform availability, hold policies, and junction throat capacities.
3. **The system admits uncertainty.** Infeasibility, model disagreement, stale advice, and candidate limitations are surfaced explicitly. Confidence percentages are never fabricated.

---

## Screens

| Screen | Purpose | Roles |
|---|---|---|
| **Login** | Role sign-in with clear synthetic-data disclaimer and rate limiting. | Public |
| **Dashboard** | Section overview, live KPIs, conflicts, delayed trains, infrastructure status, pending decisions. | All |
| **Train Movements** | Searchable/sortable train list with location, schedule, delay, category, and route. | All |
| **Railway Network** | Schematic of the four-section network, live block occupancy, platforms, throat capacity, closures. | All |
| **Conflict Detection** | Filterable projected conflicts with severity, evidence, constraint IDs, and station-scope filtering. | All |
| **AI Recommendations** | Decision queue and detail: validated candidate, measured outcome, alternatives, PPO ranking, CP-SAT status, and trade-offs. | All |
| **Disruption Management** | Inject block/section closures, platform outages, delays, and speed restrictions. | Section Master |
| **What-if Simulation** | Run hypothetical actions on cloned simulations to compare KPIs and conflicts. Never applied live. | All |
| **Analytics** | Measured KPIs, section/platform utilisation, delay statistics, and human decision records. | All |
| **Assumptions & Constraints** | Full register of 15 synthetic assumptions, 17 constraints, version register, and overrides. | All |
| **Audit Trail** | Append-only hash-chained event log with live cryptographic integrity and truncation verification. | Section Master |

---

## Architecture

```
React 19 + Vite + TypeScript
        │  REST /api/v1 (JWT bearer + Security Headers)
        ▼
FastAPI (Python 3.14)
  ├── routers        auth · scenarios · simulations · recommendations · audit · models · system
  ├── services       simulation lifecycle · recommendation persistence · human decisions · audit · analytics
  └── domain
        ├── spec.py            assumptions (15) and constraints (13 hard, 4 soft) manifest
        ├── network.py         synthetic topology (NDL–KRN–MLG–SRP–VSN, junction throats, gradients)
        ├── scenarios.py       14 deterministic scenario definitions + dynamic spec builder
        ├── state.py           simulation engine, actions, discrete-event progression
        ├── projection.py      future kinematic occupancy projection
        ├── conflicts.py       13-type conflict detection + deduplication
        ├── candidates.py      candidate generation + deterministic baseline ranking
        ├── optimizer.py       OR-Tools CP-SAT multi-profile scheduling & feasibility
        ├── validator.py       independent hard-constraint validation + outcome evaluation
        ├── ppo.py             PyTorch actor-critic policy network, features, inference
        ├── pipeline.py        hybrid orchestration, eligibility, disagreement, trade-offs
        └── explanation.py     evidence-based explanation text
        │
        ▼
Database: SQLite (development) / PostgreSQL (production-ready ORM schema)
```

---

## Quick Start

Requirements: Python 3.12+ (tested on Python 3.14), Node.js 20+ (tested on 26), npm.

```bash
# 1. Clone and enter repo
cd /Users/madhu/RAILGORITHM

# 2. Python environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt

# 3. Run the backend API
PYTHONPATH=backend python -m uvicorn app.main:app --port 8000

# 4. In another terminal: run the frontend
cd frontend
npm install
npm run dev          # http://localhost:5173
```

Or build the frontend once and let FastAPI serve it directly:

```bash
cd frontend && npm install && npm run build
cd .. && PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --port 8000
# http://127.0.0.1:8000
```

### Demo Accounts

| Role | Username | Password | Scope |
|---|---|---|---|
| Section Master | `section.master` | `Section@123` | Full synthetic network |
| Station Master | `station.master` | `Station@123` | Station `MLG` only |

---

## Verification and Testing

### Backend Test Suite (206 tests)

```bash
cd /Users/madhu/RAILGORITHM
PYTHONPATH=backend .venv/bin/pytest backend/tests -v
```
**Result:** `206 passed in 4.74s`

### Frontend Test Suite (26 tests) & Typecheck

```bash
cd /Users/madhu/RAILGORITHM/frontend
npx vitest run
npx tsc --noEmit
npm run build
```
**Result:** `26 passed in 2.13s`, TypeScript clean, build successful.

### Reproducible Benchmarks

```bash
# Run scenario, CP-SAT, and PPO benchmarks
PYTHONPATH=backend .venv/bin/python backend/ml/benchmark.py --all --label v2_1

# Run multi-seed unseen generalization benchmark
PYTHONPATH=backend .venv/bin/python backend/ml/run_generalization.py
```

---

## Documentation Index

- `VERIFICATION.md` — Complete Version 2.1 verification report and baseline comparison.
- `docs/PPO_BASELINE_RECONCILIATION.md` — Root cause analysis and reconciliation of historical baseline metrics.
- `docs/PPO_STATISTICAL_EVALUATION.md` — 8-seed statistical evaluation, bootstrap CIs, paired t-test, and Wilcoxon tests.
- `docs/CPSAT_OBJECTIVE_AND_CONSTRAINT_AUDIT.md` — Multi-objective CP-SAT formulation, bound verification, and adversarial stress tests.
- `docs/DISAGREEMENT_ANALYSIS_REPORT.md` — Audit of model disagreement cases, dual visibility, and zero auto-resolution.
- `docs/GENERALIZATION_TEST_REPORT.md` — Generalization and graceful degradation across novel unseen scenarios.
- `docs/SECURITY_AND_AUDIT_REPORT.md` — Threat model, database triggers, hash chaining, and adversarial penetration tests.
- `docs/REGRESSION_TEST_RESULTS.md` — Full automated regression test breakdown and defect fixes.
- `docs/RAILWAY_SIMULATION_ASSUMPTIONS.md` — Formal synthetic assumptions register.
- `docs/CONSTRAINT_SPECIFICATION.md` — Hard (HC-001..HC-013) and Soft (SC-001..SC-004) constraints.
- `docs/PPO_TRAINING_AND_EVALUATION.md` — Neural policy training, multi-seed evaluation, and promotion report.
- `docs/CPSAT_BENCHMARK_REPORT.md` — Multi-objective CP-SAT formulation and benchmark matrix.
- `docs/SCENARIO_BENCHMARK_RESULTS.md` — 14-scenario benchmark results and pipeline latencies.
- `docs/SECURITY_REVIEW.md` — Authentication, RBAC, audit hash chain, and PostgreSQL migration.
