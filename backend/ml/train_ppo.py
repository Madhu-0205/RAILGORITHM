"""Train and evaluate the PPO candidate-ranking policy.

The policy learns to pick one of several *independently validated* candidate
actions. It never invents actions and never overrides the constraint validator.
Training data comes only from synthetic simulations.

Run from the repository root:

    PYTHONPATH=backend .venv/bin/python -m ml.train_ppo

Artifacts are written to backend/ml/artifacts/:
    ppo_policy.pt     torch checkpoint (state dict + feature names)
    ppo_metrics.json  honest training/evaluation metadata used by the API
"""
from __future__ import annotations

import argparse
import json
import random
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from torch import nn
from torch.distributions import Categorical

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.config import settings  # noqa: E402
from app.domain.candidates import baseline_rank  # noqa: E402
from app.domain.pipeline import generate_recommendation  # noqa: E402
from app.domain.ppo import (  # noqa: E402
    CANDIDATE_DIM,
    CANDIDATE_FEATURE_NAMES,
    GLOBAL_DIM,
    GLOBAL_FEATURE_NAMES,
    PolicyNet,
    build_features,
    save_policy,
)
from app.domain.scenarios import SCENARIOS  # noqa: E402  (validates catalogue import)
from app.domain.state import advance, apply_action, initialise_state  # noqa: E402

TRAIN_SCENARIOS = [
    "normal_traffic",
    "evening_peak",
    "single_line_meet",
    "delayed_express",
    "block_closure",
    "platform_outage",
    "priority_train",
]
EVAL_SCENARIOS = list(TRAIN_SCENARIOS)

MODEL_VERSION = "ppo-candidate-ranker-1.0.0"
HORIZON_MIN = 75
APPLY_MINUTES = 45
STEP_MINUTES = 15
STEPS_PER_EPISODE = 4


class UnavailablePPO:
    """Stub used while generating training data; ranking is not needed."""

    available = False
    model_version = "ppo-unavailable"
    metadata: dict = {}

    def rank(self, state, conflicts, candidates):  # noqa: ANN001, ARG002
        return {
            "available": False,
            "trained": False,
            "reason": "Training data collection does not use a policy",
            "ranking": [],
            "model_version": self.model_version,
        }


@dataclass
class Transition:
    global_vector: np.ndarray
    candidate_matrix: np.ndarray
    action_index: int
    old_log_prob: float
    value: float
    reward: float
    return_value: float = 0.0
    advantage: float = 0.0


def _eligible_payload(state: dict) -> dict | None:
    payload = generate_recommendation(
        state,
        horizon_min=HORIZON_MIN,
        apply_minutes=APPLY_MINUTES,
        ppo_agent=UnavailablePPO(),  # type: ignore[arg-type]
    )
    eligible = [item for item in payload["alternatives"] if item["eligible"]]
    if len(eligible) < 2:
        return None
    return {"payload": payload, "eligible": eligible}


def _candidate_dicts(eligible: list[dict]) -> list[dict]:
    return [
        {
            "id": item["candidate_id"],
            "action": item["action"],
            "source": item["source"],
        }
        for item in eligible
    ]


def _baseline_score(eligible: list[dict]) -> float:
    scores = [
        item["score"]
        for item in eligible
        if item["action"].get("type") == "DO_NOTHING" and item["score"] is not None
    ]
    if scores:
        return float(scores[0])
    return float(np.median([item["score"] for item in eligible if item["score"] is not None]))


def _reward(chosen: dict, eligible: list[dict]) -> float:
    baseline = _baseline_score(eligible)
    chosen_score = float(chosen["score"] or baseline)
    improvement = (baseline - chosen_score) / max(1.0, abs(baseline))
    baseline_conflicts = len(
        next(
            (
                item["expected_outcome"]["residual_conflicts"]
                for item in eligible
                if item["action"].get("type") == "DO_NOTHING"
            ),
            [],
        )
    )
    chosen_conflicts = len(chosen["expected_outcome"]["residual_conflicts"])
    conflict_bonus = 0.05 * (baseline_conflicts - chosen_conflicts)
    return float(np.clip(improvement + conflict_bonus - 0.01, -2.0, 2.0))


def collect_episode(
    model: PolicyNet, scenario: str, seed: int, warmup: int, rng: random.Random
) -> list[Transition]:
    state = initialise_state(scenario, seed_override=seed)
    if warmup > 0:
        advance(state, warmup)
    transitions: list[Transition] = []
    for _ in range(STEPS_PER_EPISODE):
        if state["status"] != "RUNNING":
            break
        prepared = _eligible_payload(state)
        if prepared is None:
            advance(state, STEP_MINUTES)
            continue
        eligible = prepared["eligible"]
        payload = prepared["payload"]
        candidates = _candidate_dicts(eligible)
        global_vector, candidate_matrix = build_features(
            state, payload["conflicts"], candidates
        )
        with torch.no_grad():
            logits, value = model(
                torch.from_numpy(global_vector),
                torch.from_numpy(candidate_matrix),
            )
            distribution = Categorical(logits=logits)
            index = int(distribution.sample().item())
            log_prob = float(distribution.log_prob(torch.tensor(index)).item())
            value_estimate = float(value.item())
        chosen = eligible[index]
        reward = _reward(chosen, eligible)
        transitions.append(
            Transition(
                global_vector=global_vector,
                candidate_matrix=candidate_matrix,
                action_index=index,
                old_log_prob=log_prob,
                value=value_estimate,
                reward=reward,
            )
        )
        try:
            apply_action(state, chosen["action"])
        except Exception:  # noqa: BLE001 - a sampled action must never crash collection
            pass
        advance(state, STEP_MINUTES)
    return transitions


def _discounted_returns(transitions: list[Transition], gamma: float) -> None:
    running = 0.0
    for transition in reversed(transitions):
        running = transition.reward + gamma * running
        transition.return_value = running
    values = np.asarray([transition.value for transition in transitions])
    returns = np.asarray([transition.return_value for transition in transitions])
    advantages = returns - values
    if len(advantages) > 1:
        advantages = (advantages - advantages.mean()) / (advantages.std() + 1e-8)
    for transition, advantage in zip(transitions, advantages):
        transition.advantage = float(advantage)


def _padded_batch(batch: list[Transition]):
    size = len(batch)
    max_candidates = max(len(item.candidate_matrix) for item in batch)
    candidate_tensor = torch.zeros(size, max_candidates, CANDIDATE_DIM)
    mask = torch.zeros(size, max_candidates, dtype=torch.bool)
    global_tensor = torch.zeros(size, GLOBAL_DIM)
    actions = torch.zeros(size, dtype=torch.long)
    old_log_probs = torch.zeros(size)
    advantages = torch.zeros(size)
    returns = torch.zeros(size)
    for row, item in enumerate(batch):
        count = len(item.candidate_matrix)
        candidate_tensor[row, :count] = torch.from_numpy(item.candidate_matrix)
        mask[row, :count] = True
        global_tensor[row] = torch.from_numpy(item.global_vector)
        actions[row] = item.action_index
        old_log_probs[row] = item.old_log_prob
        advantages[row] = item.advantage
        returns[row] = item.return_value
    return (
        global_tensor,
        candidate_tensor,
        mask,
        actions,
        old_log_probs,
        advantages,
        returns,
    )


def ppo_update(
    model: PolicyNet,
    optimizer: torch.optim.Optimizer,
    transitions: list[Transition],
    *,
    epochs: int,
    minibatch: int,
    clip: float,
    entropy_coef: float,
    value_coef: float,
    rng: random.Random,
) -> dict:
    indices = list(range(len(transitions)))
    stats = {"policy_loss": 0.0, "value_loss": 0.0, "entropy": 0.0, "batches": 0}
    for _ in range(epochs):
        rng.shuffle(indices)
        for start in range(0, len(indices), minibatch):
            batch = [transitions[index] for index in indices[start : start + minibatch]]
            (
                global_tensor,
                candidate_tensor,
                mask,
                actions,
                old_log_probs,
                advantages,
                returns,
            ) = _padded_batch(batch)
            logits, values = model(global_tensor, candidate_tensor)
            logits = logits.masked_fill(~mask, -1e9)
            log_probs = torch.log_softmax(logits, dim=1)
            new_log_probs = log_probs[torch.arange(len(batch)), actions]
            entropy = -(log_probs.exp() * log_probs).sum(dim=1).mean()
            ratio = torch.exp(new_log_probs - old_log_probs)
            surrogate = torch.minimum(
                ratio * advantages,
                torch.clamp(ratio, 1 - clip, 1 + clip) * advantages,
            )
            policy_loss = -surrogate.mean()
            value_loss = nn.functional.mse_loss(values, returns)
            loss = policy_loss + value_coef * value_loss - entropy_coef * entropy
            optimizer.zero_grad()
            loss.backward()
            nn.utils.clip_grad_norm_(model.parameters(), 0.5)
            optimizer.step()
            stats["policy_loss"] += float(policy_loss.item())
            stats["value_loss"] += float(value_loss.item())
            stats["entropy"] += float(entropy.item())
            stats["batches"] += 1
    if stats["batches"]:
        for key in ("policy_loss", "value_loss", "entropy"):
            stats[key] = round(stats[key] / stats["batches"], 6)
    return stats


def evaluate(model: PolicyNet, *, seeds: list[int]) -> dict:
    model.eval()
    rows: list[dict] = []
    skipped = 0
    with torch.no_grad():
        for scenario in EVAL_SCENARIOS:
            for seed in seeds:
                state = initialise_state(scenario, seed_override=seed)
                warmup = 5 + (seed % 10)
                advance(state, warmup)
                for _ in range(STEPS_PER_EPISODE):
                    if state["status"] != "RUNNING":
                        break
                    prepared = _eligible_payload(state)
                    if prepared is None:
                        skipped += 1
                        advance(state, STEP_MINUTES)
                        continue
                    eligible = prepared["eligible"]
                    payload = prepared["payload"]
                    candidates = _candidate_dicts(eligible)
                    global_vector, candidate_matrix = build_features(
                        state, payload["conflicts"], candidates
                    )
                    logits, _ = model(
                        torch.from_numpy(global_vector),
                        torch.from_numpy(candidate_matrix),
                    )
                    index = int(torch.argmax(logits).item())
                    chosen = eligible[index]
                    best = min(
                        (item for item in eligible if item["score"] is not None),
                        key=lambda item: item["score"],
                    )
                    baseline_choice = baseline_rank(candidates)[0]["id"]
                    baseline_item = next(
                        item for item in eligible if item["candidate_id"] == baseline_choice
                    )
                    cpsat_item = next(
                        (
                            item
                            for item in eligible
                            if item["action"].get("type") == "SCHEDULE"
                        ),
                        None,
                    )
                    rows.append(
                        {
                            "scenario": scenario,
                            "policy_score": float(chosen["score"]),
                            "best_score": float(best["score"]),
                            "baseline_score": float(baseline_item["score"]),
                            "cpsat_score": (
                                float(cpsat_item["score"]) if cpsat_item else None
                            ),
                            "policy_top1_is_best": chosen["candidate_id"]
                            == best["candidate_id"],
                            "policy_delay": float(
                                chosen["expected_outcome"]["total_delay_min"] or 0
                            ),
                            "policy_residual": len(
                                chosen["expected_outcome"]["residual_conflicts"]
                            ),
                        }
                    )
                    try:
                        apply_action(state, chosen["action"])
                    except Exception:  # noqa: BLE001
                        pass
                    advance(state, STEP_MINUTES)
    model.train()
    if not rows:
        return {
            "decisions": 0,
            "skipped": skipped,
            "note": "No evaluable decisions were produced.",
        }
    policy_scores = np.asarray([row["policy_score"] for row in rows])
    best_scores = np.asarray([row["best_score"] for row in rows])
    baseline_scores = np.asarray([row["baseline_score"] for row in rows])
    cpsat_rows = [row for row in rows if row["cpsat_score"] is not None]
    cpsat_scores = np.asarray([row["cpsat_score"] for row in cpsat_rows])
    cpsat_regrets = np.asarray(
        [row["cpsat_score"] - row["best_score"] for row in cpsat_rows]
    )
    return {
        "decisions": len(rows),
        "skipped": skipped,
        "scenarios": sorted({row["scenario"] for row in rows}),
        "seeds": seeds,
        "policy_top1_matches_measured_best_pct": round(
            100 * sum(row["policy_top1_is_best"] for row in rows) / len(rows), 2
        ),
        "mean_regret_vs_best": round(float(np.mean(policy_scores - best_scores)), 3),
        "baseline_mean_regret_vs_best": round(
            float(np.mean(baseline_scores - best_scores)), 3
        ),
        "cpsat_mean_regret_vs_best": (
            round(float(np.mean(cpsat_regrets)), 3) if len(cpsat_regrets) else None
        ),
        "mean_policy_score": round(float(np.mean(policy_scores)), 3),
        "mean_baseline_score": round(float(np.mean(baseline_scores)), 3),
        "mean_cpsat_score": (
            round(float(np.mean(cpsat_scores)), 3) if len(cpsat_scores) else None
        ),
        "mean_policy_total_delay_min": round(
            float(np.mean([row["policy_delay"] for row in rows])), 2
        ),
        "mean_policy_residual_conflicts": round(
            float(np.mean([row["policy_residual"] for row in rows])), 2
        ),
        "measurement_note": (
            "All evaluation values are measured on synthetic cloned simulations. "
            "Scores are weighted delay plus residual-conflict penalty; lower is better. "
            "Regret is the chosen score minus the best measured eligible score at the "
            "same state. Mean score fields are descriptive and the CP-SAT mean covers "
            "only states where a CP-SAT candidate existed; compare regret instead."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Train the RAILGORITHM PPO ranker")
    parser.add_argument("--iterations", type=int, default=6)
    parser.add_argument("--episodes-per-iteration", type=int, default=20)
    parser.add_argument("--epochs", type=int, default=4)
    parser.add_argument("--minibatch", type=int, default=64)
    parser.add_argument("--lr", type=float, default=3e-4)
    parser.add_argument("--gamma", type=float, default=0.95)
    parser.add_argument("--clip", type=float, default=0.2)
    parser.add_argument("--entropy-coef", type=float, default=0.01)
    parser.add_argument("--value-coef", type=float, default=0.5)
    parser.add_argument("--seed", type=int, default=20261121)
    parser.add_argument("--output", type=Path, default=settings.artifact_dir)
    args = parser.parse_args()

    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    rng = random.Random(args.seed)

    model = PolicyNet()
    optimizer = torch.optim.Adam(model.parameters(), lr=args.lr)
    started = time.time()
    history: list[dict] = []
    total_transitions = 0

    for iteration in range(1, args.iterations + 1):
        transitions: list[Transition] = []
        episode_batches: list[list[Transition]] = []
        for episode in range(args.episodes_per_iteration):
            scenario = TRAIN_SCENARIOS[(iteration * args.episodes_per_iteration + episode) % len(TRAIN_SCENARIOS)]
            seed = 1000 + iteration * 100 + episode
            warmup = rng.randint(0, 20)
            episode_transitions = collect_episode(model, scenario, seed, warmup, rng)
            if episode_transitions:
                episode_batches.append(episode_transitions)
                transitions.extend(episode_transitions)
        if not transitions:
            continue
        for episode_transitions in episode_batches:
            _discounted_returns(episode_transitions, args.gamma)
        stats = ppo_update(
            model,
            optimizer,
            transitions,
            epochs=args.epochs,
            minibatch=args.minibatch,
            clip=args.clip,
            entropy_coef=args.entropy_coef,
            value_coef=args.value_coef,
            rng=rng,
        )
        total_transitions += len(transitions)
        history.append(
            {
                "iteration": iteration,
                "transitions": len(transitions),
                **stats,
            }
        )
        print(
            f"iteration {iteration}/{args.iterations}: "
            f"transitions={len(transitions)} "
            f"policy_loss={stats['policy_loss']:.4f} "
            f"value_loss={stats['value_loss']:.4f} "
            f"entropy={stats['entropy']:.4f}",
            flush=True,
        )

    evaluation = evaluate(model, seeds=[5000, 5001, 5002, 5003])
    metadata = {
        "trained": True,
        "status": "TRAINED_AND_EVALUATED",
        "model_version": MODEL_VERSION,
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "training_data": "Synthetic scenarios only; no real railway data.",
        "observation_space": (
            f"{GLOBAL_DIM} global features + {CANDIDATE_DIM} features per candidate"
        ),
        "action_space": "Select one of K independently validated candidate actions",
        "reward_design": (
            "Normalised improvement in weighted delay plus residual-conflict penalty "
            "relative to the no-intervention candidate, minus a small step cost."
        ),
        "global_feature_names": GLOBAL_FEATURE_NAMES,
        "candidate_feature_names": CANDIDATE_FEATURE_NAMES,
        "training_config": {
            "iterations": args.iterations,
            "episodes_per_iteration": args.episodes_per_iteration,
            "steps_per_episode": STEPS_PER_EPISODE,
            "step_minutes": STEP_MINUTES,
            "ppo_epochs": args.epochs,
            "minibatch": args.minibatch,
            "learning_rate": args.lr,
            "gamma": args.gamma,
            "clip": args.clip,
            "entropy_coef": args.entropy_coef,
            "value_coef": args.value_coef,
            "seed": args.seed,
            "train_scenarios": TRAIN_SCENARIOS,
            "train_seeds": "1000 + iteration*100 + episode",
        },
        "episodes": args.iterations * args.episodes_per_iteration,
        "transitions": total_transitions,
        "training_seconds": round(time.time() - started, 1),
        "history": history,
        "evaluation": evaluation,
        "limitations": [
            "Trained and evaluated only on synthetic simulation data.",
            "The policy ranks pre-validated candidates; it cannot create or execute actions.",
            "Policy probabilities are sampling scores, not calibrated operational confidence.",
            "Evaluation shares the same scenario families as training with different seeds; "
            "this measures stability, not out-of-distribution generalisation.",
            "Lower scores are better; regret is the comparable metric. Operational decisions remain human.",
        ],
    }

    args.output.mkdir(parents=True, exist_ok=True)
    save_policy(model, args.output / "ppo_policy.pt", metadata)
    (args.output / "ppo_metrics.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(evaluation, indent=2))
    print(f"Saved artifacts to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
