"""Conflict detection over projected state."""
from __future__ import annotations

from app.domain.conflicts import detect_conflicts, primary_conflicts
from app.domain.state import advance, initialise_state


def test_single_line_crossing_is_detected():
    state = initialise_state("single_line_meet")
    advance(state, 2)
    conflicts = detect_conflicts(state)
    types = {conflict["type"] for conflict in conflicts}
    assert "SINGLE_LINE_CROSSING" in types
    crossing = next(
        conflict for conflict in conflicts if conflict["type"] == "SINGLE_LINE_CROSSING"
    )
    assert crossing["severity"] in {"HIGH", "CRITICAL"}
    assert len(crossing["trains"]) == 2
    assert crossing["location"]["section_id"]


def test_conflicts_have_required_evidence_fields():
    state = initialise_state("evening_peak")
    advance(state, 5)
    for conflict in detect_conflicts(state):
        assert conflict["id"]
        assert conflict["type"]
        assert conflict["severity"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        assert conflict["description"]
        assert conflict["start_min"] <= conflict["end_min"]
        assert conflict["location"]["kind"] in {"STATION", "SECTION", "BLOCK", "TRAIN"}
        assert isinstance(conflict["trains"], list)


def test_conflict_ids_are_unique_within_a_snapshot():
    state = initialise_state("evening_peak")
    advance(state, 5)
    ids = [conflict["id"] for conflict in detect_conflicts(state)]
    assert len(ids) == len(set(ids))


def test_block_closure_scenario_reports_closure_conflict():
    state = initialise_state("block_closure")
    advance(state, 3)
    conflicts = detect_conflicts(state)
    assert any(conflict["type"] == "BLOCK_CLOSURE" for conflict in conflicts)


def test_primary_conflicts_are_severity_ordered_and_limited():
    state = initialise_state("evening_peak")
    advance(state, 5)
    conflicts = detect_conflicts(state)
    primary = primary_conflicts(conflicts, limit=3)
    assert len(primary) <= 3
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3}
    severities = [order[conflict["severity"]] for conflict in primary]
    assert severities == sorted(severities)
