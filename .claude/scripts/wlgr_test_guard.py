#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Tests for the local-config guard hook, fed the JSON Claude Code sends.
Run: python wlgr_test_guard.py   (exit 0 = all passed)."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
import unittest
from pathlib import Path

HOOKS = Path(__file__).resolve().parent.parent / "hooks"
SCRIPT = HOOKS / "wlgr-guard-local-config.sh"
BASH = shutil.which("bash") or "bash"
FILE = "C:\\work\\repo\\.claude\\workledger-kit.local.json"


def call(payload: object = None, env: dict | None = None, raw: str | None = None) -> str:
    """The hook's decision, or "" when it has no opinion."""
    result = subprocess.run(
        [BASH, str(SCRIPT)],
        # Raw UTF-8, as JSON.stringify sends it.
        input=raw if raw is not None else json.dumps(payload, ensure_ascii=False),
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr
    if not result.stdout.strip():
        return ""
    return json.loads(result.stdout)["hookSpecificOutput"]["permissionDecision"]


def tool(path: object, name: str = "Write", **extra: object) -> dict:
    return {"tool_name": name, "tool_input": {"file_path": path, **extra}}


class GuardTests(unittest.TestCase):
    def test_asks_for_the_file_whatever_its_spelling(self) -> None:
        for path in (
            FILE,
            "/home/me/repo/.claude/workledger-kit.local.json",
            "/home/me/repo/.Claude/WorkLedger-Kit.LOCAL.json",
            "C:\\r\\.claude\\workledger-kit.local.json.",
            "C:\\r\\.claude\\workledger-kit.local.json::$DATA",
            "/r/.claude/skills/../workledger-kit.local.json",
            "\\\\?\\C:\\r\\.claude\\workledger-kit.local.json",
            "\\\\host\\share\\.claude\\workledger-kit.local.json",
            "C:\\r\\CLAUDE~1\\WORKLE~1.JSO",
            ".claude/workledger-kit.local.json",
            '/r/a"b/.claude/workledger-kit.local.json',
            "/r/.claude/\u00fc/../workledger-kit.local.json",
        ):
            with self.subTest(path=path):
                self.assertEqual(call(tool(path)), "ask")
                self.assertEqual(call(tool(path, content="x")), "ask")
        for name in ("Edit", "MultiEdit"):
            with self.subTest(name=name):
                self.assertEqual(call(tool(FILE, name)), "ask")

    def test_passes_everything_else(self) -> None:
        for payload in (
            tool("/r/src/main.py"),
            tool("/r/docs/notes.md", content="see .claude/workledger-kit.local.json"),
            tool("C:\\Users\\me~1\\x.py"),
            tool("/r/.claude/settings.json"),
            tool("/r/a.md", content='"file_path": ".claude/workledger-kit.local.json"'),
        ):
            with self.subTest(payload=payload):
                self.assertEqual(call(payload), "")

    def test_content_cannot_hide_the_path(self) -> None:
        # The content comes before the path, and carries its own fake, harmless "file_path".
        fake = '{"file_path": "/r/safe.txt"}'
        payload = {"tool_name": "Write", "tool_input": {"content": fake, "file_path": FILE}}
        self.assertEqual(call(payload), "ask")

    def test_another_path_key_cannot_answer_for_the_real_one(self) -> None:
        for extra in (
            {"FILE_PATH": "/r/safe"},
            {"edits": [{"file_path": "/r/safe"}]},
        ):
            for tool_input in ({**extra, "file_path": FILE}, {"file_path": FILE, **extra}):
                with self.subTest(tool_input=tool_input):
                    payload = {"tool_name": "MultiEdit", "tool_input": tool_input}
                    self.assertEqual(call(payload), "ask")

    def test_input_without_a_readable_path_asks_only_when_it_names_the_file(self) -> None:
        self.assertEqual(call(raw="{broken workledger-kit.local.json"), "ask")
        self.assertEqual(call(raw='{"tool_input":"workledger-kit.local.json"}'), "ask")
        self.assertEqual(call(raw="{broken"), "")
        self.assertEqual(call(raw=""), "")

    def test_nothing_on_path(self) -> None:
        with tempfile.TemporaryDirectory() as empty:
            env = {"PATH": empty}
            if os.name == "nt":
                env["SYSTEMROOT"] = os.environ["SYSTEMROOT"]
            self.assertEqual(call(tool(FILE), env=env), "ask")
            self.assertEqual(call(tool("/r/src/main.py"), env=env), "")

    def test_a_cat_on_path_is_not_run(self) -> None:
        with tempfile.TemporaryDirectory() as planted:
            marker = Path(planted) / "ran"
            fake = Path(planted) / "cat"
            fake.write_text(f"#!/bin/sh\ntouch '{marker.as_posix()}'\n", encoding="utf-8")
            fake.chmod(0o755)
            env = {**os.environ, "PATH": planted + os.pathsep + os.environ["PATH"]}
            self.assertEqual(call(tool(FILE), env=env), "ask")
            self.assertEqual(call(tool("/r/src/main.py"), env=env), "")
            self.assertFalse(marker.exists())

    def test_a_large_write_is_quick(self) -> None:
        started = time.monotonic()
        self.assertEqual(call(tool("/r/big.txt", content="a b " * 1_000_000)), "")
        self.assertEqual(call(tool(FILE, content="a b " * 1_000_000)), "ask")
        big = {"content": "a b " * 1_000_000, "file_path": FILE}
        self.assertEqual(call({"tool_name": "Write", "tool_input": big}), "ask")
        self.assertLess(time.monotonic() - started, 15)

    def test_a_link_with_another_name_is_not_covered(self) -> None:
        # Pins a documented limit: the hook opens no path.
        self.assertEqual(call(tool("/r/notes.txt")), "")

    def test_the_hook_is_executable_in_git(self) -> None:
        result = subprocess.run(
            ["git", "ls-files", "-s", "--", SCRIPT.name],
            cwd=HOOKS,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0 or not result.stdout.strip():
            self.skipTest("the hook is not in the index")
        self.assertTrue(result.stdout.startswith("100755"), result.stdout)

    def test_registration(self) -> None:
        hooks = json.loads((HOOKS / "hooks.json").read_text(encoding="utf-8"))["hooks"]
        # The .claude mirror merges every plugin's hooks into one file: find this guard's entry.
        matches = [
            (entry, hook)
            for entry in hooks["PreToolUse"]
            for hook in entry["hooks"]
            if hook["command"].endswith(f"/hooks/{SCRIPT.name}")
        ]
        self.assertEqual(len(matches), 1, matches)
        ((entry, _),) = matches
        self.assertEqual(entry["matcher"], "^(Write|Edit|MultiEdit)$")


if __name__ == "__main__":
    unittest.main()
