#!/usr/bin/env python3
"""Outcomes ledger for `handling-review-findings`: one disposition per review finding.

JSON files with the same shape, {"entries": [...]}:
  - a local, gitignored working ledger (default .claude/review-ledger.local.json), written
    during the fix loop (`record` adds it to the repository's .git/info/exclude when no ignore
    rule covers it);
  - a git-tracked directory (default .claude/review-outcomes/) holding one pr-<N>.json per PR,
    which `promote` fills with that PR's entries before its last push. A PR writes only its own
    file, so concurrent PRs never edit the same lines and never conflict.

Subcommands: record, refuted, promote. Exit codes: 0 ok, 2 refused (bad input, or a ledger file
that is not valid JSON of the expected shape - it is never overwritten)."""

from __future__ import annotations

import argparse
import functools
import json
import os
import re
import shutil
import subprocess  # nosec B404  # runs git with list arguments, never a shell
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

DISPOSITIONS = ("accepted", "fixed", "declined", "false_positive", "ignored")
REFUTED = (
    "false_positive",
)  # a decline can rest on a reason that lapses; only a refutation stands
DEFAULT_LOCAL = ".claude/review-ledger.local.json"
DEFAULT_TRACKED = ".claude/review-outcomes"
PR_FILE = re.compile(r"pr-([1-9][0-9]*)\.json")
# save()'s temp file (mkstemp, prefix "<name>.", suffix ".tmp"): a hard kill can leave one behind.
SAVE_TEMP = re.compile(r"pr-[1-9][0-9]*\.json\.[A-Za-z0-9_]+\.tmp")
# The only inherited variables git is given: locale and time zone. Everything else (GIT_DIR,
# GIT_CONFIG_*, GIT_TRACE*, GIT_EXEC_PATH, HOME, XDG_CONFIG_HOME, PAGER, ...) is dropped (#588).
# Mirrors git-verify-fix-diff.py, which documents the same choices.
_KEEP_ENV = ("LANG", "LC_ALL", "LC_CTYPE", "TZ")
# Repository configuration can name an fsmonitor command, and hooks run on index writes and
# checkouts; both are switched off on every call.
_HARDENING = ("-c", "core.fsmonitor=false", "-c", f"core.hooksPath={os.devnull}")
_PINNED_ENV = {
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_NO_LAZY_FETCH": "1",
    "GIT_NO_REPLACE_OBJECTS": "1",
    "GIT_OPTIONAL_LOCKS": "0",
    "GIT_TERMINAL_PROMPT": "0",
}


class LedgerError(Exception):
    pass


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
        raise LedgerError("no usable git: it is missing, or found inside the repository")
    return found


def _clean_env() -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k in _KEEP_ENV}
    env["PATH"] = os.path.dirname(_git_path())
    env.update(_PINNED_ENV)
    return env


def _git(
    cwd: Path,
    *args: str,
    text: bool = False,
    env: dict[str, str] | None = None,
    repin: bool = True,
) -> subprocess.CompletedProcess:
    trusted = (
        [part for d in _trusted_directories() for part in ("-c", f"safe.directory={d}")]
        if repin
        else []
    )
    return subprocess.run(  # nosec B603 B607  # literal git subcommand, list arguments, no shell
        [_git_path(), *_HARDENING, *trusted, *args],
        cwd=cwd,
        env=env or _clean_env(),
        capture_output=True,
        text=text,
    )


@functools.cache
def _trusted_directories() -> tuple[str, ...]:
    """The `safe.directory` entries in the user's own global git configuration.

    Git honours them only from protected configuration, which the pinned environment discards, so a
    checkout owned by another user (a host-mounted repository in a container) would be refused. Only
    these values are read back, as data, and passed on the command line; every other global setting
    stays out. Values come in order and empty ones are kept: for git an empty value resets the list,
    so a directory the user revoked stays revoked. A leading `~` is expanded here, because the
    pinned environment has no HOME for git to do it. `-z` keeps a value with an escaped newline in
    one piece. Entries in `include`d files are not read, so such a checkout is still refused. A
    configuration file the checkout could have written (a file under it, or the target of a link in
    HOME) is branch content, not the user's own, and is ignored."""
    home = os.environ.get("HOME", "")
    if not os.path.isabs(home) or not os.path.isdir(home):
        return ()
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    config_dirs = [home, xdg] if os.path.isabs(xdg) else [home]
    try:
        here = Path(os.path.realpath(Path.cwd()))
        guards = [here, *_repository_roots(here)]
        xdg_dir = xdg if len(config_dirs) == 2 else str(Path(home) / ".config")
        files = [Path(d) / "config" for d in config_dirs]  # the directories themselves
        files += [  # and where the two files git reads really are, which a link can move
            Path(os.path.realpath(Path(home) / ".gitconfig")),
            Path(os.path.realpath(Path(xdg_dir) / "git" / "config")),
        ]
        if any(_is_inside(f, guards) for f in files):
            return ()
        env = {
            "HOME": home,
            "PATH": os.path.dirname(_git_path()),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
        }
        if len(config_dirs) == 2:
            env["XDG_CONFIG_HOME"] = xdg
        read = _git(
            Path(home),
            "config",
            "--global",
            "-z",
            "--get-all",
            "safe.directory",
            env=env,
            repin=False,
        )
    except (OSError, ValueError):
        return ()
    if read.returncode != 0:
        return ()
    values = os.fsdecode(read.stdout).split("\0")
    entries = values[:-1] if values[-1] == "" else values
    # Git expands a leading `~/` or `~user/` itself, but its pinned environment has no HOME to do it
    # with; an entry that cannot be expanded would make git die on every check, so it is dropped.
    expanded = (os.path.expanduser(v) if v.startswith("~") else v for v in entries)
    return tuple(v for v in expanded if not v.startswith("~"))


def repo_root() -> Path:
    out = _git(Path.cwd(), "rev-parse", "--show-toplevel", text=True)
    return Path(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else Path.cwd()


def confine(raw: str, root: Path, directory: bool = False) -> Path:
    """A ledger lives only under the repository's .claude/ directory (symlinks resolved)."""
    if (root / ".claude").is_symlink():
        raise LedgerError(f"{root / '.claude'} is a symlink; ledgers live in a real .claude/ only")
    path = Path(raw)
    candidate = path if path.is_absolute() else root / path
    if candidate.is_symlink():  # a tracked symlink could name a ledger the PR chose
        raise LedgerError(f"{raw} is a symlink; ledgers are regular files only")
    resolved = candidate.resolve()
    if any(ord(c) < 32 for c in str(resolved)):
        raise LedgerError("a ledger path may not contain control characters")
    if not directory and resolved.suffix != ".json":
        raise LedgerError(f"{raw} is not a .json file; ledgers are JSON files only")
    if (root / ".claude").resolve() not in resolved.parents:
        raise LedgerError(f"{raw} is outside {root / '.claude'}; ledgers live under .claude/ only")
    return resolved


def refuse_if_tracked(path: Path, root: Path) -> None:
    """The working ledger must stay untracked (a force-added copy could carry planted entries)."""
    rel = os.path.relpath(path, root.resolve())
    tracked = _git(root, "ls-files", "--error-unmatch", "--", f":(top,literal){rel}")
    if tracked.returncode not in (0, 1):
        raise LedgerError(
            f"could not check whether {rel} is tracked (git exit {tracked.returncode})"
        )
    if tracked.returncode == 0:
        raise LedgerError(f"{rel} is tracked by git; the local working ledger must stay untracked")


def ensure_ignored(path: Path, root: Path) -> None:
    """Keep the working ledger out of `git status`, whatever the repository's own ignore rules say.

    Where nothing ignores it (a repository without a `*.local.*` rule), add it to this
    repository's `info/exclude`; refuse to write the ledger if git still does not ignore it."""
    rel = os.path.relpath(path, root.resolve())

    def ignored() -> bool:
        probe = _git(root, "check-ignore", "-q", "--no-index", "--", rel)
        if probe.returncode not in (0, 1):
            raise LedgerError(
                f"could not check whether {rel} is ignored (git exit {probe.returncode})"
            )
        return probe.returncode == 0

    if ignored():
        return
    located = _git(root, "rev-parse", "--git-path", "info/exclude", text=True)
    if located.returncode != 0 or not located.stdout.strip():
        raise LedgerError(f"could not locate this repository's info/exclude to ignore {rel}")
    exclude = Path(located.stdout.strip())
    exclude = exclude if exclude.is_absolute() else root / exclude
    exclude.parent.mkdir(parents=True, exist_ok=True)
    escaped = "".join("\\" + c if c in "*?[\\" else c for c in rel.replace(os.sep, "/"))
    with exclude.open("a", encoding="utf-8") as handle:
        handle.write(f"/{escaped}\n")
    if not ignored():
        raise LedgerError(f"{rel} is not ignored by git and could not be excluded; not writing it")


def load(path: Path) -> list[dict]:
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise LedgerError(f"{path} is not readable JSON: {exc}") from exc
    entries = data.get("entries") if isinstance(data, dict) else None
    if not isinstance(entries, list) or not all(isinstance(e, dict) for e in entries):
        raise LedgerError(f'{path} does not have the shape {{"entries": [...]}}')
    return entries


def save(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=path.name + ".", suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump({"entries": entries}, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


_FINDING_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9._:-]{0,63}")


def finding_id(raw: str) -> str:
    """A stable finding id (a review comment id or node id): a short token of ASCII letters, digits
    and . _ : - only."""
    if not _FINDING_ID.fullmatch(raw):
        raise argparse.ArgumentTypeError(
            f"{raw[:40]!r} is not a finding id: 1 to 64 ASCII letters, digits or . _ : -"
        )
    return raw


def positive_int(raw: str) -> int:
    """A PR number: the tracked layout names its files pr-<N>.json, so N is 1 or greater."""
    try:
        value = int(raw)
    except ValueError:
        raise argparse.ArgumentTypeError(f"{raw!r} is not a PR number") from None
    if value < 1:
        raise argparse.ArgumentTypeError("a PR number must be 1 or greater")
    return value


def pr_file(directory: Path, pr: int) -> Path:
    return directory / f"pr-{pr}.json"


def _check_regular(path: Path) -> None:
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise LedgerError(f"{path} is not a regular file; tracked ledgers are regular files only")


def load_pr(directory: Path, pr: int) -> list[dict]:
    """One PR's tracked entries; a file carrying another PR's entry is refused."""
    path = pr_file(directory, pr)
    _check_regular(path)
    entries = load(path)
    if any(e.get("pr") != pr for e in entries):
        raise LedgerError(f"{path} holds entries for a PR other than {pr}")
    return entries


def load_dir(directory: Path) -> list[dict]:
    """Every PR's tracked entries in PR-number order (the corpus reader; a bad file refuses)."""
    if not directory.exists():
        return []
    if not directory.is_dir():
        raise LedgerError(f"{directory} is not a directory")
    numbered = []
    for child in directory.iterdir():
        if SAVE_TEMP.fullmatch(child.name):
            continue  # an interrupted save's leftover is not a ledger file and is never read
        match = PR_FILE.fullmatch(child.name)
        if not match:
            raise LedgerError(f"{child} is not named pr-<N>.json")
        numbered.append((int(match.group(1)), child))
    entries: list[dict] = []
    for pr, _ in sorted(numbered):
        entries += load_pr(directory, pr)
    return entries


def _sort_key(entry: dict) -> tuple:
    finding = str(entry.get("finding", ""))
    if not (finding.isascii() and finding.isdigit()):
        return (True, 0, finding)
    normalized = finding.lstrip("0") or "0"  # compare by length then text: no int(), no digit limit
    return (False, len(normalized), normalized, finding)


def _key(entry: dict) -> tuple:
    return (entry.get("pr"), entry.get("finding"))


def upsert(entries: list[dict], entry: dict) -> list[dict]:
    return [e for e in entries if _key(e) != _key(entry)] + [entry]


def cmd_record(args: argparse.Namespace) -> int:
    local = args.local
    entries = load(local)
    entry = {
        "pr": args.pr,
        "finding": args.finding,
        "disposition": args.disposition,
        "recorded_at": datetime.now(UTC).isoformat(timespec="seconds"),
    }
    for field in ("path", "line", "rule", "note"):
        value = getattr(args, field)
        if value is not None:
            entry[field] = value
    save(local, upsert(entries, entry))
    return 0


def cmd_refuted(args: argparse.Namespace) -> int:
    merged = load_pr(args.tracked, args.pr)
    for entry in load(args.local):  # a later local record replaces the promoted one
        merged = upsert(merged, entry)
    refuted = [e for e in merged if e.get("pr") == args.pr and e.get("disposition") in REFUTED]
    print(json.dumps({"refuted": refuted}, indent=2))
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    local, tracked = args.local, args.tracked
    local_entries = load(local)
    moving = [e for e in local_entries if e.get("pr") == args.pr]
    if not moving:
        print(f"No ledger entries for PR {args.pr}; nothing to promote.")
        return 0
    merged = load_pr(tracked, args.pr)
    for entry in moving:
        merged = upsert(merged, entry)
    target = pr_file(tracked, args.pr)
    save(target, sorted(merged, key=_sort_key))
    save(local, [e for e in local_entries if e.get("pr") != args.pr])
    print(f"Promoted {len(moving)} entries for PR {args.pr} to {target}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="git-review-ledger.py")
    parser.add_argument("--local", default=DEFAULT_LOCAL)
    parser.add_argument("--tracked", default=DEFAULT_TRACKED)
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record", help="record or replace one finding's disposition")
    record.add_argument("--pr", type=positive_int, required=True)
    record.add_argument(
        "--finding", type=finding_id, required=True, help="stable id, e.g. the review comment id"
    )
    record.add_argument("--disposition", required=True, choices=DISPOSITIONS)
    record.add_argument("--path")
    record.add_argument("--line", type=int)
    record.add_argument("--rule")
    record.add_argument("--note")
    record.set_defaults(func=cmd_record)

    refuted = sub.add_parser("refuted", help="list a PR's false-positive entries")
    refuted.add_argument("--pr", type=positive_int, required=True)
    refuted.set_defaults(func=cmd_refuted)

    promote = sub.add_parser("promote", help="move a PR's entries to its tracked pr-<N>.json")
    promote.add_argument("--pr", type=positive_int, required=True)
    promote.set_defaults(func=cmd_promote)
    return parser


def main(argv: list[str] | None = None) -> int:
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) and exc.code == 0 else 2
    try:
        root = repo_root()
        args.local = confine(args.local, root)
        args.tracked = confine(args.tracked, root, directory=True)
        if args.tracked.exists() and not args.tracked.is_dir():
            raise LedgerError(f"--tracked {args.tracked} must be a directory")
        if args.local == args.tracked or args.tracked in args.local.parents:
            raise LedgerError("--local must be a different file, outside the --tracked directory")
        refuse_if_tracked(args.local, root)
        if args.command == "record":
            ensure_ignored(args.local, root)
        return args.func(args)
    except LedgerError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as exc:  # ValueError: a path that is not valid UTF-8
        print(f"Refused: could not read or write a ledger file: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
