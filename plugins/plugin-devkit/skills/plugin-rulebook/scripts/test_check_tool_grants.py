#!/usr/bin/env python3
"""Fixture-based test for check_tool_grants.py. Run:
    python scripts/test_check_tool_grants.py

Builds temporary SKILL.md-shaped fixtures, runs check_tool_grants.py as a
subprocess, and asserts on exit code + expected substrings in stdout/stderr.
"""

import re
import subprocess
import sys
import tempfile
from pathlib import Path

SCRIPT = Path(__file__).parent / "check_tool_grants.py"
SAFE_FILENAME_RE = re.compile(r"[^A-Za-z0-9_-]+")


def run(*args):
    result = subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.returncode, result.stdout, result.stderr


FIXTURE_ISSUE61_REPRO = """---
name: reviewing-evals
description: test fixture
allowed-tools: Read Glob Grep Bash(python:*) Bash(node:*) AskUserQuestion Skill
---

# Test Skill

Run `git diff <base>...<branch>` to see the reviewed change range.
"""

FIXTURE_ISSUE61_FIXED = """---
name: reviewing-evals
description: test fixture
allowed-tools: Read Glob Grep Bash(python:*) Bash(node:*) Bash(git diff:*) AskUserQuestion Skill
---

# Test Skill

Run `git diff <base>...<branch>` to see the reviewed change range.
"""

FIXTURE_FALSE_POSITIVE_GUARDS = """---
name: guard-fixture
description: test fixture
allowed-tools: Read Bash(git:*)
---

# Test Skill

- A bare flag, not a command: `--continue`/`--abort`/`--rebase-merges`.
- A bare template placeholder: `{branch_name}`.
- Grant-syntax documentation, not a real invocation: `Bash(git:*)`.
- A quoted example message, not a command: `2 required checks still running: lint, test`.
- A path-based script invocation, not tool-name-checked here: `${CLAUDE_PLUGIN_ROOT}/scripts/x.sh`.
- **Wrong:** `sh -c "rm -rf /"` is an example of what NOT to do.
- A broader grant covers a narrower command: `git log -1` is covered by Bash(git:*).
- A bare shell-variable reference, not a command: `$ARGUMENTS`.
"""

FIXTURE_UNIVERSAL_GRANT = """---
name: universal-fixture
description: test fixture
allowed-tools: Read Bash(*)
---

# Test Skill

Run `sleep 30` and `anything_at_all --flag value`.
"""

FIXTURE_COMMA_SEPARATED = """---
name: comma-fixture
description: test fixture
allowed-tools: Read,Glob,Bash(git diff:*)
---

# Test Skill

Run `git diff origin/main...HEAD`.
"""

FIXTURE_YAML_LIST = """---
name: yaml-list-fixture
description: test fixture
allowed-tools:
  - Read
  - Glob
  - Bash(git diff:*)
---

# Test Skill

Run `git diff origin/main...HEAD`.
"""

FIXTURE_TRUE_MISSING_GRANTS = """---
name: multi-missing-fixture
description: test fixture
allowed-tools: Read Bash(python:*)
---

# Test Skill

First `cd .claude/worktrees/foo`, then `sleep 30`, then `grep -rn TODO .`.
"""

FIXTURE_NO_FRONTMATTER = """# No frontmatter here

Run `git diff` anyway, best-effort scan should not crash.
"""


def main():
    failures = []
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        cases = []

        for name, content, expected_code, expected_substrings, not_expected in [
            (
                "issue-61 repro: git diff missing its grant",
                FIXTURE_ISSUE61_REPRO,
                1,
                ["MISSING GRANT", "git diff <base>...<branch>", "1 finding"],
                [],
            ),
            (
                "issue-61 fixed: git diff grant present",
                FIXTURE_ISSUE61_FIXED,
                0,
                ["PASS (tool grants)"],
                ["MISSING GRANT"],
            ),
            (
                "false-positive guards all suppressed",
                FIXTURE_FALSE_POSITIVE_GUARDS,
                0,
                ["PASS (tool grants)"],
                ["MISSING GRANT"],
            ),
            (
                "universal Bash(*) grant covers everything",
                FIXTURE_UNIVERSAL_GRANT,
                0,
                ["PASS (tool grants)"],
                ["MISSING GRANT"],
            ),
            (
                "comma-separated allowed-tools parses correctly",
                FIXTURE_COMMA_SEPARATED,
                0,
                ["PASS (tool grants)"],
                ["MISSING GRANT"],
            ),
            (
                "YAML-list allowed-tools parses correctly",
                FIXTURE_YAML_LIST,
                0,
                ["PASS (tool grants)"],
                ["MISSING GRANT"],
            ),
            (
                "multiple genuinely-missing grants all reported",
                FIXTURE_TRUE_MISSING_GRANTS,
                1,
                [
                    "MISSING GRANT -- command `cd .claude/worktrees/foo`",
                    "MISSING GRANT -- command `sleep 30`",
                    "MISSING GRANT -- command `grep -rn TODO .`",
                    "3 finding(s)",
                ],
                [],
            ),
            (
                "no frontmatter: best-effort, no crash",
                FIXTURE_NO_FRONTMATTER,
                1,
                ["MISSING GRANT"],
                [],
            ),
        ]:
            fixture_path = tmp_path / f"{SAFE_FILENAME_RE.sub('_', name)}.md"
            fixture_path.write_text(content, encoding="utf-8")
            cases.append(
                (name, [str(fixture_path)], expected_code, expected_substrings, not_expected)
            )

        for name, args, expected_code, expected_substrings, not_expected_substrings in cases:
            code, out, err = run("--file", *args)
            combined = out + err
            if code != expected_code:
                failures.append(
                    f"[{name}] exit code {code}, expected {expected_code}\n  output: {combined!r}"
                )
            for s in expected_substrings:
                if s not in combined:
                    failures.append(
                        f"[{name}] missing expected substring: {s!r}\n  output: {combined!r}"
                    )
            for s in not_expected_substrings:
                if s in combined:
                    failures.append(
                        f"[{name}] found substring that should be absent: {s!r}\n"
                        f"  output: {combined!r}"
                    )

        # Nonexistent file: blocking failure, not a crash.
        code, out, err = run("--file", str(tmp_path / "does-not-exist.md"))
        combined = out + err
        if code != 2:
            failures.append(f"[nonexistent file] exit code {code}, expected 2")
        if "not found" not in combined:
            failures.append(f"[nonexistent file] missing 'not found' in output: {combined!r}")

    if failures:
        print(f"FAIL: {len(failures)} case(s) failed")
        for f in failures:
            print(f"  - {f}")
        return 1

    print(f"PASS: all {len(cases) + 1} fixture cases behaved as expected")
    return 0


if __name__ == "__main__":
    sys.exit(main())
