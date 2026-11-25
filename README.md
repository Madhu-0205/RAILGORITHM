# RAILGORITHM 2.0

AI-assisted railway traffic management and **human decision support** on a deterministic, synthetic network. The system simulates train movements, detects projected conflicts, generates candidate control actions, checks feasibility with Google OR-Tools CP-SAT, independently validates every candidate against formal hard constraints, ranks them with a trained PPO policy, explains the evidence, and **waits for an authorised human controller to decide**.

> **Synthetic data only.** This is a simulation testbed and is not connected to Indian Railways or any live signalling, interlocking, or control system. It is not a validated digital twin. Every screen, API response and report labels the data as synthetic.

---

## What's New in Version 2.0

- **14 Deterministic Benchmark Scenarios:** Expanded from 8 to 14 scenarios, adding double-line overtaking, junction throat congestion, 4-hour engineering possessions, cascading delay propagation, multi-disruption recovery, and traffic surges.
- **13-Type Conflict Taxonomy:** Comprehensive detection of block exclusivity, headway, single-line crossing, route overlaps, overtaking, platform capacity, junction throat bottlenecks, block closures, maintenance restrictions, and cascading delay risks.
- **Configurable Multi-Profile CP-SAT:** Supports `balanced`, `delay_focused`, `priority_focused`, and `throughput_focused` objective profiles, reporting both solution value and proven lower bounds.
- **PPO Candidate Ranker Upgrades:** Multi-seed evaluation on 6 held-out scenario families demonstrating **61.8% Top-1 match** (up from 25.8% baseline) and **15.26 mean regret** (down from 16.20) with zero constraint violations. Baseline checkpoints preserved.
- **Assumptions & Constraint Specification:** 15 inspectable synthetic assumptions (`ASSUMPTIONS`) and 13 Hard + 4 Soft constraints (`CONSTRAINTS`) surfaced via API and a dedicated frontend screen.
- **Enhanced Audit Integrity:** SHA-256 hash chain with dedicated `AuditChainHead` table and database triggers to detect tail truncation attacks.
- **Security & PostgreSQL Migration Path:** Production boot assertions (`assert_safe_for_production`), login rate limiting, security headers, and PostgreSQL schema portability.
- **Expanded Test Coverage:** 186 backend pytest tests and 26 frontend vitest tests passing with 100% success rate.

---

## Core Principles

1. **The human decides.** No recommendation is applied automatically. Approval requires explicit confirmation (`confirm_apply: true`) plus a written rationale (minimum 5 characters).
2. **Validation is independent of AI.** CP-SAT and PPO cannot make an invalid action executable. A separate hard-constraint validator checks topology, exclusivity, headway, closures, platform availability, and hold policies.
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
        ├── scenarios.py       14 deterministic scenario definitions
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

### Backend Test Suite (186 tests)

```bash
cd /Users/madhu/RAILGORITHM
PYTHONPATH=backend .venv/bin/pytest backend/tests -v
```
**Result:** `186 passed in 3.36s`

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
PYTHONPATH=backend .venv/bin/python backend/ml/benchmark.py --all --label v2
```

---

## Documentation Index

- `VERIFICATION.md` — Complete Version 2.0 verification report and baseline comparison.
- `docs/RAILWAY_SIMULATION_ASSUMPTIONS.md` — Formal synthetic assumptions register.
- `docs/CONSTRAINT_SPECIFICATION.md` — Hard (HC-001..HC-013) and Soft (SC-001..SC-004) constraints.
- `docs/PPO_TRAINING_AND_EVALUATION.md` — Neural policy training, multi-seed evaluation, and promotion report.
- `docs/CPSAT_BENCHMARK_REPORT.md` — Multi-objective CP-SAT formulation and benchmark matrix.
- `docs/SCENARIO_BENCHMARK_RESULTS.md` — 14-scenario benchmark results and pipeline latencies.
- `docs/SECURITY_REVIEW.md` — Authentication, RBAC, audit hash chain, and PostgreSQL migration.
- `docs/REGRESSION_TEST_RESULTS.md` — Full automated regression test breakdown and defect fixes.
