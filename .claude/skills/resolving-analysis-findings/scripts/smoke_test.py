#!/usr/bin/env python3
"""Smoke test for resolving-analysis-findings: structure, grants and decision-rule invariants.

This skill is prose with no executable of its own, so the test checks what can drift: frontmatter,
every referenced file, the tool grants against what the body uses, the five-rung ladder and the
decision-rights table, the one-way dependency on collecting-analysis-findings, and that the inline
suppression syntax is the same in this skill's references, docs/ci.md and the git-kit scripts it
documents. Checks that need the repository are skipped, not failed, when the plugin runs elsewhere.
Exit 0 when every check passes, 1 otherwise.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILL_DIR = HERE.parent
COLLECTING = SKILL_DIR.parent / "collecting-analysis-findings"
ALLOWED_FIELDS = {"name", "description", "argument-hint", "allowed-tools"}

failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    print(f"{'PASS' if ok else 'FAIL'}: {name}" + (f" -- {detail}" if detail and not ok else ""))
    if not ok:
        failures.append(name)


def skip(name: str, why: str) -> None:
    print(f"SKIP: {name} -- {why}")


def read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def frontmatter(text: str) -> dict[str, str]:
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    fields: dict[str, str] = {}
    key = None
    for line in (match.group(1) if match else "").splitlines():
        top = re.match(r"^([a-z][a-z-]*):\s*(.*)$", line)
        if top:
            key = top.group(1)
            fields[key] = top.group(2).strip()
        elif key:
            fields[key] += " " + line.strip()
    return fields


def find_repo_root() -> Path | None:
    for parent in HERE.parents:
        if (parent / "docs" / "ci.md").is_file() and (parent / "plugins" / "git-kit").is_dir():
            return parent
    return None


def check_structure(text: str, fm: dict[str, str], body: str) -> None:
    check("frontmatter name matches directory", fm.get("name") == SKILL_DIR.name)
    check("description present", len(fm.get("description", "")) >= 80)
    extra = sorted(set(fm) - ALLOWED_FIELDS)
    check("frontmatter uses only allowed fields", not extra, ", ".join(extra))
    for heading in (
        "## Quick Start",
        "## When to Use",
        "## When NOT to Use",
        "## Testing & Validation",
        "## Reference Guide",
    ):
        check(f"section present: {heading}", heading in text)

    refs = set(re.findall(r"`(references/[A-Za-z0-9_.-]+)`", body))
    missing = sorted(r for r in refs if not (SKILL_DIR / r).is_file())
    check("referenced files exist", not missing, ", ".join(missing))
    on_disk = {f"references/{p.name}" for p in (SKILL_DIR / "references").glob("*.md")}
    check("every reference file is referenced", on_disk <= refs, ", ".join(sorted(on_disk - refs)))


def check_grants(fm: dict[str, str], body: str) -> None:
    grants = fm.get("allowed-tools", "")
    check("grants the collecting skill", "Skill(collecting-analysis-findings)" in grants)
    check(
        "pre-approves no codacy command (write flags the grant cannot narrow)",
        not re.search(r"Bash\(codacy(?!-analysis)", grants),
    )
    check(
        "does not grant AskUserQuestion, Write or a bare Bash",
        not re.search(r"\b(AskUserQuestion|Write)\b|Bash(?!\()", grants),
    )
    check("grants no Bash at all (every command raises a prompt)", "Bash" not in grants)
    check(
        "boundaries tell the user never to choose don't ask again",
        'never choose "don\'t ask again"' in body.replace("\n", " "),
    )
    check("body calls the collecting skill", "Skill(collecting-analysis-findings)" in body)


def check_rules(body: str) -> None:
    rungs = re.findall(r"^\| ([1-5])\. ", body, re.MULTILINE)
    check(
        "ladder has rungs 1 to 5", sorted(set(rungs)) == ["1", "2", "3", "4", "5"], ",".join(rungs)
    )
    rights = body.split("## Decision rights", 1)[1].split("\n## ", 1)[0]
    check(
        "decision rights cover rungs 3 and 4 and rung 5",
        all(k in rights for k in ("Rung 3", "Rung 4", "Rung 5")),
    )
    check(
        "decision rights name the other remote writes",
        all(k in rights for k in ("--unignore-issue", "--reanalyze", "-F")),
    )
    check("rung 3 is a per-command approval", "per command" in rights and "remote write" in rights)
    check("rung 5 is handed over, never run", "Not run here" in rights)
    check("severity rows cover Medium", "Medium" in rights)
    check("bulk flags are handed over, not run", "Not run here, like rung 5" in rights)
    check(
        "an edit target must be a relative path inside the repository",
        "no leading `/`, no `..` segment" in body.replace("\n", " "),
    )
    check(
        "issue_id is validated before a command is built",
        "^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$" in body,
    )
    check(
        "edits and remote writes re-collect for the current head first",
        "after the fresh re-collect" in rights,
    )
    stale = [
        p.name
        for p in (SKILL_DIR / "references").glob("*.md")
        if "`Critical`, `High` or `Error`" in p.read_text(encoding="utf-8")
    ]
    check("references do not restate a shorter approval severity list", not stale, ", ".join(stale))
    check("init is never run unprompted", "never run `codacy-analysis init`" in body)
    check(
        "init is handed to the user, never run here",
        "`codacy-analysis init` is never run here" in body.replace("\n", " "),
    )


def check_dependency() -> None:
    collecting = read(COLLECTING / "SKILL.md") if (COLLECTING / "SKILL.md").is_file() else ""
    if not collecting:
        skip("one-way dependency", "collecting-analysis-findings not found beside this skill")
        return
    grants = frontmatter(collecting).get("allowed-tools", "")
    check("collecting grants no Skill()", "Skill(" not in grants)
    check("collecting never calls this skill", "Skill(resolving" not in collecting)


def check_syntax_consistency() -> None:
    formats = read(SKILL_DIR / "references" / "suppression-formats.md")
    check(
        "suppression-formats recommends the trailing-comment form",
        "# nosec B603 B607  # " in formats,
    )
    root = find_repo_root()
    if root is None:
        skip(
            "nosec form in docs/ci.md and git-kit scripts", "not inside the marketplace repository"
        )
        return
    ci = read(root / "docs" / "ci.md")
    check("docs/ci.md B404 row uses the trailing-comment form", "`# nosec B404  # <reason>`" in ci)
    bad = []
    for name in ("git-verify-fix-diff.py", "git-review-ledger.py"):
        text = read(root / "plugins" / "git-kit" / "scripts" / name)
        if not re.search(r"^import subprocess  # nosec B404  # \S", text, re.MULTILINE):
            bad.append(f"{name}: import line")
        if re.search(r"# nosec B\d+ -- ", text):
            bad.append(f"{name}: old -- form")
    check("git-kit scripts use the trailing-comment form", not bad, ", ".join(bad))


def main() -> int:
    text = read(SKILL_DIR / "SKILL.md")
    fm = frontmatter(text)
    body = text.split("\n---\n", 1)[1]
    check_structure(text, fm, body)
    check_grants(fm, body)
    check_rules(body)
    check_dependency()
    check_syntax_consistency()
    print(f"\n{len(failures)} failure(s)" if failures else "\nall checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
