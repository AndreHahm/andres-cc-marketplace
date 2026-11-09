#!/usr/bin/env python3
"""Run one fixed SonarQube Cloud read and print only the fields the quality-kit skills use.

The pre-approved grant for this script replaces `Bash(sonar list issues:*)`, which also admitted a
bare run that prints `author` and `assignee`, and the ungranted `sonar api get | jq` reads. Every
form is a read with a fixed argument list (no shell), every value is validated before it reaches the
command line, and the response is projected here, so identity fields never reach stdout.

Forms:
  pr-list     --project KEY [--pull-request N]    the project's PR list (analysis state)
  issues      --project KEY [--pull-request N | --branch B] [--file F]
                                                  open issues, every page
  ignored     --project KEY                       ACCEPTED and FALSE_POSITIVE issues, every page
  issue-state --issue ID                          one issue's key, issueStatus and comment count
  gate-status --project KEY (--branch B | --pull-request N)
                                                  the quality gate status and its conditions

`issues` and `ignored` print one JSON document per page, which `collect_sonar.py` reads from a pipe.
Exit codes: 0 success; 1 `sonar` failed or timed out; 2 invalid arguments, no `sonar` on PATH
outside the caller's repository, or a response that is not the expected shape; 3 more issues than
PAGE_LIMIT pages hold. For `gate-status`, a `sonar` exit of 51 (failing gate) or 1 (no verdict
computed) that printed a gate object is a verdict: it is printed and the wrapper exits 0.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess  # nosec B404  # runs sonar with a list argument and validated values, never a shell
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

PROJECT = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,399}$")
BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")
FILE = re.compile(r"^[A-Za-z0-9._][A-Za-z0-9._/-]{0,1022}$")
ISSUE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
PULL_REQUEST = re.compile(r"^[1-9][0-9]{0,9}$")
PAGE_SIZE = 500
PAGE_LIMIT = 20  # 10,000 issues: the search API's own result window.
TIMEOUT_SECONDS = 120
ISSUE_FIELDS = (
    "key",
    "rule",
    "severity",
    "type",
    "component",
    "line",
    "message",
    "issueStatus",
    "pullRequest",
)
EXIT_SONAR, EXIT_INVALID, EXIT_TOO_MANY = 1, 2, 3
GATE_FAILED = 51  # `sonar quality-gate status` exit code for a failing gate


class ReadError(Exception):
    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code


def _checked(value: str | None, pattern: re.Pattern[str], name: str) -> str | None:
    if value is None:
        return None
    if not pattern.fullmatch(value) or any(part == ".." for part in value.split("/")):
        raise ReadError(f"{name}: not an accepted value", EXIT_INVALID)
    return value


def _execute(sonar: str, arguments: list[str]) -> tuple[int, bytes]:
    # Home, not the checkout: the CLI reads project configuration from its working directory, and a
    # repository-controlled file there must not choose the server the token is sent to.
    try:
        done = subprocess.run(  # nosec B603  # nosemgrep  # list argv, absolute sonar, no shell
            [sonar, *arguments],
            cwd=Path.home(),
            env=_child_env(),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except subprocess.TimeoutExpired as error:
        raise ReadError(f"sonar timed out after {TIMEOUT_SECONDS}s", EXIT_SONAR) from error
    return done.returncode, done.stdout


def _json(stdout: bytes) -> Any:
    try:
        return json.loads(stdout)
    except ValueError as error:
        raise ReadError("sonar printed something that is not JSON", EXIT_INVALID) from error


def _run(sonar: str, arguments: list[str]) -> Any:
    code, stdout = _execute(sonar, arguments)
    if code != 0:
        raise ReadError(f"sonar exited {code}", EXIT_SONAR)
    return _json(stdout)


def _object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReadError(f"{where}: expected an object", EXIT_INVALID)
    return value


def _array(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise ReadError(f"{where}: expected an array", EXIT_INVALID)
    return value


def _issue(raw: Any, where: str, *, comments: bool) -> dict[str, Any]:
    issue = _object(raw, where)
    kept = {name: issue[name] for name in ISSUE_FIELDS if name in issue}
    kept["impacts"] = [
        {"softwareQuality": item.get("softwareQuality"), "severity": item.get("severity")}
        for item in (
            _object(entry, f"{where}.impacts")
            for entry in _array(issue.get("impacts", []), f"{where}.impacts")
        )
    ]
    if comments:
        # The last comment's text only, the one the adapter records: a comment's login and dates
        # identify a person, and older comments are not used.
        entries = _array(issue.get("comments", []), f"{where}.comments")
        kept["comments"] = [
            {"markdown": _object(entry, f"{where}.comments").get("markdown")}
            for entry in entries[-1:]
        ]
    return kept


def _page(document: Any, *, comments: bool) -> tuple[dict[str, Any], int]:
    root = _object(document, "response")
    paging = _object(root.get("paging"), "paging")
    kept: dict[str, int] = {}
    for name in ("pageIndex", "pageSize", "total"):
        value = paging.get(name)
        if not isinstance(value, int) or isinstance(value, bool):
            raise ReadError("paging: expected integers", EXIT_INVALID)
        kept[name] = value
    issues = [
        _issue(item, f"issues[{index}]", comments=comments)
        for index, item in enumerate(_array(root.get("issues"), "issues"))
    ]
    return {"paging": kept, "issues": issues}, kept["total"]


def _pages(fetch: Any, *, comments: bool) -> list[dict[str, Any]]:
    pages: list[dict[str, Any]] = []
    for number in range(1, PAGE_LIMIT + 1):
        page, total = _page(fetch(number), comments=comments)
        pages.append(page)
        if number * PAGE_SIZE >= total:
            return pages
    raise ReadError(f"more than {PAGE_LIMIT * PAGE_SIZE} issues; narrow the read", EXIT_TOO_MANY)


def _nested(entry: dict[str, Any], name: str) -> dict[str, Any]:
    value = entry.get(name)
    return value if isinstance(value, dict) else {}


def _pr_list(sonar: str, project: str, pull_request: str | None) -> dict[str, Any]:
    query = urlencode({"project": project})
    root = _object(
        _run(sonar, ["api", "get", f"/api/project_pull_requests/list?{query}"]), "response"
    )
    kept = []
    for index, raw in enumerate(_array(root.get("pullRequests"), "pullRequests")):
        entry = _object(raw, f"pullRequests[{index}]")
        if pull_request is not None and entry.get("key") != pull_request:
            continue
        commit = _nested(entry, "commit")
        status = _nested(entry, "status")
        kept.append(
            {
                "key": entry.get("key"),
                "analysisDate": entry.get("analysisDate"),
                "commit": {"sha": commit.get("sha")},
                "status": {"qualityGateStatus": status.get("qualityGateStatus")},
            }
        )
    return {"pullRequests": kept}


def _gate_status(
    sonar: str, project: str, pull_request: str | None, branch: str | None
) -> dict[str, Any]:
    # Always one named target: a bare form reports whatever the working directory's checkout is.
    if (pull_request is None) == (branch is None):
        raise ReadError("gate-status needs exactly one of --branch or --pull-request", EXIT_INVALID)
    target = ["--pull-request", pull_request] if pull_request else ["--branch", str(branch)]
    code, stdout = _execute(
        sonar, ["quality-gate", "status", "-p", project, *target, "--format", "json"]
    )
    # The CLI prints the verdict and then exits 51 for a failing gate and 1 when no verdict was
    # computed (its verdict.ts, checked 2026-11-09), so those two codes carry a gate verdict. A
    # lookup failure (a missing project also exits 1) prints no gate object and stays an error.
    if code not in (0, 1, GATE_FAILED):
        raise ReadError(f"sonar exited {code}", EXIT_SONAR)
    try:
        gate = _object(_object(_json(stdout), "response").get("qualityGate"), "qualityGate")
    except ReadError as error:
        if code != 0:
            raise ReadError(f"sonar exited {code}", EXIT_SONAR) from error
        raise
    if code == GATE_FAILED and gate.get("status") != "ERROR":
        raise ReadError("sonar exited 51 without a failed gate", EXIT_INVALID)
    fields = ("status", "metricKey", "comparator", "errorThreshold", "actualValue")
    return {
        "qualityGate": {
            **{
                name: gate[name]
                for name in ("status", "project", "branch", "pullRequest")
                if name in gate
            },
            "conditions": [
                {name: condition.get(name) for name in fields}
                for condition in (
                    _object(entry, "qualityGate.conditions[]")
                    for entry in _array(gate.get("conditions", []), "qualityGate.conditions")
                )
            ],
        }
    }


def _arguments(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0], allow_abbrev=False)
    parser.add_argument(
        "form", choices=("pr-list", "issues", "ignored", "issue-state", "gate-status")
    )
    parser.add_argument("--project")
    parser.add_argument("--pull-request")
    parser.add_argument("--branch")
    parser.add_argument("--file")
    parser.add_argument("--issue")
    return parser.parse_args(argv)


def _read(args: argparse.Namespace, sonar: str) -> list[Any]:
    project = _checked(args.project, PROJECT, "--project")
    pull_request = _checked(args.pull_request, PULL_REQUEST, "--pull-request")
    branch = _checked(args.branch, BRANCH, "--branch")
    file = _checked(args.file, FILE, "--file")
    issue = _checked(args.issue, ISSUE, "--issue")
    allowed = {
        "pr-list": {"project", "pull_request"},
        "issues": {"project", "pull_request", "branch", "file"},
        "ignored": {"project"},
        "issue-state": {"issue"},
        "gate-status": {"project", "pull_request", "branch"},
    }[args.form]
    given = {
        name
        for name in ("project", "pull_request", "branch", "file", "issue")
        if getattr(args, name) is not None
    }
    if given - allowed:
        raise ReadError(
            f"{args.form} does not take {', '.join(sorted(given - allowed))}", EXIT_INVALID
        )
    if args.form == "issue-state":
        if issue is None:
            raise ReadError("issue-state needs --issue", EXIT_INVALID)
        query = urlencode({"issues": issue, "additionalFields": "comments"})
        root = _object(_run(sonar, ["api", "get", f"/api/issues/search?{query}"]), "response")
        states = [_object(item, "issues[]") for item in _array(root.get("issues"), "issues")]
        return [
            {
                "issues": [
                    {
                        "key": item.get("key"),
                        "issueStatus": item.get("issueStatus"),
                        "comments": len(_array(item.get("comments", []), "issues[].comments")),
                    }
                    for item in states
                ]
            }
        ]
    if project is None:
        raise ReadError(f"{args.form} needs --project", EXIT_INVALID)
    if args.form == "pr-list":
        return [_pr_list(sonar, project, pull_request)]
    if args.form == "gate-status":
        return [_gate_status(sonar, project, pull_request, branch)]
    if args.form == "ignored":

        def fetch_ignored(number: int) -> Any:
            query = urlencode(
                {
                    "projects": project,
                    "issueStatuses": "ACCEPTED,FALSE_POSITIVE",
                    "additionalFields": "comments",
                    "ps": PAGE_SIZE,
                    "p": number,
                }
            )
            return _run(sonar, ["api", "get", f"/api/issues/search?{query}"])

        return _pages(fetch_ignored, comments=True)
    if pull_request is not None and branch is not None:
        raise ReadError("--pull-request and --branch cannot be combined", EXIT_INVALID)
    scope = (["--pull-request", pull_request] if pull_request else []) + (
        ["--branch", branch] if branch else []
    )
    scope += ["--file", file] if file else []

    def fetch_issues(number: int) -> Any:
        return _run(
            sonar,
            [
                "list",
                "issues",
                "-p",
                project,
                *scope,
                "--format",
                "json",
                "--page-size",
                str(PAGE_SIZE),
                "--page",
                str(number),
            ],
        )

    return _pages(fetch_issues, comments=False)


IS_WINDOWS = os.name == "nt"
# Variables the sonar CLI reads to choose the server or binaries it talks to (its own bundle, read
# 2026-11-09). Inherited, any of them would send the token elsewhere, so they are dropped, like
# codex-kit's gitEnv drops GIT_DIR and its siblings. Authentication variables are kept.
STRIPPED_ENV = frozenset(
    {
        "SONARQUBE_URL",
        "SONAR_HOST_URL",
        "SONARQUBE_CLI_BINARIES_URL",
        "SONARQUBE_CLI_SONARCLOUD_URL",
        "SONARQUBE_CLI_SONARCLOUD_API_URL",
        "SONARQUBE_CLI_SONARCLOUD_US_URL",
        "SONARQUBE_CLI_SONARCLOUD_US_API_URL",
        "SONARQUBE_CLI_SONARCLOUD_SCA_SCANNER_CDN_URL",
    }
)


def _repo_roots(start: Path) -> list[Path]:
    # Every enclosing checkout, not only the nearest: this repository keeps worktrees inside the
    # main checkout, and a submodule sits inside its superproject, so the outer tree's own `.venv`
    # or `node_modules/.bin` must count as inside too (security review M1, 2026-11-09).
    return [directory for directory in (start, *start.parents) if (directory / ".git").exists()]


def _norm(path: str) -> str:
    return os.path.normcase(os.path.normpath(path))


def _identity(path: str) -> tuple[int, int] | None:
    try:
        info = os.stat(path)
    except OSError:
        return None
    return (info.st_dev, info.st_ino) if info.st_ino else None  # 0: no file id on this platform


def _inside(path: str, roots: list[Path]) -> bool:
    # Inside by the lexical spelling, or by file identity of the resolved path or any of its
    # parents, so a symlink, junction, 8.3 alias or case-only spelling cannot name an in-repo folder
    # (codex-kit's isInsideRoot, widened by the security review's m2).
    def within(child: str, parent: str) -> bool:
        try:
            return os.path.commonpath([child, parent]) == parent
        except ValueError:  # different drives on Windows
            return False

    lexical = _norm(os.path.abspath(path))
    if any(within(lexical, _norm(str(root))) for root in roots):
        return True
    ids = {identity for root in roots if (identity := _identity(str(root))) is not None}
    resolved = Path(os.path.realpath(path))
    return any(_identity(str(step)) in ids for step in (resolved, *resolved.parents))


def _trusted_path() -> tuple[list[str], list[Path]]:
    roots = _repo_roots(Path.cwd())
    kept = []
    for raw in os.environ.get("PATH", "").split(os.pathsep):
        directory = raw.strip('"')
        if directory and os.path.isabs(directory) and not _inside(directory, roots):
            kept.append(directory)
    return kept, roots


def _find_sonar() -> str:
    # Search PATH here, never the current directory, a relative or empty entry, or a folder inside
    # the caller's repository: an activated `.venv` or `node_modules/.bin` there is routinely on
    # PATH, and a branch can commit a `sonar` into it (codex-kit's gitExecutable, security re-review
    # M-1). On Windows only `sonar.exe` is accepted, so a `.cmd` shim never runs through cmd.exe.
    directories, roots = _trusted_path()
    name = "sonar.exe" if IS_WINDOWS else "sonar"
    for directory in directories:
        candidate = os.path.join(directory, name)
        if not (os.path.isfile(candidate) and os.access(candidate, os.X_OK)):
            continue
        # A link outside the repository can still point at a file inside it (review m3).
        if _inside(os.path.dirname(os.path.realpath(candidate)), roots):
            continue
        return candidate
    raise ReadError(f"{name} not found on PATH outside the repository", EXIT_INVALID)


def _child_env() -> dict[str, str]:
    # The child gets the same filtered PATH, so whatever `sonar` itself looks up by name never
    # comes from a folder inside the repository either (security review M2).
    env = {
        key: value
        for key, value in os.environ.items()
        if key.upper() not in STRIPPED_ENV and key.upper() != "PATH"
    }
    env["PATH"] = os.pathsep.join(_trusted_path()[0])
    return env


def main(argv: list[str] | None = None) -> int:
    args = _arguments(argv)
    try:
        sonar = _find_sonar()
        documents = _read(args, sonar)
    except ReadError as error:
        print(f"sonar_read: {error}", file=sys.stderr)
        return error.code
    try:
        for document in documents:
            sys.stdout.write(json.dumps(document, ensure_ascii=False) + "\n")
        sys.stdout.flush()
    except (BrokenPipeError, ValueError):
        return EXIT_SONAR
    return 0


if __name__ == "__main__":
    sys.exit(main())
