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
import subprocess  # nosec B404 -- only used to invoke this skill's own bundled script
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
REGRESSION_SCRIPT = SKILL_DIR / "scripts" / "test-generator.py"


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


def check_regression_suite():
    if not REGRESSION_SCRIPT.is_file():
        return False, f"{REGRESSION_SCRIPT} does not exist"

    # Fixed argv (sys.executable + this skill's own script path resolved from __file__, no shell,
    # no untrusted input) -- static analysis can't see that REGRESSION_SCRIPT is a constant.
    proc = subprocess.run(  # nosemgrep
        [sys.executable, str(REGRESSION_SCRIPT)],
        capture_output=True,
        text=True,
        cwd=str(SKILL_DIR),
    )  # nosec B603
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
