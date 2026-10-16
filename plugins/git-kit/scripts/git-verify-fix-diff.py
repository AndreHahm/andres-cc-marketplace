#!/usr/bin/env python3
"""Re-run this repository's Phase 2 verifiers on a fix's own diff (review-findings step 4).

Diffs `--base` (the commit before the fix) against HEAD - or, with `--worktree`, against the
uncommitted working tree (tracked changes and new, non-ignored files), so a fix can be checked
before it is committed. Runs `run_verifiers` over the changed paths; every finding it returns
blocks. This is touched-file logic with no touched-line filter of its own. It is not the CI
verdict: the verifiers that compare with a base (size tiers, known paths, call-graph edges) compare
with `--base`, the commit before the fix, so a value that was already over a limit before the fix
and is not worse after it passes here, and CI can still block it.
Prints one JSON object: {"checked": [...], "blocking": [...]}.

The verifier modules are loaded from `--base` (`git archive`), never from the tree being judged;
this driver runs from wherever it was started, so the exit 2 below for a fix that changes the
verifiers (scripts/marketplace_ci/), their registry (.claude/marketplace-sync.json) or this
script only catches an honest edit. Such a fix cannot be judged by them, so it exits 2. A
`--worktree` run snapshots the working tree into a throwaway commit built with a temporary
index and verifies it in a temporary shared clone: no ref, the real index or the working tree
is touched, but the snapshot's objects (including any untracked, non-ignored file) are written
to the repository's object store as unreachable objects until `git gc` prunes them. Without
`--worktree` the committed HEAD is verified in a temporary clone, whatever the disk holds.

Needs PyYAML and markdown-it-py (the verifiers' own imports); without them every run exits 2.

Exit codes: 0 clean, 1 a blocking finding, 2 not verified (the verifiers could not run, nothing
changed, or the fix touches what grades it) - never a pass. Exit 0 with "nothing to check" only
where neither the base nor the working tree has scripts/marketplace_ci/review_verifiers.py
(git-kit is installed in other repositories). A clean result with an empty `checked` list means
no changed file was a verifier-covered component: do not report it as "verifiers passed".
"""

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
_VERIFIERS = "scripts/marketplace_ci/review_verifiers.py"
_UNJUDGEABLE = (
    "scripts/marketplace_ci/",
    ".claude/marketplace-sync.json",
    "plugins/git-kit/scripts/git-verify-fix-diff.py",
    ".claude/scripts/git-verify-fix-diff.py",
)
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
def _snapshot(repo_root: Path, head_sha: str) -> Iterator[tuple[Path, str]]:
    """A repository whose HEAD is the working tree's current state, and that commit's id."""
    with tempfile.TemporaryDirectory(prefix="verify-fix-") as tmp:
        ident = {
            "GIT_AUTHOR_NAME": "snapshot",
            "GIT_AUTHOR_EMAIL": "snapshot@example.invalid",
            "GIT_COMMITTER_NAME": "snapshot",
            "GIT_COMMITTER_EMAIL": "snapshot@example.invalid",
        }
        env = _clean_env(GIT_INDEX_FILE=os.path.join(tmp, "index"), **ident)

        def run(*args: str, cwd: Path = repo_root, env: dict[str, str] = env) -> str:
            return _git(cwd, *args, env=env).decode().strip()

        run("read-tree", head_sha)
        run("add", "-A")
        tree = run("write-tree")
        sha = run(
            "-c", "commit.gpgsign=false", "commit-tree", tree, "-p", head_sha, "-m", "snapshot"
        )
        clone = Path(tmp) / "clone"
        plain = _clean_env(**ident)
        run("clone", "--shared", "--no-checkout", "-q", str(repo_root), str(clone), env=plain)
        run("checkout", "-q", "--detach", sha, cwd=clone, env=plain)
        yield clone, sha


@contextlib.contextmanager
def _commit_clone(repo_root: Path, sha: str) -> Iterator[tuple[Path, str]]:
    """A temporary shared clone checked out at `sha`: the files on disk are exactly that commit."""
    with tempfile.TemporaryDirectory(prefix="verify-fix-") as tmp:
        clone = Path(tmp) / "clone"
        _git(repo_root, "clone", "--shared", "--no-checkout", "-q", str(repo_root), str(clone))
        _git(clone, "checkout", "-q", "--detach", sha)
        yield clone, sha


def main(argv: list[str] | None = None) -> int:
    for var in _GIT_LOCATION_VARS:  # the verifiers' own git calls inherit os.environ
        os.environ.pop(var, None)
    parser = argparse.ArgumentParser(prog="git-verify-fix-diff.py")
    parser.add_argument("--base", required=True, help="full object id of the commit before the fix")
    parser.add_argument(
        "--worktree", action="store_true", help="verify the uncommitted working tree, not HEAD"
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    try:
        top = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=Path.cwd(),
            env=_clean_env(),
            capture_output=True,
            text=True,
        )
        in_repo = top.returncode == 0
        repo_root = Path(top.stdout.strip()) if in_repo else Path.cwd()
        here = (repo_root / _VERIFIERS).is_file()
        if in_repo and not _OBJECT_ID.fullmatch(args.base):
            raise RuntimeError(f"base is not a full object id: {args.base!r}")
        at_base = in_repo and (
            subprocess.run(
                ["git", "cat-file", "-e", f"{args.base}^{{commit}}:{_VERIFIERS}"],
                cwd=repo_root,
                env=_clean_env(),
                capture_output=True,
            ).returncode
            == 0
        )
        if not here and not at_base:
            print(
                f"No scripts/marketplace_ci/review_verifiers.py in {repo_root}; nothing to check."
            )
            return 0
        if not at_base:
            raise RuntimeError(
                "the verifiers are not present at --base; nothing trustworthy to run"
            )
        if not here:
            raise RuntimeError("the verifiers exist at --base but not in this working tree")
        head_sha = _git(repo_root, "rev-parse", "HEAD").decode().strip()
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", args.base, head_sha],
            cwd=repo_root,
            env=_clean_env(),
            capture_output=True,
        )
        if ancestor.returncode != 0:
            raise RuntimeError("--base is not an ancestor of HEAD")

        run_verifiers, parse_name_status_z = _load_verifiers(repo_root, args.base)
        with contextlib.ExitStack() as stack:
            if args.worktree:
                verify_repo, head = stack.enter_context(_snapshot(repo_root, head_sha))
            else:
                verify_repo, head = stack.enter_context(_commit_clone(repo_root, head_sha))
            raw = _git(
                repo_root, "diff", "--name-status", "-z", "--find-renames", f"{args.base}..{head}"
            )
            changed = parse_name_status_z(raw)
            if not changed:
                note = "no diff between base and head; not a pass"
                print(json.dumps({"nothing_changed": True, "note": note}))
                return 2
            touched = {p for c in changed for p in (c.old_path, c.new_path) if p}
            if any(p.startswith(prefix) for p in touched for prefix in _UNJUDGEABLE):
                msg = (
                    "the fix changes the verifiers, their registry or this script; cannot judge it"
                )
                print(msg, file=sys.stderr)
                print(json.dumps({"cannot_judge": True, "note": msg}))
                return 2
            outcomes = run_verifiers(verify_repo, changed, args.base)
    except Exception as exc:  # noqa: BLE001 - any failure must read as "could not run", never a pass
        print(f"Verifiers could not run: {exc}", file=sys.stderr)
        print(json.dumps({"could_not_run": str(exc)}))
        return 2

    checked = sorted({p for o in outcomes for p in o.checked})
    blocking = [
        {
            "verifier": outcome.name,
            "rule": f.rule,
            "path": f.path,
            "line": f.line,
            "evidence": f.evidence,
            "remediation": f.remediation,
        }
        for outcome in outcomes
        for f in outcome.findings
    ]
    print(json.dumps({"checked": checked, "blocking": blocking}, indent=2))
    return 1 if blocking else 0


if __name__ == "__main__":
    raise SystemExit(main())
