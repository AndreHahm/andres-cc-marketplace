"""Tests for scripts/failure_aggregator.py -- written before the implementation (TDD),
per Wave 2 Task 3+4 Step 1. Covers: known denominator, unknown denominator (uncategorized
failure), recovered failure, repeated identical failure, missing timestamp."""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import failure_aggregator  # noqa: E402

aggregate = failure_aggregator.aggregate


def test_known_denominator_counts_attempts_and_failures():
    events = [
        {"subject": "Bash(pytest)", "category": None, "result": "success", "timestamp": None},
        {"subject": "Bash(pytest)", "category": "tool", "result": "failure", "timestamp": None},
        {"subject": "Edit(x.py)", "category": None, "result": "success", "timestamp": None},
    ]
    result = aggregate(events)
    assert result["attempts"] == 3
    assert result["failures"] == 1
    assert result["by_category"]["tool"] == 1


def test_unknown_denominator_uncategorized_failure_disclosed_not_hidden():
    events = [
        {"subject": "Bash(curl)", "category": None, "result": "failure", "timestamp": None},
    ]
    result = aggregate(events)
    assert result["failures"] == 1
    assert result["by_category"]["uncategorized"] == 1
    # No fabricated category -- "uncategorized" must be the only bucket touched.
    assert sum(result["by_category"].values()) == 1


def test_recovered_failure_matches_failure_to_next_success_same_subject():
    events = [
        {
            "subject": "Bash(npm install)",
            "category": "environment",
            "result": "failure",
            "timestamp": "2026-09-10T10:00:00Z",
        },
        {
            "subject": "Bash(npm install)",
            "category": None,
            "result": "success",
            "timestamp": "2026-09-10T10:00:05Z",
        },
    ]
    result = aggregate(events)
    assert result["recoveries"] == 1
    assert len(result["recovery_details"]) == 1
    detail = result["recovery_details"][0]
    assert detail["subject"] == "Bash(npm install)"
    assert detail["time_to_recovery_seconds"] == 5.0


def test_repeated_identical_failure_flagged():
    events = [
        {"subject": "Bash(pytest)", "category": "tool", "result": "failure", "timestamp": None},
        {"subject": "Bash(pytest)", "category": "tool", "result": "failure", "timestamp": None},
        {"subject": "Bash(pytest)", "category": "tool", "result": "failure", "timestamp": None},
    ]
    result = aggregate(events)
    assert result["repeated_failures"] == [{"subject": "Bash(pytest)", "count": 3}]


def test_missing_timestamp_yields_null_time_to_recovery_not_estimate():
    events = [
        {"subject": "Bash(pytest)", "category": "flaky", "result": "failure", "timestamp": None},
        {"subject": "Bash(pytest)", "category": None, "result": "success", "timestamp": None},
    ]
    result = aggregate(events)
    assert result["recoveries"] == 1
    assert result["recovery_details"][0]["time_to_recovery_seconds"] is None


def test_unresolved_failure_with_no_following_success_is_not_counted_as_recovered():
    events = [
        {
            "subject": "Bash(deploy)",
            "category": "fail-open",
            "result": "failure",
            "timestamp": None,
        },
    ]
    result = aggregate(events)
    assert result["recoveries"] == 0
    assert result["unresolved_failures"] == [{"subject": "Bash(deploy)", "category": "fail-open"}]


def test_out_of_order_timestamps_yield_null_time_to_recovery_not_negative():
    # Success appears in list order after the failure, but its own timestamp is
    # earlier -- interleaved/non-chronological input must never produce a
    # negative time_to_recovery_seconds.
    events = [
        {
            "subject": "Bash(pytest)",
            "category": "flaky",
            "result": "failure",
            "timestamp": "2026-09-10T10:00:10Z",
        },
        {
            "subject": "Bash(pytest)",
            "category": None,
            "result": "success",
            "timestamp": "2026-09-10T10:00:00Z",
        },
    ]
    result = aggregate(events)
    assert result["recoveries"] == 1
    assert result["recovery_details"][0]["time_to_recovery_seconds"] is None


def test_empty_events_returns_zeroed_result_not_error():
    result = aggregate([])
    assert result["attempts"] == 0
    assert result["failures"] == 0
    assert result["recoveries"] == 0
    assert result["repeated_failures"] == []
    assert result["unresolved_failures"] == []
