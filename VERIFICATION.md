# RAILGORITHM — Verification Report

**Date:** 24 November 2026  
**Scope:** Greenfield prototype built in this workspace.  
**Data:** Synthetic only. No live railway system is connected.  
**Human control:** Every operational action requires an explicit human decision. Nothing executes automatically.

---

## 1. Verdict

The requested prototype is implemented and verified end to end:

- 8 required screens plus an Audit Trail screen.
- Deterministic synthetic simulation, conflict detection, candidate generation, CP-SAT, independent validation, PPO ranking, explanation, human decision and append-only audit.
- **141 backend tests passed** (`pytest`).
- **25 frontend tests passed** (`Vitest`, 5 files).
- TypeScript typecheck clean; production build succeeds.
- API-level end-to-end matrix over all 8 scenarios: 7 approvals applied to the synthetic simulation; the infeasible scenario correctly refused approval with HTTP 409.
- Browser smoke test passed for login, dashboard, recommendation generation, approval, audit verification and Station Master scope/RBAC.
- No fabricated feasible schedules, confidence percentages or test results.

This is **not** production-ready and must not be connected to real railway infrastructure. See limitations and risks in sections 8 and 9.

---

## 2. Implemented feature matrix

| Area | Requirement | Status | Evidence |
|---|---|---|---|
| Authentication | Demo login, signed tokens, expiry | Implemented | `test_api_auth.py` (8 tests), browser login |
| RBAC | Section Master and Station Master, server-enforced | Implemented | `test_api_rbac.py` (9), `test_api_decisions.py` scope tests, browser scope check |
| Station scope | Station Master limited to `MLG`; out-of-scope advice hidden/blocked | Implemented | API scope tests; conflicts page label “filtered to your station scope” |
| Simulation | Deterministic synthetic state, advance, pause/reset, events | Implemented | `test_simulation.py` (14), `test_scenarios.py` (14) |
| Network | 4 sections, single/double line, junction, blocks, platforms, headways | Implemented | `test_network.py` (7), Railway Network screen |
| Conflict detection | Block, headway, single-line crossing, platform, junction, closure, delay risk | Implemented | `test_conflicts.py` (5), Conflict Detection screen |
| CP-SAT | OR-Tools feasibility and schedule optimisation with holds, closures, platforms, headway | Implemented | `test_optimizer.py` (5); OPTIMAL schedules in 7 scenarios, INFEASIBLE in 1 |
| Independent validator | Separate hard-constraint checks; validates actions, schedules and cloned outcomes | Implemented | `test_validator.py` (11), `test_recommendation.py` (9) |
| Candidate generation | Do nothing, holds, precedence, platform reassignment, CP-SAT schedule | Implemented | `test_recommendation.py`, API alternatives |
| PPO | Real PyTorch PPO ranker over pre-validated candidates | Trained and loaded | `test_ppo.py` (5), `ppo_metrics.json`, health endpoint |
| Selection | Lowest measured weighted delay + residual-conflict penalty among eligible candidates | Implemented | `test_recommendation.py`, API matrix |
| Explanations | Ten required questions answered from measured evidence | Implemented | `test_recommendation.py`, recommendation detail screen |
| Human decisions | Approve, modify, reject, defer, request alternatives; explicit confirmation; re-validation | Implemented | `test_api_decisions.py` (15) |
| Staleness | State-version mismatch blocks approval | Implemented | `test_api_decisions.py` |
| Audit | Append-only hash chain, SQLite triggers, verification | Implemented | `test_api_audit.py` (4), `test_db.py` (5), Audit screen |
| Analytics | Simulation, conflict, decision and delay statistics | Implemented | `test_api_analytics.py` (4) |
| What-if | Clone-and-compare actions without touching live simulation | Implemented | `test_api_simulations.py` (15), What-if screen |
| Disruption management | Closure and platform-outage injection with validation | Implemented | API tests, browser/API smoke; occupied-block closure correctly refused |
| Model status | PPO/CP-SAT provenance exposed; no fake training claims | Implemented | Health endpoint, dashboard model panel |
| Documentation | Setup, architecture, API, algorithms, testing, limitations | Implemented | `README.md`, this report |

### Not implemented / out of scope

- Live railway, interlocking, signalling or train-control integration.
- Real Indian Railways data or a validated digital twin.
- Production identity provider/SSO, external secret management, horizontal scaling or HA.
- Certified safety case, formal verification or regulatory approval.
- Calibrated operational confidence for PPO scores.
- Mobile-native apps.

---

## 3. Test execution

### Environment

| Component | Version |
|---|---|
| Python | 3.14.7 |
| FastAPI | 0.165.0 |
| SQLAlchemy | 2.1.9 |
| OR-Tools | 9.15.6755 |
| PyTorch | 2.15.0 |
| Node.js | 26.3.0 |
| npm | 11.16.0 |
| Database | SQLite (single node) |

### Backend

```bash
cd /Users/madhu/RAILGORITHM/backend
../.venv/bin/python -m pytest tests -q
```

**Result:** `141 passed, 1 warning in 3.08s`

The single warning is a Starlette/httpx deprecation warning from the test client. It does not affect application behaviour.

| Test file | Tests |
|---|---:|
| `test_api_analytics.py` | 4 |
| `test_api_audit.py` | 4 |
| `test_api_auth.py` | 8 |
| `test_api_decisions.py` | 15 |
| `test_api_models.py` | 2 |
| `test_api_rbac.py` | 9 |
| `test_api_simulations.py` | 15 |
| `test_conflicts.py` | 5 |
| `test_db.py` | 5 |
| `test_network.py` | 7 |
| `test_optimizer.py` | 5 |
| `test_ppo.py` | 5 |
| `test_recommendation.py` | 9 |
| `test_scenarios.py` | 14 |
| `test_security.py` | 9 |
| `test_simulation.py` | 14 |
| `test_validator.py` | 11 |
| **Total** | **141** |

### Frontend

```bash
cd /Users/madhu/RAILGORITHM/frontend
npx vitest run
npx tsc --noEmit
npm run build
```

**Results:**

- `Test Files 5 passed (5)`, `Tests 25 passed (25)`, duration 2.90 s.
- TypeScript: no errors.
- Build: 60 modules transformed; `dist/assets/index-t6-jc9Fj.js` 342.88 kB (101.91 kB gzip); `dist/assets/index-qjioeM1L.css` 19.73 kB (4.82 kB gzip).

Test files: `src/api.test.ts`, `src/components/Shell.test.tsx`, `src/components/ui.test.tsx`, `src/lib/format.test.ts`, `src/pages/Login.test.tsx`.

---

## 4. API end-to-end scenario matrix

Executed against a fresh SQLite database with a live `uvicorn` server and the real HTTP API, logged in as `section.master`. For each scenario: create simulation → advance 5 minutes → generate recommendation → approve with `confirm_apply: true` and a rationale.

| Scenario | Evidence | CP-SAT | Schedule validation | Recommended | Source | Residual critical | Eligible | Decision |
|---|---|---|---|---|---|---:|---:|---|
| `normal_traffic` | MODEL_DISAGREEMENT | OPTIMAL | VALIDATED_WITH_ASSUMPTIONS | Hold FRT-701 at VSN for 10 min | HEURISTIC | 0 | 12/12 | **200 applied** |
| `evening_peak` | MODEL_DISAGREEMENT | OPTIMAL | VALIDATED_WITH_ASSUMPTIONS | Apply validated CP-SAT schedule | CP_SAT | 0 | 12/12 | **200 applied** |
| `single_line_meet` | MODEL_DISAGREEMENT | OPTIMAL | VALIDATED | Continue without intervention | BASELINE | 0 | 4/4 | **200 applied** |
| `delayed_express` | MODEL_DISAGREEMENT | OPTIMAL | VALIDATED_WITH_ASSUMPTIONS | Apply validated CP-SAT schedule | CP_SAT | 0 | 7/7 | **200 applied** |
| `block_closure` | VALIDATED | OPTIMAL | VALIDATED_WITH_ASSUMPTIONS | Apply validated CP-SAT schedule | CP_SAT | 0 | 1/8 | **200 applied** |
| `platform_outage` | MODEL_DISAGREEMENT | OPTIMAL | VALIDATED | Apply validated CP-SAT schedule | CP_SAT | 0 | 8/8 | **200 applied** |
| `priority_train` | MODEL_DISAGREEMENT | OPTIMAL | VALIDATED_WITH_ASSUMPTIONS | Apply validated CP-SAT schedule | CP_SAT | 0 | 7/7 | **200 applied** |
| `no_feasible_schedule` | NO_FEASIBLE_SOLUTION | INFEASIBLE | NO_FEASIBLE_SOLUTION | *none* | — | — | 0/7 | **409 refused** |

Notes:

- `MODEL_DISAGREEMENT` means the PPO top choice and the CP-SAT candidate differ. The recommendation is still selected by measured outcome; the disagreement is displayed separately and never silently resolved.
- In `block_closure`, 7 of 8 candidates were ineligible because they left an unresolved critical closure conflict. The validated CP-SAT schedule was the only executable option.
- In `no_feasible_schedule`, the API returned `recommended: null` and the decision endpoint refused approval with “The system will not fabricate an executable action.”
- Every applied decision advanced the synthetic simulation and wrote a decision and audit record. No real system was touched.

---

## 5. Defect found during final verification (fixed)

The final end-to-end check initially exposed a real inconsistency:

1. Candidate outcomes were measured by advancing a clone and *then* detecting conflicts only in the window after that advance. With the default 75-minute evaluation, the conflict check covered minutes 75–95 and skipped the current closure window (06:05–07:15).
2. As a result, `block_closure` briefly marked **Continue without intervention** as eligible, selected it on weighted delay, and then the decision endpoint correctly refused approval with HTTP 422 because re-validation found critical closure conflicts.
3. The refusal was safe, but the recommendation was presented as executable when it was not.

Fix:

- `evaluate_candidate` now projects post-action conflicts **from the post-action state, before advancing**, over the full recommendation horizon.
- The decision service uses the same `post_conflicts` evidence and horizon for its approval gate.
- The 75-minute planning horizon and 30-minute application horizon are now explicit and consistent: conflicts anywhere in the planning horizon make a candidate ineligible.

Regression tests added (raising the backend suite from 138 to 141):

- `test_candidate_conflicts_cover_the_window_before_advancing`
- `test_block_closure_rejects_do_nothing_at_the_full_decision_horizon`
- `test_approval_of_a_block_closure_schedule_matches_recommendation_evidence`

After the fix, `block_closure` selects the validated CP-SAT schedule at both 30-minute and 75-minute evaluation horizons, and the API approval succeeds.

---

## 6. PPO status and measured results

Artifacts:

- `backend/ml/artifacts/ppo_policy.pt`
- `backend/ml/artifacts/ppo_metrics.json`

The policy is a real PyTorch PPO implementation (clipped surrogate objective, value head, entropy bonus, gradient clipping) over pre-validated candidate sets. It cannot create actions, override the validator or execute anything.

| Metric | Measured value |
|---|---|
| Model version | `ppo-candidate-ranker-1.0.0` |
| Training | 24 iterations × 32 episodes = 768 episodes |
| Transitions | 2,824 |
| Training time | 100.8 s |
| Evaluation decisions | 102 (8 skipped) |
| Evaluation seeds | 4 held-out seeds |
| Scenario families | 7 (the infeasible scenario is not used for ranking) |
| Top-1 match with measured best | 55.88% |
| Mean regret vs measured best | 19.51 |
| Baseline heuristic mean regret | 21.42 |
| CP-SAT-only subset mean regret | 31.21 |
| Mean policy total delay | 103.98 min |
| Mean residual conflicts | 4.61 |

Interpretation:

- Scores are weighted delay plus residual-conflict penalty; **lower is better**.
- The policy beats the baseline heuristic on mean regret by a modest margin (19.51 vs 21.42) and matches the measured best in 55.88% of evaluated decisions.
- CP-SAT-only selection has higher regret on the subset where a CP-SAT candidate exists (31.21), so “always use the optimizer schedule” is not supported by this evaluation.
- The CP-SAT mean score field covers only states with a CP-SAT candidate and is not directly comparable with the all-state policy/baseline means; regret is the comparable metric.
- Evaluation uses the same scenario families as training with different seeds. It measures stability, not out-of-distribution generalisation.
- PPO scores are sampling scores, not calibrated confidence percentages. The UI says so.

No retraining was performed after the final verification. Only explanatory metric text was corrected (the earlier note incorrectly said higher scores were better). The measured numbers above are the original training/evaluation values.

---

## 7. Data and modelling assumptions

- All data is synthetic and labelled `SYNTHETIC — NOT REAL INDIAN RAILWAYS DATA`.
- Network: NDL–KRN (single line), KRN–MLG (double line), MLG–SRP (single line), SRP–VSN (double line); MLG is the junction.
- Scenarios are deterministic given `(scenario_key, seed)`.
- Train types have configured priorities, dwell times, maximum holds and run times.
- Conflicts and constraints are evaluated against configured simulation assumptions, not verified signalling rules.
- Recommendation planning horizon: 75 minutes by default (`RAILGORITHM_RECOMMENDATION_HORIZON`).
- Decision application horizon: 30 minutes by default (`RAILGORITHM_DECISION_APPLY_MINUTES`).
- Candidate outcomes are measured on cloned simulations, not real trains.
- SQLite is single-node storage suitable for a prototype.
- Time zone label is Asia/Kolkata (IST); all scenario times are simulated clock times.

---

## 8. Known limitations

- **Not operationally safe.** The simulator is not a validated digital twin; simplified signalling, topology, timings and constraints.
- **No live integration.** There is no interface to interlocking, train control or any railway system.
- **CP-SAT is time-limited.** It can return `INFEASIBLE`, `UNKNOWN` or a time-limited feasible schedule. Infeasibility is surfaced, not hidden.
- **PPO quality is modest.** 55.88% top-1 match and mean regret 19.51 are research results on synthetic scenarios, not operational evidence.
- **Scenario coverage is small.** Eight scenarios and four evaluation seeds cannot cover real traffic variability.
- **Disagreement is common.** Six of eight scenarios produced PPO-vs-CP-SAT disagreement in the final matrix; the UI flags this, but a real controller would need training and procedures for it.
- **SQLite concurrency.** No multi-writer production concurrency, HA or horizontal scaling.
- **Development security defaults.** Demo credentials and a default JWT secret are included for the prototype; they must be replaced before any shared deployment.
- **Audit is tamper-evident, not tamper-proof.** SQLite triggers block UPDATE/DELETE and the SHA-256 chain detects edits, but an attacker with full filesystem control could replace the database.
- **No external IdP/SSO, rate limiting or production secret management.**
- **Browser testing is not exhaustive.** The smoke test used the in-app Chromium browser; no cross-browser or accessibility certification was performed.
- **Decision re-validation is model-based.** It prevents internal inconsistency, not real-world harm.

---

## 9. Remaining risks

- A user could over-trust a validated recommendation; the UI and documentation must keep stating that validation is against synthetic assumptions.
- Constraint or topology simplifications could make a schedule look safer than it is in reality.
- PPO ranking disagreement could slow decisions or encourage arbitrary override if controllers are not trained.
- The 75-minute planning horizon and 30-minute application horizon are configured assumptions; changing them changes eligibility and outcomes.
- Infeasible or time-limited CP-SAT results depend on the configured time limit and single-worker setting.
- Single-node SQLite and local artifacts are not a production persistence or backup design.
- Synthetic evaluation cannot establish generalisation to real traffic, real disruptions or adversarial conditions.

---

## 10. Reproduction

### Run the application

```bash
cd /Users/madhu/RAILGORITHM
RAILGORITHM_DATABASE_URL=sqlite:////tmp/railgorithm_verify.db \
PYTHONPATH=backend .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Open `http://127.0.0.1:8000`.

Demo accounts:

- `section.master` / `Section@123` — full section authority
- `station.master` / `Station@123` — station `MLG` scope

### Run tests

```bash
cd /Users/madhu/RAILGORITHM/backend
../.venv/bin/python -m pytest tests -q

cd /Users/madhu/RAILGORITHM/frontend
npx vitest run
npx tsc --noEmit
npm run build
```

### Retrain PPO (optional)

```bash
cd /Users/madhu/RAILGORITHM
PYTHONPATH=backend .venv/bin/python backend/ml/train_ppo.py
```

Training overwrites the artifacts and metrics. The report above reflects the existing artifacts, not a fresh retrain.

---

## 11. Browser smoke test (actual steps)

Performed against the built frontend served by FastAPI, using the in-app Chromium browser:

1. Logged in as `section.master`.
2. Dashboard loaded with simulation state, metrics, conflicts, model status and pending-decision panel.
3. Selected the `single_line_meet` simulation, opened AI Recommendations and generated a recommendation.
4. Recommendation detail showed `PENDING`, evidence status, validation checks, measured outcome, PPO/CP-SAT comparison and the ten explanation questions.
5. Entered a rationale, checked the explicit confirmation box and approved. Status changed to `APPROVED`; the simulation advanced; the page showed the recorded decision.
6. Audit Trail showed a valid hash chain (36 events at that point), append-only trigger protection and the new decision event.
7. Signed out and logged in as `station.master`.
8. Confirmed the Station Master navigation omits Audit Trail and Disruption Management and that “New simulation” is unavailable.
9. Conflict Detection showed “filtered to your station scope”.
10. No browser console errors were reported.

The final API matrix and browser test used the fixed build. The earlier 422 refusal is retained in this report as evidence that the approval gate worked, together with the fix that removed the underlying inconsistency.
