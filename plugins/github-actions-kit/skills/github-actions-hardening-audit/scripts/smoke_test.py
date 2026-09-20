#!/usr/bin/env python3
"""Persisted smoke test for github-actions-hardening-audit: SKILL.md
frontmatter validity, plus a real invocation of
scripts/workflow_hardening_audit.py against the skill's own bundled
fixtures/*.yml -- reproducing exactly the scores the skill's own Testing &
Validation "Quality gates" section documents (clean.yml=0/ok,
risky.yml=9/critical, reusable-caller.yml=0/ok).
"""

import json
import os
import pathlib
import re
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "workflow_hardening_audit.py"
FIXTURES_DIR = SKILL_DIR / "fixtures"

EXPECTED_SCORES = {
    "clean.yml": 0,
    "risky.yml": 9,
    "reusable-caller.yml": 0,
}


def _parse_frontmatter_fields(fm: str) -> dict:
    # A top-level `key: >-`/`key: |` starts a YAML block scalar whose real value is the
    # following more-indented lines, not the `>-`/`|` marker itself -- every SKILL.md in this
    # plugin uses `description: >-`, so a naive single-line split would always see a truthy
    # 2-character placeholder instead of the actual description body.
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


def check_script_and_fixtures_exist():
    missing = []
    if not SCRIPT.is_file():
        missing.append(str(SCRIPT))
    for name in EXPECTED_SCORES:
        if not (FIXTURES_DIR / name).is_file():
            missing.append(str(FIXTURES_DIR / name))
    if missing:
        return False, "missing file(s): " + ", ".join(missing)
    return True, "script and all three documented fixtures exist"


def check_fixture_scores():
    if not SCRIPT.is_file() or not FIXTURES_DIR.is_dir():
        return False, "script or fixtures/ missing -- skipping execution check"

    env = dict(os.environ)
    env["WORKFLOW_GLOB"] = str(FIXTURES_DIR / "*.y*ml")
    env["OUTPUT_FORMAT"] = "json"

    proc = subprocess.run([sys.executable, str(SCRIPT)], capture_output=True, text=True, env=env)
    if proc.returncode != 0:
        return (
            False,
            f"expected exit 0 in report mode, got {proc.returncode}: {proc.stderr.strip()}",
        )

    try:
        payload = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        return False, f"stdout is not valid JSON: {exc}"

    scores_by_file = {}
    for group in ("all_workflows", "workflows", "critical_workflows"):
        for row in payload.get(group, []):
            name = pathlib.Path(row.get("workflow_file", "")).name
            if name in EXPECTED_SCORES:
                scores_by_file[name] = row.get("score")

    mismatches = []
    for name, expected in EXPECTED_SCORES.items():
        actual = scores_by_file.get(name)
        if actual != expected:
            mismatches.append(f"{name}: expected {expected}, got {actual}")

    if mismatches:
        return False, "fixture score mismatch(es): " + "; ".join(mismatches)

    return True, "clean.yml=0, risky.yml=9, reusable-caller.yml=0 -- all match documented scores"


CHECKS = [check_frontmatter, check_script_and_fixtures_exist, check_fixture_scores]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
