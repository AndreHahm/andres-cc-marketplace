"""git-kit's git-bypass-attestation-marker.py (#861): its output must be the marker CI accepts."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.marketplace_ci import review

SCRIPT = (
    Path(__file__).resolve().parents[2] / "plugins/git-kit/scripts/git-bypass-attestation-marker.py"
)
SHA = "a1" * 20


def _run(tmp_path, reason, actor="octocat", sha=SHA):
    path = tmp_path / "reason.txt"
    path.write_bytes(reason if isinstance(reason, bytes) else reason.encode("utf-8"))
    return subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(path), actor, sha],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        check=False,
    )


@pytest.mark.parametrize(
    "reason",
    [
        "Tier-1 change, reviewed by hand",
        "quotes \" and ' and $(id) and `id` and $ENV",
        "two\nlines\tand a tab",
        "no-break" + chr(0xA0) + "space and joiner" + chr(0x200D),
        "braces {} } and a backslash \\",
        "umlaut ä and emoji \U0001f600",
    ],
)
def test_ci_accepts_the_marker(tmp_path, reason):
    done = _run(tmp_path, reason + "\n")
    assert done.returncode == 0, done.stderr
    marker = review.parse_attestation_marker(done.stdout)
    assert marker is not None
    assert (marker["actor"], marker["sha"], marker["reason"]) == ("octocat", SHA, reason)
    assert marker["created_at"].endswith("Z")
    assert "\\u" not in done.stdout


@pytest.mark.parametrize(
    "reason",
    [
        "",
        " \n",
        "a --> b",
        "<!-- a",
        "bell \x07",
        "a --!> b",
        "x \\u003c",
        "bidi \u202e",
        "x" * 16385,
        b"\xff\xfe",
    ],
)
def test_a_bad_reason_is_refused(tmp_path, reason):
    done = _run(tmp_path, reason)
    assert (done.returncode, done.stdout) == (2, "")


@pytest.mark.parametrize(
    ("actor", "sha"),
    [
        ("", SHA),
        ("app[bot]", SHA),
        ("a b", SHA),
        ("$ACTOR", SHA),
        ("octocat", ""),
        ("octocat", SHA.upper()),
        ("octocat", SHA[:39]),
    ],
)
def test_a_bad_actor_or_sha_is_refused(tmp_path, actor, sha):
    done = _run(tmp_path, "reason", actor, sha)
    assert (done.returncode, done.stdout) == (2, "")


def test_a_symlinked_or_missing_reason_file_is_refused(tmp_path):
    missing = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(tmp_path / "none"), "octocat", SHA],
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert missing.returncode == 2
    target = tmp_path / "target"
    target.write_text("reason", encoding="utf-8")
    link = tmp_path / "link"
    try:
        os.symlink(target, link)
    except OSError:
        pytest.skip("symlinks not available")
    linked = subprocess.run(
        [sys.executable, "-I", str(SCRIPT), str(link), "octocat", SHA],
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert linked.returncode == 2
