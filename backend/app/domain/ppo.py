"""PPO candidate-ranking policy: features, model and inference.

This is a real PPO actor-critic policy over *pre-validated candidate actions*.
It never executes an action. Policy probabilities are sampling probabilities,
not calibrated operational confidence; the UI labels them accordingly.

Training is performed by backend/ml/train_ppo.py. If no trained artifact and
evaluation metadata exist, inference reports the model as unavailable and the
recommendation pipeline falls back to a clearly labelled deterministic baseline.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from ..config import settings
from .candidates import ACTION_TYPES, CONFLICT_TYPES
from .state import projected_delay

try:  # torch is optional at import time so the API can degrade gracefully
    import torch
    from torch import nn
except Exception:  # pragma: no cover - exercised only when torch is absent
    torch = None
    nn = None

GLOBAL_FEATURE_NAMES = [
    "sim_time_fraction",
    "active_trains_scaled",
    "total_projected_delay_scaled",
    "max_projected_delay_scaled",
    "conflict_count_scaled",
    "primary_severity_scaled",
    "block_occupancy_fraction",
    "platform_occupancy_fraction",
    "completion_fraction",
    "horizon_fraction",
]
CANDIDATE_FEATURE_NAMES = [
    *[f"action_{name.lower()}" for name in ACTION_TYPES],
    "hold_min_scaled",
    "has_hold",
    "target_priority_scaled",
    "target_delay_scaled",
    "target_projected_delay_scaled",
    "target_is_express",
    "target_is_freight",
    "target_at_station",
    "target_remaining_legs_scaled",
    "target_max_hold_scaled",
    *[f"conflict_{name.lower()}" for name in CONFLICT_TYPES],
    "conflict_severity_scaled",
    "conflict_train_count_scaled",
    "conflict_headway_scaled",
    "conflict_platform_capacity_scaled",
    "conflict_closure_flag",
    "source_cp_sat",
    "schedule_hold_count_scaled",
]
GLOBAL_DIM = len(GLOBAL_FEATURE_NAMES)
CANDIDATE_DIM = len(CANDIDATE_FEATURE_NAMES)
INPUT_DIM = GLOBAL_DIM + CANDIDATE_DIM
SEVERITY_VALUE = {"CRITICAL": 3, "HIGH": 2, "MEDIUM": 1, "LOW": 0}

DEFAULT_ARTIFACT = "ppo_policy.pt"
DEFAULT_METADATA = "ppo_metrics.json"


def _global_vector(state: dict, conflicts: list[dict]) -> list[float]:
    trains = state["trains"]
    active = [train for train in trains if train["status"] != "COMPLETED"]
    now = int(state["sim_time_min"])
    delays = [projected_delay(train, now) for train in trains]
    blocks_total = max(
        1,
        sum(len(section["blocks"]) for section in state["network"]["sections"]),
    )
    platforms_total = max(
        1, sum(len(station["platforms"]) for station in state["network"]["stations"])
    )
    occupied_blocks = sum(
        1 for value in state.get("block_occupancy", {}).values() if value.get("train_id")
    )
    occupied_platforms = sum(
        1
        for platforms in state.get("platform_occupancy", {}).values()
        for train_id in platforms.values()
        if train_id
    )
    primary = conflicts[0] if conflicts else None
    return [
        now / 1440.0,
        len(active) / 10.0,
        sum(delays) / 120.0,
        (max(delays) if delays else 0) / 120.0,
        len(conflicts) / 10.0,
        (SEVERITY_VALUE.get(primary["severity"], 0) / 3.0) if primary else 0.0,
        occupied_blocks / blocks_total,
        occupied_platforms / platforms_total,
        (len(trains) - len(active)) / max(1, len(trains)),
        0.5,
    ]


def _candidate_vector(
    state: dict, conflicts: list[dict], candidate: dict
) -> list[float]:
    action = candidate["action"]
    action_type = action.get("type")
    train_lookup = {train["id"]: train for train in state["trains"]}
    train = train_lookup.get(action.get("train_id"))
    now = int(state["sim_time_min"])
    primary = conflicts[0] if conflicts else None
    vector: list[float] = []
    vector.extend(1.0 if action_type == name else 0.0 for name in ACTION_TYPES)
    hold_min = int(action.get("hold_min", 0))
    vector.append(min(1.0, hold_min / 30.0))
    vector.append(1.0 if hold_min > 0 else 0.0)
    if train:
        vector.extend(
            [
                int(train["priority"]) / 5.0,
                min(2.0, int(train["delay_min"]) / 60.0),
                min(2.0, projected_delay(train, now) / 60.0),
                1.0 if train["train_type"] == "EXPRESS" else 0.0,
                1.0 if train["train_type"] == "FREIGHT" else 0.0,
                1.0 if train["status"] == "AT_STATION" else 0.0,
                min(1.0, (len(train["route"]) - int(train["route_index"])) / 5.0),
                min(1.0, int(train["max_hold_min"]) / 60.0),
            ]
        )
    else:
        vector.extend([0.0] * 8)
    if primary:
        conflict_type = primary["type"]
        vector.extend(1.0 if conflict_type == name else 0.0 for name in CONFLICT_TYPES)
        vector.extend(
            [
                SEVERITY_VALUE.get(primary["severity"], 0) / 3.0,
                min(1.0, len(primary["trains"]) / 4.0),
                min(1.0, int(primary.get("headway_min", 0)) / 10.0),
                min(
                    1.0,
                    int(primary.get("evidence", {}).get("available_platforms", 3)) / 3.0,
                ),
                1.0 if conflict_type == "BLOCK_CLOSURE" else 0.0,
            ]
        )
    else:
        vector.extend([0.0] * 11)
    vector.append(1.0 if candidate.get("source") == "CP_SAT" else 0.0)
    vector.append(min(1.0, len(action.get("holds", [])) / 3.0))
    return vector


def build_features(
    state: dict, conflicts: list[dict], candidates: list[dict]
) -> tuple[np.ndarray, np.ndarray]:
    global_vector = np.asarray(_global_vector(state, conflicts), dtype=np.float32)
    candidate_matrix = np.asarray(
        [_candidate_vector(state, conflicts, candidate) for candidate in candidates],
        dtype=np.float32,
    )
    return global_vector, candidate_matrix


if nn is not None:

    class PolicyNet(nn.Module):
        def __init__(self, global_dim: int = GLOBAL_DIM, candidate_dim: int = CANDIDATE_DIM):
            super().__init__()
            self.global_encoder = nn.Sequential(
                nn.Linear(global_dim, 64), nn.Tanh()
            )
            self.candidate_encoder = nn.Sequential(
                nn.Linear(candidate_dim, 64),
                nn.Tanh(),
                nn.Linear(64, 64),
                nn.Tanh(),
            )
            self.score = nn.Linear(64, 1)
            self.value = nn.Sequential(
                nn.Linear(global_dim, 64), nn.Tanh(), nn.Linear(64, 1)
            )

        def forward(self, global_x, candidate_x):
            global_hidden = self.global_encoder(global_x)
            if global_hidden.dim() == 1:
                global_hidden = global_hidden.unsqueeze(0)
            else:
                global_hidden = global_hidden.unsqueeze(1)
            candidate_hidden = self.candidate_encoder(candidate_x)
            logits = self.score(candidate_hidden + global_hidden).squeeze(-1)
            value = self.value(global_x).squeeze(-1)
            return logits, value

else:  # pragma: no cover
    PolicyNet = None  # type: ignore[assignment]


def save_policy(
    model: Any, path: Path, metadata: dict
) -> None:
    if torch is None:
        raise RuntimeError("PyTorch is not installed")
    path.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "state_dict": model.state_dict(),
            "global_dim": GLOBAL_DIM,
            "candidate_dim": CANDIDATE_DIM,
            "global_features": GLOBAL_FEATURE_NAMES,
            "candidate_features": CANDIDATE_FEATURE_NAMES,
            "metadata": metadata,
        },
        path,
    )


class PPOAgent:
    """Loads a trained policy artifact and ranks validated candidates."""

    def __init__(self, artifact_dir: Path | None = None):
        self.artifact_dir = artifact_dir or settings.artifact_dir
        self.model = None
        self.metadata: dict = {}
        self.available = False
        self.reason = "PPO artifact not loaded"
        self.model_version = "ppo-unavailable"
        self._load()

    def _load(self) -> None:
        if torch is None:
            self.reason = "PyTorch is not installed; PPO inference unavailable"
            return
        policy_path = self.artifact_dir / DEFAULT_ARTIFACT
        metadata_path = self.artifact_dir / DEFAULT_METADATA
        if not policy_path.exists() or not metadata_path.exists():
            self.reason = (
                "No trained PPO artifact and evaluation metadata were found. "
                "Baseline ranking will be used and labelled as such."
            )
            return
        try:
            checkpoint = torch.load(policy_path, map_location="cpu", weights_only=False)
            metadata = json.loads(metadata_path.read_text())
            if not metadata.get("trained"):
                self.reason = "PPO metadata marks the model as untrained"
                return
            if checkpoint.get("global_dim") != GLOBAL_DIM or checkpoint.get("candidate_dim") != CANDIDATE_DIM:
                self.reason = "PPO artifact feature dimensions do not match this build"
                return
            model = PolicyNet()
            model.load_state_dict(checkpoint["state_dict"])
            model.eval()
            self.model = model
            self.metadata = metadata
            self.model_version = metadata.get("model_version", "ppo-unknown")
            self.available = True
            self.reason = "Trained PPO policy loaded"
        except Exception as exc:  # noqa: BLE001 - model failure must degrade safely
            self.reason = f"PPO artifact could not be loaded: {exc}"
            self.available = False
            self.model = None

    def rank(
        self, state: dict, conflicts: list[dict], candidates: list[dict]
    ) -> dict:
        if not candidates:
            return {
                "available": False,
                "reason": "No candidates to rank",
                "ranking": [],
                "model_version": self.model_version,
            }
        if not self.available or self.model is None:
            return {
                "available": False,
                "reason": self.reason,
                "trained": False,
                "ranking": [],
                "model_version": "ppo-unavailable",
                "disclaimer": (
                    "PPO is unavailable. The recommendation uses a deterministic "
                    "baseline ranking and is labelled accordingly."
                ),
            }
        global_vector, candidate_matrix = build_features(state, conflicts, candidates)
        with torch.no_grad():
            logits, value = self.model(
                torch.from_numpy(global_vector), torch.from_numpy(candidate_matrix)
            )
            probabilities = torch.softmax(logits, dim=0).numpy()
        scores = logits.numpy()
        order = np.argsort(-scores)
        ranking = [
            {
                "candidate_id": candidates[int(index)]["id"],
                "score": round(float(scores[int(index)]), 6),
                "policy_probability": round(float(probabilities[int(index)]), 6),
            }
            for index in order
        ]
        return {
            "available": True,
            "trained": True,
            "reason": "Trained PPO policy applied to validated candidates",
            "ranking": ranking,
            "top_candidate_id": ranking[0]["candidate_id"],
            "value_estimate": round(float(value.numpy()), 6),
            "model_version": self.model_version,
            "model_metrics": self.metadata.get("evaluation", {}),
            "disclaimer": (
                "Policy probabilities are sampling scores, not calibrated "
                "operational confidence. They do not replace validation or human judgement."
            ),
        }


def metadata_summary() -> dict:
    """Read model metadata for the model registry without loading the network."""
    path = settings.artifact_dir / DEFAULT_METADATA
    if not path.exists():
        return {
            "trained": False,
            "status": "UNTRAINED_DEVELOPMENT_COMPONENT",
            "reason": "No training/evaluation artifact found.",
        }
    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        return {
            "trained": False,
            "status": "ARTIFACT_CORRUPT",
            "reason": f"Metadata unreadable: {exc}",
        }
    data.setdefault("trained", False)
    return data
