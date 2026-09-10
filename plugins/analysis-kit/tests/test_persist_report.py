"""Tests for scripts/persist_report.py -- redaction, LF normalization,
atomic replacement, and the standard confirmation line.

CRLF handling is two-layered, not one: `Path.read_text()`'s default
universal-newline translation silently converts a CRLF-containing *input*
file to LF before the script's own code ever sees it (verified live -- this
is Python's own behavior, not something persist_report.py does explicitly);
the script's own explicit `\\r\\n` check is defense-in-depth against CRLF
introduced *after* that read (e.g. by a future change to redact()'s own
substitution logic), which it refuses to persist rather than silently
writing. Both layers are tested below rather than assumed.

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


def test_persist_report_redacts_secrets_from_lf_input(tmp_path, monkeypatch, capsys):
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


def test_persist_report_normalizes_real_crlf_input_to_lf(tmp_path, monkeypatch):
    # A prior version of this test fed only LF input while asserting "no CRLF
    # in output," which passed trivially regardless of whether CRLF handling
    # worked at all (CodeRabbit finding). This feeds genuine CRLF bytes and
    # confirms the actual end-to-end outcome: read_text()'s own universal-
    # newline translation normalizes CRLF to LF before persist_report.py's
    # code runs, so this succeeds (exit 0) with an LF-only result -- it does
    # not fail the way a naive "detects and refuses CRLF" assumption would
    # predict; see the module docstring for why both are true depending on
    # which layer introduces the CRLF.
    scratch = tmp_path / "scratch.md"
    scratch.write_bytes(b"line one\r\nline two\r\n")
    final = tmp_path / "out" / "final.md"

    rc = _run_main(monkeypatch, scratch, final)

    assert rc == 0
    written = final.read_bytes()
    assert b"\r\n" not in written
    assert written == b"line one\nline two\n"


def test_persist_report_refuses_crlf_introduced_after_the_read(tmp_path, monkeypatch, capsys):
    # Defense-in-depth layer: read_text()'s universal newlines only protects
    # against CRLF already present in the *input file* -- it can't protect
    # against CRLF introduced later, e.g. by a future change to redact()'s
    # own substitution logic. Simulate that by monkeypatching redact() to
    # return CRLF-injected text, exercising the script's own explicit check
    # (otherwise unreachable via a real file, since read_text() launders any
    # CRLF a real file could contain before this check ever runs).
    scratch = tmp_path / "scratch.md"
    scratch.write_text("clean LF input\n", encoding="utf-8")
    final = tmp_path / "out" / "final.md"

    monkeypatch.setattr(persist_report, "redact", lambda text: ("corrupted\r\noutput", {}))
    rc = _run_main(monkeypatch, scratch, final)
    captured = capsys.readouterr()

    assert rc == 1
    assert not final.exists()
    assert "CRLF" in captured.err


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
