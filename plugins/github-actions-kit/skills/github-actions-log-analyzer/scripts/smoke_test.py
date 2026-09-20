#!/usr/bin/env python3
"""Persisted smoke test for github-actions-log-analyzer: SKILL.md frontmatter
validity, plus a real invocation of scripts/find_step_boundaries.py against a
synthetic log exercising all three boundary detectors (flue markers,
##[group]/##[endgroup], generic START/END), the RESULT_START/RESULT_END
marker path, and null-byte content -- matching the skill's own Testing &
Validation "Verify find_step_boundaries.py" checklist.
"""

import json
import pathlib
import re
import subprocess
import sys
import tempfile

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "find_step_boundaries.py"

SYNTHETIC_LOG = (
    '[flue] skill("build"): starting\n'
    "building things\n"
    '[flue] skill("build"): completed\n'
    "##[group]Run tests\n"
    "running tests\n"
    "##[endgroup]\n"
    "START\n"
    "doing custom work\n"
    "END\n"
    "RESULT_START\n"
    '{"ok": true}\n'
    "RESULT_END\n"
    "line with a null byte: \x00 -- should not crash the parser\n"
)


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


def check_script_exists():
    if not SCRIPT.is_file():
        return False, f"{SCRIPT} does not exist"
    return True, "scripts/find_step_boundaries.py exists"


def check_boundary_detection():
    if not SCRIPT.is_file():
        return False, "scripts/find_step_boundaries.py missing -- skipping execution check"

    with tempfile.TemporaryDirectory() as tmp:
        log_path = pathlib.Path(tmp) / "synthetic-run.log"
        log_path.write_bytes(SYNTHETIC_LOG.encode("utf-8"))

        proc = subprocess.run(
            [sys.executable, str(SCRIPT), str(log_path)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            return False, f"script exited {proc.returncode}: {proc.stderr.strip()}"

        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            return False, f"stdout is not valid JSON: {exc}"

        steps = payload.get("steps", [])
        sources = sorted(step["source"] for step in steps)
        if sources != ["custom", "flue", "group"]:
            return (
                False,
                f"expected one boundary of each type (flue, group, custom), got sources={sources}",
            )

        result_markers = payload.get("result_markers", [])
        if len(result_markers) != 1:
            return False, f"expected exactly 1 result marker, got {len(result_markers)}"

        # RESULT_START/RESULT_END must not also be double-counted as a generic custom boundary.
        custom_names = [step["name"] for step in steps if step["source"] == "custom"]
        if any("RESULT" in name for name in custom_names):
            return False, "RESULT_START/RESULT_END was double-counted as a generic custom boundary"

        total_lines = payload.get("total_lines")
        expected_lines = SYNTHETIC_LOG.count("\n")
        if total_lines != expected_lines:
            return False, f"total_lines={total_lines}, expected {expected_lines}"

    return (
        True,
        "flue/group/custom boundaries and result markers detected correctly; null byte handled",
    )


CHECKS = [check_frontmatter, check_script_exists, check_boundary_detection]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
