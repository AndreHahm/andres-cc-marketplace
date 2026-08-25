#!/usr/bin/env python3
"""Persisted smoke test for plugin-inventory: frontmatter validity, referenced-file
existence, Bash-scope grant consistency, and the shared CLI script's own subcommands."""

import json
import pathlib
import re
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "plugin-inventory.py"


def check_frontmatter():
    text = SKILL_MD.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        return False, "SKILL.md does not start with a frontmatter block"
    end = text.find("\n---\n", 4)
    if end == -1:
        return False, "frontmatter block is never closed"
    fm = text[4:end]
    if "name:" not in fm or "description:" not in fm:
        return False, "missing required frontmatter field ('name' or 'description')"
    return True, "frontmatter present and closed"


def check_referenced_files():
    text = SKILL_MD.read_text(encoding="utf-8")
    missing = []
    for match in re.finditer(
        r"`((?:\.\./)*(?:references/[\w.-]+\.md|scripts/[\w./-]+|assets/[\w.-]+))`", text
    ):
        path = SKILL_DIR / match.group(1)
        if not path.exists():
            missing.append(match.group(1))
    if missing:
        return False, "referenced file(s) do not exist: " + ", ".join(sorted(set(missing)))
    return True, "all referenced files exist"


def check_bash_grants():
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    frontmatter, body = text[:header_end], text[header_end:]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    granted = set(re.findall(r"Bash\([^)]*\)", fm_line_match.group(1))) if fm_line_match else set()
    referenced = set(re.findall(r"`(Bash\([^)]*\))", body))
    missing = referenced - granted
    if missing:
        return False, "body invokes Bash scope(s) missing from allowed-tools: " + ", ".join(
            sorted(missing)
        )
    return True, "every Bash invocation in the body is granted"


def _find_repo_root():
    """Walk upward from this file to find the repo root (marked by
    .claude-plugin/marketplace.json) -- the number of parent directories
    differs between the canonical plugins/plugin-devkit/... location and
    the .claude/skills/... mirror, so this can't be a fixed parent count."""
    current = SKILL_DIR
    while current != current.parent:
        if (current / ".claude-plugin" / "marketplace.json").is_file():
            return current
        current = current.parent
    raise RuntimeError(
        "could not find repo root (.claude-plugin/marketplace.json) above " + str(SKILL_DIR)
    )


def check_cli_bootstrap_check_roundtrip():
    """A live functional check, not just structural: bootstrap a fresh
    inventory from this repo's own plugin-devkit plugin, run check
    immediately after, and confirm zero drift -- the same round-trip
    Testing & Validation scenario 2 describes."""
    import tempfile

    repo_root = _find_repo_root()
    plugin_dir = repo_root / "plugins" / "plugin-devkit"
    if not plugin_dir.is_dir():
        return False, f"resolved plugin_dir does not exist: {plugin_dir}"
    with tempfile.TemporaryDirectory() as tmpdir:
        inventory_path = pathlib.Path(tmpdir) / "plugin-inventory.json"
        bootstrap = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "bootstrap",
                str(plugin_dir),
                str(inventory_path),
                "plugin_deadbeef",
                "plugin-devkit",
            ],
            capture_output=True,
            text=True,
        )
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        check = subprocess.run(
            [sys.executable, str(SCRIPT), "check", str(inventory_path), str(plugin_dir)],
            capture_output=True,
            text=True,
        )
        if check.returncode != 0:
            return False, f"check failed: {check.stderr.strip()}"
        result = json.loads(check.stdout)
        if result["drift_count"] != 0:
            return (
                False,
                f"expected 0 drift immediately after bootstrap, got {result['drift_count']}",
            )
        return True, f"bootstrap+check round-trip clean ({result['drift_count']} drift)"


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_cli_bootstrap_check_roundtrip,
]


def main():
    failed = False
    for check in CHECKS:
        ok, message = check()
        print(("PASS  " if ok else "FAIL  ") + check.__name__ + ": " + message)
        failed = failed or not ok
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
