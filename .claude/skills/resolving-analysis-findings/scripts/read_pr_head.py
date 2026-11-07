#!/usr/bin/env python3
"""Print one pull request's head commit SHA, for the re-check before a remote write.

Usage: read_pr_head.py <owner/repo> <pull-request-number>

Both arguments are validated before `gh` runs and nothing else is accepted, so a grant on this
script reaches one read of one host, where a `gh pr view` prefix grant also matches flags added
after it.
Only the validated SHA reaches stdout. The script leaves the working directory first, so a `gh`
executable committed to the repository being checked is not picked up from there.

Exit codes: 0 SHA printed, 2 invalid command line, `gh` failed, or its output was not one SHA.
"""

from __future__ import annotations

import json
import os
import re
import subprocess  # nosec B404  # runs gh with a list argument and validated values, never a shell
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

REPO = re.compile(r"[A-Za-z0-9][A-Za-z0-9-]*/[A-Za-z0-9._-]+\Z")
NUMBER = re.compile(r"[1-9][0-9]{0,9}\Z")
SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?\Z")
TIMEOUT_SECONDS = 30


def fail(message: str) -> int:
    print(f"read_pr_head: {message}", file=sys.stderr)
    return 2


def main(
    argv: Sequence[str],
    run: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
) -> int:
    if len(argv) != 2:
        return fail("expected exactly <owner/repo> <pull-request-number>")
    repo, number = argv
    if not REPO.match(repo) or repo.split("/")[1] in {".", ".."}:
        return fail("repository must be owner/repo")
    if not NUMBER.match(number):
        return fail("pull request number must be at most 10 digits")
    try:
        result = run(  # nosec B603 B607  # list form with a literal subcommand and validated values
            ["gh", "pr", "view", number, "--repo", f"github.com/{repo}", "--json", "headRefOid"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdin=subprocess.DEVNULL,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return fail(f"could not run gh: {type(exc).__name__}")
    if result.returncode != 0:
        return fail(f"gh exited {result.returncode}")
    try:
        sha = json.loads(result.stdout).get("headRefOid")
    except (ValueError, AttributeError, RecursionError):
        return fail("gh output was not the expected JSON")
    if not isinstance(sha, str) or not SHA.match(sha):
        return fail("gh output did not hold a commit SHA")
    print(sha)
    return 0


if __name__ == "__main__":
    os.chdir(Path(__file__).resolve().parent)
    raise SystemExit(main(sys.argv[1:]))
