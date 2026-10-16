#!/usr/bin/env python3
"""Outcomes ledger for `handling-review-findings`: one disposition per review finding.

Two JSON files with the same shape, {"entries": [...]}:
  - a local, gitignored working ledger (default .claude/review-ledger.local.json), written
    during the fix loop;
  - a git-tracked file (default .claude/review-outcomes.json) that `promote` fills with a
    PR's entries before its last push.

Subcommands: record, refuted, promote. Exit codes: 0 ok, 2 refused (bad input, or a ledger file
that is not valid JSON of the expected shape - it is never overwritten)."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

DISPOSITIONS = ("accepted", "fixed", "declined", "false_positive", "ignored")
REFUTED = (
    "false_positive",
)  # a decline can rest on a reason that lapses; only a refutation stands
DEFAULT_LOCAL = ".claude/review-ledger.local.json"
DEFAULT_TRACKED = ".claude/review-outcomes.json"


class LedgerError(Exception):
    pass


def repo_root() -> Path:
    out = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    return Path(out.stdout.strip()) if out.returncode == 0 and out.stdout.strip() else Path.cwd()


def confine(raw: str, root: Path) -> Path:
    """A ledger lives only under the repository's .claude/ directory (symlinks resolved)."""
    if (root / ".claude").is_symlink():
        raise LedgerError(f"{root / '.claude'} is a symlink; ledgers live in a real .claude/ only")
    path = Path(raw)
    resolved = (path if path.is_absolute() else root / path).resolve()
    if resolved.suffix != ".json":
        raise LedgerError(f"{raw} is not a .json file; ledgers are JSON files only")
    if (root / ".claude").resolve() not in resolved.parents:
        raise LedgerError(f"{raw} is outside {root / '.claude'}; ledgers live under .claude/ only")
    return resolved


def refuse_if_tracked(path: Path, root: Path) -> None:
    """The working ledger must stay untracked (a force-added copy could carry planted entries)."""
    rel = os.path.relpath(path, root.resolve())
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", f":(top,literal){rel}"],
        cwd=root,
        capture_output=True,
    )
    if tracked.returncode not in (0, 1):
        raise LedgerError(
            f"could not check whether {rel} is tracked (git exit {tracked.returncode})"
        )
    if tracked.returncode == 0:
        raise LedgerError(f"{rel} is tracked by git; the local working ledger must stay untracked")


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
    refuted = [
        e
        for e in [*load(args.local), *load(args.tracked)]
        if e.get("pr") == args.pr and e.get("disposition") in REFUTED
    ]
    print(json.dumps({"refuted": refuted}, indent=2))
    return 0


def cmd_promote(args: argparse.Namespace) -> int:
    local, tracked = args.local, args.tracked
    local_entries = load(local)
    moving = [e for e in local_entries if e.get("pr") == args.pr]
    if not moving:
        print(f"No ledger entries for PR {args.pr}; nothing to promote.")
        return 0
    merged = load(tracked)
    for entry in moving:
        merged = upsert(merged, entry)
    save(tracked, merged)
    save(local, [e for e in local_entries if e.get("pr") != args.pr])
    print(f"Promoted {len(moving)} entries for PR {args.pr} to {tracked}.")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="git-review-ledger.py")
    parser.add_argument("--local", default=DEFAULT_LOCAL)
    parser.add_argument("--tracked", default=DEFAULT_TRACKED)
    sub = parser.add_subparsers(dest="command", required=True)

    record = sub.add_parser("record", help="record or replace one finding's disposition")
    record.add_argument("--pr", type=int, required=True)
    record.add_argument("--finding", required=True, help="stable id, e.g. the review comment id")
    record.add_argument("--disposition", required=True, choices=DISPOSITIONS)
    record.add_argument("--path")
    record.add_argument("--line", type=int)
    record.add_argument("--rule")
    record.add_argument("--note")
    record.set_defaults(func=cmd_record)

    refuted = sub.add_parser("refuted", help="list a PR's false-positive entries")
    refuted.add_argument("--pr", type=int, required=True)
    refuted.set_defaults(func=cmd_refuted)

    promote = sub.add_parser("promote", help="move a merged PR's entries to the tracked file")
    promote.add_argument("--pr", type=int, required=True)
    promote.set_defaults(func=cmd_promote)
    return parser


def main(argv: list[str] | None = None) -> int:
    for var in ("GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_COMMON_DIR", "GIT_PREFIX"):
        os.environ.pop(var, None)
    try:
        args = build_parser().parse_args(argv)
    except SystemExit as exc:
        return int(exc.code) if isinstance(exc.code, int) and exc.code == 0 else 2
    try:
        root = repo_root()
        args.local = confine(args.local, root)
        args.tracked = confine(args.tracked, root)
        if args.local == args.tracked:
            raise LedgerError("--local and --tracked must be different files")
        refuse_if_tracked(args.local, root)
        return args.func(args)
    except LedgerError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"Refused: could not read or write a ledger file: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
