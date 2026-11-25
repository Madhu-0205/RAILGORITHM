"""Reproducible scenario, CP-SAT and PPO benchmarks.

This script is intentionally independent of the API and writes JSON reports so
that Version 1.0 (``baseline-v1``) and Version 2.0 results can be compared under
identical conditions.

Run from the repository root:

    PYTHONPATH=backend .venv/bin/python backend/ml/benchmark.py --all --label baseline

The output is synthetic evidence only. It is not a real-world railway benchmark.
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from app.domain.optimizer import optimise
from app.domain.pipeline import generate_recommendation
from app.domain.ppo import PPOAgent
from app.domain.scenarios import SCENARIOS
from app.domain.state import advance, apply_action, initialise_state
from app.domain.validator import validate_schedule

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPORTS_DIR = BACKEND_DIR / "ml" / "reports"
HORIZON_MIN = 75
APPLY_MINUTES = 45
STEP_MINUTES = 15
DEFAULT_SEEDS = [5000, 5001]
DEFAULT_STEPS = 2


def _warmup(seed: int) -> int:
    return 5 + (seed % 10)


def _json_default(value):  # noqa: ANN001
    if isinstance(value, Path):
        return str(value)
    return str(value)


def scenario_benchmark(
    *,
    seeds: list[int],
    steps: int,
    scenario_keys: list[str],
    artifact_dir: Path | None = None,
) -> dict:
    ppo = PPOAgent(artifact_dir=artifact_dir)
    rows: list[dict] = []
    started = time.perf_counter()
    for scenario in scenario_keys:
        for seed in seeds:
            state = initialise_state(scenario, seed_override=seed)
            advance(state, _warmup(seed))
            for step in range(steps):
                if state["status"] != "RUNNING":
                    break
                before = time.perf_counter()
                payload = generate_recommendation(
                    state,
                    horizon_min=HORIZON_MIN,
                    apply_minutes=APPLY_MINUTES,
                    ppo_agent=ppo,
                )
                elapsed_ms = (time.perf_counter() - before) * 1000
                recommended = payload.get("recommended")
                alternatives = payload.get("alternatives", [])
                row = {
                    "scenario": scenario,
                    "seed": seed,
                    "step": step,
                    "sim_time_min": state["sim_time_min"],
                    "state_version": state["version"],
                    "pipeline_ms": round(elapsed_ms, 2),
                    "evidence_status": payload.get("evidence_status"),
                    "optimizer_status": payload.get("optimizer", {}).get("status"),
                    "optimizer_solve_time_s": payload.get("optimizer", {}).get("solve_time_s"),
                    "schedule_validation": payload.get("optimizer", {}).get(
                        "schedule_validation_status"
                    ),
                    "recommended_source": recommended.get("source") if recommended else None,
                    "recommended_label": recommended.get("label") if recommended else None,
                    "recommended_score": recommended.get("score") if recommended else None,
                    "residual_critical": (
                        recommended.get("expected_outcome", {}).get("residual_critical")
                        if recommended
                        else None
                    ),
                    "candidates_total": len(alternatives),
                    "candidates_eligible": sum(1 for item in alternatives if item.get("eligible")),
                    "candidates_rejected": sum(
                        1 for item in alternatives if not item.get("eligible")
                    ),
                    "disagreement": bool(payload.get("disagreement")),
                    "ppo_available": bool(payload.get("ppo", {}).get("available")),
                }
                rows.append(row)
                if recommended:
                    try:
                        apply_action(state, recommended["action"])
                    except Exception:  # noqa: BLE001 - benchmark observes, it does not repair
                        pass
                advance(state, STEP_MINUTES)
    statuses = Counter(row["optimizer_status"] for row in rows)
    evidence = Counter(row["evidence_status"] for row in rows)
    sources = Counter(row["recommended_source"] for row in rows)
    solve_times = [
        float(row["optimizer_solve_time_s"])
        for row in rows
        if row.get("optimizer_solve_time_s") is not None
    ]
    pipeline_times = [float(row["pipeline_ms"]) for row in rows]
    return {
        "label": "SYNTHETIC_BENCHMARK",
        "measurement_note": (
            "Measured on deterministic synthetic scenarios. Pipeline latency includes "
            "conflict detection, CP-SAT, candidate validation and PPO inference on this "
            "machine; it is not a production latency claim."
        ),
        "scenarios": scenario_keys,
        "seeds": seeds,
        "steps": steps,
        "decisions": len(rows),
        "optimizer_status_counts": dict(statuses),
        "evidence_status_counts": dict(evidence),
        "recommended_source_counts": dict(sources),
        "mean_pipeline_ms": round(statistics.fmean(pipeline_times), 2) if pipeline_times else None,
        "median_pipeline_ms": round(statistics.median(pipeline_times), 2) if pipeline_times else None,
        "mean_optimizer_solve_time_s": (
            round(statistics.fmean(solve_times), 3) if solve_times else None
        ),
        "max_optimizer_solve_time_s": round(max(solve_times), 3) if solve_times else None,
        "rows": rows,
        "elapsed_s": round(time.perf_counter() - started, 2),
    }


def cpsat_benchmark(*, seeds: list[int], scenario_keys: list[str]) -> dict:
    rows: list[dict] = []
    for scenario in scenario_keys:
        for seed in seeds:
            state = initialise_state(scenario, seed_override=seed)
            advance(state, _warmup(seed))
            started = time.perf_counter()
            result = optimise(state, horizon_min=HORIZON_MIN)
            elapsed = time.perf_counter() - started
            validation = None
            if result.get("status") in {"OPTIMAL", "FEASIBLE"}:
                validation = validate_schedule(state, result)
            rows.append(
                {
                    "scenario": scenario,
                    "seed": seed,
                    "status": result.get("status"),
                    "is_optimal": result.get("status") == "OPTIMAL",
                    "objective_value": result.get("objective_value"),
                    "objective_bound": result.get("objective_bound"),
                    "solve_time_s": result.get("solve_time_s"),
                    "wall_time_s": round(elapsed, 3),
                    "validation_status": validation.get("status") if validation else None,
                    "validation_violations": validation.get("violations", []) if validation else [],
                    "train_count": len(result.get("trains", {})),
                    "message": result.get("message"),
                }
            )
    statuses = Counter(row["status"] for row in rows)
    solve_times = [float(row["solve_time_s"] or 0) for row in rows]
    return {
        "label": "SYNTHETIC_CP_SAT_BENCHMARK",
        "scenarios": scenario_keys,
        "seeds": seeds,
        "solves": len(rows),
        "status_counts": dict(statuses),
        "optimal_count": sum(1 for row in rows if row["is_optimal"]),
        "feasible_not_optimal_count": sum(1 for row in rows if row["status"] == "FEASIBLE"),
        "mean_solve_time_s": round(statistics.fmean(solve_times), 3) if solve_times else None,
        "max_solve_time_s": round(max(solve_times), 3) if solve_times else None,
        "rows": rows,
    }


def ppo_benchmark(
    *,
    seeds: list[int],
    scenario_keys: list[str] | None = None,
    artifact_dir: Path | None = None,
) -> dict:
    # Imported lazily so the scenario/CP-SAT benchmarks work without torch.
    from ml.train_ppo import evaluate

    agent = PPOAgent(artifact_dir=artifact_dir)
    if not agent.available or agent.model is None:
        return {
            "label": "SYNTHETIC_PPO_BENCHMARK",
            "available": False,
            "reason": agent.reason,
            "decisions": 0,
        }
    result = evaluate(agent.model, seeds=seeds)
    return {
        "label": "SYNTHETIC_PPO_BENCHMARK",
        "note": "Evaluation uses the current EVAL_SCENARIOS in backend/ml/train_ppo.py.",
        "model_version": agent.model_version,
        **result,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="RAILGORITHM benchmark runner")
    parser.add_argument("--label", default="run")
    parser.add_argument("--seeds", type=int, nargs="+", default=DEFAULT_SEEDS)
    parser.add_argument("--steps", type=int, default=DEFAULT_STEPS)
    parser.add_argument("--scenarios", nargs="*", default=None)
    parser.add_argument("--output", type=Path, default=REPORTS_DIR)
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help="PPO artifact directory to evaluate; defaults to the configured artifact dir.",
    )
    parser.add_argument("--scenario", action="store_true")
    parser.add_argument("--cpsat", action="store_true")
    parser.add_argument("--ppo", action="store_true")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()

    scenario_keys = args.scenarios or [scenario.key for scenario in SCENARIOS]
    args.output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).isoformat()
    produced: list[str] = []

    if args.all or args.scenario:
        report = scenario_benchmark(
            seeds=args.seeds,
            steps=args.steps,
            scenario_keys=scenario_keys,
            artifact_dir=args.artifact_dir,
        )
        report.update({"generated_at": stamp, "label_name": args.label})
        path = args.output / f"{args.label}_scenario.json"
        path.write_text(json.dumps(report, indent=2, default=_json_default))
        produced.append(str(path))
        print(f"scenario: {report['decisions']} decisions -> {path}")

    if args.all or args.cpsat:
        report = cpsat_benchmark(seeds=args.seeds, scenario_keys=scenario_keys)
        report.update({"generated_at": stamp, "label_name": args.label})
        path = args.output / f"{args.label}_cpsat.json"
        path.write_text(json.dumps(report, indent=2, default=_json_default))
        produced.append(str(path))
        print(f"cpsat: {report['solves']} solves -> {path}")

    if args.all or args.ppo:
        report = ppo_benchmark(
            seeds=args.seeds,
            scenario_keys=scenario_keys,
            artifact_dir=args.artifact_dir,
        )
        report.update({"generated_at": stamp, "label_name": args.label})
        path = args.output / f"{args.label}_ppo.json"
        path.write_text(json.dumps(report, indent=2, default=_json_default))
        produced.append(str(path))
        print(f"ppo: {report.get('decisions')} decisions -> {path}")

    return 0 if produced else 1


if __name__ == "__main__":
    raise SystemExit(main())
