#!/usr/bin/env python3
"""Normalize Codacy Cloud CLI JSON into one provider-neutral findings record.

Reads the JSON that `codacy pull-request ... --output json` or `codacy issues ... --output json`
wrote to a file (or stdin) and prints the record, or writes it with --output to a file inside a
scratchpad directory. It runs no command, opens no network
connection and never opens a path named inside the findings: every value in the input is data to
copy into the record, not something to act on.

Exit codes: 0 record written, 2 input unreadable, not a shape this adapter knows, or an invalid
command line. On exit 2 nothing is written to stdout, so a caller never sees a partial record.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path
from typing import Any

# POSIX only: used to check who owns the scratchpad directory. Windows has no uid, so the ownership
# check is skipped there.
getuid: Callable[[], int] | None = None
try:
    from os import getuid as _os_getuid
except ImportError:
    pass
else:
    getuid = _os_getuid

SCHEMA_VERSION = "1.0.0"
PROVIDER = "codacy"
EXIT_BAD_INPUT = 2
MAX_INPUT_BYTES = 32 * 1024 * 1024
ISSUE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
GROUP_KEYS = {"rule": ("rule",), "file": ("file",), "rule,file": ("rule", "file")}


class ShapeError(ValueError):
    """The input is not the Cloud CLI shape this adapter was verified against."""


def _obj(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ShapeError(f"{where}: expected an object, got {type(value).__name__}")
    return value


def _list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise ShapeError(f"{where}: expected a list, got {type(value).__name__}")
    return value


def _str(container: dict[str, Any], key: str, where: str, *, required: bool = True) -> str | None:
    value = container.get(key)
    if value is None:
        if required:
            raise ShapeError(f"{where}.{key}: missing")
        return None
    if not isinstance(value, str):
        raise ShapeError(f"{where}.{key}: expected a string, got {type(value).__name__}")
    return value


def _issue_id(container: dict[str, Any], where: str) -> str | None:
    value = _str(container, "issueId", where, required=False)
    if value is not None and not ISSUE_ID.fullmatch(value):
        raise ShapeError(f"{where}.issueId: not a plain identifier (letters, digits, - and _ only)")
    return value


def _line(container: dict[str, Any], where: str) -> int | None:
    value = container.get("lineNumber")
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int):
        raise ShapeError(f"{where}.lineNumber: expected an integer, got {type(value).__name__}")
    return value


def _finding(
    issue: dict[str, Any],
    where: str,
    *,
    state: str,
    tool: str | None,
    delta_type: str | None = None,
    ignored: bool = False,
) -> dict[str, Any]:
    pattern = _obj(issue.get("patternInfo"), f"{where}.patternInfo")
    return {
        "provider": PROVIDER,
        "tool": tool,
        "rule": _str(pattern, "id", f"{where}.patternInfo"),
        "severity": _str(pattern, "severityLevel", f"{where}.patternInfo"),
        "category": _str(pattern, "category", f"{where}.patternInfo"),
        "subcategory": _str(pattern, "subCategory", f"{where}.patternInfo", required=False),
        "file": _str(issue, "filePath", where),
        "line": _line(issue, where),
        "issue_id": _issue_id(issue, where),
        "message": _str(issue, "message", where),
        "state": state,
        "delta_type": delta_type,
        "ignored": ignored,
        "ignore_reason": _str(issue, "reason", where, required=False) if ignored else None,
        "ignore_comment": _str(issue, "comment", where, required=False) if ignored else None,
    }


def _pr_findings(items: list[Any], where: str, state: str) -> list[dict[str, Any]]:
    findings = []
    for index, item in enumerate(items):
        entry = _obj(item, f"{where}[{index}]")
        issue = _obj(entry.get("commitIssue"), f"{where}[{index}].commitIssue")
        tool_info = issue.get("toolInfo")
        tool = _str(
            _obj(tool_info, f"{where}[{index}].toolInfo"), "name", f"{where}[{index}].toolInfo"
        )
        delta = _str(entry, "deltaType", f"{where}[{index}]", required=False)
        findings.append(
            _finding(
                issue, f"{where}[{index}].commitIssue", state=state, tool=tool, delta_type=delta
            )
        )
    return findings


def parse_pull_request(data: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = _obj(data, "input")
    summary = _obj(root.get("pullRequest"), "pullRequest")
    pr = _obj(summary.get("pullRequest"), "pullRequest.pullRequest")
    owner = _obj(pr.get("owner"), "pullRequest.pullRequest.owner")
    number = pr.get("number")
    if isinstance(number, bool) or not isinstance(number, int):
        raise ShapeError("pullRequest.pullRequest.number: expected an integer")
    analysing = summary.get("isAnalysing")
    if not isinstance(analysing, bool):
        raise ShapeError("pullRequest.isAnalysing: expected a boolean")
    source = {
        "kind": "pr",
        "repository": f"{_str(owner, 'name', 'owner')}/"
        f"{_str(pr, 'repository', 'pullRequest.pullRequest')}",
        "pull_request": number,
        "pr_status": _str(pr, "status", "pullRequest.pullRequest", required=False),
        "head_commit_sha": _str(pr, "headCommitSha", "pullRequest.pullRequest"),
        "is_analysing": analysing,
    }
    findings = _pr_findings(_list(root.get("newIssues"), "newIssues"), "newIssues", "new")
    findings += _pr_findings(
        _list(root.get("potentialIssues"), "potentialIssues"), "potentialIssues", "potential"
    )
    return source, findings


def parse_repository_issues(data: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    items = _list(_obj(data, "input").get("issues"), "issues")
    findings = [
        _finding(_obj(item, f"issues[{i}]"), f"issues[{i}]", state="existing", tool=None)
        for i, item in enumerate(items)
    ]
    return {"kind": "repo"}, findings


def parse_ignored_issues(data: Any) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    items = _list(_obj(data, "input").get("ignoredIssues"), "ignoredIssues")
    findings = [
        _finding(
            _obj(item, f"ignoredIssues[{i}]"),
            f"ignoredIssues[{i}]",
            state="existing",
            tool=None,
            ignored=True,
        )
        for i, item in enumerate(items)
    ]
    return {"kind": "ignored"}, findings


PARSERS = {
    "pr": parse_pull_request,
    "repo": parse_repository_issues,
    "ignored": parse_ignored_issues,
}


def group(findings: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    counts = Counter(tuple(f[key] for key in keys) for f in findings)
    rows = [dict(zip(keys, combo, strict=True), count=n) for combo, n in counts.items()]
    return sorted(rows, key=lambda r: (-r["count"], *(r[k] for k in keys)))


def build_record(kind: str, data: Any, *, category: str | None, group_by: str) -> dict[str, Any]:
    source, findings = PARSERS[kind](data)
    if category is not None:
        findings = [f for f in findings if f["category"] == category]
    by_category = Counter(f["category"] for f in findings)
    return {
        "schema_version": SCHEMA_VERSION,
        "provider": PROVIDER,
        "source": source,
        "findings": findings,
        "groups": group(findings, GROUP_KEYS[group_by]),
        "counts": {"total": len(findings), "by_category": dict(sorted(by_category.items()))},
    }


# C0 and C1 controls, DEL, zero-width and directional marks, line and paragraph separators,
# bidi controls, and the backslash itself
LINE_BREAKING = re.compile(
    r"[\x00-\x1f\x7f-\x9f\u200b-\u200f\u061c\ufeff\u2028\u2029\u202a-\u202e\u2066-\u2069\\]"
)


def _printable(value: Any) -> str:
    """Escape control and line-breaking characters so a file name cannot forge a table row."""
    return LINE_BREAKING.sub(
        lambda match: (
            f"\\x{ord(match.group()):02x}"
            if ord(match.group()) <= 0xFF
            else f"\\u{ord(match.group()):04x}"
        ),
        str(value),
    )


def render_table(record: dict[str, Any]) -> str:
    lines = [f"{record['counts']['total']} finding(s) from {record['provider']}"]
    for row in record["groups"]:
        label = "  ".join(_printable(value) for key, value in row.items() if key != "count")
        lines.append(f"{row['count']:>5}  {label}")
    return "\n".join(lines)


def _read_json(source: str) -> Any:
    try:
        if source == "-":
            # Read bytes, so the decode never depends on the console's locale encoding.
            stream = getattr(sys.stdin, "buffer", None)
            if stream is not None:
                raw = stream.read(MAX_INPUT_BYTES + 1)
            else:  # a text-only stdin, as in the smoke test
                raw = sys.stdin.read(MAX_INPUT_BYTES + 1).encode("utf-8")
        else:
            path = Path(source)
            if not path.is_file():
                raise ShapeError("cannot read input: not a regular file")
            with path.open("rb") as handle:
                raw = handle.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ShapeError(f"cannot read input: larger than {MAX_INPUT_BYTES} bytes")
        return json.loads(raw.decode("utf-8"))
    except (
        OSError,
        ValueError,
        RecursionError,
        MemoryError,
    ) as exc:  # ValueError: JSON, UTF-8, huge int
        if isinstance(exc, ShapeError):
            raise
        raise ShapeError(f"cannot read input: {type(exc).__name__}: {exc}") from exc


def _private_dir(directory: Path) -> bool:
    """True when the directory is owned by this user and not writable by group or others."""
    if getuid is None:  # no POSIX owner to compare on this platform
        return False
    try:
        info = directory.stat()
    except OSError:
        return False
    return info.st_uid == getuid() and not info.st_mode & 0o022


def _scratch_path(raw: str, option: str) -> Path:
    """Resolve a path that must sit in a scratchpad directory you own, outside any git work tree.

    Symlinks are followed first, so a link at the name or in a parent cannot point elsewhere.
    On POSIX the nearest enclosing scratchpad directory must be owned by the current user and not
    writable by group or others. A path under any folder that contains `.git` is refused. A work
    tree whose git directory lives elsewhere is not detected.
    """
    path = Path(raw).resolve()
    scratch_dirs = [parent for parent in path.parents if parent.name == "scratchpad"]
    if not scratch_dirs:
        raise ShapeError(f"{option} must be a file inside a scratchpad directory")
    if getuid is not None and not _private_dir(scratch_dirs[0]):  # nearest one, not any
        raise ShapeError(
            f"{option}'s scratchpad directory must be owned by you and not writable by others"
        )
    if any((parent / ".git").exists() for parent in path.parents):
        raise ShapeError(f"{option} must be outside any git work tree")
    return path


def _scratch_output(raw: str) -> Path:
    """Resolve --output: a new or existing file in a scratchpad directory that already exists."""
    try:
        path = _scratch_path(raw, "--output")
        if path.is_dir():
            raise ShapeError("--output must be a file, not a directory")
        if not path.parent.is_dir():
            raise ShapeError("--output's directory does not exist")
    except (OSError, RuntimeError) as exc:
        raise ShapeError(f"cannot use --output: {type(exc).__name__}") from exc
    return path


def _scratch_input(raw: str) -> Path:
    """Resolve --input (anything but `-`) under the same rules: the read stays in a scratchpad."""
    try:
        return _scratch_path(raw, "--input")
    except (OSError, RuntimeError) as exc:
        raise ShapeError(f"cannot use --input: {type(exc).__name__}") from exc


def _write_private(path: Path, text: str) -> None:
    """Write via a new 0600 temporary file in the same directory, then replace the target.

    The replace swaps a symlink or hard link at the target name for the new file instead of writing
    through it, and a failed run leaves any existing target untouched.
    """
    temporary = path.with_name(f".{path.name}.tmp")
    created = False
    try:
        temporary.touch(mode=0o600, exist_ok=False)
        created = True
        temporary.write_text(text + "\n", encoding="utf-8")
        temporary.replace(path)
    except FileExistsError as exc:
        raise ShapeError(f"cannot write --output: remove the stale file {temporary.name}") from exc
    except OSError as exc:
        raise ShapeError(f"cannot write --output: {type(exc).__name__}") from exc
    finally:
        if created:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kind", choices=sorted(PARSERS), required=True)
    parser.add_argument(
        "--input",
        default="-",
        help="JSON file written by the Cloud CLI (inside a scratchpad directory), or - for stdin",
    )
    parser.add_argument("--group-by", choices=sorted(GROUP_KEYS), default="rule,file")
    parser.add_argument("--category", help="keep only findings whose category equals this value")
    parser.add_argument("--format", choices=("json", "table"), default="json")
    parser.add_argument(
        "--output",
        help="write the record to this file (inside a scratchpad directory) instead of stdout",
    )
    args = parser.parse_args(argv)
    try:
        out_path = _scratch_output(args.output) if args.output else None
        source = "-" if args.input == "-" else str(_scratch_input(args.input))
        record = build_record(
            args.kind, _read_json(source), category=args.category, group_by=args.group_by
        )
    except ShapeError as exc:
        print(f"collect_codacy: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT
    text = render_table(record) if args.format == "table" else json.dumps(record, indent=2)
    if out_path is not None:
        try:
            if _scratch_output(args.output) != out_path:  # re-check just before writing
                raise ShapeError("--output changed while the input was being read")
            _write_private(out_path, text)
        except ShapeError as exc:
            print(f"collect_codacy: {exc}", file=sys.stderr)
            return EXIT_BAD_INPUT
        print(f"{record['counts']['total']} finding(s) written to {out_path.name}")
        return 0
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if args.format == "table" and callable(reconfigure):
        reconfigure(errors="backslashreplace")  # provider text may not fit the terminal encoding
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
