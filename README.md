# RAILGORITHM

AI-assisted railway traffic management and **human decision support** on a deterministic, synthetic network. The system simulates train movements, detects projected conflicts, generates candidate control actions, checks feasibility with CP-SAT, independently validates every candidate, ranks them with a trained PPO policy, explains the evidence, and then **waits for an authorised human controller to decide**.

> **Synthetic data only.** This is not connected to Indian Railways or any live signalling, interlocking or control system. It is not a validated digital twin. Every screen, API response and report labels the data as synthetic.

---

## Why this exists

Section controllers make safety-critical sequencing decisions under time pressure. Software can help by measuring options, but it must not pretend to be authoritative. RAILGORITHM is built around three rules:

1. **The human decides.** No recommendation is applied automatically. Approval requires an explicit confirmation flag plus a written rationale.
2. **Validation is independent of AI.** CP-SAT and PPO cannot make an invalid action executable. A separate constraint validator checks topology, occupancy, headway, closures, platform availability and hold policy.
3. **The system admits uncertainty.** Infeasibility, model disagreement, stale advice and untrained components are surfaced explicitly. Nothing is fabricated.

---

## Screens

| Screen | Purpose |
| --- | --- |
| **Login** | Demo role sign-in with clear synthetic-data disclaimer. |
| **Dashboard** | Section overview, KPIs, conflicts, delayed trains, infrastructure status, model status, pending decisions. |
| **Train Movements** | Searchable/sortable train list with location, schedule, delay, hold reason and route. |
| **Railway Network** | Schematic of the four-section network, live block occupancy, platform status, closures and outages. |
| **Conflict Detection** | Filterable projected conflicts with severity, evidence and station-scope filtering. |
| **AI Recommendations** | Decision queue plus a detail view: validated candidate, measured outcome, alternatives, PPO ranking, CP-SAT status, comparison table and the ten-question explanation. |
| **Disruption Management** | Inject block/section closures, platform outages, train delays and priority overrides. Section Master only. |
| **What-if Simulation** | Run a hypothetical action on a cloned simulation and compare baseline vs hypothetical KPIs and conflicts. Never applied live. |
| **Analytics** | Measured KPIs, section/platform utilisation, train delays, human decision statistics and the latest recommendation comparison. |
| **Audit Trail** | Append-only hash-chained event log with live integrity verification. Section Master only. |

Role-based navigation is enforced server-side as well as in the UI.

---

## Architecture

```
React 19 + Vite + TypeScript
        │  REST /api/v1 (JWT bearer)
        ▼
FastAPI (Python 3.14)
  ├── routers        auth · scenarios · simulations · recommendations · audit · models
  ├── services       simulation lifecycle · recommendation persistence · human decisions · audit · analytics
  └── domain
        ├── network.py         synthetic topology (NDL–KRN–MLG–SRP–VSN)
        ├── scenarios.py       8 deterministic scenario definitions
        ├── state.py           simulation engine, actions, metrics
        ├── projection.py      future occupancy projection
        ├── conflicts.py       headway / single-line / platform conflict detection
        ├── candidates.py      candidate generation + deterministic baseline ranking
        ├── optimizer.py       OR-Tools CP-SAT feasibility and objective
        ├── validator.py       independent hard-constraint validation + candidate outcome evaluation
        ├── ppo.py             PyTorch policy network, features, inference
        ├── pipeline.py        hybrid orchestration, eligibility, disagreement, comparison
        └── explanation.py     evidence-based explanation text
        │
        ▼
SQLite: users · simulations · recommendations · decisions · audit_events · model_versions
```

### Recommendation pipeline

```
simulation state
   → conflict detection
   → candidate actions (do nothing, holds, precedence, platform reassignment, CP-SAT schedule)
   → CP-SAT feasibility solve
   → independent validation of every action and its cloned 75-minute outcome
     (conflicts are projected from the current time, including the closure window)
   → PPO ranking of validated candidates
   → deterministic selection by measured weighted delay + residual-conflict penalty
   → explanation with evidence and limitations
   → human APPROVE / MODIFY / REJECT / DEFER / REQUEST_ALTERNATIVES
   → re-validation, simulated application, append-only decision + audit record
```

Eligibility is decided by validation, not by ranking. A candidate with unresolved **CRITICAL** conflicts in the full post-action projection horizon is ineligible, even if the conflict would fall outside a shorter measurement window. Residual non-critical conflicts are reported as warnings. If no candidate is eligible, the API returns `NO_FEASIBLE_SOLUTION` and `recommended: null` — it does not invent an action.

### Decision rules

- **Section Master** has full section authority.
- **Station Master** is scoped to station `MLG`; recommendations whose affected stations fall outside that scope cannot be read or decided by them.
- A recommendation is **stale** when the simulation's `state_version` has advanced since generation. Stale advice cannot be approved.
- `disagreement` means the **PPO top choice and the CP-SAT candidate differ**. The selected candidate is still chosen by measured outcome; the disagreement is displayed, never silently resolved.
- Approvals and modifications require `confirm_apply: true`, a rationale of at least five characters, and a successful server-side re-validation.
- Execution mode is always `SIMULATED_ONLY`.

---

## Quick start

Requirements: Python 3.12+ (developed on 3.14), Node.js 20+ (developed on 26), npm.

```bash
# 1. Python environment
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

# 2. Run the API (creates and seeds the SQLite DB on startup)
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --port 8000

# 3. In another terminal: run the UI in dev mode
cd frontend
npm install
npm run dev          # http://localhost:5173, proxies /api to :8000
```

Or build the UI once and let FastAPI serve it:

```bash
cd frontend && npm install && npm run build
cd .. && PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --port 8000
# http://127.0.0.1:8000
```

### Demo accounts

| Role | Username | Password | Scope |
| --- | --- | --- | --- |
| Section Master | `section.master` | `Section@123` | Whole synthetic section |
| Station Master | `station.master` | `Station@123` | Station `MLG` |

These are demo credentials. Change the JWT secret and replace the seeded users before any shared deployment.

### Configuration

| Variable | Default | Meaning |
| --- | --- | --- |
| `RAILGORITHM_DATABASE_URL` | `sqlite:///backend/railgorithm.db` | SQLAlchemy database URL |
| `RAILGORITHM_JWT_SECRET` | development default | **Override in any shared environment** |
| `RAILGORITHM_JWT_TTL_MINUTES` | `480` | Token lifetime |
| `RAILGORITHM_CORS_ORIGINS` | localhost:5173 | Comma-separated allowed origins |
| `RAILGORITHM_CP_SAT_TIME_LIMIT` | `8` | CP-SAT solve limit (seconds) |
| `RAILGORITHM_CP_SAT_WORKERS` | `1` | CP-SAT worker count (deterministic default) |
| `RAILGORITHM_RECOMMENDATION_HORIZON` | `75` | Conflict projection horizon (minutes) |
| `RAILGORITHM_DECISION_APPLY_MINUTES` | `30` | Post-approval simulated evaluation window |
| `RAILGORITHM_SEED_DEMO` | `true` | Seed users, model registry and a demo simulation |
| `RAILGORITHM_ARTIFACT_DIR` | `backend/ml/artifacts` | PPO artifact location |

---

## Synthetic network and scenarios

Four sections, five stations, one junction:

- `NDL–KRN` — single line
- `KRN–MLG` — double line
- `MLG–SRP` — single line (the main bottleneck)
- `SRP–VSN` — double line
- `MLG` — junction station

Scenarios are deterministic given `(scenario_key, seed)`:

`normal_traffic`, `evening_peak`, `single_line_meet`, `delayed_express`, `block_closure`, `platform_outage`, `priority_train`, `no_feasible_schedule`.

`no_feasible_schedule` deliberately makes CP-SAT infeasible so the system can demonstrate honest infeasibility reporting.

---

## Algorithms and honest status

| Component | What it is | Status |
| --- | --- | --- |
| **Simulation** | Deterministic discrete-event-ish engine over a synthetic timetable; reproducible by seed. | Implemented, tested |
| **Conflict detection** | Projected block/platform contention, headway and single-line crossing checks. | Implemented, tested |
| **CP-SAT** | OR-Tools feasibility/optimisation over train intervals, holds, headway, closures and platforms. | Implemented, tested; **not a trained model** |
| **Validator** | Independent hard-constraint checks and cloned-outcome evaluation. | Implemented, tested |
| **PPO** | PyTorch actor-critic that ranks pre-validated candidates. | Trained on synthetic data; artifacts included |
| **Selection** | Lowest measured weighted delay + residual-conflict penalty among eligible candidates. | Implemented, tested |

### PPO: what was actually trained

The policy is a real PPO implementation (clipped surrogate objective, value head, entropy bonus, gradient clipping) over **pre-validated candidate sets**. It cannot create actions and cannot override the validator.

Recorded in `backend/ml/artifacts/ppo_metrics.json`:

- 24 iterations × 32 episodes = 768 episodes, 2,824 transitions, 100.8 s training
- 102 evaluation decisions over 4 held-out seeds, 7 scenario families
- Top-1 match with the measured best candidate: **55.88%**
- Mean regret vs measured best: **19.51** (baseline heuristic: **21.42**; CP-SAT-only subset: **31.21**)
- Mean policy total delay: **103.98 min**; mean residual conflicts: **4.61**

These are measured on synthetic simulations. They are **not** a claim of operational readiness, and the evaluation shares scenario families with training. See `VERIFICATION.md` for the full report and limitations.

---

## API overview

All endpoints are under `/api/v1`; except for login and health, they require `Authorization: Bearer <token>`.

| Method | Path | Roles | Purpose |
| --- | --- | --- | --- |
| `POST` | `/auth/login` | public | Obtain JWT |
| `GET` | `/auth/me` | any | Current user |
| `GET` | `/scenarios` | any | Scenario catalogue |
| `GET` | `/simulations` | any | List simulations |
| `POST` | `/simulations` | Section Master | Create a simulation |
| `GET` | `/simulations/{id}` | any | Full simulation view |
| `GET` | `/simulations/{id}/dashboard` | any | Scoped dashboard |
| `GET` | `/simulations/{id}/trains` | any | Train movements |
| `GET` | `/simulations/{id}/network` | any | Topology, occupancy, platforms |
| `GET` | `/simulations/{id}/conflicts` | any | Scoped conflicts |
| `POST` | `/simulations/{id}/advance` | Section Master | Advance simulated clock |
| `POST` | `/simulations/{id}/pause` | Section Master | Pause/resume |
| `POST` | `/simulations/{id}/reset` | Section Master | Reset to initial state |
| `POST` | `/simulations/{id}/disruptions` | Section Master | Inject a disruption |
| `POST` | `/simulations/{id}/what-if` | any | Cloned hypothetical comparison |
| `GET` | `/simulations/{id}/analytics` | any | Measured KPIs and decision stats |
| `POST` | `/simulations/{id}/recommendations` | any | Generate advice |
| `GET` | `/simulations/{id}/recommendations` | any | List advice |
| `GET` | `/recommendations/{id}` | scoped | Recommendation detail |
| `POST` | `/recommendations/{id}/decision` | scoped | Record a human decision |
| `GET` | `/audit` | Section Master | Audit events + verification |
| `GET` | `/audit/verify` | Section Master | Hash-chain verification |
| `GET` | `/models` | any | Model registry with honest status |
| `GET` | `/health` | public | Health and safety flags |

---

## Testing

Backend (141 tests):

```bash
cd backend
../.venv/bin/python -m pytest tests -q
```

Frontend (25 tests, TypeScript typecheck + production build):

```bash
cd frontend
npx vitest run
npx tsc --noEmit
npm run build
```

The backend suite covers security, network topology, scenarios, simulation, conflict detection, validation, CP-SAT, candidate ranking, the hybrid pipeline, PPO feature/inference behaviour, database schema/triggers, auth, RBAC/station scope, decisions, staleness, audit integrity and analytics. The frontend suite covers formatting, the API client, UI primitives, login and role-based navigation.

A manual browser smoke test was also performed against the built app: login, dashboard, trains, network, conflicts, recommendation generation, approval with confirmation, audit verification, Station Master navigation/RBAC, what-if simulation and a disruption injection (including a correctly refused closure of an occupied section). See `VERIFICATION.md` for exact results.

---

## Project layout

```
backend/
  app/
    domain/        simulation, topology, scenarios, conflicts, CP-SAT, validator, PPO, pipeline
    routers/       HTTP API
    services/      persistence, decisions, audit, analytics, seeding
    main.py        FastAPI app, lifespan, static frontend mount
  ml/
    train_ppo.py   real PPO training/evaluation
    artifacts/     ppo_policy.pt, ppo_metrics.json
  tests/           pytest suite
frontend/
  src/
    pages/         Dashboard, Trains, Network, Conflicts, Recommendations, Disruptions, WhatIf, Analytics, Audit, Login
    components/    Shell, UI primitives, new-simulation dialog
    lib/           formatting, async hook
    api.ts         typed API client
  dist/            production build served by FastAPI
```

---

## Safety, scope and known limitations

- **Not for operational use.** Synthetic data, synthetic timetable, simplified signalling.
- **No live integration.** There is no interface to interlocking, train control, or any railway system.
- **Simplified model.** The simulator is not a validated digital twin; constraint checks use configured assumptions, not verified signalling rules.
- **PPO is a research component.** It ranks validated candidates only; its scores are sampling scores, not calibrated confidence. Its measured ranking quality is modest and is reported honestly.
- **CP-SAT has a time limit.** It can return `INFEASIBLE`, `UNKNOWN` or a time-limited feasible schedule; infeasibility is surfaced rather than hidden.
- **SQLite single-node storage.** Suitable for a prototype, not for multi-user production concurrency.
- **Demo credentials and default JWT secret.** Must be replaced before any shared deployment.
- **Audit integrity is tamper-evident, not tamper-proof.** Database triggers block UPDATE/DELETE and the hash chain detects edits, but an attacker with full filesystem control could replace the database.

See `VERIFICATION.md` for the implementation/test matrix, measured results and remaining risks.
