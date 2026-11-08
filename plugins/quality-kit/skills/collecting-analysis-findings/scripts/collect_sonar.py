#!/usr/bin/env python3
"""Normalize SonarQube Cloud JSON into the same provider-neutral findings record.

Reads what `sonar list issues` or `sonar api get` printed, from stdin or a scratchpad file, and
prints the record, or writes it with --output to a file inside a scratchpad directory. It runs no
command, opens no network connection and never opens a path named inside the findings: every value
in the input is data to copy into the record, not something to act on.

Exit codes: 0 record written, 1 stdout could not be written, so the output may be incomplete,
2 input unreadable, not a shape this adapter knows, or an invalid command line, 3 the response
has more pages than the input holds. On 2 and 3 nothing is written to stdout, so a caller never
sees a partial record.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from math import ceil
from pathlib import Path
from typing import Any

# `python3 -I` leaves this directory off sys.path. Appended, so the standard library still wins.
# It also ignores PYTHONDONTWRITEBYTECODE, and the import below must not leave a __pycache__ here.
sys.dont_write_bytecode = True
sys.path.append(str(Path(__file__).resolve().parent))
from collect_codacy import (  # noqa: E402 - the path must be set first
    EXIT_BAD_INPUT,
    GROUP_KEYS,
    ISSUE_ID,
    ShapeError,
    _list,
    _obj,
    _print_stdout,
    _read_json,
    _scratch_input,
    _scratch_output,
    _str,
    _write_private,
    group,
    render_table,
)

SCHEMA_VERSION = "1.1.0"
PROVIDER = "sonar"
EXIT_MORE_PAGES = 3
# Checked 2026-11-07: the API answers 400 past this many results.
MAX_RESULTS = 10_000
PROJECT_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,399}$")
COMMIT_SHA = re.compile(r"^[0-9a-f]{40}$")
BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]*$")
OPEN_STATUSES = {"OPEN", "CONFIRMED"}
IGNORED_STATUSES = {"ACCEPTED", "FALSE_POSITIVE"}
STATUS_KEYS = {"project", "pull_request", "head_commit_sha", "analysis_date", "quality_gate"}


class MorePages(Exception):
    """The input is a valid start of a response that continues on further pages."""


def _load_documents(text: str) -> list[Any]:
    """Parse one JSON document, or several written one after another (a multi-page run)."""
    decoder = json.JSONDecoder()
    documents, index = [], 0
    while True:
        while index < len(text) and text[index] in " \t\r\n":  # JSON's own whitespace, no other
            index += 1
        if index == len(text):
            return documents
        document, index = decoder.raw_decode(text, index)
        documents.append(document)


def _int(container: dict[str, Any], key: str, where: str) -> int:
    value = container.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise ShapeError(f"{where}.{key}: expected an integer")
    return value


def _collect_issues(documents: list[Any]) -> list[Any]:
    """Return every issue, or refuse: a partial list would feed wrong counts to a decision."""
    if not documents:
        raise ShapeError("cannot read input: it is empty")
    issues: list[Any] = []
    first: tuple[int, int] | None = None
    for position, document in enumerate(documents, start=1):
        root = _obj(document, f"page {position}")
        paging = _obj(root.get("paging"), f"page {position}.paging")
        size, total = _int(paging, "pageSize", "paging"), _int(paging, "total", "paging")
        if size < 1 or total < 0:
            raise ShapeError("paging: pageSize or total is out of range")
        if first is None:
            first = (size, total)
        if (size, total) != first or _int(paging, "pageIndex", "paging") != position:
            raise ShapeError(f"page {position}: pages are missing, repeated or from another query")
        issues += _list(root.get("issues"), f"page {position}.issues")
    if total > MAX_RESULTS:
        raise ShapeError(f"{total} results: the API returns only the first {MAX_RESULTS}")
    pages = ceil(total / size)
    if len(documents) < pages:
        raise MorePages(f"{pages} pages are needed and the input holds {len(documents)}")
    if len(issues) != total or len(documents) > max(pages, 1):
        raise ShapeError(f"paging.total says {total}, the input holds {len(issues)} issue(s)")
    return issues


def _file(issue: dict[str, Any], where: str, project: str) -> str:
    component = _str(issue, "component", where)
    prefix = f"{project}:"
    if component is None or not component.startswith(prefix) or component == prefix:
        raise ShapeError(f"{where}.component: not a file of project {project}")
    return component[len(prefix) :]


def _line(issue: dict[str, Any], where: str) -> int | None:
    return None if issue.get("line") is None else _int(issue, "line", where)


def _key(issue: dict[str, Any], where: str) -> str:
    value = _str(issue, "key", where)
    if value is None or not ISSUE_ID.fullmatch(value):
        raise ShapeError(f"{where}.key: not a plain identifier (letters, digits, - and _ only)")
    return value


def _impacts(issue: dict[str, Any], where: str) -> list[dict[str, str | None]]:
    """Keep each impact's quality and level: severity alone can understate a finding."""
    return [
        {
            "software_quality": _str(_obj(item, f"{where}.impacts"), "softwareQuality", where),
            "severity": _str(item, "severity", where),
        }
        for item in _list(issue.get("impacts", []), f"{where}.impacts")
    ]


def _finding(item: Any, where: str, *, project: str, state: str, ignored: bool) -> dict[str, Any]:
    issue = _obj(item, where)
    status = _str(issue, "issueStatus", where)
    if status not in (IGNORED_STATUSES if ignored else OPEN_STATUSES):
        raise ShapeError(f"{where}.issueStatus: not a status this kind of list holds")
    comment = None
    if ignored:
        # An issue marked without a comment may omit the key: not seen, so allowed.
        comments = _list(issue.get("comments", []), f"{where}.comments")
        if comments:  # The API lists them oldest first: checked 2026-11-07.
            last = _obj(comments[-1], f"{where}.comments[-1]")
            comment = _str(last, "markdown", f"{where}.comments[-1]", required=False)
    return {
        "provider": PROVIDER,
        "tool": None,
        "rule": _str(issue, "rule", where),
        "severity": _str(issue, "severity", where),
        "category": _str(issue, "type", where),
        "impacts": _impacts(issue, where),
        "subcategory": None,
        "file": _file(issue, where, project),
        "line": _line(issue, where),
        "issue_id": _key(issue, where),
        "message": _str(issue, "message", where),
        "state": state,
        "delta_type": None,
        "ignored": ignored,
        "ignore_reason": status if ignored else None,
        "ignore_comment": comment,
    }


def _findings(
    issues: list[Any], *, project: str, state: str, ignored: bool = False
) -> list[dict[str, Any]]:
    findings = [
        _finding(item, f"issues[{i}]", project=project, state=state, ignored=ignored)
        for i, item in enumerate(issues)
    ]
    ids = [f["issue_id"] for f in findings]
    if len(set(ids)) != len(ids):
        raise ShapeError("the same issue key appears twice: pages overlap")
    return findings


def _read_status(raw: str, *, project: str) -> dict[str, Any]:
    """Read a `pr-status` file. Its shape is checked; that it came from such a run cannot be."""
    status = _obj(_read_json(str(_scratch_input(raw))), "--status")
    if set(status) != STATUS_KEYS:
        raise ShapeError("--status: not the shape --kind pr-status writes")
    if status["project"] != project:
        raise ShapeError("--status: written for another project")
    _status_sha(status)
    if _int(status, "pull_request", "--status") < 1:
        raise ShapeError("--status.pull_request: out of range")
    _str(status, "analysis_date", "--status")
    _str(status, "quality_gate", "--status")
    return status


def _status_sha(status: dict[str, Any]) -> None:
    sha = status.get("head_commit_sha")
    if not isinstance(sha, str) or not COMMIT_SHA.fullmatch(sha):
        raise ShapeError("head commit: not a 40-character hexadecimal SHA")


def parse_pull_request(
    data: list[Any], project: str, status: dict[str, Any]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    issues = _collect_issues(data)
    for index, item in enumerate(issues):
        issue = _obj(item, f"issues[{index}]")
        if issue.get("pullRequest") != str(status["pull_request"]):
            raise ShapeError(f"issues[{index}].pullRequest: not the PR in --status")
    source = {
        "kind": "pr",
        "repository": project,
        "pull_request": status["pull_request"],
        "pr_status": None,
        "head_commit_sha": status["head_commit_sha"],
        "is_analysing": None,
        "quality_gate": status["quality_gate"],
    }
    return source, _findings(issues, project=project, state="new")


def parse_repository_issues(
    data: list[Any], project: str, branch: str | None = None
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    issues = _collect_issues(data)
    for index, item in enumerate(issues):
        if "pullRequest" in _obj(item, f"issues[{index}]"):
            raise ShapeError(f"issues[{index}]: a PR issue in a repository list")
    source: dict[str, Any] = {"kind": "repo", "repository": project}
    if branch is not None:  # absent means the default branch, as before
        source["branch"] = branch
    return source, _findings(issues, project=project, state="existing")


def parse_ignored_issues(
    data: list[Any], project: str
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    findings = _findings(_collect_issues(data), project=project, state="existing", ignored=True)
    return {"kind": "ignored", "repository": project}, findings


def build_record(
    kind: str,
    data: list[Any],
    *,
    project: str,
    status: dict[str, Any] | None,
    category: str | None,
    group_by: str,
    branch: str | None = None,
) -> dict[str, Any]:
    if status is not None:
        source, findings = parse_pull_request(data, project, status)
    elif kind == "repo":
        source, findings = parse_repository_issues(data, project, branch)
    else:
        source, findings = parse_ignored_issues(data, project)
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


def build_status(data: list[Any], *, project: str, pull_request: int) -> dict[str, Any]:
    """Keep only the head, date and gate of one PR: the list also carries identity fields."""
    if len(data) != 1:
        raise ShapeError("pr-status: expected one JSON document")
    entries = _list(_obj(data[0], "input").get("pullRequests"), "pullRequests")
    matches = [
        entry
        for index, item in enumerate(entries)
        if (entry := _obj(item, f"pullRequests[{index}]")).get("key") == str(pull_request)
    ]
    if len(matches) != 1:
        raise ShapeError(f"PR {pull_request} is not listed once: no analysis to compare")
    entry = matches[0]
    status = {
        "project": project,
        "pull_request": pull_request,
        "head_commit_sha": _obj(entry.get("commit"), "commit").get("sha"),
        "analysis_date": _str(entry, "analysisDate", "pullRequest"),
        "quality_gate": _str(
            _obj(entry.get("status"), "status"), "qualityGateStatus", "pullRequest.status"
        ),
    }
    _status_sha(status)
    return status


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--kind", choices=("ignored", "pr", "pr-status", "repo"), required=True)
    parser.add_argument("--project", required=True, help="the SonarQube Cloud project key")
    parser.add_argument(
        "--input",
        default="-",
        help="JSON file written by the sonar CLI (inside a scratchpad directory), or - for stdin",
    )
    parser.add_argument("--pull-request", type=int, help="required for --kind pr-status")
    parser.add_argument("--status", help="file written by --kind pr-status, for --kind pr")
    parser.add_argument("--branch", help="for --kind repo: the --branch the list was read with")
    parser.add_argument("--group-by", choices=sorted(GROUP_KEYS), default="rule,file")
    parser.add_argument("--category", help="keep only findings whose category equals this value")
    parser.add_argument("--format", choices=("json", "table"), default="json")
    parser.add_argument(
        "--output",
        help="write the result to this file (inside a scratchpad directory) instead of stdout",
    )
    args = parser.parse_args(argv)
    if not PROJECT_KEY.fullmatch(args.project):
        parser.error("--project: not a project key")
    if args.kind == "pr-status" and (args.pull_request is None or args.pull_request < 1):
        parser.error("--kind pr-status needs --pull-request")
    if args.kind == "pr-status" and args.format == "table":
        parser.error("--kind pr-status has no table format")
    if args.kind == "pr" and not args.status:
        parser.error("--kind pr needs --status")
    if args.branch is not None and (
        args.kind != "repo" or not BRANCH.fullmatch(args.branch) or ".." in args.branch.split("/")
    ):
        parser.error("--branch: only for --kind repo, and only a plain branch name")
    return args


def _build(args: argparse.Namespace) -> dict[str, Any]:
    source = "-" if args.input == "-" else str(_scratch_input(args.input))
    # Read --status first: a stale or foreign one should stop the run before the larger input.
    status = _read_status(args.status, project=args.project) if args.kind == "pr" else None
    data = _read_json(source, decode=_load_documents)
    if args.kind == "pr-status":
        return build_status(data, project=args.project, pull_request=args.pull_request)
    return build_record(
        args.kind,
        data,
        project=args.project,
        status=status,
        category=args.category,
        group_by=args.group_by,
        branch=args.branch,
    )


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        out_path = _scratch_output(args.output) if args.output else None
        result = _build(args)
    except MorePages as exc:
        print(f"collect_sonar: {exc}", file=sys.stderr)
        return EXIT_MORE_PAGES
    except (ShapeError, OSError, RuntimeError) as exc:
        print(f"collect_sonar: {exc}", file=sys.stderr)
        return EXIT_BAD_INPUT
    text = render_table(result) if args.format == "table" else json.dumps(result, indent=2)
    if out_path is not None:
        try:
            if _scratch_output(args.output) != out_path:  # re-check just before writing
                raise ShapeError("--output changed while the input was being read")
            _write_private(out_path, text)
        except ShapeError as exc:
            print(f"collect_sonar: {exc}", file=sys.stderr)
            return EXIT_BAD_INPUT
        kind_pr_status = args.kind == "pr-status"
        summary = "status" if kind_pr_status else f"{result['counts']['total']} finding(s)"
        return _print_stdout(f"{summary} written to {out_path.name}", "collect_sonar")
    reconfigure = getattr(sys.stdout, "reconfigure", None)
    if args.format == "table" and callable(reconfigure):
        try:  # provider text may not fit the terminal encoding
            reconfigure(errors="backslashreplace")
        except ValueError:  # a closed stream: _print_stdout reports it
            pass
    return _print_stdout(text, "collect_sonar")


if __name__ == "__main__":
    sys.exit(main())
