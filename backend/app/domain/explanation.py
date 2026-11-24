"""Human-readable explanation generation.

Every statement is derived from the actual pipeline evidence. No confidence
percentage is invented: the evidence status is a categorical assessment of
validation completeness and model agreement.
"""
from __future__ import annotations

from .state import format_minutes, projected_delay


def _fmt(value, suffix: str = "") -> str:
    if value is None:
        return "not available"
    return f"{value}{suffix}"


def _conflict_sentence(conflict: dict) -> str:
    return conflict.get("description", "No description available.")


def build_explanation(
    *,
    state: dict,
    conflicts: list[dict],
    recommended: dict | None,
    alternatives: list[dict],
    optimizer: dict,
    ppo: dict,
    evidence_status: str,
    disagreement: bool,
    baseline: dict | None = None,
    comparison: dict | None = None,
    quantitative: dict | None = None,
    data_issues: list[str] | None = None,
) -> dict:
    now = int(state["sim_time_min"])
    trains = {train["id"]: train for train in state["trains"]}
    actionable = [conflict for conflict in conflicts if conflict["type"] != "DELAY_RISK"]
    primary = actionable[0] if actionable else (conflicts[0] if conflicts else None)
    affected_ids: list[str] = []
    for conflict in conflicts:
        for train_id in conflict["trains"]:
            if train_id not in affected_ids:
                affected_ids.append(train_id)
    affected = [
        {
            "train_id": train_id,
            "name": trains[train_id]["name"] if train_id in trains else train_id,
            "type": trains[train_id]["train_type"] if train_id in trains else "unknown",
            "priority": trains[train_id]["priority"] if train_id in trains else None,
            "current_delay_min": (
                projected_delay(trains[train_id], now) if train_id in trains else None
            ),
        }
        for train_id in affected_ids
    ]

    if data_issues:
        headline = "Analysis stopped: simulation data is incomplete."
    elif recommended:
        headline = f"Recommendation: {recommended['description']}"
    elif evidence_status == "NO_FEASIBLE_SOLUTION":
        headline = "No feasible operational alternative was found for the configured constraints."
    else:
        headline = "No intervention is recommended from the current analysis."

    q1 = (
        f"At {format_minutes(now)} the simulation reports {len(conflicts)} detected "
        f"conflict(s), {len(actionable)} of which require an operational decision. "
        + (
            _conflict_sentence(primary)
            if primary
            else "No active block, platform, junction or closure conflict is projected in the horizon."
        )
    )

    q2 = (
        "Affected trains: "
        + (
            "; ".join(
                f"{item['train_id']} {item['name']} ({item['type']}, priority "
                f"{item['priority']}, current delay {item['current_delay_min']} min)"
                for item in affected
            )
            if affected
            else "none"
        )
        + "."
    )

    if primary:
        evidence = primary.get("evidence", {})
        if primary["type"] == "SINGLE_LINE_CROSSING":
            windows = evidence.get("block_windows", [])
            window_text = ", ".join(
                f"{window['train_id']} {format_minutes(window['entry_min'])}–"
                f"{format_minutes(window['exit_min'])}"
                for window in windows
            )
            q3 = (
                f"This is a single-line crossing conflict on {primary['location']['label']}. "
                f"Only one train may occupy the bidirectional block at a time, but the "
                f"projected occupancy windows are {window_text}. Configured headway is "
                f"{evidence.get('headway_min')} minutes."
            )
        elif primary["type"] == "HEADWAY":
            q3 = (
                f"Two trains are projected on the same block with less than the configured "
                f"headway. {primary.get('description', '')}"
            )
        elif primary["type"] == "PLATFORM_CAPACITY":
            q3 = (
                f"Platform demand exceeds available capacity at "
                f"{primary['location']['label']}. "
                f"{primary.get('description', '')}"
            )
        elif primary["type"] == "BLOCK_CLOSURE":
            closure = evidence.get("closure", {})
            q3 = (
                f"The route requires a block that is closed for '{closure.get('reason', 'maintenance')}' "
                f"from {format_minutes(closure.get('start_min'))} to "
                f"{format_minutes(closure.get('end_min'))}. This topology has no diversion."
            )
        else:
            q3 = primary.get("description", "The projected state violates a configured constraint.")
    else:
        q3 = "No conflict is currently projected, so there is no safety or capacity violation to resolve."

    if recommended:
        outcome = recommended.get("expected_outcome", {})
        hybrid = (comparison or {}).get("hybrid_recommended") or {}
        no_intervention = (comparison or {}).get("no_intervention") or {}
        weighted_delta = None
        if hybrid.get("weighted_delay") is not None and no_intervention.get("weighted_delay") is not None:
            weighted_delta = round(
                hybrid["weighted_delay"] - no_intervention["weighted_delay"], 2
            )
        residual_delta = None
        if hybrid and no_intervention:
            residual_delta = len(hybrid.get("residual_conflicts", [])) - len(
                no_intervention.get("residual_conflicts", [])
            )
        if recommended.get("action", {}).get("type") == "DO_NOTHING":
            q4 = (
                "No generated candidate strictly improved the measured weighted delay plus "
                "residual-conflict score, so the system recommends continuing without "
                "intervention. The predicted conflict is resolved by the simulation's "
                "priority and block-exclusivity rules, but the operational outcome is not "
                "better than the no-intervention baseline in the measured horizon. "
                "Alternatives remain available for human review."
            )
        else:
            q4 = (
                f"The suggested action is: {recommended['description']} It was selected because, "
                f"among independently validated candidates measured in a cloned "
                f"{outcome.get('simulation_minutes', 75)}-minute simulation, it produced the lowest "
                f"weighted delay plus residual-conflict penalty. "
                + (
                    f"Compared with no intervention, weighted delay changes by "
                    f"{weighted_delta:+.2f} and residual conflicts by {residual_delta:+d}. "
                    if weighted_delta is not None and residual_delta is not None
                    else ""
                )
                + f"Predicted weighted delay is {_fmt(recommended.get('weighted_delay'), ' weighted minutes')}."
            )
    elif evidence_status == "NO_FEASIBLE_SOLUTION":
        q4 = (
            "No candidate could be presented as executable. The optimizer reported "
            f"'{optimizer.get('status')}' and every generated action either failed hard "
            "constraint validation or left a critical conflict unresolved. The system does "
            "not fabricate a feasible recommendation."
        )
    else:
        q4 = "No recommendation is available from the current evidence."

    checks = (recommended or {}).get("validation_summary", {})
    q5 = (
        f"The independent validator ({checks.get('validator_version', 'validator')}) evaluated "
        f"{checks.get('checks_total', 0)} checks: {checks.get('checks_passed', 0)} passed, "
        f"{checks.get('checks_warned', 0)} warned, {checks.get('checks_failed', 0)} failed. "
        "Checks cover block exclusivity, headway, directional restrictions, platform capacity, "
        "closures, dwell/continuity, timetable departure rules and configured priority policy. "
        "Constraint feasibility is evaluated against synthetic assumptions, not verified "
        "signalling regulations."
    )

    alt_lines = []
    for item in alternatives:
        outcome = item.get("expected_outcome", {})
        alt_lines.append(
            f"{item['label']} — {'eligible' if item['eligible'] else 'rejected'}; "
            f"predicted total delay {_fmt(outcome.get('total_delay_min'), ' min')}, "
            f"conflict change {outcome.get('conflict_reduction', 'n/a')}"
            + (f"; reason: {item['rejection_reason']}" if item.get("rejection_reason") else "")
        )
    q6 = (
        f"{len(alternatives)} alternative(s) were evaluated in cloned simulations. "
        + (" | ".join(alt_lines) if alt_lines else "No alternatives were generated.")
    )

    rejected = [item for item in alternatives if not item["eligible"]]
    worse = [
        item
        for item in alternatives
        if item["eligible"] and recommended and item["candidate_id"] != recommended["candidate_id"]
    ]
    q7 = (
        "Rejected alternatives: "
        + (
            "; ".join(
                f"{item['label']} ({item.get('rejection_reason') or 'validation failed'})"
                for item in rejected
            )
            if rejected
            else "none were invalid."
        )
        + " Eligible alternatives not selected: "
        + (
            "; ".join(
                f"{item['label']} (weighted delay {item.get('weighted_delay')})"
                for item in worse
            )
            if worse
            else "none."
        )
        + " The final choice is based on measured outcomes, not on an unvalidated model score."
    )

    if recommended:
        outcome = recommended.get("expected_outcome", {})
        hybrid = (comparison or {}).get("hybrid_recommended") or {}
        no_intervention = (comparison or {}).get("no_intervention") or {}
        if hybrid and no_intervention:
            delay_delta = (hybrid.get("weighted_delay") or 0) - (
                no_intervention.get("weighted_delay") or 0
            )
            conflict_delta = len(hybrid.get("residual_conflicts", [])) - len(
                no_intervention.get("residual_conflicts", [])
            )
            benefit_text = (
                f"Relative to no intervention, weighted delay changes by {delay_delta:+.2f} "
                f"and residual actionable conflicts change by {conflict_delta:+d}. "
            )
        else:
            benefit_text = ""
        q8 = (
            f"Expected outcome: total simulated delay {_fmt(outcome.get('total_delay_min'), ' min')}, "
            f"average delay {_fmt(outcome.get('average_delay_min'), ' min')}, "
            f"on-time performance {_fmt(outcome.get('on_time_performance_pct'), '%')}, "
            f"throughput {_fmt(outcome.get('throughput_trains_per_hour'), ' trains/hour')}. "
            + benefit_text
            + f"Residual actionable conflicts after the horizon: "
            f"{len(outcome.get('residual_conflicts', []))}. These are estimates from a cloned "
            "simulation, not measured real-world benefits."
        )
    else:
        q8 = "No expected benefit can be claimed without a validated feasible action."

    model_line = (
        f"PPO is {'available' if ppo.get('available') else 'unavailable'}: {ppo.get('reason')}. "
        + (
            "PPO is genuinely trained and evaluated; its metadata is shown in the model registry. "
            if ppo.get("trained")
            else "The recommendation uses a clearly labelled deterministic baseline fallback. "
        )
    )
    q9 = (
        "Residual risks and uncertainty: all traffic data are synthetic; candidate outcomes are "
        "cloned-simulation estimates over the stated evaluation horizon; unmodelled perturbations, "
        "rolling-stock failures and real interlocking rules are out of scope. "
        + model_line
        + (
            " PPO and CP-SAT rankings disagree; both are presented and the disagreement is not "
            "silently resolved."
            if disagreement
            else ""
        )
        + " Constraint feasibility does not certify real-world safety."
    )

    if baseline:
        q10 = (
            f"If the controller rejects the recommendation, the measured no-intervention "
            f"projection gives total delay {_fmt(baseline.get('total_delay_min'), ' min')} with "
            f"{len(baseline.get('residual_conflicts', []))} residual conflict(s). The simulation "
            "will not apply the rejected recommendation. The controller can request alternatives, "
            "defer, modify, or record a rejection with a rationale."
        )
    else:
        q10 = (
            "If the controller rejects or defers, no recommendation is applied to the simulation. "
            "The decision and rationale are recorded, and the controller can request new alternatives."
        )

    if evidence_status == "NO_FEASIBLE_SOLUTION":
        q10 = (
            "Rejecting or deferring is the only safe path while no feasible alternative exists. "
            "The closure or capacity condition must change before a feasible recommendation can "
            "be generated; the system will not invent one."
        )

    key_facts = [
        f"Evidence status: {evidence_status}",
        f"Simulation time: {format_minutes(now)}",
        f"Actionable conflicts detected: {len(actionable)}",
        f"CP-SAT solver status: {optimizer.get('status')}",
        f"PPO: {'trained policy available' if ppo.get('trained') else 'unavailable — baseline fallback'}",
        f"Model disagreement: {'yes' if disagreement else 'no'}",
    ]

    return {
        "headline": headline,
        "evidence_status": evidence_status,
        "questions": {
            "1_what_is_happening": q1,
            "2_which_trains_are_affected": q2,
            "3_why_is_this_a_conflict": q3,
            "4_why_is_this_recommended": q4,
            "5_which_constraints_were_checked": q5,
            "6_which_alternatives_were_evaluated": q6,
            "7_why_were_other_alternatives_rejected": q7,
            "8_what_is_the_expected_benefit": q8,
            "9_what_risks_or_uncertainties_remain": q9,
            "10_what_if_the_controller_rejects": q10,
        },
        "key_facts": key_facts,
        "confidence_policy": (
            "No arbitrary confidence percentage is displayed. The categorical evidence "
            "status reflects validation completeness and model agreement only."
        ),
        "comparison": comparison or {},
    }
