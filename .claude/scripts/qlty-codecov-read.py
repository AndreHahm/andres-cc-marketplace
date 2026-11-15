#!/usr/bin/env python3
"""Run one fixed Codecov API v2 read and print only the fields the quality-kit skills use.

Every form is a GET to https://api.codecov.io/api/v2/ with validated path values, through urllib
(no subprocess, no shell). Responses are projected here, so author fields and user-written text
(titles, commit messages) never reach stdout.

Forms:
  repo    --owner O --repo R                      activation state, default branch, latest totals
  totals  --owner O --repo R (--branch B | --sha S)
                                                  coverage totals and per-file totals for one commit
  pull    --owner O --repo R --pull N             a pull request's head, base and patch totals

Common options: --service (github, gitlab or bitbucket; default github).
Token: CODECOV_API_TOKEN, when set, is sent as a bearer token and never printed. A public repository
needs none. Codecov's `compare` endpoint is not offered: without a token it answered 403 (a GitHub
rate limit on Codecov's side) on 2026-11-15, and no token was available to verify it.
Exit codes: 0 success; 1 the request failed, timed out or answered another HTTP error; 2 invalid
arguments or a response that is not the expected shape; 4 Codecov answered 401 (a token is missing
or not valid); 5 Codecov has no coverage report for that commit or branch.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Any
from urllib.parse import quote, urlencode

API = "https://api.codecov.io/api/v2"
SERVICES = ("github", "gitlab", "bitbucket")
NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,99}$")
BRANCH = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,254}$")
SHA = re.compile(r"^[0-9a-f]{40}$")  # Codecov answers 404 for an abbreviated SHA (2026-11-15)
# 404 details that mean "nothing uploaded for this commit or branch", as Codecov worded them
# on 2026-11-15.
NO_REPORT = ("No coverage report", "is not in our records", "in not in our records")
PULL = re.compile(r"^[1-9][0-9]{0,9}$")
TIMEOUT_SECONDS = 60
MAX_BYTES = 20 * 1024 * 1024
TOTAL_FIELDS = ("coverage", "files", "lines", "hits", "misses", "partials")
PATCH_FIELDS = ("coverage", "hits", "misses", "partials")
AUTH_ENV = "CODECOV_API_TOKEN"
# File names come from the repository; at most this many are printed, the rest only counted.
MAX_FILES = 200

EXIT_REQUEST = 1
EXIT_INPUT = 2
EXIT_AUTH = 4
EXIT_NO_REPORT = 5


class ReadError(Exception):
    def __init__(self, message: str, code: int) -> None:
        super().__init__(message)
        self.code = code


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse redirects, so the bearer token is never replayed to another URL."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001, ARG002
        raise ReadError(f"Codecov answered a {code} redirect, which is refused", EXIT_REQUEST)


def _checked(value: str | None, pattern: re.Pattern[str], name: str) -> str | None:
    if value is not None and not pattern.fullmatch(value):
        raise ReadError(f"invalid {name}", EXIT_INPUT)
    return value


def _get(path: str, query: dict[str, str] | None = None) -> Any:
    url = f"{API}/{path}" + (f"?{urlencode(query)}" if query else "")
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    token = os.environ.get(AUTH_ENV)
    if token:
        request.add_unredirected_header("Authorization", f"Bearer {token}")
    opener = urllib.request.build_opener(_NoRedirect)
    try:
        with opener.open(request, timeout=TIMEOUT_SECONDS) as response:  # nosec B310  # fixed https base
            body = response.read(MAX_BYTES + 1)
    except urllib.error.HTTPError as error:
        detail = ""
        try:
            parsed = json.loads(error.read(4096) or b"{}")
            detail = parsed.get("detail", "") if isinstance(parsed, dict) else ""
        except ValueError:
            pass
        if error.code == 401:
            message = f"Codecov answered 401: set {AUTH_ENV} for this repository"
            raise ReadError(message, EXIT_AUTH) from None
        no_report = isinstance(detail, str) and any(text in detail for text in NO_REPORT)
        if error.code == 404 and no_report:
            message = "Codecov has no coverage report for that commit or branch"
            raise ReadError(message, EXIT_NO_REPORT) from None
        raise ReadError(f"Codecov answered HTTP {error.code}", EXIT_REQUEST) from None
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        raise ReadError(f"request failed ({error.__class__.__name__})", EXIT_REQUEST) from None
    if len(body) > MAX_BYTES:
        raise ReadError("response is larger than the read limit", EXIT_INPUT)
    try:
        return json.loads(body)
    except ValueError:
        raise ReadError("response is not JSON", EXIT_INPUT) from None


def _object(value: Any, where: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ReadError(f"unexpected response shape at {where}", EXIT_INPUT)
    return value


def _totals(value: Any, fields: tuple[str, ...] = TOTAL_FIELDS) -> dict[str, Any] | None:
    if value is None:
        return None
    totals = _object(value, "totals")
    return {field: totals.get(field) for field in fields}


def repo_form(base: str) -> dict[str, Any]:
    document = _object(_get(f"{base}/"), "repo")
    return {
        "name": document.get("name"),
        "private": document.get("private"),
        "active": document.get("active"),
        "activated": document.get("activated"),
        "branch": document.get("branch"),
        "totals": _totals(document.get("totals")),
    }


def totals_form(base: str, branch: str | None, sha: str | None) -> dict[str, Any]:
    query = {"branch": branch} if branch else {"sha": sha or ""}
    document = _object(_get(f"{base}/totals/", query), "totals")
    files = document.get("files", [])
    if not isinstance(files, list):
        raise ReadError("unexpected response shape at files", EXIT_INPUT)
    return {
        "branch": branch,
        "sha": sha,
        "totals": _totals(document.get("totals")),
        "files": [
            {"name": _object(entry, "files[]").get("name"), **(_totals(entry.get("totals")) or {})}
            for entry in files[:MAX_FILES]
        ],
        "files_not_shown": max(len(files) - MAX_FILES, 0),
    }


def pull_form(base: str, pull: str) -> dict[str, Any]:
    document = _object(_get(f"{base}/pulls/{pull}/"), "pull")
    return {
        "pullid": document.get("pullid"),
        "state": document.get("state"),
        "ci_passed": document.get("ci_passed"),
        "updatestamp": document.get("updatestamp"),
        "base_totals": _totals(document.get("base_totals")),
        "head_totals": _totals(document.get("head_totals")),
        "patch": _totals(document.get("patch"), PATCH_FIELDS),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n", 1)[0])
    parser.add_argument("form", choices=("repo", "totals", "pull"))
    parser.add_argument("--service", choices=SERVICES, default="github")
    parser.add_argument("--owner", required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--branch")
    parser.add_argument("--sha")
    parser.add_argument("--pull")
    args = parser.parse_args(argv)
    try:
        owner = _checked(args.owner, NAME, "owner")
        repo = _checked(args.repo, NAME, "repo")
        branch = _checked(args.branch, BRANCH, "branch")
        sha = _checked(args.sha, SHA, "sha")
        pull = _checked(args.pull, PULL, "pull number")
        base = f"{args.service}/{quote(owner or '')}/repos/{quote(repo or '')}"
        if args.form == "repo":
            if branch or sha or pull:
                raise ReadError("repo takes no --branch, --sha or --pull", EXIT_INPUT)
            result = repo_form(base)
        elif args.form == "totals":
            if (branch is None) == (sha is None) or pull:
                raise ReadError("totals takes exactly one of --branch or --sha", EXIT_INPUT)
            result = totals_form(base, branch, sha)
        else:
            if pull is None or branch or sha:
                raise ReadError("pull takes --pull only", EXIT_INPUT)
            result = pull_form(base, pull)
    except ReadError as error:
        print(f"qlty-codecov-read: {error}", file=sys.stderr)
        return error.code
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
