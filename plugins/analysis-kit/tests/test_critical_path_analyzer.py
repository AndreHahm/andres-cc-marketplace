"""Tests for scripts/critical_path_analyzer.py -- written before the implementation
(TDD), per Wave 2 Task 3+4 Step 1. Covers: sequential work, overlapping spans,
missing end timestamps, unrelated session IDs."""

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import critical_path_analyzer  # noqa: E402

analyze = critical_path_analyzer.analyze


def test_sequential_work_no_overlap():
    spans = [
        {
            "session_id": "s1",
            "label": "tool-a",
            "start": "2026-09-10T10:00:00Z",
            "end": "2026-09-10T10:00:10Z",
        },
        {
            "session_id": "s1",
            "label": "tool-b",
            "start": "2026-09-10T10:00:10Z",
            "end": "2026-09-10T10:00:20Z",
        },
    ]
    result = analyze(spans)
    s1 = result["sessions"]["s1"]
    assert s1["elapsed_seconds"] == 20.0
    assert s1["active_seconds"] == 20.0
    assert s1["overlapping_seconds"] == 0.0
    assert s1["waiting_seconds"] == 0.0
    assert s1["unknown_spans"] == 0


def test_overlapping_spans_union_not_sum():
    spans = [
        {
            "session_id": "s1",
            "label": "tool-a",
            "start": "2026-09-10T10:00:00Z",
            "end": "2026-09-10T10:00:10Z",
        },
        {
            "session_id": "s1",
            "label": "tool-b",
            "start": "2026-09-10T10:00:05Z",
            "end": "2026-09-10T10:00:15Z",
        },
    ]
    result = analyze(spans)
    s1 = result["sessions"]["s1"]
    # Union of [0,10] and [5,15] is [0,15] = 15 seconds, not 10+10=20.
    assert s1["active_seconds"] == 15.0
    assert s1["overlapping_seconds"] == 5.0
    assert s1["elapsed_seconds"] == 15.0
    assert s1["waiting_seconds"] == 0.0


def test_missing_end_timestamp_counted_as_unknown_not_zero_duration():
    spans = [
        {
            "session_id": "s1",
            "label": "tool-a",
            "start": "2026-09-10T10:00:00Z",
            "end": "2026-09-10T10:00:10Z",
        },
        {"session_id": "s1", "label": "tool-b", "start": "2026-09-10T10:00:20Z", "end": None},
    ]
    result = analyze(spans)
    s1 = result["sessions"]["s1"]
    assert s1["unknown_spans"] == 1
    assert s1["known_spans"] == 1
    # Only the fully-known span contributes to elapsed/active.
    assert s1["elapsed_seconds"] == 10.0
    assert s1["active_seconds"] == 10.0


def test_unrelated_session_ids_never_merged_or_compared():
    spans = [
        {
            "session_id": "s1",
            "label": "tool-a",
            "start": "2026-09-10T10:00:00Z",
            "end": "2026-09-10T10:00:10Z",
        },
        {
            "session_id": "s2",
            "label": "tool-b",
            "start": "2026-09-10T10:00:05Z",
            "end": "2026-09-10T10:00:15Z",
        },
    ]
    result = analyze(spans)
    assert set(result["sessions"].keys()) == {"s1", "s2"}
    # Despite overlapping wall-clock times, different session_ids never overlap each other.
    assert result["sessions"]["s1"]["overlapping_seconds"] == 0.0
    assert result["sessions"]["s2"]["overlapping_seconds"] == 0.0


def test_waiting_gap_between_sequential_spans():
    spans = [
        {
            "session_id": "s1",
            "label": "tool-a",
            "start": "2026-09-10T10:00:00Z",
            "end": "2026-09-10T10:00:10Z",
        },
        {
            "session_id": "s1",
            "label": "tool-b",
            "start": "2026-09-10T10:00:30Z",
            "end": "2026-09-10T10:00:40Z",
        },
    ]
    result = analyze(spans)
    s1 = result["sessions"]["s1"]
    assert s1["elapsed_seconds"] == 40.0
    assert s1["active_seconds"] == 20.0
    assert s1["waiting_seconds"] == 20.0


def test_no_known_spans_yields_null_elapsed_not_zero():
    spans = [
        {"session_id": "s1", "label": "tool-a", "start": None, "end": None},
    ]
    result = analyze(spans)
    s1 = result["sessions"]["s1"]
    assert s1["elapsed_seconds"] is None
    assert s1["active_seconds"] is None
    assert s1["waiting_seconds"] is None
    assert s1["unknown_spans"] == 1


def test_empty_spans_returns_empty_sessions():
    result = analyze([])
    assert result["sessions"] == {}


def test_end_before_start_treated_as_unknown_not_negative_duration():
    spans = [
        {
            "session_id": "s1",
            "label": "tool-a",
            "start": "2026-09-10T10:00:10Z",
            "end": "2026-09-10T10:00:00Z",
        },
    ]
    result = analyze(spans)
    s1 = result["sessions"]["s1"]
    assert s1["unknown_spans"] == 1
    assert s1["known_spans"] == 0
    assert s1["elapsed_seconds"] is None
    assert s1["active_seconds"] is None
