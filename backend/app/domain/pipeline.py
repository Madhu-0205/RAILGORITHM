"""Hybrid recommendation pipeline.

Workflow (mirrors the product requirement):
1. read simulation state and check integrity
2. detect conflicts
3. run CP-SAT for feasible scheduling alternatives
4. independently validate the optimizer schedule
5. generate candidate actions
6. remove candidates that violate hard constraints
7. rank eligible candidates with PPO (or a labelled baseline)
8. measure every candidate in a cloned simulation
9. select on measured operational outcome
10. explain the recommendation, disagreements and uncertainty

Nothing here mutates the live simulation or makes a decision.
"""
from __future__ import annotations

from datetime import datetime, timezone

from .candidates import (
    baseline_rank,
    describe_action,
    generate_candidates,
)
from .conflicts import detect_conflicts, primary_conflicts
from .explanation import build_explanation
from .optimizer import optimise
from .ppo import PPOAgent
from .state import (
    format_minutes,
    projected_delay,
    state_metrics,
    validate_state_integrity,
)
from .validator import (
    INCOMPLETE_DATA,
    INVALID,
    NO_FEASIBLE_SOLUTION,
    VALIDATED,
    VALIDATED_WITH_ASSUMPTIONS,
    evaluate_candidate,
    validate_action,
    validate_schedule,
)

SEVERITY_PENALTY = {"CRITICAL": 100, "HIGH": 5, "MEDIUM": 2, "LOW": 1}
MEASUREMENT_LABEL = "SIMULATED_ESTIMATE"
LIMITATIONS = [
    "All data and outcomes are synthetic; this is not a validated digital twin of Indian Railways.",
    "Constraint feasibility is checked against configured simulation assumptions, not verified signalling rules.",
    "Candidate outcomes are estimates from a cloned simulation, not guaranteed real-world results.",
    "PPO policy scores are sampling scores, not calibrated confidence percentages.",
    "The human controller remains the final decision-maker; no action is executed automatically.",
]


def _weighted_delay(state: dict) -> float:
    now = int(state["sim_time_min"])
    total = 0.0
    for train in state["trains"]:
        weight = max(1, 6 - int(train["priority"]))
        total += weight * projected_delay(train, now)
    return round(total, 2)


def _residual_penalty(conflicts: list[dict]) -> int:
    return sum(
        SEVERITY_PENALTY.get(conflict["severity"], 1)
        for conflict in conflicts
        if conflict["type"] != "DELAY_RISK"
    )


def _outcome_payload(
    evaluation: dict, conflicts_before: int, horizon_minutes: int
) -> dict:
    metrics = evaluation.get("metrics") or {}
    post_conflicts = evaluation.get("post_conflicts", [])
    actionable_after = [
        conflict for conflict in post_conflicts if conflict["type"] != "DELAY_RISK"
    ]
    return {
        "measurement": MEASUREMENT_LABEL,
        "simulation_minutes": horizon_minutes,
        "total_delay_min": metrics.get("total_delay_min"),
        "average_delay_min": metrics.get("average_delay_min"),
        "max_delay_min": metrics.get("max_delay_min"),
        "weighted_delay": evaluation.get("weighted_delay"),
        "on_time_performance_pct": metrics.get("on_time_performance_pct"),
        "throughput_trains_per_hour": metrics.get("throughput_trains_per_hour"),
        "conflicts_before": conflicts_before,
        "conflicts_after": len(actionable_after),
        "conflict_reduction": conflicts_before - len(actionable_after),
        "residual_conflicts": [
            {
                "id": conflict["id"],
                "type": conflict["type"],
                "severity": conflict["severity"],
                "description": conflict["description"],
            }
            for conflict in actionable_after
        ],
        "residual_critical": sum(
            1 for conflict in actionable_after if conflict["severity"] == "CRITICAL"
        ),
    }


def _train_evidence(
    before: dict, after: dict, train_ids: list[str]
) -> list[dict]:
    before_now = int(before["sim_time_min"])
    after_now = int(after["sim_time_min"])
    before_trains = {train["id"]: train for train in before["trains"]}
    after_trains = {train["id"]: train for train in after["trains"]}
    evidence = []
    for train_id in train_ids:
        old = before_trains.get(train_id)
        new = after_trains.get(train_id)
        if not old or not new:
            continue
        old_delay = projected_delay(old, before_now)
        new_delay = projected_delay(new, after_now)
        expected_departure = None
        expected_arrival = None
        if new["status"] == "AT_STATION":
            expected_departure = format_minutes(
                max(after_now, int(new.get("ready_departure_min") or after_now), int(new.get("hold_until_min") or 0))
            )
        elif new["status"] == "RUNNING":
            expected_arrival = format_minutes(new.get("exit_min"))
        elif new["status"] == "COMPLETED":
            expected_arrival = format_minutes(new.get("completed_at_min"))
        evidence.append(
            {
                "train_id": train_id,
                "name": new["name"],
                "train_type": new["train_type"],
                "priority": new["priority"],
                "current_delay_min": old_delay,
                "predicted_delay_after_action_min": new_delay,
                "delay_change_min": new_delay - old_delay,
                "current_status": old["status"],
                "status_after_horizon": new["status"],
                "expected_next_departure": expected_departure,
                "expected_next_arrival": expected_arrival,
                "waiting_time_after_min": new.get("total_wait_min", 0),
                "measurement": "SIMULATED_ACTUAL_CURRENT / SIMULATED_ESTIMATE_AFTER",
            }
        )
    return evidence


def generate_recommendation(
    state: dict,
    *,
    conflicts: list[dict] | None = None,
    horizon_min: int = 75,
    apply_minutes: int = 30,
    ppo_agent: PPOAgent | None = None,
    include_schedule_checks: bool = True,
) -> dict:
    generated_at = datetime.now(timezone.utc).isoformat()
    base = {
        "generated_at": generated_at,
        "state_version": int(state["version"]),
        "simulation_time": format_minutes(state["sim_time_min"]),
        "simulation_time_min": int(state["sim_time_min"]),
        "label": "SYNTHETIC",
        "limitations": LIMITATIONS,
    }
    problems = validate_state_integrity(state)
    if problems:
        return {
            **base,
            "evidence_status": INCOMPLETE_DATA,
            "conflicts": [],
            "recommended": None,
            "alternatives": [],
            "optimizer": {"status": "NOT_RUN", "message": "Incomplete simulation state."},
            "ppo": {"available": False, "reason": "Pipeline stopped on incomplete data."},
            "disagreement": False,
            "data_issues": problems,
            "explanation": build_explanation(
                state=state,
                conflicts=[],
                recommended=None,
                alternatives=[],
                optimizer={"status": "NOT_RUN", "message": "Incomplete simulation state."},
                ppo={"available": False, "reason": "Pipeline stopped on incomplete data."},
                evidence_status=INCOMPLETE_DATA,
                disagreement=False,
                data_issues=problems,
            ),
            "quantitative_evidence": {},
            "comparison": {},
        }

    conflicts = conflicts if conflicts is not None else detect_conflicts(state, horizon_min)
    actionable_conflicts = [
        conflict for conflict in conflicts if conflict["type"] != "DELAY_RISK"
    ]
    optimizer_result = optimise(state, horizon_min=horizon_min)
    schedule_validation = None
    if optimizer_result.get("status") in {"OPTIMAL", "FEASIBLE"}:
        schedule_validation = validate_schedule(state, optimizer_result)
        schedule_valid = schedule_validation["status"] in {
            VALIDATED,
            VALIDATED_WITH_ASSUMPTIONS,
        }
    else:
        schedule_valid = False
        schedule_validation = {
            "status": NO_FEASIBLE_SOLUTION,
            "checks": [],
            "violations": [
                {
                    "kind": "NO_FEASIBLE_SOLUTION",
                    "detail": optimizer_result.get("message", "No feasible schedule."),
                }
            ],
            "assumptions": [],
            "validator_version": "validator-1.0.0",
        }

    candidates = generate_candidates(
        state,
        conflicts,
        cpsat_schedule=optimizer_result if schedule_valid else None,
    )
    ppo = ppo_agent or PPOAgent()

    evaluations: list[dict] = []
    for candidate in candidates:
        action = candidate["action"]
        if action.get("type") == "SCHEDULE":
            action_validation = schedule_validation
        else:
            action_validation = validate_action(state, action)
        outcome = evaluate_candidate(
            state,
            action,
            minutes=apply_minutes,
            conflict_horizon_min=horizon_min,
        )
        post_conflicts = outcome.get("post_conflicts", [])
        weighted = _weighted_delay(outcome["state"]) if outcome.get("state") else None
        actionable_after = [
            conflict for conflict in post_conflicts if conflict["type"] != "DELAY_RISK"
        ]
        residual_critical = sum(
            1 for conflict in actionable_after if conflict["severity"] == "CRITICAL"
        )
        residual_penalty = _residual_penalty(post_conflicts)
        outcome_status = (outcome.get("validation") or {}).get("status", INCOMPLETE_DATA)
        eligible = True
        rejection_reason = None
        if action_validation["status"] in {INVALID, INCOMPLETE_DATA, NO_FEASIBLE_SOLUTION}:
            eligible = False
            rejection_reason = (
                f"Action validation: {action_validation['status']}. "
                + "; ".join(
                    violation.get("detail", "")
                    for violation in action_validation.get("violations", [])[:3]
                )
            )
        elif outcome_status in {INVALID, INCOMPLETE_DATA}:
            eligible = False
            rejection_reason = f"Simulated outcome validation: {outcome_status}."
        elif residual_critical > 0:
            eligible = False
            rejection_reason = (
                "Residual critical conflict (for example an unresolved block closure) "
                "means this action cannot be presented as executable."
            )
        score = (
            (weighted or 10**9) + residual_penalty
            if eligible
            else None
        )
        evaluations.append(
            {
                "candidate": candidate,
                "action_validation": action_validation,
                "outcome": outcome,
                "outcome_status": outcome_status,
                "post_conflicts": post_conflicts,
                "weighted_delay": weighted,
                "residual_critical": residual_critical,
                "residual_penalty": residual_penalty,
                "eligible": eligible,
                "rejection_reason": rejection_reason,
                "score": score,
                "expected_outcome": _outcome_payload(
                    {
                        **outcome,
                        "post_conflicts": post_conflicts,
                        "weighted_delay": weighted,
                    },
                    len(actionable_conflicts),
                    apply_minutes,
                ),
            }
        )

    eligible = [item for item in evaluations if item["eligible"]]
    eligible.sort(
        key=lambda item: (
            item["score"],
            0 if item["candidate"]["action"].get("type") == "DO_NOTHING" else 1,
            0 if item["candidate"]["source"] == "CP_SAT" else 1,
            int(item["candidate"]["action"].get("hold_min", 0) or 0),
            item["candidate"]["id"],
        )
    )
    selected = eligible[0] if eligible else None

    ppo_candidates = [item["candidate"] for item in eligible]
    ppo_result = ppo.rank(state, conflicts, ppo_candidates) if ppo_candidates else {
        "available": ppo.available,
        "trained": ppo.available,
        "ranking": [],
        "reason": "No eligible candidates to rank",
        "model_version": ppo.model_version,
    }
    baseline = baseline_rank(ppo_candidates) if ppo_candidates else []
    baseline_top = baseline[0] if baseline else None
    ppo_top_id = ppo_result.get("top_candidate_id")
    recommended_id = selected["candidate"]["id"] if selected else None
    ppo_disagreement = bool(ppo_result.get("available") and ppo_top_id and ppo_top_id != recommended_id)
    cpsat_candidate = next(
        (
            item
            for item in eligible
            if item["candidate"]["action"].get("type") == "SCHEDULE"
        ),
        None,
    )
    cpsat_disagreement = bool(
        cpsat_candidate and cpsat_candidate["candidate"]["id"] != recommended_id
    )
    ppo_vs_cpsat_disagreement = bool(
        ppo_result.get("available")
        and ppo_top_id
        and cpsat_candidate
        and ppo_top_id != cpsat_candidate["candidate"]["id"]
    )
    disagreement = ppo_vs_cpsat_disagreement

    if not selected:
        evidence_status = NO_FEASIBLE_SOLUTION
    elif disagreement:
        evidence_status = "MODEL_DISAGREEMENT"
    elif (
        selected["outcome_status"] == VALIDATED_WITH_ASSUMPTIONS
        or not ppo_result.get("available")
        or selected["expected_outcome"]["residual_conflicts"]
    ):
        evidence_status = VALIDATED_WITH_ASSUMPTIONS
    else:
        evidence_status = VALIDATED

    recommended_payload = None
    quantitative: dict = {}
    if selected:
        candidate = selected["candidate"]
        action = candidate["action"]
        affected = list(
            dict.fromkeys(
                list(
                    primary_conflicts(conflicts, limit=3)[0]["trains"]
                    if primary_conflicts(conflicts, limit=3)
                    else []
                )
                + ([action["train_id"]] if action.get("train_id") else [])
            )
        )
        before_state = state
        after_state = selected["outcome"]["state"]
        train_evidence = _train_evidence(before_state, after_state, affected)
        before_metrics = state_metrics(state)
        after_metrics = selected["outcome"]["metrics"]
        before_blocks = sum(
            1 for value in state.get("block_occupancy", {}).values() if value.get("train_id")
        )
        after_blocks = sum(
            1
            for value in after_state.get("block_occupancy", {}).values()
            if value.get("train_id")
        )
        before_platforms = sum(
            1
            for platforms in state.get("platform_occupancy", {}).values()
            for train_id in platforms.values()
            if train_id
        )
        after_platforms = sum(
            1
            for platforms in after_state.get("platform_occupancy", {}).values()
            for train_id in platforms.values()
            if train_id
        )
        quantitative = {
            "measurement_note": (
                "Current values are simulated actuals. After-action values are "
                "estimates from a cloned simulation, not real-world predictions."
            ),
            "affected_trains": train_evidence,
            "current_total_delay_min": before_metrics["total_delay_min"],
            "predicted_total_delay_min": after_metrics["total_delay_min"],
            "total_delay_change_min": after_metrics["total_delay_min"] - before_metrics["total_delay_min"],
            "current_average_delay_min": before_metrics["average_delay_min"],
            "predicted_average_delay_min": after_metrics["average_delay_min"],
            "conflicts_detected": len(actionable_conflicts),
            "predicted_conflicts_after": selected["expected_outcome"]["conflicts_after"],
            "expected_conflict_reduction": selected["expected_outcome"]["conflict_reduction"],
            "block_occupancy_before": before_blocks,
            "block_occupancy_after": after_blocks,
            "platform_occupancy_before": before_platforms,
            "platform_occupancy_after": after_platforms,
            "section_utilization_before_pct": before_metrics["section_utilization_pct"],
            "section_utilization_after_pct": after_metrics["section_utilization_pct"],
            "platform_utilization_before_pct": before_metrics["platform_utilization_pct"],
            "platform_utilization_after_pct": after_metrics["platform_utilization_pct"],
            "throughput_before": before_metrics["throughput_trains_per_hour"],
            "throughput_after": after_metrics["throughput_trains_per_hour"],
            "on_time_before_pct": before_metrics["on_time_performance_pct"],
            "on_time_after_pct": after_metrics["on_time_performance_pct"],
            "schedule_deviation_min": after_metrics["total_delay_min"],
            "residual_conflicts": selected["expected_outcome"]["residual_conflicts"],
            "horizon_minutes": apply_minutes,
        }
        recommended_payload = {
            "candidate_id": candidate["id"],
            "label": candidate["label"],
            "description": describe_action(action),
            "action": action,
            "source": candidate["source"],
            "expected_outcome": selected["expected_outcome"],
            "validation_status": selected["outcome_status"],
            "action_validation_status": selected["action_validation"]["status"],
            "validation_summary": {
                "checks_total": len(selected["action_validation"].get("checks", [])),
                "checks_passed": sum(
                    1
                    for check in selected["action_validation"].get("checks", [])
                    if check["status"] == "PASS"
                ),
                "checks_warned": sum(
                    1
                    for check in selected["action_validation"].get("checks", [])
                    if check["status"] == "WARN"
                ),
                "checks_failed": sum(
                    1
                    for check in selected["action_validation"].get("checks", [])
                    if check["status"] == "FAIL"
                ),
                "validator_version": selected["action_validation"].get("validator_version"),
            },
            "weighted_delay": selected["weighted_delay"],
            "score": selected["score"],
        }

    alternatives = []
    for item in evaluations:
        candidate = item["candidate"]
        alternatives.append(
            {
                "candidate_id": candidate["id"],
                "label": candidate["label"],
                "description": describe_action(candidate["action"]),
                "action": candidate["action"],
                "source": candidate["source"],
                "eligible": item["eligible"],
                "selected": bool(selected and candidate["id"] == selected["candidate"]["id"]),
                "rejection_reason": item["rejection_reason"],
                "validation_status": item["outcome_status"],
                "action_validation_status": item["action_validation"]["status"],
                "expected_outcome": item["expected_outcome"],
                "weighted_delay": item["weighted_delay"],
                "score": item["score"],
            }
        )

    no_intervention = next(
        (
            item
            for item in evaluations
            if item["candidate"]["action"].get("type") == "DO_NOTHING"
        ),
        None,
    )
    cpsat_evaluation = cpsat_candidate
    comparison = {
        "measurement_note": (
            f"All comparison values are measured on cloned {apply_minutes}-minute "
            "simulations from the same state. They are not real-world performance claims."
        ),
        "no_intervention": no_intervention["expected_outcome"] if no_intervention else None,
        "baseline_heuristic_choice": next(
            (
                item["expected_outcome"]
                for item in evaluations
                if baseline_top and item["candidate"]["id"] == baseline_top["id"]
            ),
            None,
        ),
        "cpsat_only": cpsat_evaluation["expected_outcome"] if cpsat_evaluation else None,
        "hybrid_recommended": selected["expected_outcome"] if selected else None,
    }

    optimizer_payload = {
        "status": optimizer_result.get("status"),
        "message": optimizer_result.get("message"),
        "objective_value": optimizer_result.get("objective_value"),
        "solve_time_s": optimizer_result.get("solve_time_s"),
        "optimizer_version": optimizer_result.get("optimizer_version"),
        "solver": optimizer_result.get("solver"),
        "schedule_validation_status": schedule_validation.get("status"),
        "schedule_validation": {
            "status": schedule_validation.get("status"),
            "violations": schedule_validation.get("violations", [])[:8],
            "checks": schedule_validation.get("checks", []) if include_schedule_checks else [],
            "assumptions": schedule_validation.get("assumptions", []),
        },
        "feasible_schedule_found": bool(
            optimizer_result.get("status") in {"OPTIMAL", "FEASIBLE"} and schedule_valid
        ),
        "trains": {
            train_id: {
                "final_delay_min": payload.get("final_delay_min"),
                "hold_min": payload.get("hold_min"),
                "segments": payload.get("segments"),
            }
            for train_id, payload in (optimizer_result.get("trains") or {}).items()
        },
        "precedence": optimizer_result.get("precedence", []),
    }

    explanation = build_explanation(
        state=state,
        conflicts=conflicts,
        recommended=recommended_payload,
        alternatives=alternatives,
        optimizer=optimizer_payload,
        ppo=ppo_result,
        evidence_status=evidence_status,
        disagreement=disagreement,
        baseline=no_intervention["expected_outcome"] if no_intervention else None,
        comparison=comparison,
        quantitative=quantitative,
        data_issues=[],
    )

    return {
        **base,
        "evidence_status": evidence_status,
        "conflicts": conflicts,
        "primary_conflicts": primary_conflicts(conflicts),
        "recommended": recommended_payload,
        "alternatives": alternatives,
        "optimizer": optimizer_payload,
        "ppo": ppo_result,
        "baseline_ranking": [
            {"candidate_id": candidate["id"], "label": candidate["label"]}
            for candidate in baseline
        ],
        "disagreement": disagreement,
        "disagreement_detail": {
            "ppo_top_candidate_id": ppo_top_id if ppo_result.get("available") else None,
            "cpsat_candidate_id": cpsat_candidate["candidate"]["id"] if cpsat_candidate else None,
            "recommended_candidate_id": recommended_id,
            "ppo_disagreement": ppo_disagreement,
            "cpsat_disagreement": cpsat_disagreement,
            "ppo_vs_cpsat_disagreement": ppo_vs_cpsat_disagreement,
            "selection_rule": (
                "The recommendation is the eligible candidate with the lowest measured "
                "weighted delay plus residual conflict penalty. PPO and CP-SAT rankings "
                "are shown separately; disagreement is never silently resolved."
            ),
        },
        "quantitative_evidence": quantitative,
        "comparison": comparison,
        "explanation": explanation,
        "model_version": ppo_result.get("model_version", "ppo-unavailable"),
        "optimizer_version": optimizer_result.get("optimizer_version", "cpsat-unknown"),
        "validator_version": "validator-1.0.0",
        "data_issues": [],
    }
