#!/usr/bin/env python3
"""GitHub Actions Workflow Hardening Audit.

Statically scores workflow YAML files for hardening gaps (missing
timeout-minutes/permissions/concurrency, floating `uses:` refs) and reports
a ranked, severity-classified summary. Configured entirely via environment
variables so it can be dropped into CI the same way as the original script.
"""

from __future__ import annotations

import glob as globmod
import json
import os
import re
import sys
from pathlib import Path
from typing import TypedDict


class WorkflowRow(TypedDict):
    workflow_file: str
    severity: str
    score: int
    total_jobs: int
    missing_timeout_jobs: list[str]
    missing_permission_jobs: list[str]
    missing_concurrency_jobs: list[str]
    floating_refs: list[dict[str, object]]
    events: list[str]


def env_str(name: str, default: str) -> str:
    return os.environ.get(name, default)


def env_int(name: str, default: int) -> int:
    raw = os.environ.get(name, str(default))
    if not re.match(r"^[0-9]+$", raw):
        print(f"ERROR: {name} must be a non-negative integer (got: {raw})", file=sys.stderr)
        sys.exit(1)
    return int(raw)


def env_bool01(name: str, default: int) -> bool:
    return env_int(name, default) == 1


def compile_optional_regex(pattern: str, label: str) -> re.Pattern[str] | None:
    if not pattern:
        return None
    try:
        return re.compile(pattern)
    except re.error as exc:
        print(f"ERROR: invalid {label} {pattern!r}: {exc}", file=sys.stderr)
        sys.exit(1)


JOB_KEY_RE = re.compile(r"^[A-Za-z0-9_.-]+:\s*(#.*)?$")
USES_RE = re.compile(r"^\s*(?:-\s*)?uses:\s*([^\s#]+)")
VALID_TRIGGER_NAMES = {
    "push",
    "pull_request",
    "pull_request_target",
    "workflow_dispatch",
    "repository_dispatch",
    "schedule",
    "merge_group",
    "workflow_run",
    "release",
}
TRIGGER_KEY_RE = re.compile(
    r"^(push|pull_request|pull_request_target|workflow_dispatch|repository_dispatch|"
    r"schedule|merge_group|workflow_run|release):"
)
ON_INLINE_RE = re.compile(r"^on\s*:\s*(.+)$")
IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def parse_inline_on_events(raw_value: str) -> list[str]:
    """Parse a single-line `on: <value>` right-hand side into trigger names.

    Handles a bare scalar (`on: push`), a quoted scalar (`on: "push"`), and a
    flow sequence (`on: [push, pull_request_target]`) — the three single-line
    forms YAML allows for the `on:` key, none of which the block-style-only
    in_on scanner above detects on its own.
    """
    value = raw_value.split("#", 1)[0].strip()
    if not value:
        return []
    if value.startswith("[") and value.endswith("]"):
        items = value[1:-1].split(",")
    else:
        items = [value]
    events: list[str] = []
    for item in items:
        token = item.strip().strip("'\"")
        if token and IDENTIFIER_RE.match(token) and token in VALID_TRIGGER_NAMES:
            events.append(token)
    return events


def classify_ref(uses_value: str, allow_ref_regex: re.Pattern[str] | None) -> str | None:
    if "@" not in uses_value:
        return None
    ref = uses_value.rsplit("@", 1)[1].strip()
    if allow_ref_regex and allow_ref_regex.search(ref):
        return None
    lowered = ref.lower()
    if lowered in {"main", "master", "head", "latest", "stable", "trunk", "dev", "develop"}:
        return "branch-like"
    if re.match(r"^v\d+$", lowered):
        return "major-tag"
    return None


def main() -> int:
    workflow_glob = env_str("WORKFLOW_GLOB", ".github/workflows/*.y*ml")
    top_n = env_int("TOP_N", 20)
    output_format = env_str("OUTPUT_FORMAT", "text")
    warn_score = env_int("WARN_SCORE", 3)
    critical_score = env_int("CRITICAL_SCORE", 7)
    require_timeout = env_bool01("REQUIRE_TIMEOUT", 1)
    require_permissions = env_bool01("REQUIRE_PERMISSIONS", 1)
    require_concurrency = env_bool01("REQUIRE_CONCURRENCY", 0)
    flag_floating_refs = env_bool01("FLAG_FLOATING_REFS", 1)
    allow_ref_regex_raw = env_str("ALLOW_REF_REGEX", "")
    workflow_file_match_raw = env_str("WORKFLOW_FILE_MATCH", "")
    workflow_file_exclude_raw = env_str("WORKFLOW_FILE_EXCLUDE", "")
    event_match_raw = env_str("EVENT_MATCH", "")
    event_exclude_raw = env_str("EVENT_EXCLUDE", "")
    fail_on_critical = env_bool01("FAIL_ON_CRITICAL", 0)

    if output_format not in ("text", "json"):
        print(
            f"ERROR: OUTPUT_FORMAT must be 'text' or 'json' (got: {output_format})", file=sys.stderr
        )
        return 1
    if top_n == 0:
        print("ERROR: TOP_N must be >= 1", file=sys.stderr)
        return 1
    if warn_score > critical_score:
        print("ERROR: WARN_SCORE must be <= CRITICAL_SCORE", file=sys.stderr)
        return 1

    allow_ref_regex = compile_optional_regex(allow_ref_regex_raw, "ALLOW_REF_REGEX")
    workflow_file_match = compile_optional_regex(workflow_file_match_raw, "WORKFLOW_FILE_MATCH")
    workflow_file_exclude = compile_optional_regex(
        workflow_file_exclude_raw, "WORKFLOW_FILE_EXCLUDE"
    )
    event_match = compile_optional_regex(event_match_raw, "EVENT_MATCH")
    event_exclude = compile_optional_regex(event_exclude_raw, "EVENT_EXCLUDE")

    files = sorted(globmod.glob(workflow_glob, recursive=True))
    if not files:
        print(f"ERROR: no files matched WORKFLOW_GLOB={workflow_glob}", file=sys.stderr)
        return 1

    if workflow_file_match:
        files = [path for path in files if workflow_file_match.search(path)]
    if workflow_file_exclude:
        files = [path for path in files if not workflow_file_exclude.search(path)]

    if not files:
        print(
            "ERROR: no files left after WORKFLOW_FILE_MATCH/WORKFLOW_FILE_EXCLUDE filtering "
            f"(match={workflow_file_match_raw or '<none>'}, "
            f"exclude={workflow_file_exclude_raw or '<none>'})",
            file=sys.stderr,
        )
        return 1

    rows: list[WorkflowRow] = []
    parse_errors = []
    skipped_by_event_filter = []

    for file_path in files:
        try:
            text = Path(file_path).read_text(encoding="utf-8")
        except Exception as exc:
            parse_errors.append(f"{file_path}: {exc}")
            continue

        lines = text.splitlines()
        workflow_permissions = False
        workflow_concurrency = False
        events: set[str] = set()

        in_on = False
        on_indent = -1

        in_jobs = False
        jobs_indent = -1
        current_job: str | None = None
        total_jobs = 0
        job_timeout: dict[str, bool] = {}
        job_permissions: dict[str, bool] = {}
        job_concurrency: dict[str, bool] = {}

        floating_refs: list[dict] = []

        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue

            indent = len(line) - len(line.lstrip(" "))

            if re.match(r"^permissions\s*:", line):
                workflow_permissions = True
            if re.match(r"^concurrency\s*:", line):
                workflow_concurrency = True

            if re.match(r"^on\s*:\s*$", line):
                in_on = True
                on_indent = indent
                continue

            if in_on:
                if indent <= on_indent and stripped:
                    in_on = False
                else:
                    trigger_match = TRIGGER_KEY_RE.match(stripped)
                    if trigger_match:
                        events.add(trigger_match.group(1))

            if not in_on:
                inline_on_match = ON_INLINE_RE.match(line)
                if inline_on_match:
                    for event_name in parse_inline_on_events(inline_on_match.group(1)):
                        events.add(event_name)

            use_match = USES_RE.match(line)
            if use_match and flag_floating_refs:
                uses_value = use_match.group(1)
                reason = classify_ref(uses_value, allow_ref_regex)
                if reason:
                    floating_refs.append({"line": idx, "uses": uses_value, "reason": reason})

            if not in_jobs and re.match(r"^jobs\s*:\s*$", line):
                in_jobs = True
                jobs_indent = indent
                current_job = None
                continue

            if in_jobs:
                if indent <= jobs_indent and stripped:
                    in_jobs = False
                    current_job = None
                    continue

                if indent == jobs_indent + 2 and JOB_KEY_RE.match(stripped):
                    current_job = stripped.split(":", 1)[0]
                    total_jobs += 1
                    job_timeout[current_job] = False
                    job_permissions[current_job] = False
                    job_concurrency[current_job] = False
                    continue

                if current_job and indent > jobs_indent + 2:
                    if re.match(r"^\s*timeout-minutes\s*:", line):
                        job_timeout[current_job] = True
                    if re.match(r"^\s*permissions\s*:", line):
                        job_permissions[current_job] = True
                    if re.match(r"^\s*concurrency\s*:", line):
                        job_concurrency[current_job] = True

        matched_events = sorted(events)
        if event_match and not any(event_match.search(event) for event in matched_events):
            skipped_by_event_filter.append(file_path)
            continue
        if event_exclude and any(event_exclude.search(event) for event in matched_events):
            skipped_by_event_filter.append(file_path)
            continue

        missing_timeout_jobs: list[str] = []
        missing_permission_jobs: list[str] = []
        missing_concurrency_jobs: list[str] = []

        if require_timeout:
            missing_timeout_jobs = [
                job for job, has_timeout in job_timeout.items() if not has_timeout
            ]

        if require_permissions:
            if workflow_permissions:
                missing_permission_jobs = []
            elif total_jobs:
                missing_permission_jobs = [
                    job for job, has_permissions in job_permissions.items() if not has_permissions
                ]
            else:
                missing_permission_jobs = ["<workflow>"]

        if require_concurrency:
            if workflow_concurrency:
                missing_concurrency_jobs = []
            elif total_jobs:
                missing_concurrency_jobs = [
                    job for job, has_concurrency in job_concurrency.items() if not has_concurrency
                ]
            else:
                missing_concurrency_jobs = ["<workflow>"]

        score = 0
        score += len(missing_timeout_jobs) * 2
        score += len(missing_permission_jobs) * 1
        score += len(missing_concurrency_jobs) * 1
        score += len(floating_refs) * 2
        if "pull_request_target" in events:
            score += 2

        severity = "ok"
        if score >= critical_score:
            severity = "critical"
        elif score >= warn_score:
            severity = "warn"

        rows.append(
            {
                "workflow_file": file_path,
                "severity": severity,
                "score": score,
                "total_jobs": total_jobs,
                "missing_timeout_jobs": missing_timeout_jobs,
                "missing_permission_jobs": missing_permission_jobs,
                "missing_concurrency_jobs": missing_concurrency_jobs,
                "floating_refs": floating_refs,
                "events": matched_events,
            }
        )

    rows.sort(key=lambda row: (-row["score"], row["workflow_file"]))
    critical_rows = [row for row in rows if row["severity"] == "critical"]

    summary = {
        "files_scanned": len(files),
        "files_evaluated": len(rows),
        "files_skipped_by_event_filter": len(skipped_by_event_filter),
        "parse_errors": parse_errors,
        "critical_workflows": len(critical_rows),
        "warn_workflows": len([row for row in rows if row["severity"] == "warn"]),
        "ok_workflows": len([row for row in rows if row["severity"] == "ok"]),
        "warn_score": warn_score,
        "critical_score": critical_score,
        "checks": {
            "require_timeout": require_timeout,
            "require_permissions": require_permissions,
            "require_concurrency": require_concurrency,
            "flag_floating_refs": flag_floating_refs,
            "allow_ref_regex": allow_ref_regex_raw or None,
            "workflow_file_match": workflow_file_match_raw or None,
            "workflow_file_exclude": workflow_file_exclude_raw or None,
            "event_match": event_match_raw or None,
            "event_exclude": event_exclude_raw or None,
        },
    }

    if output_format == "json":
        print(
            json.dumps(
                {
                    "summary": summary,
                    "workflows": rows[:top_n],
                    "all_workflows": rows,
                    "critical_workflows": critical_rows,
                },
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print("GITHUB ACTIONS WORKFLOW HARDENING AUDIT")
        print("---")
        print(
            "SUMMARY: "
            f"files={summary['files_scanned']} evaluated={summary['files_evaluated']} "
            f"filtered={summary['files_skipped_by_event_filter']} "
            f"critical={summary['critical_workflows']} warn={summary['warn_workflows']} "
            f"ok={summary['ok_workflows']}"
        )
        if parse_errors:
            print("PARSE_ERRORS:")
            for err in parse_errors:
                print(f"- {err}")
        print("---")
        print(f"TOP WORKFLOWS ({min(top_n, len(rows))})")
        if not rows:
            print("none")
        else:
            for row in rows[:top_n]:
                print(
                    f"- [{row['severity']}] file={row['workflow_file']} "
                    f"score={row['score']} jobs={row['total_jobs']} "
                    f"missing_timeout={len(row['missing_timeout_jobs'])} "
                    f"missing_permissions={len(row['missing_permission_jobs'])} "
                    f"missing_concurrency={len(row['missing_concurrency_jobs'])} "
                    f"floating_refs={len(row['floating_refs'])} "
                    f"events={','.join(row['events']) if row['events'] else '<none>'}"
                )

    return 1 if (fail_on_critical and critical_rows) else 0


if __name__ == "__main__":
    sys.exit(main())
