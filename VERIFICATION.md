# RAILGORITHM 2.1 — Verification and Engineering Report

**Date:** 25 November 2026  
**Version:** 2.1.0  
**Scope:** Trustworthy intelligence validation, statistical significance testing, baseline reconciliation, CP-SAT audit, generalization stress testing, adversarial security verification, and regression test suite.  
**Classification:** Synthetic Simulation-Only Decision Support. No live railway connection.  
**Human Control:** Every operational action requires explicit human authorization and confirmation. Autonomous execution is strictly prohibited.

---

## 1. Executive Summary and Verdict

RAILGORITHM 2.1 represents the formal scientific and technical verification phase following the Version 2.0 release. It establishes the reproducibility, statistical significance, and boundary limits of the reported improvements under strict adversarial and held-out evaluation conditions.

### Verification Verdict: FULLY PASSED
- **Backend Test Suite:** **206 passed** (up from 141 in v1.0 and 186 in v2.0).
- **Frontend Test Suite:** **26 passed** across 6 test suites.
- **TypeScript Typecheck:** Clean (0 errors).
- **Production Build:** Clean build (`vite build`: 348.6 kB JS, 19.7 kB CSS).
- **PPO Baseline Reconciliation:** Reconciled historical 55.88% in-distribution figure with 25.84% held-out baseline; documented in `docs/PPO_BASELINE_RECONCILIATION.md`.
- **Multi-Seed Statistical Evaluation:** 8 independent seeds (`5000, 5001, 5002, 5003, 6000, 6001, 6002, 6003`), 178 decisions; Candidate V2 achieves **61.80% Top-1 match** ($\chi^2 = 46.74, p = 8.12 \times 10^{-12}$, statistically significant) and **86.2% residual conflict reduction** (1.39 vs 10.08); mean regret difference (15.258 vs 16.202) is honestly reported as not statistically significant ($p = 0.731$); documented in `docs/PPO_STATISTICAL_EVALUATION.md`.
- **CP-SAT Objective & Constraint Audit:** Formally verified 4 objective profiles, proved hard constraint isolation, explained the 26 feasible benchmark solves, passed 8 adversarial stress tests; documented in `docs/CPSAT_OBJECTIVE_AND_CONSTRAINT_AUDIT.md`.
- **Recommendation Disagreement Handling:** Formally verified 11 `MODEL_DISAGREEMENT` cases, ensured dual-model visibility, trade-offs presentation, zero auto-resolution, and immutable human audit; documented in `docs/DISAGREEMENT_ANALYSIS_REPORT.md`.
- **Generalization & Graceful Degradation:** Evaluated 3 novel unseen scenarios (`gen_freight_convoy_surge`, `gen_cascading_junction_gridlock`, `gen_emergency_single_line_cross`) across 4 seeds; Candidate V2 achieves **41.67% Top-1 match** (vs Baseline 0.0%), **46.2% regret reduction** (24.50 vs 45.50), **90.4% residual conflict reduction** (1.04 vs 10.83), and **zero constraint violations**; documented in `docs/GENERALIZATION_TEST_REPORT.md`.
- **Security & Adversarial Audit:** Verified database triggers blocking `UPDATE` and `DELETE`, hash-chain tampering detection, tail truncation detection via `audit_chain_head`, head tampering detection, concurrent decision race condition handling (`[200, 409]`), RBAC station scoping, and stale recommendation rejection; documented in `docs/SECURITY_AND_AUDIT_REPORT.md`.

---

## 2. Comparative Matrix: Baseline V1.0 vs Version 2.0 vs Version 2.1

| Evaluation Dimension | Baseline V1.0 | Version 2.0 | Version 2.1 (Validated) | Delta / Verification Result |
|---|---|---|---|---|
| **Backend Tests** | 141 passed | 186 passed | **206 passed** | +65 tests (+46.1% over v1; +20 over v2) |
| **Frontend Tests** | 25 passed | 26 passed | **26 passed** | 100% passing |
| **Statistical Seeds Evaluated** | 1 seed | 4 seeds (89 decisions) | **8 seeds (178 decisions)** | Extensive multi-seed statistical validation |
| **PPO Top-1 Match (Held-out)**| 25.84% [19.7, 32.6] | 61.80% | **61.80% [55.1, 69.1]** | **$\chi^2 = 46.74, p < 10^{-11}$** (Statistically significant) |
| **PPO Mean Regret (Held-out)** | 16.202 [12.2, 20.2] | 15.258 | **15.258 [11.3, 19.2]** | $t = 0.344, p = 0.731$ (Not statistically significant) |
| **PPO Median Regret** | 6.000 | 0.000 | **0.000** | Wilcoxon $p = 0.821$ |
| **PPO Residual Conflicts** | 10.08 | 1.39 | **1.39** | **-86.2% conflict reduction** |
| **Generalization (Unseen Scenarios)**| 0.0% Top-1, 45.5 Regret| Not evaluated | **41.7% Top-1, 24.5 Regret**| **-90.4% conflict reduction** on novel scenarios |
| **Adversarial CP-SAT Tests** | None | Implicit | **8 dedicated adversarial tests** | Timeout, Infeasible, Profiles, Headway, Platform, Throat, Closures |
| **Adversarial Security Tests** | 4 basic tests | 4 basic tests | **8 dedicated adversarial tests** | Triggers, Hash tampering, Head tampering, Tail truncation, Race conditions |
| **Junction Throat Check (HC-006)**| Unchecked | Unchecked | **Independently validated** | Rejects throat overflow independently of optimizer |
| **Model Disagreement Handling** | Undocumented | Explicit | **Formally audited** | Dual visibility, trade-offs, zero auto-resolution |
| **Uncalibrated Confidence** | Risk present | Prohibited | **Strictly null** | Explicit sampling score disclaimers |

---

## 3. Deliverables Summary

1. **`docs/PPO_BASELINE_RECONCILIATION.md` (Deliverable 1):**
   - Reconciles historical 55.88% in-distribution figure with 25.84% held-out baseline.
   - Explains dataset partition mismatch and candidate simulation bugfixes.
2. **`docs/PPO_STATISTICAL_EVALUATION.md` (Deliverable 2):**
   - 8-seed statistical evaluation on 178 decisions across held-out scenarios.
   - Bootstrap 95% CIs, paired t-test, Wilcoxon signed-rank, Pearson $\chi^2$.
   - Honest disclosure of statistically significant Top-1 match alongside statistically neutral mean regret delta.
3. **`docs/CPSAT_OBJECTIVE_AND_CONSTRAINT_AUDIT.md` (Deliverable 3):**
   - Audit of all 4 objective profiles (`balanced`, `delay_focused`, `priority_focused`, `throughput_focused`).
   - Hard constraint vs soft objective penalty separation.
   - Explanation of the 26 feasible benchmark solves in `v2_cpsat.json`.
   - Adversarial stress testing (timeouts, infeasible schedules, tampered constraints).
4. **`docs/DISAGREEMENT_ANALYSIS_REPORT.md` (Deliverable 4):**
   - Review of all 11 `MODEL_DISAGREEMENT` cases.
   - Dual-model visibility, trade-off presentation, absence of auto-resolution, immutable human audit.
5. **`docs/GENERALIZATION_TEST_REPORT.md` (Deliverable 5):**
   - Evaluation on 3 brand new held-out scenarios (`gen_freight_convoy_surge`, `gen_cascading_junction_gridlock`, `gen_emergency_single_line_cross`).
   - 24 decisions evaluated across 4 seeds; Candidate V2 achieves 41.67% Top-1, 24.5 regret, 1.04 residual conflicts, 0 violations.
   - Graceful degradation verified under severe bottleneck capacity reduction and emergency closures.
6. **`docs/SECURITY_AND_AUDIT_REPORT.md` (Deliverable 6):**
   - Comprehensive threat modeling (T1–T9).
   - SQL triggers, cryptographic hash chaining, head tracking, concurrent decision race handling, scope enforcement, and limits of DB-level protections.
7. **`docs/REGRESSION_TEST_RESULTS.md` (Deliverable 7):**
   - Full test breakdown across all 206 backend tests and 26 frontend tests.
   - Documentation of specific regression protections.
8. **`VERIFICATION.md` (Deliverable 8):**
   - Comprehensive RAILGORITHM 2.1 verification report.

---

## 4. Verification Commands & Execution Instructions

To reproduce all verification findings from the repository root:

```bash
# 1. Backend Automated Regression Suite (206 tests)
PYTHONPATH=backend .venv/bin/pytest backend/tests/ -v

# 2. Frontend Automated Regression Suite (26 tests)
cd frontend && npm test -- --run && cd ..

# 3. TypeScript Typecheck
cd frontend && npx tsc --noEmit && cd ..

# 4. Production Web Application Build
cd frontend && npm run build && cd ..

# 5. Multi-Seed Statistical Evaluation
PYTHONPATH=backend .venv/bin/python backend/ml/benchmark.py --all --label v2_1

# 6. Unseen Scenario Generalization Evaluation
PYTHONPATH=backend .venv/bin/python backend/ml/run_generalization.py
```
