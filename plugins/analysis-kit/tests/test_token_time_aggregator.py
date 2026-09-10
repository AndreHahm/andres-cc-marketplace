"""Tests for scripts/token_time_aggregator.py's level-aware aggregation, added for
Wave 2 Task 3+4 (analyzing-session-operations' Performance & Cost section)."""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import token_time_aggregator  # noqa: E402

aggregate = token_time_aggregator.aggregate


def test_entries_without_level_default_to_subagent_backward_compat():
    entries = [{"label": "a", "tokens": 100, "duration_ms": 500}]
    result = aggregate(entries)
    assert result["by_level"] == {"subagent": {"tokens": 100, "duration_ms": 500, "count": 1}}
    assert result["levels_present"] == ["subagent"]
    # Original fields are unchanged.
    assert result["total_tokens"] == 100
    assert result["by_label"] == {"a": {"tokens": 100, "duration_ms": 500, "count": 1}}


def test_multiple_levels_rolled_up_separately():
    entries = [
        {"label": "a", "tokens": 100, "duration_ms": 500, "level": "subagent"},
        {"label": "b", "tokens": 50, "duration_ms": 200, "level": "tool"},
        {"label": "c", "tokens": 900, "duration_ms": 4000, "level": "whole_session"},
    ]
    result = aggregate(entries)
    assert result["by_level"]["subagent"]["tokens"] == 100
    assert result["by_level"]["tool"]["tokens"] == 50
    assert result["by_level"]["whole_session"]["tokens"] == 900
    assert set(result["levels_present"]) == {"subagent", "tool", "whole_session"}
    assert "whole_session" in result["scope_note"]


def test_unknown_level_value_falls_back_to_subagent():
    entries = [{"label": "a", "tokens": 10, "duration_ms": 10, "level": "not-a-real-level"}]
    result = aggregate(entries)
    assert result["levels_present"] == ["subagent"]


def test_no_whole_session_level_present_disclosed_in_scope_note():
    entries = [{"label": "a", "tokens": 10, "duration_ms": 10, "level": "subagent"}]
    result = aggregate(entries)
    assert "whole_session" not in result["levels_present"]
    assert "subagent" in result["scope_note"]


def test_non_hashable_level_value_falls_back_to_subagent_not_typeerror():
    entries = [{"label": "a", "tokens": 10, "duration_ms": 10, "level": ["not", "a", "string"]}]
    result = aggregate(entries)
    assert result["levels_present"] == ["subagent"]


def test_empty_entries_returns_empty_levels_not_error():
    result = aggregate([])
    assert result["by_level"] == {}
    assert result["levels_present"] == []
    assert "none" in result["scope_note"]
