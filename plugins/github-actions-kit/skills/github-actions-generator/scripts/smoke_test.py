#!/usr/bin/env python3
"""Persisted smoke test for github-actions-generator: SKILL.md frontmatter
validity, plus a real invocation of this skill's own regression suite
(scripts/test-generator.py), which already exercises the generated
templates/examples end-to-end (YAML validity, SHA-pinning, EOF newlines,
SHA consistency, required keys, template placeholders, script-injection
risk). This smoke test delegates to it rather than duplicating its checks.
"""

import pathlib
import re
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
REGRESSION_SCRIPT = SKILL_DIR / "scripts" / "test-generator.py"


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


def check_regression_suite():
    if not REGRESSION_SCRIPT.is_file():
        return False, f"{REGRESSION_SCRIPT} does not exist"

    proc = subprocess.run(
        [sys.executable, str(REGRESSION_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(SKILL_DIR),
    )
    if proc.returncode != 0:
        tail = "\n".join(proc.stdout.strip().splitlines()[-15:])
        return False, f"test-generator.py exited {proc.returncode}:\n{tail}\n{proc.stderr.strip()}"

    return True, "scripts/test-generator.py passed against assets/templates/ and examples/"


CHECKS = [check_frontmatter, check_regression_suite]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
