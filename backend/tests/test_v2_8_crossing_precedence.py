"""Tests for Feature 3: Crossing & Precedence Analysis (v2.8)."""
import pytest
from app.domain.candidates import generate_candidates
from app.domain.conflicts import detect_conflicts
from app.domain.state import initialise_state


def test_dynamic_meet_pass_candidates():
    state = initialise_state("single_line_meet")
    conflicts = detect_conflicts(state, 60)
    candidates = generate_candidates(state, conflicts)

    # Check that candidates contain meet-pass or crossing actions
    labels = [c["label"] for c in candidates]
    actions = [c["action"] for c in candidates]

    assert any(c["action"]["type"] == "DO_NOTHING" for c in candidates)
    assert any(c["action"]["type"] == "HOLD" for c in candidates)
    assert any(c["action"]["type"] == "PRECEDENCE" for c in candidates)

    meet_pass = [c for c in candidates if "Meet-pass" in c["label"]]
    if meet_pass:
        first_mp = meet_pass[0]
        assert first_mp["action"]["hold_min"] > 0
        assert "loop capacity" in first_mp["rationale"].lower() or "single platform" in first_mp["rationale"].lower()


def test_loop_line_overtaking_candidate():
    state = initialise_state("double_line_overtaking")
    conflicts = detect_conflicts(state, 60)
    candidates = generate_candidates(state, conflicts)

    # Check candidates for loop line overtaking or precedence
    assert len(candidates) > 0
    hold_or_prec = [
        c for c in candidates
        if c["action"]["type"] in {"HOLD", "PRECEDENCE"}
    ]
    assert len(hold_or_prec) > 0


def test_priority_awareness_in_crossing():
    state = initialise_state("priority_train")
    conflicts = detect_conflicts(state, 60)
    candidates = generate_candidates(state, conflicts)

    # Ensure high-priority train has precedence options
    precedence_candidates = [c for c in candidates if c["action"]["type"] == "PRECEDENCE"]
    assert len(precedence_candidates) > 0
