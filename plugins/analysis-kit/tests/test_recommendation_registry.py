"""Tests for scripts/recommendation_registry.py -- written before the implementation (TDD),
per Wave 2 Task 9 Step 1. Covers: valid transitions, invalid transition rejection, append-only
history, reopened items, supersession, historical records with missing optional fields, the
lock's fail-loud-on-timeout guarantee (AKR-019), stale-lock auto-recovery, the append-before-
mkdir ordering regression, non-dict line rejection, and a CLI-level roundtrip via main()."""

import json
import os
import sys
import time
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import recommendation_registry as rr  # noqa: E402


def _event(recommendation_id, status, **extra):
    return {
        "recommendation_id": recommendation_id,
        "timestamp": extra.pop("timestamp", "2026-09-11T10:00:00Z"),
        "status": status,
        **extra,
    }


def test_valid_transition_accepted_from_proposed():
    ok, reason = rr.validate_transition(None, "proposed")
    assert ok, reason
    ok, reason = rr.validate_transition("proposed", "accepted")
    assert ok, reason
    ok, reason = rr.validate_transition("accepted", "implemented")
    assert ok, reason
    ok, reason = rr.validate_transition("implemented", "verified")
    assert ok, reason
    ok, reason = rr.validate_transition("verified", "measured")
    assert ok, reason
    ok, reason = rr.validate_transition("measured", "closed")
    assert ok, reason


def test_invalid_transition_rejected():
    ok, reason = rr.validate_transition("proposed", "measured")
    assert not ok
    assert "proposed" in reason and "measured" in reason


def test_new_recommendation_id_must_start_at_proposed():
    ok, reason = rr.validate_transition(None, "accepted")
    assert not ok
    assert "proposed" in reason


def test_reopened_from_closed_and_declined():
    ok, _ = rr.validate_transition("closed", "reopened")
    assert ok
    ok, _ = rr.validate_transition("declined", "reopened")
    assert ok
    # A reopened item re-enters the pipeline via accepted or implemented, not straight to measured.
    ok, _ = rr.validate_transition("reopened", "accepted")
    assert ok
    ok, reason = rr.validate_transition("reopened", "measured")
    assert not ok


def test_supersession_allowed_from_most_non_terminal_states():
    for status in ("proposed", "accepted", "implemented", "verified", "measured"):
        ok, reason = rr.validate_transition(status, "superseded")
        assert ok, f"{status} -> superseded should be valid: {reason}"
    # superseded itself is terminal.
    ok, _ = rr.validate_transition("superseded", "accepted")
    assert not ok


def test_append_only_history_preserves_every_event(tmp_path):
    registry_path = tmp_path / "events.jsonl"
    rr.append_event(registry_path, _event("rec-001", "proposed"))
    rr.append_event(registry_path, _event("rec-001", "accepted"))
    rr.append_event(registry_path, _event("rec-001", "implemented"))

    events = rr.read_events(registry_path)
    assert len(events) == 3
    assert [e["status"] for e in events] == ["proposed", "accepted", "implemented"]
    # The file is append-only -- earlier lines are never rewritten.
    lines = registry_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 3
    assert json.loads(lines[0])["status"] == "proposed"


def test_append_rejects_invalid_transition(tmp_path):
    registry_path = tmp_path / "events.jsonl"
    rr.append_event(registry_path, _event("rec-002", "proposed"))
    with pytest.raises(ValueError):
        rr.append_event(registry_path, _event("rec-002", "measured"))
    # The rejected append must not have landed in the file.
    events = rr.read_events(registry_path)
    assert len(events) == 1


def test_append_missing_optional_fields_still_reads_back(tmp_path):
    registry_path = tmp_path / "events.jsonl"
    minimal = {
        "recommendation_id": "rec-003",
        "timestamp": "2026-09-11T10:00:00Z",
        "status": "proposed",
    }
    rr.append_event(registry_path, minimal)
    events = rr.read_events(registry_path)
    assert len(events) == 1
    assert events[0]["recommendation_id"] == "rec-003"
    # Optional fields simply absent, never fabricated.
    assert "source_report" not in events[0] or events[0]["source_report"] is None


def test_list_recommendations_reports_latest_status_per_id(tmp_path):
    registry_path = tmp_path / "events.jsonl"
    rr.append_event(registry_path, _event("rec-a", "proposed", timestamp="2026-09-11T10:00:00Z"))
    rr.append_event(registry_path, _event("rec-a", "accepted", timestamp="2026-09-11T11:00:00Z"))
    rr.append_event(registry_path, _event("rec-b", "proposed", timestamp="2026-09-11T10:30:00Z"))

    events = rr.read_events(registry_path)
    summary = {
        row["recommendation_id"]: row["current_status"] for row in rr.list_recommendations(events)
    }
    assert summary == {"rec-a": "accepted", "rec-b": "proposed"}


def test_show_recommendation_returns_full_history_in_order(tmp_path):
    registry_path = tmp_path / "events.jsonl"
    rr.append_event(registry_path, _event("rec-x", "proposed"))
    rr.append_event(registry_path, _event("rec-x", "accepted"))
    events = rr.read_events(registry_path)
    history = rr.show_recommendation(events, "rec-x")
    assert [e["status"] for e in history] == ["proposed", "accepted"]


def test_validate_registry_detects_invalid_transition_written_out_of_band(tmp_path):
    registry_path = tmp_path / "events.jsonl"
    # Write two events directly, bypassing append_event's own validation, to simulate a
    # corrupted/hand-edited registry file that validate must still catch.
    with registry_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(_event("rec-y", "proposed")) + "\n")
        f.write(json.dumps(_event("rec-y", "closed")) + "\n")  # proposed -> closed is invalid
    violations = rr.validate_registry(registry_path)
    assert violations
    assert any("rec-y" in v for v in violations)


def test_validate_registry_clean_file_has_no_violations(tmp_path):
    registry_path = tmp_path / "events.jsonl"
    rr.append_event(registry_path, _event("rec-z", "proposed"))
    rr.append_event(registry_path, _event("rec-z", "accepted"))
    violations = rr.validate_registry(registry_path)
    assert violations == []


def test_read_events_missing_file_returns_empty_list(tmp_path):
    assert rr.read_events(tmp_path / "does-not-exist.jsonl") == []


def test_lock_timeout_raises_rather_than_silently_dropping(tmp_path):
    lock_path = tmp_path / "events.jsonl.lock"
    lock_path.touch()  # simulate another writer already holding the lock
    with pytest.raises(TimeoutError):
        rr.acquire_lock(lock_path, timeout=0.2, poll=0.05)


def test_acquire_lock_breaks_a_stale_lock(tmp_path):
    lock_path = tmp_path / "events.jsonl.lock"
    lock_path.touch()
    stale_time = time.time() - (rr.LOCK_STALE_SECONDS + 10)
    os.utime(lock_path, (stale_time, stale_time))
    # A lock older than LOCK_STALE_SECONDS is broken automatically -- this must succeed
    # immediately, not wait out the timeout or raise.
    token = rr.acquire_lock(lock_path, timeout=0.2, poll=0.05)
    assert lock_path.exists()  # re-acquired by this call, not left absent
    rr.release_lock(lock_path, token)


def test_lock_release_then_reacquire_succeeds(tmp_path):
    lock_path = tmp_path / "events.jsonl.lock"
    token = rr.acquire_lock(lock_path, timeout=1.0)
    rr.release_lock(lock_path, token)
    # A second, sequential acquire after a clean release must not be blocked by the first.
    token = rr.acquire_lock(lock_path, timeout=1.0)
    rr.release_lock(lock_path, token)


def test_release_lock_does_not_delete_a_lock_it_no_longer_owns(tmp_path):
    # Regression test for the lock-hijack race: if this lock was already broken as stale
    # and re-acquired by someone else, release_lock() must not delete their active lock.
    lock_path = tmp_path / "events.jsonl.lock"
    token_a = rr.acquire_lock(lock_path, timeout=1.0)
    # Simulate a second writer breaking A's lock as stale and acquiring its own, without
    # A's own release ever running -- write a different token directly, as the stale-break
    # path's own re-acquire would.
    lock_path.write_text("someone-elses-token", encoding="utf-8")
    rr.release_lock(lock_path, token_a)
    assert lock_path.exists()
    assert lock_path.read_text(encoding="utf-8") == "someone-elses-token"


def test_append_event_redacts_secret_shaped_patterns_in_free_text_fields(tmp_path):
    # Regression test: a caller-supplied rationale/evidence/expected_effect/observed_effect
    # field containing a secret-shaped pattern (e.g. an AWS access key literal pasted into
    # "the actual verification command/evidence") must never reach the persisted registry
    # file unredacted -- this is the plugin's own redact_secrets.py gate, applied here the
    # same way persist_report.py already applies it to every other persisted artifact.
    registry_path = tmp_path / "events.jsonl"
    rr.append_event(
        registry_path,
        _event(
            "rec-secret",
            "proposed",
            rationale="see AKIA1234567890ABCDEF for the deploy credentials used",
            evidence="ran the check with AKIA1234567890ABCDEF as the access key",
        ),
    )
    raw_line = registry_path.read_text(encoding="utf-8")
    assert "AKIA1234567890ABCDEF" not in raw_line

    events = rr.read_events(registry_path)
    assert len(events) == 1
    assert "AKIA1234567890ABCDEF" not in events[0]["rationale"]
    assert "AKIA1234567890ABCDEF" not in events[0]["evidence"]
    # Structural fields are never touched by redaction.
    assert events[0]["recommendation_id"] == "rec-secret"
    assert events[0]["status"] == "proposed"


def test_append_event_redacts_home_directory_path_in_source_report_field(tmp_path):
    # Regression test: source_report is caller-supplied (comparing-sessions' own Phase 4
    # populates it from --source-report) and can plausibly carry an absolute path revealing
    # the OS username -- it must be redacted the same way rationale/evidence are, not left as
    # a "structural" field exempt from the gate.
    registry_path = tmp_path / "events.jsonl"
    rr.append_event(
        registry_path,
        _event(
            "rec-path",
            "proposed",
            source_report=r"C:\Users\andre\Dev\Repos\andres-cc-marketplace\evals\report.md",
        ),
    )
    events = rr.read_events(registry_path)
    assert len(events) == 1
    assert r"C:\Users\andre" not in events[0]["source_report"]
    assert r"Dev\Repos\andres-cc-marketplace\evals\report.md" in events[0]["source_report"]


def test_append_event_creates_parent_directory_before_locking(tmp_path):
    # Regression test: append_event must create the registry's parent directory before
    # acquire_lock runs, since os.open(O_CREAT|O_EXCL) against a nonexistent directory
    # raises FileNotFoundError, which the lock's retry loop doesn't catch.
    registry_path = tmp_path / "fresh-subdir" / "events.jsonl"
    assert not registry_path.parent.exists()
    rr.append_event(registry_path, _event("rec-fresh", "proposed"))
    events = rr.read_events(registry_path)
    assert len(events) == 1


def test_append_event_aborts_if_its_lock_was_stolen_before_the_write(tmp_path, monkeypatch):
    # Regression test: append_event's own token re-check, immediately before the write,
    # must detect that this process's lock was broken and replaced by another writer
    # sometime after acquire_lock() returned -- and abort without writing, rather than
    # completing a write validated against state that may now be stale.
    registry_path = tmp_path / "events.jsonl"
    rr.append_event(registry_path, _event("rec-hijacked", "proposed"))

    real_acquire_lock = rr.acquire_lock

    def acquire_then_simulate_theft(lock_path, timeout=10.0, poll=0.05):
        token = real_acquire_lock(lock_path, timeout=timeout, poll=poll)
        # Simulate a second writer breaking this lock as stale and replacing it with its
        # own, sometime between this acquisition and append_event's pre-write re-check --
        # exactly what a long stall (not a crash) on this process's own side would expose.
        lock_path.write_text("someone-elses-token", encoding="utf-8")
        return token

    monkeypatch.setattr(rr, "acquire_lock", acquire_then_simulate_theft)
    with pytest.raises(TimeoutError, match="broken by another writer"):
        rr.append_event(registry_path, _event("rec-hijacked", "accepted"))

    # Nothing was written -- the registry still shows only the original proposed event.
    events = rr.read_events(registry_path)
    assert len(events) == 1
    assert events[0]["status"] == "proposed"
    # The "other writer's" lock (not this process's own) must survive the abort --
    # release_lock()'s own token check must not delete a lock this process doesn't own.
    assert (tmp_path / "events.jsonl.lock").read_text(encoding="utf-8") == "someone-elses-token"


def test_read_events_rejects_non_dict_line(tmp_path):
    registry_path = tmp_path / "events.jsonl"
    with registry_path.open("w", encoding="utf-8") as f:
        f.write(json.dumps(["not", "an", "object"]) + "\n")
    with pytest.raises(ValueError):
        rr.read_events(registry_path)


def test_read_events_locked_matches_read_events(tmp_path):
    registry_path = tmp_path / "events.jsonl"
    rr.append_event(registry_path, _event("rec-locked", "proposed"))
    assert rr.read_events_locked(registry_path) == rr.read_events(registry_path)
    # The lock must be released afterward, not left held.
    assert not (tmp_path / "events.jsonl.lock").exists()


def test_read_events_locked_against_uninitialized_registry_returns_empty_list(tmp_path):
    # Regression test: show/list/validate must not crash with an unhandled
    # FileNotFoundError against a registry whose parent directory was never created
    # (no prior init or append) -- acquire_lock()'s own os.open(O_CREAT|O_EXCL) only
    # catches FileExistsError, not the FileNotFoundError it raises against a missing
    # parent directory.
    registry_path = tmp_path / "never-created-subdir" / "events.jsonl"
    assert not registry_path.parent.exists()
    assert rr.read_events_locked(registry_path) == []
    # Must not have created the lock file (or anything else) as a side effect.
    assert not registry_path.parent.exists()


def test_cli_append_then_show_then_list_roundtrip(tmp_path, capsys, monkeypatch):
    registry_path = tmp_path / "events.jsonl"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "recommendation_registry.py",
            "--registry",
            str(registry_path),
            "append",
            "--recommendation-id",
            "rec-cli",
            "--status",
            "proposed",
            "--timestamp",
            "2026-09-11T10:00:00Z",
        ],
    )
    assert rr.main() == 0
    capsys.readouterr()

    monkeypatch.setattr(
        sys, "argv", ["recommendation_registry.py", "--registry", str(registry_path), "list"]
    )
    assert rr.main() == 0
    out = capsys.readouterr().out
    assert "rec-cli" in out
    assert "proposed" in out

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "recommendation_registry.py",
            "--registry",
            str(registry_path),
            "append",
            "--recommendation-id",
            "rec-cli",
            "--status",
            "measured",  # invalid from "proposed"
        ],
    )
    assert rr.main() == 1


def test_cli_registry_flag_works_after_the_subcommand_for_list_and_show(tmp_path, capsys, monkeypatch):
    # Regression test: --registry attached only to the top-level parser can never appear in a
    # subcommand-scoped Bash grant pattern (e.g. "recommendation_registry.py list:*") at all,
    # since --registry --registry <path> would have to precede "list" in that shape. comparing-
    # sessions needs exactly this ("list --registry <path>", "show --registry <path>") to narrow
    # its own grant to read-only subcommands -- confirm both subcommands accept --registry in
    # this position and that it actually targets the given file, not the default path.
    registry_path = tmp_path / "events.jsonl"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "recommendation_registry.py",
            "append",
            "--registry",
            str(registry_path),
            "--recommendation-id",
            "rec-after",
            "--status",
            "proposed",
            "--timestamp",
            "2026-09-11T10:00:00Z",
        ],
    )
    assert rr.main() == 0
    capsys.readouterr()

    monkeypatch.setattr(
        sys, "argv", ["recommendation_registry.py", "list", "--registry", str(registry_path)]
    )
    assert rr.main() == 0
    out = capsys.readouterr().out
    assert "rec-after" in out
    assert "proposed" in out

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "recommendation_registry.py",
            "show",
            "--registry",
            str(registry_path),
            "--recommendation-id",
            "rec-after",
        ],
    )
    assert rr.main() == 0
    out = capsys.readouterr().out
    assert "rec-after" in out
