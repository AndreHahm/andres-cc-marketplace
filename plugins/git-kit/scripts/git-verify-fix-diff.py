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

The verifier modules are loaded (`git archive`) from the commit where HEAD last met the target
branch (`refs/remotes/origin/HEAD`), never from the tree being judged and never from `--base`: a
PR's own earlier commit can precede `--base`, and the loaded modules are imported and run. Without
that ref, or when `origin`'s fetch URL is not the required `--upstream owner/repo` (the PR's base
repository), the run exits 2. This driver runs from wherever it was started, so the exit 2 below
for a fix that changes the verifiers (scripts/marketplace_ci/), their registry
(.claude/marketplace-sync.json) or this script only catches an honest edit. Such a fix cannot be
judged by them, so it exits 2. A `--worktree` run snapshots the working tree into a throwaway
commit built with a temporary
index and verifies it in a temporary shared clone: no ref, the real index or the working tree is
touched, and no object is written to the repository's object store. The snapshot's objects
(including any untracked, non-ignored file) go to a temporary object directory that a normal exit
or an exception deletes; a SIGKILL or SIGTERM leaves it (mode 0700, in the system temp directory).
A `--worktree` run in a sparse checkout exits 2: the snapshot's fresh index would record every
file outside the sparse cone as deleted.
Without `--worktree` the committed HEAD is verified in a temporary clone, whatever the disk holds.

Needs PyYAML and markdown-it-py (the verifiers' own imports); without them every run exits 2.

Exit codes: 0 clean, 1 a blocking finding, 2 not verified (the verifiers could not run, nothing
changed, or the fix touches what grades it) - never a pass. Exit 0 with "nothing to check" only
where neither the target branch nor the working tree has scripts/marketplace_ci/review_verifiers.py
(git-kit is installed in other repositories). A clean result with an empty `checked` list means
no changed file was a verifier-covered component: do not report it as "verifiers passed".
"""

from __future__ import annotations

# ruff: noqa: E402
import os
import sys

# Python puts this script's own directory first on sys.path. In a checked-out PR that directory is
# PR content, so a sibling argparse.py or yaml.py would be imported in place of the real module.
_HERE = os.path.dirname(os.path.realpath(__file__))
sys.path[:] = [p for p in sys.path if os.path.realpath(p or os.curdir) != _HERE]

import argparse
import atexit
import contextlib
import functools
import io
import json
import re
import shutil
import subprocess  # nosec B404  # runs git with list arguments, never a shell
import tarfile
import tempfile
from collections.abc import Iterator
from pathlib import Path

_OBJECT_ID = re.compile(r"[0-9a-f]{40}|[0-9a-f]{64}")
_REPO = r"[A-Za-z0-9._-]+/[A-Za-z0-9._-]+"
_UPSTREAM = re.compile(_REPO)
_ORIGIN_URL = re.compile(
    rf"(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)({_REPO}?)(?:\.git)?/?"
)
_VERIFIERS = "scripts/marketplace_ci/review_verifiers.py"
_UNJUDGEABLE = (
    "scripts/marketplace_ci/",
    ".claude/marketplace-sync.json",
    "plugins/git-kit/scripts/git-verify-fix-diff.py",
    ".claude/scripts/git-verify-fix-diff.py",
)
# The only inherited variables git is given: locale and time zone. Everything else (GIT_DIR,
# GIT_CONFIG_*, GIT_TRACE*, GIT_EXEC_PATH, HOME, XDG_CONFIG_HOME, PAGER, ...) is dropped (#588).
_KEEP_ENV = ("LANG", "LC_ALL", "LC_CTYPE", "TZ")
# Repository configuration can name an fsmonitor command, and hooks run on index writes and
# checkouts; both are switched off on every call. `git add -A` still runs a clean filter that the
# repository's own configuration defines.
_HARDENING = ("-c", "core.fsmonitor=false", "-c", f"core.hooksPath={os.devnull}")


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


@functools.cache
def _git_path() -> str:
    found = _find_git()
    if found is None:
        raise RuntimeError("no usable git: it is missing, or found inside the repository")
    return found


def _git_cmd(*args: str) -> list[str]:
    return [_git_path(), *_HARDENING, *args]


def _clone_args(tmp: str) -> list[str]:
    """A local shared clone with an empty template directory, so no template hook is copied in."""
    template = os.path.join(tmp, "no-template")
    os.makedirs(template, exist_ok=True)
    return ["--shared", "--no-checkout", "-q", f"--template={template}"]


_PINNED_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
}


def _clean_env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in _KEEP_ENV}
    env["PATH"] = os.path.dirname(_git_path())
    env.update(_PINNED_ENV)
    env.update(extra)
    return env


def _git(cwd: Path, *args: str, env: dict[str, str] | None = None) -> bytes:
    return subprocess.run(  # nosec B603 B607  # literal git subcommand, list arguments, no shell
        _git_cmd(*args), cwd=cwd, env=env or _clean_env(), capture_output=True, check=True
    ).stdout


def _origin_repo(repo_root: Path) -> str | None:
    """`owner/repo` named by origin's fetch URL when it is a GitHub URL, else None."""
    out = subprocess.run(  # nosec B603 B607  # literal git subcommand, list arguments, no shell
        _git_cmd("remote", "get-url", "origin"),
        cwd=repo_root,
        env=_clean_env(),
        capture_output=True,
        text=True,
    )
    matched = _ORIGIN_URL.fullmatch(out.stdout.strip()) if out.returncode == 0 else None
    return matched.group(1) if matched else None


def _target_ref(repo_root: Path) -> str | None:
    """The target branch: whatever `refs/remotes/origin/HEAD` points at, or None.

    This is local state; main() only trusts it after `origin` is confirmed to be --upstream."""
    out = subprocess.run(  # nosec B603 B607  # literal git subcommand, list arguments, no shell
        _git_cmd("symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"),
        cwd=repo_root,
        env=_clean_env(),
        capture_output=True,
        text=True,
    )
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def _has_verifiers(repo_root: Path, rev: str) -> bool:
    return (
        subprocess.run(  # nosec B603 B607  # literal git subcommand, list arguments, no shell
            _git_cmd("cat-file", "-e", f"{rev}^{{commit}}:{_VERIFIERS}"),
            cwd=repo_root,
            env=_clean_env(),
            capture_output=True,
        ).returncode
        == 0
    )


def _trusted_commit(repo_root: Path, target: str, head_sha: str) -> str:
    """The commit the verifiers are loaded from: where `head_sha` last met the target branch.

    Nothing on the PR's own branch (including --base, which a PR author's earlier commit can
    precede) is trusted to supply code that this script then imports. The branch still picks
    which version of the target's verifiers judges it: the one at that merge-base."""
    merged = subprocess.run(  # nosec B603 B607  # literal git subcommand, list arguments, no shell
        _git_cmd("merge-base", head_sha, target),
        cwd=repo_root,
        env=_clean_env(),
        capture_output=True,
        text=True,
    )
    sha = merged.stdout.strip()
    if merged.returncode != 0 or not _OBJECT_ID.fullmatch(sha):
        raise RuntimeError("HEAD shares no history with the target branch; no trusted verifiers")
    return sha


def _load_verifiers(extract_root: Path, base: str):
    """`run_verifiers` and `parse_name_status_z` as at `base`, imported from a private copy.

    `base` is the trusted commit (see `_trusted_commit`), never the caller's --base."""
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
        objects = os.path.join(tmp, "objects")  # the snapshot's objects land here, not in the repo
        os.makedirs(os.path.join(objects, "info"))
        real_objects = _git(
            repo_root, "rev-parse", "--path-format=absolute", "--git-path", "objects"
        ).decode()
        with open(os.path.join(objects, "info", "alternates"), "w", encoding="utf-8") as handle:
            handle.write(real_objects.strip() + "\n")  # read the repo's objects, never write them
        env = _clean_env(
            GIT_INDEX_FILE=os.path.join(tmp, "index"), GIT_OBJECT_DIRECTORY=objects, **ident
        )

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
        run("clone", *_clone_args(tmp), str(repo_root), str(clone), env=plain)
        alternates = clone / ".git" / "objects" / "info" / "alternates"
        with alternates.open("a", encoding="utf-8") as handle:
            handle.write(objects + "\n")  # lets the clone read the snapshot commit
        run("checkout", "-q", "--detach", sha, cwd=clone, env=plain)
        yield clone, sha


@contextlib.contextmanager
def _commit_clone(repo_root: Path, sha: str) -> Iterator[tuple[Path, str]]:
    """A temporary shared clone checked out at `sha`: the files on disk are exactly that commit."""
    with tempfile.TemporaryDirectory(prefix="verify-fix-") as tmp:
        clone = Path(tmp) / "clone"
        _git(repo_root, "clone", *_clone_args(tmp), str(repo_root), str(clone))
        _git(clone, "checkout", "-q", "--detach", sha)
        yield clone, sha


def main(argv: list[str] | None = None) -> int:
    # The verifiers' own git calls inherit os.environ: drop every GIT_* variable (GIT_DIR,
    # GIT_TRACE, GIT_CONFIG_*, ...), pin the configuration, and put the vetted git first on PATH.
    for var in [k for k in os.environ if k.startswith("GIT_")]:
        del os.environ[var]
    os.environ.update(_PINNED_ENV)
    parser = argparse.ArgumentParser(prog="git-verify-fix-diff.py")
    parser.add_argument("--base", required=True, help="full object id of the commit before the fix")
    parser.add_argument(
        "--upstream",
        required=True,
        help="owner/repo of the PR's base repository; origin's fetch URL must name it",
    )
    parser.add_argument(
        "--worktree", action="store_true", help="verify the uncommitted working tree, not HEAD"
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 0 if exc.code == 0 else 2

    try:
        os.environ["PATH"] = os.pathsep.join(
            [os.path.dirname(_git_path()), os.environ.get("PATH", "")]
        )
        top = subprocess.run(  # nosec B603 B607  # literal git subcommand, list arguments, no shell
            _git_cmd("rev-parse", "--show-toplevel"),
            cwd=Path.cwd(),
            env=_clean_env(LC_ALL="C"),
            capture_output=True,
            text=True,
        )
        if top.returncode != 0 and "not a git repository" not in top.stderr:
            raise RuntimeError(f"git could not locate the repository: {top.stderr.strip()}")
        in_repo = top.returncode == 0
        repo_root = Path(top.stdout.strip()) if in_repo else Path.cwd()
        here = (repo_root / _VERIFIERS).is_file()
        if in_repo and not _OBJECT_ID.fullmatch(args.base):
            raise RuntimeError(f"base is not a full object id: {args.base!r}")
        target = _target_ref(repo_root) if in_repo else None
        at_target = target is not None and _has_verifiers(repo_root, target)
        if not here and not at_target:
            print(
                f"No scripts/marketplace_ci/review_verifiers.py in {repo_root}; nothing to check."
            )
            return 0
        if not in_repo:
            raise RuntimeError("not inside a git repository; the verifiers cannot be anchored")
        if target is None:
            raise RuntimeError(
                "no refs/remotes/origin/HEAD to anchor the verifiers "
                "(git remote set-head origin -a)"
            )
        if not _UPSTREAM.fullmatch(args.upstream):
            raise RuntimeError(f"--upstream is not owner/repo: {args.upstream!r}")
        origin = _origin_repo(repo_root)
        if origin is None or origin.lower() != args.upstream.lower():
            raise RuntimeError(
                f"origin ({origin or 'not a GitHub URL'}) is not {args.upstream}; "
                "refusing to import verifiers from its default branch"
            )
        head_sha = _git(repo_root, "rev-parse", "HEAD").decode().strip()
        trusted = _trusted_commit(repo_root, target, head_sha)
        if not _has_verifiers(repo_root, trusted):
            raise RuntimeError(
                "the verifiers are not present where HEAD met the target branch; "
                "nothing trustworthy to run"
            )
        if not here:
            raise RuntimeError("the verifiers exist at the target branch but not in this tree")
        ancestor = subprocess.run(  # nosec B603 B607  # literal git subcommand, list args, no shell
            _git_cmd("merge-base", "--is-ancestor", args.base, head_sha),
            cwd=repo_root,
            env=_clean_env(),
            capture_output=True,
        )
        if ancestor.returncode != 0:
            raise RuntimeError("--base is not an ancestor of HEAD")
        sparse = _git(repo_root, "config", "--bool", "--default", "false", "core.sparseCheckout")
        if args.worktree and sparse.decode().strip() == "true":
            raise RuntimeError("--worktree does not support a sparse checkout")

        run_verifiers, parse_name_status_z = _load_verifiers(repo_root, trusted)
        with contextlib.ExitStack() as stack:
            if args.worktree:
                verify_repo, head = stack.enter_context(_snapshot(repo_root, head_sha))
            else:
                verify_repo, head = stack.enter_context(_commit_clone(repo_root, head_sha))
            raw = _git(
                verify_repo, "diff", "--name-status", "-z", "--find-renames", f"{args.base}..{head}"
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
