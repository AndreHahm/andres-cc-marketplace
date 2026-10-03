#!/usr/bin/env python3
"""Shared helpers for promptlibrary-kit's per-skill smoke tests.

Each skill's scripts/smoke_test.py imports this module so the grant-parsing and fixture logic
lives in one place. Standard library only. Nothing here touches the real repository: live checks
run the validator against a throwaway git repository under the system temp directory.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

PLUGIN_DIR = Path(__file__).resolve().parent.parent
VALIDATOR = PLUGIN_DIR / "scripts" / "plib_catalog_validate.py"

_SPEC = importlib.util.spec_from_file_location("plib_catalog_validate", VALIDATOR)
if _SPEC is None or _SPEC.loader is None:
    raise SystemExit(f"cannot load the validator at {VALIDATOR}")
V = importlib.util.module_from_spec(_SPEC)
sys.modules["plib_catalog_validate"] = V
_SPEC.loader.exec_module(V)

BODY = "Review the diff for missing tests.\nList each gap with a file and line."
SLUG = "review__missing-tests"
# Built from pieces so this file itself holds no complete secret-shaped literal.
FAKE_KEY = "AKIA" + "ABCDEFGHIJKLMNOP"


def read_skill(skill_dir: Path) -> tuple[str, str]:
    """Return (frontmatter text, body text) of a skill's SKILL.md."""
    text = (skill_dir / "SKILL.md").read_text(encoding="utf-8").replace("\r\n", "\n")
    if not text.startswith("---\n"):
        raise ValueError("SKILL.md does not start with a frontmatter block")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise ValueError("frontmatter block is never closed")
    return text[4:end], text[end + 5 :]


def frontmatter_field(frontmatter: str, key: str) -> str | None:
    """Single-line value of a top-level key, or None when the key is absent."""
    match = re.search(rf"^{re.escape(key)}:[ \t]*(.*)$", frontmatter, re.MULTILINE)
    return match.group(1).strip() if match else None


def has_block_description(frontmatter: str) -> bool:
    return re.search(r"^description:[ \t]*>-?[ \t]*$", frontmatter, re.MULTILINE) is not None


def split_grants(allowed_tools: str) -> list[str]:
    """Split an allowed-tools line on top-level commas (commas inside parentheses stay)."""
    grants, depth, current = [], 0, ""
    for ch in allowed_tools:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth == 0:
            grants.append(current.strip())
            current = ""
        else:
            current += ch
    if current.strip():
        grants.append(current.strip())
    return grants


def grant_name(grant: str) -> str:
    return grant.split("(", 1)[0].strip()


def validator_subcommands_granted(allowed_tools: str) -> list[str]:
    """Subcommands named by Bash grants that run the validator, in order of appearance."""
    pattern = r'plib_catalog_validate\.py"\s+([a-z][a-z-]*):\*'
    return re.findall(pattern, allowed_tools)


def body_subcommands(body: str) -> set[str]:
    """Validator subcommands the skill body tells the model to run (`<CLI> <subcommand>`)."""
    return set(re.findall(r"<CLI>\s+([a-z][a-z-]*)", body))


def referenced_files_missing(skill_dir: Path, body: str) -> list[str]:
    """Backticked references/ or assets/ markdown files that do not exist in the skill dir."""
    pattern = r"`((?:references|assets)/[\w.-]+\.md)`"
    return sorted({p for p in re.findall(pattern, body) if not (skill_dir / p).is_file()})


class Fixture:
    """A throwaway git repository under the system temp directory, plus validator helpers."""

    def __init__(self) -> None:
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.repo = Path(self._tmp.name)
        self._scratch_files: list[Path] = []
        subprocess.run(["git", "init", "-q"], cwd=self.repo, check=True)

    def close(self) -> None:
        for path in self._scratch_files:
            path.unlink(missing_ok=True)
        self._tmp.cleanup()

    def run(self, *args: str) -> tuple[int, dict]:
        proc = subprocess.run(
            [sys.executable, str(VALIDATOR), *args],
            cwd=self.repo,
            capture_output=True,
            text=True,
            timeout=60,
        )
        try:
            return proc.returncode, json.loads(proc.stdout)
        except ValueError:
            return proc.returncode, {"ok": False, "error": "validator printed no JSON"}

    def scratch(self, **over: object) -> str:
        """Write a draft record to a scratch file in the temp area and return its path."""
        meta = {
            "name": "Missing tests review",
            "area": "review",
            "slug": SLUG,
            "internal_id": "p000000000001",
            "version": 1,
            "short_description": "Find changes that lack tests.",
            "status": "draft",
            "origin": "user",
        }
        meta.update(over)
        body = str(meta.pop("_body", BODY))
        handle, name = tempfile.mkstemp(suffix=".md")
        os.close(handle)
        path = Path(name)
        self._scratch_files.append(path)
        text = "---\n" + V.dump_yaml(meta, V.FIELD_ORDER) + "---\n\n" + body + "\n"
        path.write_text(text, encoding="utf-8", newline="\n")
        return str(path)

    def active_prompt(self) -> str:
        """Create a verified, active prompt; return its internal id. Raises on any failure."""
        steps = [("init",), ("draft", self.scratch())]
        for step in steps:
            code, out = self.run(*step)
            if code != 0:
                raise RuntimeError(f"{step[0]} failed: {out.get('error')}")
        draft_hash = V.text_hash(BODY)
        for step in (
            (
                "record-verification",
                "p000000000001",
                "--kind",
                "quality",
                "--expect-sha256",
                draft_hash,
            ),
            ("activate", "p000000000001", "--expect-sha256", draft_hash),
        ):
            code, out = self.run(*step)
            if code != 0:
                raise RuntimeError(f"{step[0]} failed: {out.get('error')}")
        return "p000000000001"

    def active_file(self) -> Path:
        return self.repo / ".claude" / "prompts" / SLUG / "active.md"


def report(results: list[tuple[str, bool, str]]) -> int:
    """Print one PASS/FAIL line per check and return the process exit code."""
    failed = 0
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name}: {detail}")
        failed += 0 if ok else 1
    print(f"{len(results) - failed}/{len(results)} checks passed")
    return 1 if failed else 0


def guarded(name: str, check) -> tuple[str, bool, str]:
    """Run one check; an unexpected exception is a failure, never a crash that hides the rest."""
    try:
        ok, detail = check()
    except Exception as exc:
        return name, False, f"raised {type(exc).__name__}: {exc}"
    return name, ok, detail
