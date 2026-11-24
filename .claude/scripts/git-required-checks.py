#!/usr/bin/env python3
"""Classify a head commit's required checks, per real source (merge-pr step 2, issue #858).

    git-required-checks.py <owner/repo> <base-branch> <head-sha>

The required list is the union of classic branch protection and every ruleset on the base branch,
each context with the app that must report it, when one is named. Every entry of a required context
on the head is then attributed to a source that the server sets, never to a display name or to
`detailsUrl` (whoever creates a check run chooses that one):

- a GitHub Actions check run whose id is the id of a job of a workflow run on this head: the
  workflow id plus the event. Runs are found through the check suite; jobs are read for all
  attempts.
- a GitHub Actions check run that is no run's job (created through the API with a workflow's
  token): its own source, so it never replaces another entry and no other entry replaces it.
- a check run of another app: that app. Only its newest entry (by server-set id) counts, even for
  "not finished": Codacy, for one, never completes the entry its next one replaces (seen live).
  `filter=latest` would drop that entry too, but also a real job hidden by a newer token-created
  run in its suite. When the newest entry is skipped, the app's newest finished entry that was not
  skipped counts instead, if there is one. An unfinished entry older than that skip never counts.
- a commit status: its creator. A failure posted with a workflow's token is never replaced.

Within a workflow source the newest run counts, by run id, so re-running an old run replaces
nothing. Until that run's current attempt has the context's job, the context is pending while the
run is unfinished; a finished run or cancelled attempt without the job makes it missing. A skipped
entry never replaces another result. A context passes only when every source passes,
and a context whose entries were all made with a workflow's token (check run or commit status) is
missing. With a named app only that app's entries count.

Limits: runs of two pull requests with the same head commit are not told apart, as in GitHub's own
per-commit rules. Any workflow's real job with the required name counts, so it can stand in for a
job that never ran. Two same-name jobs in one workflow can pass before the second one is created.
One app's several same-name check runs count as one. When an attempt lists fewer same-name jobs
than an earlier one, every attempt's entries count, so a failure that a partial re-run fixed keeps
the context failing until a full re-run (fails closed). Attempts are compared by that number only,
so a partial re-run that leaves out a failed job but adds as many others is not noticed. Same-name
jobs that exclude each other are not told apart, so one's success replaces the other's failure of
an earlier run or attempt. Only `required_status_checks` rules are evaluated, not required
workflows, code scanning or deployments. A failing token-created entry is never superseded (fails
closed). An unfinished job of any run, even an older one, keeps the context pending until it ends
(fails closed). `gh` is resolved through PATH.

Prints one JSON object. Exit 0 when every required context passes, 1 when one does not, 2 when the
answer could not be determined (nothing on stdout then). Every request is a GET against github.com
with a fixed argv. Standard library only (`python3 -I`).
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from typing import Any
from urllib.parse import quote

GH_TIMEOUT = 120
REPO_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*/[A-Za-z0-9._-]+")
BRANCH_RE = re.compile(r"[A-Za-z0-9._/@+=-]+")
SHA_RE = re.compile(r"[0-9a-f]{40}")
APP_LOGIN_RE = re.compile(r"([A-Za-z0-9-]+)\[bot\]")
ACTIONS_SLUG = "github-actions"
MAX_SUITES = 1000  # GitHub lists check runs of at most this many suites per commit
PASSING_CONCLUSIONS = {"success", "neutral", "skipped"}

CHECK_RUNS = (
    ".check_runs[] | {id, name, status, conclusion, "
    "app_id: .app.id, app_slug: .app.slug, suite: .check_suite.id}"
)
STATUSES = (
    ".[] | {id, context, state, created_at, creator_id: .creator.id, "
    "creator_login: .creator.login, creator_type: .creator.type}"
)
RUNS = (
    ".workflow_runs[] | {id, workflow_id, event, status, conclusion, run_attempt, "
    "suite: .check_suite_id, head_sha}"
)
JOBS = ".jobs[] | {id, run_id, run_attempt}"
RULES = (
    '.[] | select(.type == "required_status_checks") | '
    ".parameters.required_status_checks[] | {context, app_id: .integration_id}"
)


class Undetermined(Exception):
    pass


def _gh(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            ["gh", "api", "--hostname", "github.com", "-X", "GET", *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=GH_TIMEOUT,
            check=False,
        )
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError) as exc:
        raise Undetermined(f"gh could not be run: {type(exc).__name__}") from exc


def get_lines(path: str, projection: str, paginate: bool = True) -> list[Any]:
    """Every page of `path` (or only the first), one projected JSON object per line."""
    done = _gh([path, *(["--paginate"] if paginate else []), "--jq", projection])
    if done.returncode != 0:
        raise Undetermined(f"request failed: {path}")
    try:
        return [json.loads(line) for line in done.stdout.split("\n") if line.strip()]
    except ValueError as exc:
        raise Undetermined(f"unreadable response: {path}") from exc


def protection_checks(repo: str, branch: str) -> list[dict[str, Any]]:
    done = _gh([f"repos/{repo}/branches/{branch}/protection"])
    try:
        data = json.loads(done.stdout)
    except ValueError as exc:
        raise Undetermined("unreadable branch protection response") from exc
    if not isinstance(data, dict):
        raise Undetermined("unreadable branch protection response")
    if done.returncode != 0:
        if data.get("message") == "Branch not protected" and str(data.get("status")) == "404":
            return []
        raise Undetermined("branch protection could not be read")
    required = data.get("required_status_checks") or {}
    checks = [
        {"context": c["context"], "app_id": c.get("app_id")} for c in required.get("checks") or []
    ]
    named = {c["context"] for c in checks}
    checks += [
        {"context": c, "app_id": None} for c in required.get("contexts") or [] if c not in named
    ]
    return checks


def required_contexts(repo: str, branch: str) -> dict[str, set[int | None]]:
    """Context name -> the apps that must report it; None stands for \"any app\"."""
    quoted = quote(branch, safe="")
    entries = protection_checks(repo, quoted)
    entries += get_lines(f"repos/{repo}/rules/branches/{quoted}?per_page=100", RULES)
    required: dict[str, set[int | None]] = {}
    for entry in entries:
        apps = required.setdefault(entry["context"], set())
        # No app named is null, or -1 ("any app") in classic protection.
        app = entry["app_id"]
        apps.add(app if app is not None and app > 0 else None)
    if not required:
        raise Undetermined("no required check could be found")
    return required


def head_runs(repo: str, sha: str) -> list[dict[str, Any]]:
    path = f"repos/{repo}/actions/runs?head_sha={sha}&per_page=100"
    return [r for r in get_lines(path, RUNS) if r["head_sha"] == sha]


def job_sources(
    repo: str, runs: list[dict[str, Any]], suites: set[int]
) -> dict[int, tuple[Any, ...]]:
    """Check run id -> (workflow id, event, run id, attempt), for real jobs on this head."""
    sources: dict[int, tuple[Any, ...]] = {}
    for run in runs:
        if run["suite"] not in suites:
            continue
        path = f"repos/{repo}/actions/runs/{run['id']}/jobs?filter=all&per_page=100"
        for job in get_lines(path, JOBS):
            sources[job["id"]] = (run["workflow_id"], run["event"], run["id"], job["run_attempt"])
    return sources


def check_run_state(run: dict[str, Any]) -> str:
    if run["status"] != "completed":
        return "pending"
    if run["conclusion"] == "skipped":
        return "skipped"
    return "passing" if run["conclusion"] in PASSING_CONCLUSIONS else "failing"


def status_state(status: dict[str, Any]) -> str:
    if status["state"] == "success":
        return "passing"
    return "pending" if status["state"] == "pending" else "failing"


def app_result(runs: list[dict[str, Any]]) -> int:
    """Id of the one check run that counts among an app's runs of one context."""
    newest = max(runs, key=lambda r: r["id"])
    if check_run_state(newest) == "skipped":
        ran = [r for r in runs if check_run_state(r) in ("passing", "failing")]
        newest = max(ran, key=lambda r: r["id"], default=newest)
    return newest["id"]


def check_run_entries(runs: list[dict[str, Any]], jobs: dict[int, tuple[Any, ...]]):
    by_app: dict[Any, list[dict[str, Any]]] = {}
    for run in runs:
        if run["app_id"] is None:
            raise Undetermined("a check run names no app")
        by_app.setdefault(run["app_id"], []).append(run)
    for run in runs:
        ident = run["id"]
        entry = {"app": run["app_id"], "state": check_run_state(run), "kind": "other"}
        if run["app_slug"] != ACTIONS_SLUG:
            if app_result(by_app[run["app_id"]]) != ident:
                continue
            entry["source"] = ("app", run["app_id"])
        elif ident in jobs:
            workflow, event, run_id, attempt = jobs[ident]
            entry.update(
                source=("workflow", workflow, event), kind="job", run=run_id, attempt=attempt
            )
        else:
            entry.update(source=("not-a-job", ident), kind="token")
        yield entry


def status_entries(statuses: list[dict[str, Any]], app_of_creator):
    newest: dict[Any, tuple[str, int]] = {}
    for status in statuses:
        order = (status["created_at"], status["id"])
        newest[status["creator_id"]] = max(newest.get(status["creator_id"], order), order)
    for status in statuses:
        ident, key, state = status["id"], status["creator_id"], status_state(status)
        token = status["creator_login"] == f"{ACTIONS_SLUG}[bot]"
        if newest[key][1] != ident and not (token and state == "failing"):
            continue
        yield {
            "source": ("status", key, ident),
            "app": app_of_creator(status),
            "state": state,
            "kind": "token" if token else "other",
        }


def run_result(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """The non-skipped entries of one run that count: the last attempt's, or all (see below)."""
    ran = [e for e in items if e["state"] != "skipped"]
    last = max(e["attempt"] for e in ran)

    def shrank(entries: list[dict[str, Any]]) -> bool:
        counts: dict[int, int] = {}
        for entry in entries:
            counts[entry["attempt"]] = counts.get(entry["attempt"], 0) + 1
        return any(n > counts[last] for attempt, n in counts.items() if attempt < last)

    # An attempt that lists fewer same-name jobs than an earlier one, skipped ones included or not,
    # re-ran only some of them, so the others' earlier results still count.
    return ran if shrank(items) or shrank(ran) else [e for e in ran if e["attempt"] == last]


def job_group_state(items: list[dict[str, Any]], runs: list[dict[str, Any]]) -> str:
    """State of one workflow source from its entries and every run of it on the head."""
    _, workflow, event = items[0]["source"]
    newest = max(
        (r for r in runs if (r["workflow_id"], r["event"]) == (workflow, event)),
        key=lambda r: r["id"],
    )
    by_run: dict[int, list[dict[str, Any]]] = {}
    for item in items:
        by_run.setdefault(item["run"], []).append(item)
    latest = by_run.get(newest["id"], [])
    if not any(e["attempt"] == newest["run_attempt"] for e in latest):
        if newest["status"] != "completed":
            return "pending"
        # Only a successful attempt can be one that kept an earlier attempt's job.
        if not latest or newest["conclusion"] != "success":
            return "missing"
    # A skipped entry never replaces another result, of an earlier attempt or an earlier run.
    for run_id in sorted(by_run, reverse=True):
        if any(e["state"] != "skipped" for e in by_run[run_id]):
            counted = run_result(by_run[run_id])
            return "failing" if any(e["state"] == "failing" for e in counted) else "passing"
    return "passing"


def classify(
    entries: list[dict[str, Any]], apps: set[int | None], runs: list[dict[str, Any]]
) -> tuple[str, str]:
    """State and reason of one required context; `apps` are the apps that must report it."""
    worst, why = "passing", ""
    for app in apps:
        counted = [e for e in entries if app is None or e["app"] == app]
        if not counted:
            return "missing", "no entry" if not entries else f"no entry from the required app {app}"
        if all(e["kind"] == "token" for e in counted):
            return "missing", "only entries made with a workflow token, no job"
        if any(e["state"] == "pending" for e in counted):
            worst, why = "pending", "an entry is not finished"
            continue
        groups: dict[tuple[Any, ...], list[dict[str, Any]]] = {}
        for item in counted:
            groups.setdefault(item["source"], []).append(item)
        for source, items in groups.items():
            if items[0]["kind"] == "job":
                state = job_group_state(items, runs)
            else:
                state = "failing" if any(e["state"] == "failing" for e in items) else "passing"
            name = "/".join(str(part) for part in source)
            if state in ("failing", "missing"):
                return state, f"source {name}"
            if state == "pending":
                worst, why = "pending", f"an unfinished run of source {name}"
    return worst, why


def evaluate(repo: str, branch: str, sha: str) -> dict[str, Any]:
    required = required_contexts(repo, branch)
    suites_path = f"repos/{repo}/commits/{sha}/check-suites?per_page=1"
    total = get_lines(suites_path, "{n: .total_count}", paginate=False)
    if len(total) != 1 or total[0]["n"] >= MAX_SUITES:
        raise Undetermined("too many check suites on this commit to see every check run")
    checks = [
        r
        for r in get_lines(
            f"repos/{repo}/commits/{sha}/check-runs?filter=all&per_page=100", CHECK_RUNS
        )
        if r["name"] in required
    ]
    statuses = [
        s
        for s in get_lines(f"repos/{repo}/commits/{sha}/statuses?per_page=100", STATUSES)
        if s["context"] in required
    ]
    suites = {r["suite"] for r in checks if r["app_slug"] == ACTIONS_SLUG}
    runs = head_runs(repo, sha) if suites else []
    jobs = job_sources(repo, runs, suites)

    app_ids: dict[str, int | None] = {}

    def app_of_creator(status: dict[str, Any]) -> int | None:
        # A commit status names no app; an app's statuses are created by its bot account.
        match = APP_LOGIN_RE.fullmatch(status["creator_login"] or "")
        if required[status["context"]] == {None} or status["creator_type"] != "Bot" or not match:
            return None
        slug = match.group(1)
        if slug not in app_ids:
            found = get_lines(f"apps/{slug}", "{id}")
            app_ids[slug] = found[0]["id"] if found else None
        return app_ids[slug]

    contexts = []
    for name, apps in sorted(required.items()):
        entries = list(check_run_entries([r for r in checks if r["name"] == name], jobs))
        entries += status_entries([s for s in statuses if s["context"] == name], app_of_creator)
        state, reason = classify(entries, apps, runs)
        contexts.append({"name": name, "state": state, "reason": reason})
    return {
        "head_sha": sha,
        "all_passing": all(c["state"] == "passing" for c in contexts),
        "contexts": contexts,
    }


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print(
            "usage: git-required-checks.py <owner/repo> <base-branch> <head-sha>", file=sys.stderr
        )
        return 2
    repo, branch, sha = argv
    if not REPO_RE.fullmatch(repo) or not BRANCH_RE.fullmatch(branch) or not SHA_RE.fullmatch(sha):
        print("invalid repository, branch or head SHA", file=sys.stderr)
        return 2
    try:
        result = evaluate(repo, branch, sha)
    except Undetermined as exc:
        print(f"cannot determine the required checks: {exc}", file=sys.stderr)
        return 2
    except (KeyError, TypeError, AttributeError) as exc:
        print(f"unexpected response shape: {type(exc).__name__}", file=sys.stderr)
        return 2
    print(json.dumps(result, indent=1))
    return 0 if result["all_passing"] else 1


if __name__ == "__main__":
    try:
        code = main(sys.argv[1:])
    except Exception as exc:  # noqa: BLE001 - any fault is "cannot tell" (2), never "not passing" (1)
        print(f"check failed: {type(exc).__name__}", file=sys.stderr)
        code = 2
    sys.exit(code)
