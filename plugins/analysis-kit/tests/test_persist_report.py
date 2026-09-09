"""Tests for scripts/persist_report.py -- redaction, LF normalization,
atomic replacement, and the standard confirmation line.

Imports the script as a module (matching test_pr_review_fetcher.py's own
convention) and calls main() directly with a monkeypatched sys.argv, so
os.replace can be monkeypatched too for the failure-injection test.
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))
import persist_report  # noqa: E402


def _run_main(monkeypatch, scratch: Path, final: Path, label: str = "Test Report") -> int:
    monkeypatch.setattr(
        sys,
        "argv",
        ["persist_report.py", "--scratch", str(scratch), "--final", str(final), "--label", label],
    )
    return persist_report.main()


def test_persist_report_redacts_and_normalizes_lf(tmp_path, monkeypatch, capsys):
    scratch = tmp_path / "scratch.md"
    scratch.write_text(
        "token: sk-ant-api03-AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA\n",
        encoding="utf-8",
    )
    final = tmp_path / "out" / "final.md"

    rc = _run_main(monkeypatch, scratch, final)

    assert rc == 0
    assert final.exists()
    written = final.read_bytes()
    assert b"\r\n" not in written
    assert b"sk-ant-api03-AAAA" not in written


def test_persist_report_replaces_destination_atomically(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch.md"
    scratch.write_text("new content\n", encoding="utf-8")
    final = tmp_path / "final.md"
    final.write_text("old content\n", encoding="utf-8")

    rc = _run_main(monkeypatch, scratch, final)

    assert rc == 0
    assert final.read_text(encoding="utf-8") == "new content\n"
    leftovers = [p for p in final.parent.iterdir() if p.name.startswith(".persist_report-")]
    assert leftovers == []


def test_persist_report_preserves_existing_destination_on_failure(tmp_path, monkeypatch):
    scratch = tmp_path / "scratch.md"
    scratch.write_text("new content\n", encoding="utf-8")
    final = tmp_path / "final.md"
    final.write_text("old content\n", encoding="utf-8")

    def _boom(*_args, **_kwargs):
        raise OSError("simulated crash before replace")

    monkeypatch.setattr(persist_report.os, "replace", _boom)
    monkeypatch.setattr(
        sys,
        "argv",
        ["persist_report.py", "--scratch", str(scratch), "--final", str(final), "--label", "x"],
    )

    raised = False
    try:
        persist_report.main()
    except OSError:
        raised = True

    assert raised, "expected os.replace failure to propagate rather than being swallowed"
    assert final.read_text(encoding="utf-8") == "old content\n"
    leftovers = [p for p in final.parent.iterdir() if p.name.startswith(".persist_report-")]
    assert leftovers == []


def test_cli_prints_standard_confirmation(tmp_path, monkeypatch, capsys):
    scratch = tmp_path / "scratch.md"
    scratch.write_text("content\n", encoding="utf-8")
    final = tmp_path / "final.md"

    rc = _run_main(monkeypatch, scratch, final, label="Session Analysis Report")

    assert rc == 0
    captured = capsys.readouterr()
    assert f"\U0001f4c4 Session Analysis Report written: `{final}`" in captured.out
