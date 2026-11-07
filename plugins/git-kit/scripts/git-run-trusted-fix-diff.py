#!/usr/bin/env python3
"""Run git-verify-fix-diff.py as committed on the target branch, never the copy in the tree.

`handling-review-findings` step 4a re-runs the marketplace verifiers on a fix's own diff. The
driver that does so must not come from the tree being judged, or a fix that edits it would grade
itself. This launcher reads the driver from the commit where HEAD last met
`origin/<target-branch>`, writes it to a private temporary directory this script creates (mode
0700) and runs it with `python3 -I`, passing the same arguments on. It replaces three separate
commands the procedure used to ask the user to approve one by one (`git remote get-url origin`,
`git cat-file -p ... > file`, `python3 -I <file>`).

Before anything from the target branch runs, this script checks the same two things the driver
re-checks itself: `origin`'s fetch URL names `--upstream` (the PR's base repository), and the commit
supplying the driver is already on the default branch (`refs/remotes/origin/HEAD`), since the PR's
author picks its base branch. Without either, nothing is executed.

Usage: git-run-trusted-fix-diff.py --upstream OWNER/REPO --target-branch NAME --base FULL_SHA
       [--worktree]

Exit codes: the driver's own (0 clean, 1 a blocking finding, 2 not verified); 2 also for any check
here that fails; 4 when the trusted commit has no driver (git-kit is installed in a repository that
does not carry it), in which case nothing was run.
"""

from __future__ import annotations

# ruff: noqa: E402
import os
import sys

# Python puts this script's own directory first on sys.path. In a checked-out PR that directory is
# PR content, so a sibling argparse.py or subprocess.py would be imported in place of the real
# module.
_HERE = os.path.dirname(os.path.realpath(__file__))
sys.path[:] = [p for p in sys.path if os.path.realpath(p or os.curdir) != _HERE]

import argparse
import re
import shutil
import subprocess  # nosec B404  # runs git and python with list arguments, never a shell
import tempfile
from pathlib import Path

DRIVER = "plugins/git-kit/scripts/git-verify-fix-diff.py"
_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_REPO = r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+"
_UPSTREAM = re.compile(_REPO)
_BRANCH_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9._-]*(?:/[A-Za-z0-9_][A-Za-z0-9._-]*)*")
_ORIGIN_URL = re.compile(
    rf"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)({_REPO}?)(?:\.git)?/?"
)
_DRIVER_LIMIT = 2_000_000  # bytes; the driver is about 26 KB
_KEEP_ENV = ("LANG", "LC_ALL", "LC_CTYPE", "TZ")
_HARDENING = ("-c", "core.fsmonitor=false", "-c", f"core.hooksPath={os.devnull}")
_PINNED_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
}


class _Refused(Exception):
    """A check failed; nothing from the target branch was run."""


def _main_working_tree(entry: Path) -> Path | None:
    """For a linked worktree's `.git` file, the directory that owns the shared git directory."""
    lines = entry.read_text(encoding="utf-8").splitlines()
    first = lines[0] if lines else ""
    if not first.startswith("gitdir:"):
        raise ValueError(f"{entry} is not a gitdir pointer")
    gitdir = (entry.parent / first.removeprefix("gitdir:").strip()).resolve()
    commondir = gitdir / "commondir"
    if not commondir.is_file():
        return None  # a submodule: its superproject is an ancestor, which the walk finds anyway
    common = (gitdir / commondir.read_text(encoding="utf-8").strip()).resolve()
    return common.parent if common.name == ".git" else common


def _repository_roots(start: Path) -> list[Path]:
    """Every directory above `start` that a branch could have written: each ancestor holding a
    `.git` entry (a directory, or the file a linked worktree or submodule has) and, for a linked
    worktree, the main working tree. Found without running git."""
    roots: list[Path] = []
    for candidate in (start, *start.parents):
        entry = candidate / ".git"
        if not entry.exists():
            continue
        roots.append(candidate)
        if entry.is_file():
            main = _main_working_tree(entry)
            if main is not None:
                roots.append(main)
    return roots


def _is_inside(path: Path, guards: list[Path]) -> bool:
    """Whether `path` lies under a guard, compared by file identity: letter case on a
    case-insensitive file system, bind mounts and other aliases cannot hide a match."""
    stats = []
    for guard in guards:
        try:
            stats.append(os.stat(guard))
        except OSError:
            continue
    for parent in path.parents:
        try:
            seen = os.stat(parent)
        except OSError:
            continue
        if any(os.path.samestat(seen, other) for other in stats):
            return True
    return False


def _find_git() -> str | None:
    """An absolute path to git that is not inside the repository the script was started in."""
    found = shutil.which("git")
    if not found or not os.path.isabs(found):  # an empty or relative PATH entry resolves here
        return None
    here = Path(os.path.realpath(Path.cwd()))
    try:
        guards = [here, *_repository_roots(here)]
    except (OSError, ValueError):
        return None  # a `.git` entry that cannot be read is not trusted
    # The path as found and where it resolves both count: a symlink in the repository is its file.
    for candidate in (Path(os.path.abspath(found)), Path(os.path.realpath(found))):
        if _is_inside(candidate, guards):
            return None
    return found


def _git_env(git: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in _KEEP_ENV}
    env["PATH"] = os.path.dirname(git)
    env.update(_PINNED_ENV)
    return env


def _run_git(git: str, cwd: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(  # nosec B603  # list arguments, no shell; git is a vetted absolute path
        [git, *_HARDENING, *args], cwd=cwd, env=_git_env(git), capture_output=True
    )


def _out(done: subprocess.CompletedProcess[bytes]) -> str:
    return done.stdout.decode(errors="replace").strip() if done.returncode == 0 else ""


def _trusted_driver(git: str, upstream: str, branch: str) -> bytes | None:
    """The driver's source at the trusted commit, or None when that commit does not carry it.

    Raises _Refused unless origin is `upstream` and the trusted commit is on the default branch."""
    cwd = Path.cwd()
    top = _out(_run_git(git, cwd, "rev-parse", "--show-toplevel"))
    if not top:
        raise _Refused("not inside a git repository")
    root = Path(top)
    matched = _ORIGIN_URL.fullmatch(_out(_run_git(git, root, "remote", "get-url", "origin")))
    if matched is None or matched.group(1).lower() != upstream.lower():
        named = matched.group(1) if matched else "not a GitHub URL"
        raise _Refused(f"origin ({named}) is not {upstream}; refusing to take the driver from it")
    target = f"refs/remotes/origin/{branch}"
    if not _OBJECT_ID.fullmatch(
        _out(_run_git(git, root, "rev-parse", "--verify", "--quiet", f"{target}^{{commit}}"))
    ):
        raise _Refused(f"no {target} to anchor the driver (git fetch origin <branch>)")
    default = _out(_run_git(git, root, "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"))
    head = _out(_run_git(git, root, "rev-parse", "HEAD"))
    trusted = _out(_run_git(git, root, "merge-base", head, target))
    if not _OBJECT_ID.fullmatch(head) or not _OBJECT_ID.fullmatch(trusted):
        raise _Refused("HEAD shares no history with the target branch; no trusted driver")
    default_name = default.removeprefix("refs/remotes/origin/")
    if (
        not default.startswith("refs/remotes/origin/")
        or not _BRANCH_NAME.fullmatch(default_name)
        or ".." in default_name
        or _run_git(git, root, "merge-base", "--is-ancestor", trusted, default).returncode
    ):
        raise _Refused(
            f"the commit where HEAD met origin/{branch} is not on the default branch "
            "(refs/remotes/origin/HEAD); refusing to run the driver from it"
        )
    spec = f"{trusted}:{DRIVER}"
    # Resolving the path needs only trees, so a blob that is missing from a partial clone fails the
    # read below (exit 2) instead of being taken for "this commit has no driver" (exit 4).
    if _run_git(git, root, "rev-parse", "--verify", "--quiet", spec).returncode:
        return None
    blob = _run_git(git, root, "cat-file", "blob", spec)
    if blob.returncode or not blob.stdout or len(blob.stdout) > _DRIVER_LIMIT:
        raise _Refused("could not read the driver at the trusted commit")
    return blob.stdout


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="git-run-trusted-fix-diff.py", allow_abbrev=False)
    parser.add_argument("--upstream", required=True)
    parser.add_argument("--target-branch", required=True)
    parser.add_argument("--base", required=True)
    parser.add_argument("--worktree", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2  # `--help` included: a run that printed no verdict is never a pass
    if not _UPSTREAM.fullmatch(args.upstream):
        print(f"--upstream is not owner/repo: {args.upstream!r}", file=sys.stderr)
        return 2
    if not _BRANCH_NAME.fullmatch(args.target_branch) or ".." in args.target_branch:
        print(
            f"--target-branch is not a plain branch name: {args.target_branch!r}", file=sys.stderr
        )
        return 2
    if not _OBJECT_ID.fullmatch(args.base):
        print(f"--base is not a full object id: {args.base!r}", file=sys.stderr)
        return 2
    git = _find_git()
    if git is None:
        print("no usable git: it is missing, or found inside the repository", file=sys.stderr)
        return 2
    try:
        source = _trusted_driver(git, args.upstream, args.target_branch)
    except (_Refused, OSError) as exc:
        print(f"Not verified: {exc}", file=sys.stderr)
        return 2
    if source is None:
        print("The trusted commit has no git-verify-fix-diff.py; nothing was run.", file=sys.stderr)
        return 4
    try:
        tmp = tempfile.mkdtemp(prefix="git-run-trusted-")  # mode 0700 on POSIX, owned by this user
    except OSError as exc:
        print(f"Not verified: no temporary directory: {exc}", file=sys.stderr)
        return 2
    try:
        driver = Path(tmp) / "git-verify-fix-diff.py"
        driver.write_bytes(source)
        command = [sys.executable, "-I", str(driver), "--base", args.base]
        command += ["--upstream", args.upstream, "--target-branch", args.target_branch]
        if args.worktree:
            command.append("--worktree")
        return subprocess.run(command, cwd=Path.cwd()).returncode  # nosec B603  # no shell
    except OSError as exc:
        print(f"Not verified: could not run the driver: {exc}", file=sys.stderr)
        return 2
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    raise SystemExit(main())
