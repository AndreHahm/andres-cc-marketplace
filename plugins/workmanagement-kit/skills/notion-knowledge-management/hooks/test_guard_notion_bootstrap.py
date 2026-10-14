#!/usr/bin/env python3
"""Fixture test for guard_notion_bootstrap.py and its bash launcher. Run:
    python hooks/test_guard_notion_bootstrap.py

Pipes PreToolUse-shaped JSON into the guard (through the launcher, as Claude Code does) and
asserts on the decision. Exits 0 when every case passes, 1 otherwise.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

CHECKS_RUN = [0]  # counts every assertion actually evaluated
HERE = Path(__file__).resolve().parent
LAUNCHER = HERE / "guard_notion_bootstrap.sh"
PY = HERE / "guard_notion_bootstrap.py"
UPDATE = "mcp__claude_ai_Notion__notion-update-data-source"
MOVE = "mcp__claude_ai_Notion__notion-move-pages"
DS = "collection://00000000-0000-4000-8000-0000000000d5"
PAGE = "00000000-0000-4000-8000-0000000000a1"
DB = "00000000-0000-4000-8000-0000000000b2"
ALTER = "ALTER COLUMN \"repo\" SET SELECT('other-repo':default, 'andres-cc-marketplace')"


def run(stdin_text, via_launcher=True):
    cmd = ["bash", str(LAUNCHER)] if via_launcher else [sys.executable, str(PY)]
    proc = subprocess.run(
        cmd, input=stdin_text, capture_output=True, text=True, encoding="utf-8", timeout=60
    )
    decision = None
    if proc.stdout.strip():
        decision = json.loads(proc.stdout)["hookSpecificOutput"]["permissionDecision"]
    return proc.returncode, decision


def call(tool, tool_input):
    return json.dumps({"tool_name": tool, "tool_input": tool_input})


def decision_of(stdout):
    return (
        json.loads(stdout)["hookSpecificOutput"]["permissionDecision"] if stdout.strip() else None
    )


def run_bash(args, stdin_text, env=None):
    proc = subprocess.run(
        args,
        input=stdin_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=60,
        env=env,
    )
    return proc.returncode, decision_of(proc.stdout)


def launcher_scenarios():
    """Launcher failure paths and the registered command string. Returns failure messages."""
    failures = []
    bash = shutil.which("bash")
    if bash is None:
        return ["launcher: bash not found, cannot test the launcher"]
    allowed = call(UPDATE, {"data_source_id": DS, "statements": ALTER})
    dropped = call(UPDATE, {"data_source_id": DS, "statements": 'DROP COLUMN "repo"'})

    def check(name, got, want):
        CHECKS_RUN[0] += 1
        if got != (0, want):
            failures.append(f"{name}: got {got!r}, wanted {(0, want)!r}")

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        empty = tmp / "empty"
        empty.mkdir()
        # 1. No interpreter at all, and not even coreutils on PATH: must deny, never fail open.
        env = {**os.environ, "PATH": str(empty)}
        check("no interpreter denies", run_bash([bash, str(LAUNCHER)], allowed, env), "deny")

        # 2. Every interpreter is a broken stub that exits 9009 (the Windows Store python3 alias).
        broken = tmp / "broken"
        broken.mkdir()
        for name in ("python3", "python"):
            stub = broken / name
            stub.write_text("#!/bin/bash\nexit 9009\n", encoding="utf-8", newline="\n")
            stub.chmod(0o755)
        env = {**os.environ, "PATH": str(broken)}
        check("broken stubs deny", run_bash([bash, str(LAUNCHER)], allowed, env), "deny")

        # 3. python3 is broken but python works: the cascade must fall through to python.
        mixed = tmp / "mixed"
        mixed.mkdir()
        (mixed / "python3").write_text("#!/bin/bash\nexit 9009\n", encoding="utf-8", newline="\n")
        real = sys.executable.replace("\\", "/")
        (mixed / "python").write_text(
            f'#!/bin/bash\nexec "{real}" "$@"\n', encoding="utf-8", newline="\n"
        )
        for name in ("python3", "python"):
            (mixed / name).chmod(0o755)
        env = {**os.environ, "PATH": str(mixed)}
        check("falls through to python: allow", run_bash([bash, str(LAUNCHER)], allowed, env), None)
        check(
            "falls through to python: deny", run_bash([bash, str(LAUNCHER)], dropped, env), "deny"
        )

        # 4. The registered command string, run exactly as SKILL.md's frontmatter spells it, from
        #    a plugin root whose path contains a space.
        skill_md = (HERE.parent / "SKILL.md").read_text(encoding="utf-8")
        found = re.search(r'^\s+command: "(.*)"$', skill_md, re.MULTILINE)
        if not found:
            failures.append("registered command: no command line found in SKILL.md frontmatter")
        else:
            command = found.group(1).replace('\\"', '"')
            plugin_root = tmp / "plugin root with space"
            target = plugin_root / "skills" / "notion-knowledge-management" / "hooks"
            shutil.copytree(HERE, target, ignore=shutil.ignore_patterns("__pycache__"))
            env = {**os.environ, "CLAUDE_PLUGIN_ROOT": str(plugin_root).replace("\\", "/")}
            check("registered command allow", run_bash([bash, "-c", command], allowed, env), None)
            check("registered command deny", run_bash([bash, "-c", command], dropped, env), "deny")
    return failures


def main():
    failures = []

    def expect(name, stdin_text, want, via_launcher=False):
        CHECKS_RUN[0] += 1
        code, decision = run(stdin_text, via_launcher)
        if code != 0 or decision != want:
            failures.append(f"{name}: exit {code}, decision {decision!r}, wanted {want!r}")

    allowed = {
        "add option": call(UPDATE, {"data_source_id": DS, "statements": ALTER}),
        "bare uuid data source": call(
            UPDATE,
            {"data_source_id": "00000000-0000-4000-8000-0000000000d5", "statements": ALTER + ";"},
        ),
        "rename only": call(UPDATE, {"data_source_id": DS, "title": "AndreHahm / prod / Note"}),
        "add option and rename": call(
            UPDATE, {"data_source_id": DS, "title": "X", "statements": ALTER}
        ),
        "option with space and dot": call(
            UPDATE,
            {
                "data_source_id": DS,
                "statements": "ALTER COLUMN \"repo\" SET SELECT('my repo v1.2')",
            },
        ),
        "option name of 100 characters": call(
            UPDATE,
            {
                "data_source_id": DS,
                "statements": 'ALTER COLUMN "repo" SET SELECT(\'' + "a" * 100 + "')",
            },
        ),
        "move one under a page": call(
            MOVE, {"page_or_database_ids": [DB], "new_parent": {"type": "page_id", "page_id": PAGE}}
        ),
        "ungoverned tool": call("mcp__claude_ai_Notion__notion-fetch", {"id": PAGE}),
    }
    for name, text in allowed.items():
        expect(f"allow: {name}", text, None)

    denied = {
        "drop column": call(UPDATE, {"data_source_id": DS, "statements": 'DROP COLUMN "repo"'}),
        "add column": call(UPDATE, {"data_source_id": DS, "statements": 'ADD COLUMN "x" TEXT'}),
        "other column": call(
            UPDATE, {"data_source_id": DS, "statements": "ALTER COLUMN \"Status\" SET SELECT('a')"}
        ),
        "second statement": call(
            UPDATE, {"data_source_id": DS, "statements": ALTER + '; DROP COLUMN "Name"'}
        ),
        "injection in option name": call(
            UPDATE,
            {
                "data_source_id": DS,
                "statements": 'ALTER COLUMN "repo" SET SELECT(\'a\'); DROP COLUMN "x"; --\')',
            },
        ),
        "quote in option name": call(
            UPDATE,
            {"data_source_id": DS, "statements": "ALTER COLUMN \"repo\" SET SELECT('it''s')"},
        ),
        "paren in option name": call(
            UPDATE, {"data_source_id": DS, "statements": "ALTER COLUMN \"repo\" SET SELECT('a)b')"}
        ),
        "newline between tokens": call(
            UPDATE, {"data_source_id": DS, "statements": "ALTER COLUMN \"repo\" SET SELECT(\n'a')"}
        ),
        "carriage return between tokens": call(
            UPDATE, {"data_source_id": DS, "statements": "ALTER COLUMN \"repo\" SET SELECT(\r'a')"}
        ),
        "no-break space between tokens": call(
            UPDATE, {"data_source_id": DS, "statements": "ALTER COLUMN \"repo\" SET SELECT('a')"}
        ),
        "double space in keywords": call(
            UPDATE, {"data_source_id": DS, "statements": "ALTER  COLUMN \"repo\" SET SELECT('a')"}
        ),
        "trailing content after semicolon": call(
            UPDATE, {"data_source_id": DS, "statements": ALTER + "; SELECT 1"}
        ),
        "uppercase colour": call(
            UPDATE,
            {"data_source_id": DS, "statements": "ALTER COLUMN \"repo\" SET SELECT('a':GREEN)"},
        ),
        "comment marker in option name": call(
            UPDATE, {"data_source_id": DS, "statements": "ALTER COLUMN \"repo\" SET SELECT('a --')"}
        ),
        "option name of 101 characters": call(
            UPDATE,
            {
                "data_source_id": DS,
                "statements": 'ALTER COLUMN "repo" SET SELECT(\'' + "a" * 101 + "')",
            },
        ),
        "dict without tool_name": json.dumps(
            {"tool_input": {"data_source_id": DS, "statements": ALTER}}
        ),
        "tool_name not a string": json.dumps({"tool_name": 5, "tool_input": {}}),
        "lowercase keywords": call(
            UPDATE, {"data_source_id": DS, "statements": "alter column \"repo\" set select('a')"}
        ),
        "empty option list": call(
            UPDATE, {"data_source_id": DS, "statements": 'ALTER COLUMN "repo" SET SELECT()'}
        ),
        "in_trash true": call(UPDATE, {"data_source_id": DS, "in_trash": True}),
        "in_trash false still unused": call(
            UPDATE, {"data_source_id": DS, "title": "x", "in_trash": False}
        ),
        "page_layout": call(UPDATE, {"data_source_id": DS, "page_layout": {"main": []}}),
        "description": call(UPDATE, {"data_source_id": DS, "description": "x"}),
        "is_inline": call(UPDATE, {"data_source_id": DS, "title": "x", "is_inline": True}),
        "no change": call(UPDATE, {"data_source_id": DS}),
        "missing data source": call(UPDATE, {"statements": ALTER}),
        "bad data source id": call(UPDATE, {"data_source_id": "not an id", "statements": ALTER}),
        "statements not a string": call(UPDATE, {"data_source_id": DS, "statements": ["x"]}),
        "empty title": call(UPDATE, {"data_source_id": DS, "title": "  "}),
        "move to workspace": call(
            MOVE, {"page_or_database_ids": [DB], "new_parent": {"type": "workspace"}}
        ),
        "move under database": call(
            MOVE,
            {
                "page_or_database_ids": [DB],
                "new_parent": {"type": "database_id", "database_id": DB},
            },
        ),
        "move under data source": call(
            MOVE,
            {
                "page_or_database_ids": [DB],
                "new_parent": {"type": "data_source_id", "data_source_id": DS},
            },
        ),
        "move two ids": call(
            MOVE,
            {
                "page_or_database_ids": [DB, PAGE],
                "new_parent": {"type": "page_id", "page_id": PAGE},
            },
        ),
        "move zero ids": call(
            MOVE, {"page_or_database_ids": [], "new_parent": {"type": "page_id", "page_id": PAGE}}
        ),
        "move ids not a list": call(
            MOVE, {"page_or_database_ids": DB, "new_parent": {"type": "page_id", "page_id": PAGE}}
        ),
        "move missing parent": call(MOVE, {"page_or_database_ids": [DB]}),
        "move extra parent key": call(
            MOVE,
            {
                "page_or_database_ids": [DB],
                "new_parent": {"type": "page_id", "page_id": PAGE, "x": 1},
            },
        ),
        "move extra parameter": call(
            MOVE,
            {
                "page_or_database_ids": [DB],
                "new_parent": {"type": "page_id", "page_id": PAGE},
                "x": 1,
            },
        ),
        "move non-id": call(
            MOVE,
            {"page_or_database_ids": ["x"], "new_parent": {"type": "page_id", "page_id": PAGE}},
        ),
        "tool_input not an object": json.dumps({"tool_name": UPDATE, "tool_input": "x"}),
        "malformed json": "{not json",
        "empty stdin": "",
        "not an object": json.dumps(["x"]),
    }
    for name, text in denied.items():
        expect(f"deny: {name}", text, "deny")

    # The launcher must give the same answers as the Python file called directly (and exec it
    # correctly).
    expect("launcher allow", allowed["add option"], None, via_launcher=True)
    expect("launcher deny", denied["drop column"], "deny", via_launcher=True)
    expect("launcher deny malformed", "{not json", "deny", via_launcher=True)

    failures.extend(launcher_scenarios())

    if failures:
        print(f"FAILED {len(failures)} check(s):")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print(f"PASS all guard_notion_bootstrap checks ({CHECKS_RUN[0]})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
