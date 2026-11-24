"""PPO policy: feature engineering, honest unavailability and inference."""
from __future__ import annotations

import json

import pytest

torch = pytest.importorskip("torch")

from app.domain.candidates import generate_candidates  # noqa: E402
from app.domain.conflicts import detect_conflicts  # noqa: E402
from app.domain.ppo import (  # noqa: E402
    CANDIDATE_DIM,
    GLOBAL_DIM,
    INPUT_DIM,
    PPOAgent,
    PolicyNet,
    build_features,
    save_policy,
)
from app.domain.state import advance, initialise_state  # noqa: E402


def _candidates(scenario: str = "single_line_meet"):
    state = initialise_state(scenario)
    advance(state, 2)
    conflicts = detect_conflicts(state)
    return state, conflicts, generate_candidates(state, conflicts)


def test_feature_dimensions_match_declared_space():
    state, conflicts, candidates = _candidates()
    global_vector, candidate_matrix = build_features(state, conflicts, candidates)
    assert global_vector.shape == (GLOBAL_DIM,)
    assert candidate_matrix.shape == (len(candidates), CANDIDATE_DIM)
    assert INPUT_DIM == GLOBAL_DIM + CANDIDATE_DIM


def test_untrained_agent_reports_unavailable(tmp_path):
    agent = PPOAgent(artifact_dir=tmp_path)
    assert agent.available is False
    result = agent.rank(*_candidates())
    assert result["available"] is False
    assert result["ranking"] == []
    assert "PPO" in result["disclaimer"] or "PPO" in result["reason"]


def test_metadata_marked_untrained_is_not_loaded(tmp_path):
    model = PolicyNet()
    save_policy(model, tmp_path / "ppo_policy.pt", {"trained": False})
    (tmp_path / "ppo_metrics.json").write_text(json.dumps({"trained": False}))
    agent = PPOAgent(artifact_dir=tmp_path)
    assert agent.available is False
    assert "untrained" in agent.reason.lower()


def test_trained_artifact_ranks_all_candidates(tmp_path):
    model = PolicyNet()
    metadata = {
        "trained": True,
        "model_version": "ppo-test-1",
        "evaluation": {"note": "synthetic test artifact"},
    }
    save_policy(model, tmp_path / "ppo_policy.pt", metadata)
    (tmp_path / "ppo_metrics.json").write_text(json.dumps(metadata))
    agent = PPOAgent(artifact_dir=tmp_path)
    assert agent.available is True
    assert agent.model_version == "ppo-test-1"
    state, conflicts, candidates = _candidates()
    result = agent.rank(state, conflicts, candidates)
    assert result["available"] is True
    assert result["trained"] is True
    assert len(result["ranking"]) == len(candidates)
    assert {entry["candidate_id"] for entry in result["ranking"]} == {
        candidate["id"] for candidate in candidates
    }
    probabilities = [entry["policy_probability"] for entry in result["ranking"]]
    assert abs(sum(probabilities) - 1.0) < 1e-4
    assert "not calibrated" in result["disclaimer"]


def test_corrupt_artifact_degrades_safely(tmp_path):
    (tmp_path / "ppo_policy.pt").write_bytes(b"not a checkpoint")
    (tmp_path / "ppo_metrics.json").write_text(json.dumps({"trained": True}))
    agent = PPOAgent(artifact_dir=tmp_path)
    assert agent.available is False
    assert "could not be loaded" in agent.reason
