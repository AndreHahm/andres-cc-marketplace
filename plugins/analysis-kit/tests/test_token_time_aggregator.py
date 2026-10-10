"""Tests for scripts/anls_token_time_aggregator.py's level-aware aggregation, added for
Wave 2 Task 3+4 (analyzing-session-operations' Performance & Cost section)."""

import json
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import anls_token_time_aggregator as token_time_aggregator  # noqa: E402

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


def test_null_label_value_present_falls_back_to_unlabeled_not_none_key():
    # entry.get("label", "unlabeled") only applies the default when the key
    # is absent -- a JSON `"label": null` entry (key present, value None)
    # must still bucket under "unlabeled", not a literal None key.
    entries = [{"label": None, "tokens": 10, "duration_ms": 10}]
    result = aggregate(entries)
    assert None not in result["by_label"]
    assert result["by_label"]["unlabeled"]["tokens"] == 10


# --- input validation (Codex review: a malformed entry used to reach `total_tokens += tokens`
# and die with an uncaught TypeError traceback) -----------------------------------------------

SCRIPT = SCRIPTS_DIR / "anls_token_time_aggregator.py"
validate_entries = token_time_aggregator.validate_entries


def _run_cli(tmp_path, payload):
    input_file = tmp_path / "entries.json"
    input_file.write_text(json.dumps(payload), encoding="utf-8")
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--input", str(input_file)],
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_rejects_string_tokens_with_clear_message_not_a_traceback(tmp_path):
    result = _run_cli(tmp_path, [{"label": "a", "tokens": "oops", "duration_ms": 5}])
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "tokens" in result.stderr
    assert result.stdout == ""


def test_cli_rejects_string_duration_with_clear_message_not_a_traceback(tmp_path):
    result = _run_cli(tmp_path, [{"label": "a", "tokens": 5, "duration_ms": "slow"}])
    assert result.returncode == 1
    assert "Traceback" not in result.stderr
    assert "duration_ms" in result.stderr


def test_cli_names_the_offending_entry_index(tmp_path):
    result = _run_cli(tmp_path, [{"tokens": 1}, {"tokens": 2}, {"tokens": "x"}])
    assert result.returncode == 1
    assert "entry 2" in result.stderr


def test_cli_still_aggregates_valid_input(tmp_path):
    result = _run_cli(
        tmp_path, [{"label": "a", "tokens": 100, "duration_ms": 500}, {"tokens": None}, {}]
    )
    assert result.returncode == 0
    assert json.loads(result.stdout)["total_tokens"] == 100


def test_validate_accepts_absent_null_int_and_float_values():
    entries = [
        {},
        {"tokens": None, "duration_ms": None},
        {"tokens": 3, "duration_ms": 2.5},
        {"tokens": 0},
    ]
    assert validate_entries(entries) is None


def _problem(entries):
    problem = validate_entries(entries)
    assert problem is not None
    return problem


def test_validate_rejects_bool_negative_nonfinite_and_non_string_label():
    assert "tokens" in _problem([{"tokens": True}])
    assert "tokens" in _problem([{"tokens": -1}])
    assert "duration_ms" in _problem([{"duration_ms": float("nan")}])
    assert "duration_ms" in _problem([{"duration_ms": float("inf")}])
    assert "label" in _problem([{"label": ["not", "a", "string"]}])
    assert "label" in _problem([{"label": 7}])


def test_validate_leaves_unknown_level_to_the_existing_fallback():
    assert validate_entries([{"label": "a", "tokens": 1, "level": "not-a-real-level"}]) is None
