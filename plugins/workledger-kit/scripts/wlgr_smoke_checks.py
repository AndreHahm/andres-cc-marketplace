#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = []
# ///
"""Shared structural smoke checks for workledger-kit's skills. Each skill's own
scripts/smoke_test.py calls run(<skill dir>); this file holds the logic once.

Checks (structural only; the skills are procedures, their logic lives in the tested scripts):
  1. SKILL.md frontmatter is present, closed, `name` equals the directory name, `description` is
     80-1024 characters, and `allowed-tools` is declared.
  2. Every backtick-quoted file path in SKILL.md and in the skill's own workflows/ and references/
     files names a file that exists. A path with `../` is resolved ONLY from the directory of the
     file
     that contains it (a workflow file is one level deeper than SKILL.md, which is exactly the
     mistake this catches); a bare `references/x` or `scripts/x` may also resolve from the skill or
     plugin root.
  3. Every scoped `Bash(${CLAUDE_PLUGIN_ROOT}/scripts/<name>:*)` grant names a script that exists,
     and the script name is actually mentioned in the skill body or its workflows (no unused grant).
  4. No bare `Bash` grant.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

_PATH_RE = re.compile(
    r"`((?:\.\./)*(?:references|scripts|assets|workflows)/[\w./-]+\.(?:md|py|json))`"
)
_GRANT_RE = re.compile(r"Bash\(\$\{CLAUDE_PLUGIN_ROOT\}/scripts/([\w.-]+):\*\)")


def _frontmatter(text: str) -> tuple[dict[str, str], str] | None:
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end == -1:
        return None
    fields: dict[str, str] = {}
    key = None
    for line in text[4:end].splitlines():
        m = re.match(r"^([\w-]+):\s*(.*)$", line)
        if m:
            key = m.group(1)
            fields[key] = m.group(2).strip()
        elif key and line.startswith((" ", "\t")):
            fields[key] = (fields[key] + " " + line.strip()).strip()
    return fields, text[end + 5 :]


def check(skill_dir: Path) -> list[str]:
    """Return a list of failures (empty = pass)."""
    failures: list[str] = []
    plugin_root = skill_dir.parent.parent
    md = skill_dir / "SKILL.md"
    if not md.is_file():
        return [f"{md} is missing"]
    text = md.read_text(encoding="utf-8")
    parsed = _frontmatter(text)
    if parsed is None:
        return ["SKILL.md has no closed frontmatter block"]
    fm, body = parsed

    if fm.get("name") != skill_dir.name:
        failures.append(
            f"frontmatter name {fm.get('name')!r} must equal directory name {skill_dir.name!r}"
        )
    desc = fm.get("description", "").lstrip(">-| ").strip()
    if not 80 <= len(desc) <= 1024:
        failures.append(f"description length {len(desc)} outside 80-1024")
    if "allowed-tools" not in fm:
        failures.append("allowed-tools is not declared")

    corpus = body
    for sub in ("workflows", "references"):
        d = skill_dir / sub
        if d.is_dir():
            corpus += "\n".join(
                f.read_text(encoding="utf-8", errors="ignore") for f in sorted(d.glob("*.md"))
            )

    docs = [md] + [
        f
        for sub in ("workflows", "references")
        if (skill_dir / sub).is_dir()
        for f in sorted((skill_dir / sub).glob("*.md"))
    ]
    for doc in docs:
        doc_text = body if doc == md else doc.read_text(encoding="utf-8", errors="ignore")
        for m in _PATH_RE.finditer(doc_text):
            rel = m.group(1)
            candidates = [doc.parent / rel]
            if not rel.startswith(
                "."
            ):  # a bare path may also name a skill-root or plugin-root file
                candidates += [skill_dir / rel, plugin_root / rel]
            if not any(c.resolve().is_file() for c in candidates):
                where = doc.relative_to(skill_dir).as_posix()
                failures.append(f"referenced file does not exist: {rel} (in {where})")

    tools = fm.get("allowed-tools", "")
    if re.search(r"(?<![\w(])Bash(?!\()", tools):
        failures.append("bare Bash grant (must be scoped)")
    for m in re.finditer(r"Bash\([^)]*\)", tools):
        if not _GRANT_RE.fullmatch(m.group(0)):
            failures.append(f"unsupported Bash grant (must be scoped to a script): {m.group(0)}")
    for m in _GRANT_RE.finditer(tools):
        script = m.group(1)
        if not (plugin_root / "scripts" / script).is_file():
            failures.append(f"granted script does not exist: scripts/{script}")
        elif script not in corpus:
            failures.append(f"granted script is never used in the skill: {script}")
    return failures


_DOC_PATH_RE = re.compile(
    r"`((?:\.\./)*(?:references|scripts|skills|workflows)/[\w./-]+\.(?:md|py|json))`"
)
_QUOTE_RE = re.compile(r"(wlgr_[a-z_]+\.py) ([a-z][a-z-]+)(?![\w.])")


def _usage_commands(script: Path) -> set[str]:
    """Subcommand words a script documents in its own docstring (`<script>.py <word> ...`)."""
    text = script.read_text(encoding="utf-8")
    return {m.group(2) for m in _QUOTE_RE.finditer(text) if m.group(1) == script.name}


def check_plugin_docs(plugin_root: Path) -> list[str]:
    """Plugin-level documents (references, README, CONTRIBUTING, and every skill's own files):
    every backticked file path resolves from the file that contains it, and every `script.py <word>`
    command quoted anywhere names a subcommand that script documents. Catches a doc that still
    quotes a
    command a refactor removed."""
    failures: list[str] = []
    docs = [
        *sorted((plugin_root / "references").glob("*.md")),
        plugin_root / "README.md",
        plugin_root / "CONTRIBUTING.md",
        *sorted((plugin_root / "skills").glob("*/SKILL.md")),
        *sorted((plugin_root / "skills").glob("*/*/*.md")),
    ]
    commands = {s.name: _usage_commands(s) for s in (plugin_root / "scripts").glob("wlgr_*.py")}
    for doc in docs:
        text = doc.read_text(encoding="utf-8", errors="ignore")
        where = doc.relative_to(plugin_root).as_posix()
        for m in _DOC_PATH_RE.finditer(text):
            rel = m.group(1)
            if not any(
                c.resolve().is_file()
                for c in (doc.parent / rel, plugin_root / rel, plugin_root / "scripts" / rel)
            ):
                failures.append(f"{where}: referenced file does not exist: {rel}")
        for m in _QUOTE_RE.finditer(text):
            script, word = m.group(1), m.group(2)
            if script in commands and commands[script] and word not in commands[script]:
                failures.append(
                    f"{where}: quotes `{script} {word}`, which that script does not document"
                )
    return failures


def run(skill_dir: Path) -> int:
    failures = check(skill_dir)
    for f in failures:
        print(f"FAIL {skill_dir.name}: {f}")
    if not failures:
        print(
            f"PASS {skill_dir.name}: frontmatter, referenced files and Bash grants are consistent"
        )
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(run(Path(sys.argv[1]).resolve()))
