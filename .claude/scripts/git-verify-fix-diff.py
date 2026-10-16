#!/usr/bin/env python3
"""Re-run this repository's Phase 2 verifiers on a fix's own diff (review-findings step 4).

Diffs `--base` (the commit before the fix) against HEAD - or, with `--worktree`, against the
uncommitted working tree (tracked changes and new, non-ignored files), so a fix can be checked
before it is committed. Runs `run_verifiers` over the changed paths and reports a finding as
blocking only when it sits on a line the fix touched, or has no line (it speaks for a changed
component). A changed file whose hunks cannot be read (pure rename, mode-only change, binary)
counts as touched throughout, so it fails closed. Prints one JSON object: {"checked": [...],
"blocking": [...], "outside_lane": [...]}.

The verifier code is loaded from `--base` (`git archive`), never from the tree being judged, so
a fix cannot weaken the check that grades it. A `--worktree` run snapshots the working tree into
a throwaway commit built with a temporary index and verifies it in a temporary shared clone: no
ref, the real index or the working tree is touched, but the snapshot's objects (including any
untracked, non-ignored file) are written to the repository's object store as unreachable objects
until `git gc` prunes them.

Exit codes: 0 clean, 1 a blocking finding, 2 not verified (verifiers could not run, or nothing
changed) - never a pass. Exit 0 with "nothing to check" only where neither the base nor the
working tree has scripts/marketplace_ci/review_verifiers.py (git-kit is installed in other
repositories)."""

from __future__ import annotations

import argparse
import atexit
import contextlib
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
from collections.abc import Iterator
from pathlib import Path

_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_HUNK = re.compile(r"^@@ -\S+ \+(\d+)(?:,(\d+))? @@")
_VERIFIERS = "scripts/marketplace_ci/review_verifiers.py"
_WHOLE_FILE = [(1, 10**9)]
_GIT_LOCATION_VARS = (
    "GIT_DIR",
    "GIT_WORK_TREE",
    "GIT_INDEX_FILE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
    "GIT_COMMON_DIR",
    "GIT_NAMESPACE",
    "GIT_PREFIX",
)


def hunk_ranges(diff_text: str) -> list[tuple[int, int]]:
    """New-side line ranges of one file's `git diff -U0` text; a pure deletion touches none.

    Only `@@` lines count and the text is split on newlines alone, so file content can never
    pass for a header."""
    ranges: list[tuple[int, int]] = []
    for line in diff_text.split("\n"):
        match = _HUNK.match(line)
        if match:
            start = int(match.group(1))
            count = 1 if match.group(2) is None else int(match.group(2))
            if count:
                ranges.append((start, start + count - 1))
    return ranges


def on_touched_line(path: str, line: int | None, ranges: dict[str, list[tuple[int, int]]]) -> bool:
    if path not in ranges:
        return False
    if line is None:
        return True
    return any(start <= line <= end for start, end in ranges[path])


def _clean_env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _GIT_LOCATION_VARS}
    env.update(extra)
    return env


def _git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> bytes:
    return subprocess.run(
        ["git", *args], cwd=cwd, env=env or _clean_env(), capture_output=True, check=True
    ).stdout


def _load_verifiers(extract_root: Path, base: str):
    """`run_verifiers` and `parse_name_status_z` as at `base`, imported from a private copy."""
    archive = _git(
        extract_root,
        "archive",
        "--format=tar",
        base,
        "scripts/__init__.py",
        "scripts/marketplace_ci",
    )
    dest = Path(tempfile.mkdtemp(prefix="verify-fix-code-"))
    atexit.register(shutil.rmtree, dest, True)
    with tarfile.open(fileobj=io.BytesIO(archive)) as tar:
        tar.extractall(dest, filter="data")
    sys.path.insert(0, str(dest))
    from scripts.marketplace_ci.git_state import parse_name_status_z  # noqa: PLC0415
    from scripts.marketplace_ci.review_verifiers import run_verifiers  # noqa: PLC0415

    return run_verifiers, parse_name_status_z


@contextlib.contextmanager
def _snapshot(repo_root: Path) -> Iterator[tuple[Path, str]]:
    """A repository whose HEAD is the working tree's current state, and that commit's id."""
    with tempfile.TemporaryDirectory(prefix="verify-fix-") as tmp:
        ident = {
            "GIT_AUTHOR_NAME": "snapshot",
            "GIT_AUTHOR_EMAIL": "snapshot@example.invalid",
            "GIT_COMMITTER_NAME": "snapshot",
            "GIT_COMMITTER_EMAIL": "snapshot@example.invalid",
        }
        env = _clean_env(GIT_INDEX_FILE=os.path.join(tmp, "index"), **ident)

        def run(*cmd: str, cwd: Path = repo_root, env: dict[str, str] = env) -> str:
            out = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, check=True, text=True)
            return out.stdout.strip()

        run("git", "read-tree", "HEAD")
        run("git", "add", "-A")
        tree = run("git", "write-tree")
        sha = run("git", "commit-tree", tree, "-p", "HEAD", "-m", "verify-fix snapshot")
        clone = Path(tmp) / "clone"
        plain = _clean_env(**ident)
        run(
            "git", "clone", "--shared", "--no-checkout", "-q", str(repo_root), str(clone), env=plain
        )
        run("git", "checkout", "-q", "--detach", sha, cwd=clone, env=plain)
        yield clone, sha


def _lanes(repo_root: Path, base: str, head: str, changed) -> dict[str, list[tuple[int, int]]]:
    """Touched line ranges per changed, non-deleted path, each from its own literal-path diff."""
    flags = ("--no-ext-diff", "--no-textconv", "--text", "-U0", "--no-color", "--find-renames")
    lanes: dict[str, list[tuple[int, int]]] = {}
    for c in changed:
        if c.new_path is None:
            continue
        paths = [c.new_path] if c.old_path in (None, c.new_path) else [c.old_path, c.new_path]
        text = _git(
            repo_root,
            "diff",
            *flags,
            "--src-prefix=a/",
            "--dst-prefix=b/",
            f"{base}..{head}",
            "--",
            *[f":(literal){p}" for p in paths],
        ).decode("utf-8", errors="replace")
        lanes[c.new_path] = hunk_ranges(text) or list(_WHOLE_FILE)
    return lanes


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="git-verify-fix-diff.py")
    parser.add_argument("--base", required=True, help="full object id of the commit before the fix")
    parser.add_argument(
        "--worktree", action="store_true", help="verify the uncommitted working tree, not HEAD"
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=Path.cwd(),
            env=_clean_env(),
            capture_output=True,
            text=True,
        )
        repo_root = Path(top.stdout.strip()) if top.returncode == 0 else Path.cwd()
        here = (repo_root / _VERIFIERS).is_file()
        if not _OBJECT_ID.fullmatch(args.base):
            if not here:
                print("No scripts/marketplace_ci/review_verifiers.py here; nothing to check.")
                return 0
            raise RuntimeError(f"base is not a full object id: {args.base!r}")
        at_base = (
            top.returncode == 0
            and subprocess.run(
                ["git", "cat-file", "-e", f"{args.base}:{_VERIFIERS}"],
                cwd=repo_root,
                env=_clean_env(),
                capture_output=True,
            ).returncode
            == 0
        )
        if not here and not at_base:
            print("No scripts/marketplace_ci/review_verifiers.py here; nothing to check.")
            return 0
        if not at_base:
            raise RuntimeError(
                "the verifiers are not present at --base; nothing trustworthy to run"
            )
        if not here:
            raise RuntimeError("the verifiers exist at --base but not in this working tree")

        run_verifiers, parse_name_status_z = _load_verifiers(repo_root, args.base)
        with contextlib.ExitStack() as stack:
            if args.worktree:
                verify_repo, head = stack.enter_context(_snapshot(repo_root))
            else:
                verify_repo = repo_root
                head = _git(repo_root, "rev-parse", "HEAD").decode().strip()
            raw = _git(
                repo_root, "diff", "--name-status", "-z", "--find-renames", f"{args.base}..{head}"
            )
            changed = parse_name_status_z(raw)
            if not changed:
                print(
                    json.dumps(
                        {
                            "nothing_changed": True,
                            "note": "no diff between base and head; not a pass",
                        }
                    )
                )
                return 2
            lanes = _lanes(repo_root, args.base, head, changed)
            outcomes = run_verifiers(verify_repo, changed, args.base)
    except Exception as exc:  # noqa: BLE001 - any failure must read as "could not run", never a pass
        print(f"Verifiers could not run: {exc}", file=sys.stderr)
        print(json.dumps({"could_not_run": str(exc)}))
        return 2

    checked = sorted({p for o in outcomes for p in o.checked})
    blocking, outside = [], []
    for outcome in outcomes:
        for f in outcome.findings:
            entry = {
                "verifier": outcome.name,
                "rule": f.rule,
                "path": f.path,
                "line": f.line,
                "evidence": f.evidence,
                "remediation": f.remediation,
            }
            (blocking if on_touched_line(f.path, f.line, lanes) else outside).append(entry)
    print(json.dumps({"checked": checked, "blocking": blocking, "outside_lane": outside}, indent=2))
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
