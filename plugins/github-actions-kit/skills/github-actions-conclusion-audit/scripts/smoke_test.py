#!/usr/bin/env python3
"""Persisted smoke test for github-actions-conclusion-audit: SKILL.md
frontmatter validity, plus real invocations of
scripts/conclusion_volatility_audit.py against synthetic run-history JSON --
matching the skill's own documented Quality gates (critical-instability
detection, FAIL_ON_CRITICAL exit codes, JSON output schema, and the
malformed-file-never-silently-passes gate).
"""

import json
import os
import pathlib
import re
import subprocess  # nosec B404 -- only used to invoke this skill's own bundled script
import sys
import tempfile

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "conclusion_volatility_audit.py"

CONCLUSIONS = ["success", "failure", "success", "failure", "success", "failure"]

# Every documented audit option, reset to conclusion_volatility_audit.py's own default before each
# run -- a caller with e.g. WARN_INSTABILITY_PCT or FAIL_ON_CRITICAL already exported would
# otherwise leak into these fixed-score assertions.
AUDIT_DEFAULTS = {
    "RUN_GLOB": "artifacts/github-actions/*.json",
    "TOP_N": "20",
    "OUTPUT_FORMAT": "text",
    "MIN_RUNS": "5",
    "WARN_INSTABILITY_PCT": "35",
    "CRITICAL_INSTABILITY_PCT": "60",
    "FAIL_ON_CRITICAL": "0",
    "WORKFLOW_MATCH": "",
    "WORKFLOW_EXCLUDE": "",
    "BRANCH_MATCH": "",
    "BRANCH_EXCLUDE": "",
    "REPO_MATCH": "",
    "REPO_EXCLUDE": "",
}


def _make_run_files(tmp_dir: pathlib.Path, conclusions):
    for i, conclusion in enumerate(conclusions):
        payload = {
            "databaseId": 1000 + i,
            "workflowName": "ci.yml",
            "headBranch": "main",
            "conclusion": conclusion,
            "createdAt": f"2026-09-{10 + i:02d}T00:00:00Z",
            "updatedAt": f"2026-09-{10 + i:02d}T00:05:00Z",
            "url": f"https://github.com/example/repo/actions/runs/{1000 + i}",
            "repository": "example/repo",
        }
        (tmp_dir / f"run-{1000 + i}.json").write_text(json.dumps(payload), encoding="utf-8")


def _parse_frontmatter_fields(fm: str) -> dict:
    # Dependency-free by design (no PyYAML) -- this script must run standalone when the plugin is
    # installed from the marketplace, where PyYAML is only a repo *dev* dependency, not something
    # available to a plugin end user. Handles the two YAML shapes these frontmatter blocks actually
    # use: a `key: >-`/`key: |` block scalar (collects the following more-indented lines as the
    # real value) and a plain scalar, rejecting an unterminated quoted value (e.g.
    # `description: "unterminated`) as malformed rather than silently accepting it.
    lines = fm.splitlines()
    fields = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if ":" in line and not line[:1].isspace():
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if re.match(r"^[|>][+-]?\d*$", value):
                block = []
                i += 1
                while i < len(lines) and (lines[i][:1].isspace() or not lines[i].strip()):
                    block.append(lines[i].strip())
                    i += 1
                fields[key] = " ".join(block).strip()
                continue
            if value[:1] in ("'", '"'):
                quote = value[0]
                if len(value) < 2 or value[-1] != quote:
                    return {}
                value = value[1:-1]
            fields[key] = value
        i += 1
    return fields


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    fields = _parse_frontmatter_fields(fm)
    if not fields.get("name"):
        return False, "frontmatter missing non-empty 'name' field"
    if not fields.get("description"):
        return False, "frontmatter missing non-empty 'description' field"
    if fields["name"] != SKILL_DIR.name:
        return (
            False,
            f"frontmatter name '{fields['name']}' does not match directory '{SKILL_DIR.name}'",
        )
    return True, "frontmatter present, closed, and name matches directory"


def check_script_exists():
    if not SCRIPT.is_file():
        return False, f"{SCRIPT} does not exist"
    return True, "scripts/conclusion_volatility_audit.py exists"


def _run(run_glob, extra_env=None):
    env = dict(os.environ)
    env.update(AUDIT_DEFAULTS)
    env["RUN_GLOB"] = run_glob
    env["OUTPUT_FORMAT"] = "json"
    env["FAIL_ON_CRITICAL"] = "1"
    if extra_env:
        env.update(extra_env)
    # Fixed argv (sys.executable + this skill's own script path resolved from __file__, no shell,
    # no untrusted input) -- static analysis can't see that SCRIPT is a constant.
    return subprocess.run(  # nosemgrep
        [sys.executable, str(SCRIPT)], capture_output=True, text=True, env=env
    )  # nosec B603


def check_critical_instability_detected():
    if not SCRIPT.is_file():
        return False, "scripts/conclusion_volatility_audit.py missing -- skipping execution check"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = pathlib.Path(tmp)
        _make_run_files(tmp_dir, CONCLUSIONS)
        proc = _run(str(tmp_dir / "*.json"), {"MIN_RUNS": "5"})

        if proc.returncode != 1:
            return (
                False,
                f"expected exit 1 (critical group + FAIL_ON_CRITICAL), got {proc.returncode}: "
                f"{proc.stderr.strip()}",
            )

        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            return False, f"stdout is not valid JSON: {exc}"

        for key in ("summary", "groups", "all_groups", "critical_groups"):
            if key not in payload:
                return False, f"JSON output missing documented top-level key '{key}'"

        if not payload["critical_groups"]:
            return False, "alternating success/failure run history did not produce a critical group"

    return (
        True,
        "alternating conclusions flagged critical, exit 1, all four documented keys present",
    )


def check_malformed_file_never_passes_gate():
    if not SCRIPT.is_file():
        return False, "scripts/conclusion_volatility_audit.py missing -- skipping execution check"

    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = pathlib.Path(tmp)
        (tmp_dir / "run-bad.json").write_text("{not valid json", encoding="utf-8")
        proc = _run(str(tmp_dir / "*.json"))

        if proc.returncode != 1:
            return (
                False,
                f"a malformed-JSON-only match with FAIL_ON_CRITICAL=1 must exit 1, got "
                f"{proc.returncode}",
            )

    return (
        True,
        "a match set with only a malformed file exits 1 rather than silently passing the gate",
    )


CHECKS = [
    check_frontmatter,
    check_script_exists,
    check_critical_instability_detected,
    check_malformed_file_never_passes_gate,
]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
