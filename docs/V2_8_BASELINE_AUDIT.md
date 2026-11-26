# RAILGORITHM v2.8 — Baseline Audit Report

**Date:** 2026-11-25  
**Baseline Git Commit/Tag:** `v2.7` (`684dbaa`)  
**Target Branch:** `v2.8`  
**Status:** Complete  

---

## Executive Summary

This document establishes the verified baseline of RAILGORITHM v2.7 prior to implementing the v2.8 AI Decision Intelligence, Predictive Train Regulation & System-Wide Enhancement.

In v2.7, the Section Controller dashboard was structured into 13 dedicated operational workspaces, maintaining safety and integrity invariants across all components. However, an in-depth audit of the recommendation generation, decision recording, and AI reasoning pipelines reveals specific mathematical, operational, and data-integrity gaps. This audit catalogs the exact system state, solver performance, model evaluation metrics, and concrete areas for v2.8 enhancement.

---

## 1. Existing Architecture

RAILGORITHM operates a multi-tier advisory architecture:
- **Frontend:** React 19 + TypeScript + Tailwind CSS + Lucide icons + Recharts, structured into role-based views (Station Master and Section Controller) and an operational shell with live WebSocket updates.
- **Backend:** FastAPI + Uvicorn + SQLAlchemy (SQLite asynchronous/synchronous engines), implementing REST endpoints and WebSocket multiplexers.
- **Decision Engine Pipeline:**
  - `backend/app/domain/pipeline.py`: Orchestrates state validation, conflict detection, CP-SAT solve, candidate generation, hard constraint filtering, PPO candidate scoring, cloned simulation measurement, and explanation formatting.
  - `backend/app/domain/optimizer.py`: Google OR-Tools CP-SAT formulation for timetable conflict resolution over a configured horizon.
  - `backend/app/domain/ppo.py`: PyTorch Actor-Critic neural network scoring candidate feature vectors against learned operational preferences.
  - `backend/app/domain/validator.py`: Independent constraint validator checking Hard Constraints (HC-001 through HC-007) and candidate safety invariants.
  - `backend/app/domain/projection.py`: Deterministic forward trajectory projection of train routes, block occupancies, and station dwell windows.
  - `backend/app/domain/conflicts.py`: Conflict detection engine identifying single-line crossings, headways, platform capacity overruns, and block closures.
- **Ingestion & Feed Safety:**
  - `backend/app/ingestion/event_processor.py` & `backend/app/ingestion/feed_manager.py`: Multi-source event ingestion with strict deduplication, sequence ordering, circuit breakers, and checkpoint persistence.
  - Strict three-way environment isolation: `SYNTHETIC_SIMULATION`, `HISTORICAL_PLAYBACK`, and `LIVE_OPERATIONAL`.

---

## 2. Existing Recommendation Pipeline Workflow

The recommendation lifecycle in `backend/app/domain/pipeline.py` executes in 10 sequential stages:
1. **State Integrity Validation:** Validates `sim_time_min`, trains array, blocks, and stations (`validate_state_integrity`).
2. **Conflict Detection:** Identifies projected spatial and temporal resource overlaps (`detect_conflicts`).
3. **CP-SAT Optimizer Run:** Attempts global horizon schedule optimization (`optimise`).
4. **Schedule Validation:** Independently verifies the CP-SAT schedule against hard constraints (`validate_schedule`).
5. **Candidate Action Generation:** Generates discrete operational actions (`generate_candidates`):
   - `DO_NOTHING` (baseline comparison)
   - `HOLD` (5, 10, 15 min at current station)
   - `PRECEDENCE` (priority override)
   - `PLATFORM_REASSIGN` (alternative platform at bottleneck station)
   - `SCHEDULE` (CP-SAT proposed global departure timings)
6. **Hard Constraint Filtering:** Discards any candidate violating block clearance, headway, or platform constraints.
7. **PPO Policy Ranking:** Scores eligible candidates using the trained neural network (`ppo.score_candidates`) or fallback rule (`baseline_rank`).
8. **Cloned Simulation Measurement:** Simulates every candidate in an isolated state clone (`evaluate_candidate`), calculating weighted delay and residual conflicts.
9. **Outcome-Based Selection:** Selects the top candidate based on measured operational score (delay reduction + conflict penalty).
10. **Explanation Synthesis:** Constructs human-readable explanation with evidence status (`build_explanation`).

---

## 3. CP-SAT and PPO Interaction

In the hybrid architecture:
- **CP-SAT Solver:** Acts as a global combinatorial search engine, producing mathematically provable feasible schedules. When solvable, its output is injected as a `SCHEDULE` candidate.
- **PPO Agent:** Acts as an operational preference ranker. It evaluates candidate feature vectors (relative train priority, delay changes, station characteristics) to select action orderings.
- **Independent Validator:** Acts as the deterministic gatekeeper. Neither CP-SAT nor PPO has authority to present an unverified action to the user.
- **Disagreement Handling:** If the PPO top recommendation diverges from the CP-SAT schedule or baseline rule, `disagreement=True` is flagged, and the evidence status is marked `MODEL_DISAGREEMENT`.

---

## 4. Current Model Evaluation Methodology

Model benchmarking is executed via `backend/ml/benchmark.py`:
- **Scenario Suite:** 14 synthetic scenarios (`normal_traffic`, `evening_peak`, `single_line_meet`, `delayed_express`, `block_closure`, `platform_outage`, `priority_train`, `no_feasible_schedule`, `double_line_overtaking`, `junction_congestion`, `maintenance_window`, `cascading_delay`, `disruption_recovery`, `time_varying_demand`).
- **Disjoint Held-out Evaluation:** Training uses 7 train scenarios; evaluation strictly uses 6 held-out scenarios (`double_line_overtaking`, `junction_congestion`, `maintenance_window`, `cascading_delay`, `disruption_recovery`, `time_varying_demand`) across seeds `5000` and `5001`.
- **Metrics Tracked:**
  - Policy Top-1 match against measured best outcome (%).
  - Mean & median regret vs. measured best (weighted delay + residual conflict penalty).
  - Solve time & status distribution for CP-SAT.
  - Pipeline latency (mean & median ms).

---

## 5. Existing Recommendation Quality & Benchmark Metrics (v2.7 Baseline)

Measurements from `backend/ml/reports/baseline-v2.7_*.json` (run on 2026-11-25):
- **Scenario Evaluation (56 decisions):**
  - CP-SAT Status: 48 OPTIMAL (85.7%), 8 INFEASIBLE (14.3%).
  - Evidence Status: 42 MODEL_DISAGREEMENT (75.0%), 6 VALIDATED (10.7%), 4 VALIDATED_WITH_ASSUMPTIONS (7.1%), 4 NO_FEASIBLE_SOLUTION (7.1%).
  - Recommended Source Distribution: BASELINE: 24 (42.9%), HEURISTIC: 16 (28.6%), CP-SAT: 12 (21.4%), null: 4 (7.1%).
  - Latency: Mean pipeline latency = **46.6 ms**, Median = **17.54 ms**. Mean CP-SAT solve time = **0.031s** (max 0.434s).
- **CP-SAT Solver Benchmark (28 solves across 14 scenarios):**
  - Optimal Solves: 26 (92.9%), Infeasible: 2 (7.1%). Mean solve time = **0.065s**.
- **PPO Candidate Ranker Benchmark (44 decisions on 6 held-out scenarios):**
  - Policy Top-1 Match: **22.73%**.
  - Mean Regret vs. Best: **16.273** (Median: 5.5).
  - Baseline Mean Regret: **24.705**.
  - Mean Inference Latency: **0.38 ms** (p95: **0.83 ms**).
  - Candidate Hard Violation Attempts: **0** (strictly filtered by independent validator).

---

## 6. Current Limitations

1. **Static Point Delays vs. Trend Dynamics:** Delays are calculated as static differences at `now`. There is no classification of delay progression (`INCREASING`, `DECREASING`, `STABLE`) or downstream knock-on window forecasting.
2. **Missing Longitudinal Predictive Timelines:** Controllers lack an explicit side-by-side predictive trajectory graph comparing "Continue Without Intervention" against "Proposed Regulation Action A/B".
3. **Rigid Candidate Generation:**
   - `HOLD` candidates test arbitrary static durations (5, 10, 15 min) rather than dynamic clearance windows calculated from crossing train block exit times.
   - Loop line availability, platform lengths, and directional priority rules at crossing stations are not dynamically evaluated during candidate generation.
4. **Explanation Completeness:** Explanations provide a high-level summary but lack the required 10-point operational structure (Situation, Problem, Recommendation, Operational Reasoning, Railway Constraints, Alternative Options, Expected Consequences, Consequences of No Action, Verified Evidence, Residual Uncertainty).
5. **No Decision Outcome Comparison:** Decisions submitted by controllers are recorded in the database, but actual simulation trajectory outcomes (actual arrival/departure, actual delay incurred) are never compared against what the AI predicted.
6. **Uncalibrated Confidence Disclosures:** Recommendations lack explicit data quality state tagging (`VERIFIED_SOURCE_DATA`, `OBSERVED`, `PREDICTED`, etc.) and uncalibrated confidence warnings.

---

## 7. Data Quality Weaknesses

1. **Binary Data Presence Assumption:** Data is either present or missing; there is no granular distinction between verified sensor feeds, estimated extrapolations, and simulation heuristics.
2. **Missing Data Gatekeeping:** If train speed or signal aspect is unobserved, the pipeline makes heuristic assumptions without flagging `CONFIDENCE: UNCALIBRATED` or withholding recommendations when safety-critical inputs are absent.
3. **Feed Integrity Nuances:** While circuit breakers and heartbeat monitoring exist in `feed_manager.py`, their status is not surfaced as an explicit gate to recommendation generation.

---

## 8. Operational Domain Assumptions

1. **Fixed Dwell Time:** Standard dwell times (e.g., 2–5 min) are treated as uniform across halts and major junctions without accounting for passenger surge or rake turnarounds.
2. **Symmetric Block Clearing:** Block occupancy is modeled on linear run times without accounting for acceleration/deceleration profiles on grade or loop entry turnouts (speed restrictions).
3. **Universal Precedence:** Priority 1 always takes precedence over Priority 2 unless manual holds are placed, without considering section-wide energy consumption or sectional capacity impacts.

---

## 9. Missing Functionality

1. **Predictive Train Regulation Engine:** Downstream knock-on impact propagation across 30, 60, and 90-minute horizons.
2. **Crossing & Precedence Intelligence:** Dynamic calculation of optimal meet points on single lines using actual loop capacities and section run times.
3. **Historical Decision & Drift Analysis:** Feedback categorization (`ACCEPTED`, `REJECTED`, `MODIFIED`, `NOT_APPLICABLE`, `SUPERSEDED`) and offline drift/error reporting comparing predicted vs. actual outcomes.
4. **10-Point Evidence-Based Structured Reasoning View:** Full transparent justification in the controller UI.

---

## 10. v2.8 Improvement Opportunities & Roadmap

- **Feature 1: Predictive Train Regulation:** Build `predictive_timeline` and trend detection in `backend/app/domain/projection.py` and `pipeline.py`.
- **Feature 2: Explainable Recommendation Reasoning:** Implement full 10-element structured reasoning in `backend/app/domain/explanation.py`.
- **Feature 3: Smarter Crossing & Precedence Analysis:** Refine `backend/app/domain/candidates.py` to calculate dynamic meeting-point holds based on crossing block geometry and loop line suitability.
- **Feature 4: Learning from Previous Decisions:** Extend `backend/app/models.py` and `backend/app/services/decision_service.py` with outcome evaluation, feedback categorization, and offline reporting.
- **Feature 5: Data Quality Gates & Confidence Calibration:** Enforce rigorous data quality tags and display `Confidence: Not calibrated` on uncalibrated models.
- **Frontend Enhancements:** Upgrade `Recommendations.tsx` and `RecommendationDetail.tsx` with predictive comparison charts, 10-point reasoning cards, and feedback capture.
