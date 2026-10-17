#!/usr/bin/env python3
"""Normalize Codacy Cloud CLI JSON into one provider-neutral findings record.

Reads the JSON that `codacy pull-request ... --output json` or `codacy issues ... --output json`
wrote to a file (or stdin) and prints the record. It runs no command, opens no network
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
from pathlib import Path
from typing import Any

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


LINE_BREAKING = re.compile(r"[\x00-\x1f\x7f\x85  ]")


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
            raw = getattr(sys.stdin, "buffer", None)  # bytes, so the decode never uses the locale
            if raw is not None:
                text = raw.read(MAX_INPUT_BYTES + 1).decode("utf-8")
            else:
                text = sys.stdin.read(MAX_INPUT_BYTES + 1)
        else:
            path = Path(source)
            if not path.is_file():
                raise ShapeError("cannot read input: not a regular file")
            with path.open(encoding="utf-8") as handle:
                text = handle.read(MAX_INPUT_BYTES + 1)
        if len(text) > MAX_INPUT_BYTES:
            raise ShapeError(f"cannot read input: larger than {MAX_INPUT_BYTES} characters")
        return json.loads(text)
    except (
        OSError,
        ValueError,
        RecursionError,
        MemoryError,
    ) as exc:  # ValueError: JSON, UTF-8, huge int
        if isinstance(exc, ShapeError):
            raise
        raise ShapeError(f"cannot read input: {type(exc).__name__}: {exc}") from exc


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--kind", choices=sorted(PARSERS), required=True)
    parser.add_argument("--input", default="-", help="JSON file written by the Cloud CLI, or -")
    parser.add_argument("--group-by", choices=sorted(GROUP_KEYS), default="rule,file")
    parser.add_argument("--category", help="keep only findings whose category equals this value")
    parser.add_argument("--format", choices=("json", "table"), default="json")
    args = parser.parse_args(argv)
    try:
        record = build_record(
            args.kind, _read_json(args.input), category=args.category, group_by=args.group_by
        )
    except ShapeError as exc:
        print(f"collect_codacy: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if args.format == "table" and callable(reconfigure):
        reconfigure(errors="backslashreplace")  # provider text may not fit the terminal encoding
    print(render_table(record) if args.format == "table" else json.dumps(record, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
