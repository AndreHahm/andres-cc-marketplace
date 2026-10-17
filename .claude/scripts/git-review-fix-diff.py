#!/usr/bin/env python3
"""Print a committed fix's own diff for handling-review-findings' self-review (step 4c, #582).

This replaces the skill's former `Bash(git diff:*)` grant. That prefix also allows
`git diff --output=<path>`, a write to any path, so it could overwrite a pinned script. It is not
enough to give `git diff` safer flags: `git diff` reads the index and the working tree, and both can
run commands named in repository configuration or an inherited environment (`core.fsmonitor`, clean
filters, the `post-index-change` hook, `GIT_CONFIG_COUNT`), and it can write the index back.

This script runs `git diff-tree`, which compares two commits' trees and never opens the index or
reads a working-tree file's contents, so the filter, fsmonitor and hook routes above do not exist
for it. It does still read the working tree's `.gitattributes` and `.gitmodules` and the repository
configuration; the flags below neutralize their effect on the output (`--text`, `--no-ext-diff`,
`--no-textconv`, `--ignore-submodules=none`, `--submodule=short`). It takes one argument,
`--base <full commit id>`, and shows that commit against `HEAD`. It takes no path, pathspec or
option from the caller, and writes only to stdout. It cannot show an uncommitted fix: there is no
`--worktree` mode, because that is exactly the index and working-tree read this script avoids. The
git binary is an absolute path from `PATH` that is not inside the repository (the nearest ancestor
of the starting directory holding a `.git` entry, found without running git; a git installed under
that root, a home-directory dotfiles repository included, is refused), the environment passed to
it is an allowlist, global and system configuration are switched off, a run is stopped after 60
seconds with its whole process group, and git's own error text is never echoed (it can quote
attacker-chosen names).

Exit codes: 0 a non-empty diff was printed, 2 it could not be shown (not in a repository, an unknown
commit or one that is not a commit, an empty diff, git not found or found inside the repository, an
over-long run, a dubious-ownership refusal, or a diff over the size limit) - never read as "no
change". An empty diff means the base is wrong for a committed fix, so it is exit 2 as in
git-verify-fix-diff.py.
"""

from __future__ import annotations

# ruff: noqa: E402
import os
import sys

# Python puts this script's own directory first on sys.path unless run with -I. In a checked-out PR
# that directory is PR content, so a sibling argparse.py or re.py would be imported in place of the
# real module. The granted command uses -I; this keeps a run without it safe too.
_HERE = os.path.dirname(os.path.realpath(__file__))
sys.path[:] = [p for p in sys.path if os.path.realpath(p or os.curdir) != _HERE]

import argparse
import re
import shutil
import signal
import subprocess
import threading
from pathlib import Path

_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_MAX_BYTES = 1_000_000
_TIMEOUT_SECONDS = 60
# The only inherited variables git is given: locale and time zone. Everything else (GIT_DIR,
# GIT_CONFIG_*, GIT_TRACE*, GIT_EXEC_PATH, GIT_SSH*, HOME, XDG_CONFIG_HOME, PAGER, ...) is dropped.
_KEEP_ENV = ("LANG", "LC_ALL", "LC_CTYPE", "TZ")
_FAILED = "could not show the diff: not a repository, an unknown commit, or git is unavailable"


def _repository_root(start: Path) -> Path | None:
    """The nearest ancestor of `start` holding a `.git` entry (a directory, or the file a linked
    worktree has), found without running git."""
    for candidate in (start, *start.parents):
        if (candidate / ".git").exists():
            return candidate
    return None


def _find_git() -> str | None:
    """An absolute path to git that is not inside the repository the script was started in."""
    found = shutil.which("git")
    if not found or not os.path.isabs(found):  # an empty or relative PATH entry resolves here
        return None
    here = Path(os.path.realpath(Path.cwd()))
    root = _repository_root(here)
    guards = [here] if root is None else [here, root]
    # The path as found and where it resolves both count: a symlink in the repository is its file.
    for candidate in (Path(os.path.abspath(found)), Path(os.path.realpath(found))):
        if any(candidate.is_relative_to(guard) for guard in guards):
            return None
    return found


def _git_env(git: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in _KEEP_ENV}
    env.update(
        {
            "PATH": os.path.dirname(git),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_NO_LAZY_FETCH": "1",
            "GIT_NO_REPLACE_OBJECTS": "1",
            "GIT_OPTIONAL_LOCKS": "0",
            "GIT_TERMINAL_PROMPT": "0",
        }
    )
    return env


def _kill(proc: subprocess.Popen) -> None:
    """Stop git and anything it started: a child can hold the output pipe open after git is gone."""
    try:
        if hasattr(os, "killpg"):
            os.killpg(proc.pid, signal.SIGKILL)
        else:
            proc.kill()
    except OSError:
        pass  # already gone


def _show(git: str, base: str) -> bytes:
    """The diff text; raises when git fails, runs too long or prints more than the size limit."""
    command = [
        git,
        "-c",
        "core.fsmonitor=false",
        "-c",
        "core.hooksPath=" + os.devnull,
        "--no-pager",
        "diff-tree",
        "-p",
        "-r",
        "--no-ext-diff",
        "--no-textconv",
        "--no-color",
        "--no-relative",
        "--text",
        "--ignore-submodules=none",
        "--submodule=short",
        base + "^{commit}",
        "HEAD",
        "--",
    ]
    proc = subprocess.Popen(
        command,
        cwd=Path.cwd(),
        env=_git_env(git),
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        start_new_session=hasattr(os, "killpg"),  # its own process group, so _kill reaches children
    )
    expired = threading.Event()

    def _expire() -> None:
        expired.set()
        _kill(proc)

    # A timer thread, not SIGALRM, so the limit also holds where SIGALRM does not exist.
    timer = threading.Timer(_TIMEOUT_SECONDS, _expire)
    timer.daemon = True
    timer.start()
    try:
        assert proc.stdout is not None
        out = proc.stdout.read(_MAX_BYTES + 1)
        if expired.is_set():
            raise TimeoutError
        if len(out) > _MAX_BYTES:
            raise OverflowError
        status = proc.wait()
        if expired.is_set():
            raise TimeoutError
        if status != 0:
            raise subprocess.CalledProcessError(status, command)
        return out
    finally:
        timer.cancel()
        if proc.poll() is None:  # never signal a group whose leader has already been reaped
            _kill(proc)
        proc.wait()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="git-review-fix-diff.py", add_help=False, allow_abbrev=False
    )
    parser.add_argument("--base", required=True, help="full object id of the commit before the fix")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2  # a usage error, and -h/--help too: never a printed diff

    if not _OBJECT_ID.fullmatch(args.base):
        print("--base must be a full 40- or 64-digit lowercase hex object id", file=sys.stderr)
        return 2
    git = _find_git()
    if git is None:
        print("could not show the diff: no absolute git found on PATH", file=sys.stderr)
        return 2
    try:
        out = _show(git, args.base)
    except OverflowError:
        print(
            f"the diff is over {_MAX_BYTES} bytes: read the changed files one by one",
            file=sys.stderr,
        )
        return 2
    except Exception:  # noqa: BLE001 - every failure is exit 2, never a partial diff
        print(_FAILED, file=sys.stderr)
        return 2

    if not out:
        print(
            "the diff is empty: --base is probably not the commit before the fix", file=sys.stderr
        )
        return 2
    try:
        sys.stdout.buffer.write(out)
        sys.stdout.buffer.flush()
    except OSError:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
