#!/usr/bin/env python3
"""Persisted smoke test for marketplace-inventory: frontmatter validity, referenced-file
existence, Bash-scope grant consistency, and the shared CLI script's own subcommands."""

import json
import pathlib
import re
import subprocess
import sys

SKILL_DIR = pathlib.Path(__file__).resolve().parent.parent
SKILL_MD = SKILL_DIR / "SKILL.md"
SCRIPT = SKILL_DIR / "scripts" / "marketplace-inventory.py"


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
    # Real invocation instructions in this body live as a literal command line inside a
    # fenced ```bash block -- not as a bare `Bash(...)` mention, which never actually
    # appears verbatim in the body and made the previous version of this check a silent
    # no-op (referenced was always empty regardless of what the body actually invoked).
    text = SKILL_MD.read_text(encoding="utf-8")
    header_end = text.find("\n---\n", 4) + 5
    frontmatter, body = text[:header_end], text[header_end:]
    fm_line_match = re.search(r"^allowed-tools:\s*(.+)$", frontmatter, re.MULTILINE)
    granted_prefixes = (
        [
            g.rsplit(":", 1)[0].strip()
            for g in re.findall(r"Bash\(([^)]*)\)", fm_line_match.group(1))
        ]
        if fm_line_match
        else []
    )
    invoked = set()
    for block in re.findall(r"```bash\n(.*?)```", body, re.DOTALL):
        for line in block.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            tokens = line.split()
            invoked.add(" ".join(tokens[:2]) if len(tokens) > 1 else tokens[0])
    uncovered = [cmd for cmd in invoked if not any(cmd.startswith(p) for p in granted_prefixes)]
    if uncovered:
        return False, "body invokes command(s) not covered by any granted Bash scope: " + ", ".join(
            sorted(uncovered)
        )
    if not invoked:
        return True, "no shell commands found in fenced bash blocks (nothing to check)"
    return True, f"every invoked command ({len(invoked)}) is covered by a granted Bash scope"


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
    """Live functional check: bootstrap a fresh marketplace inventory from
    this repo's own root and confirm check reports zero drift immediately
    after -- Testing & Validation scenario 2."""
    import tempfile

    repo_root = _find_repo_root()
    with tempfile.TemporaryDirectory() as tmpdir:
        inventory_path = pathlib.Path(tmpdir) / "marketplace-inventory.json"
        bootstrap = subprocess.run(
            [sys.executable, str(SCRIPT), "bootstrap", str(repo_root), str(inventory_path)],
            capture_output=True,
            text=True,
        )
        if bootstrap.returncode != 0:
            return False, f"bootstrap failed: {bootstrap.stderr.strip()}"
        check = subprocess.run(
            [sys.executable, str(SCRIPT), "check", str(repo_root), str(inventory_path)],
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


def check_schema_conformance():
    """Structural, dependency-free comparison (no jsonschema library needed):
    confirm the schema's declared `plugin` required-key set matches exactly
    what `apply_add()` in the script actually writes into a new record, so
    the two can't silently drift apart with nothing catching it."""
    schema_path = SKILL_DIR / "assets" / "marketplace-inventory.schema.json"
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    schema_keys = set(schema.get("definitions", {}).get("plugin", {}).get("required", []))
    if not schema_keys:
        return False, "schema has no definitions.plugin.required to compare against"
    script_text = SCRIPT.read_text(encoding="utf-8")
    match = re.search(r"def apply_add\(.*?\n    record = \{(.*?)\n    \}", script_text, re.DOTALL)
    if not match:
        return False, "could not locate apply_add()'s record literal in the script"
    # Only top-level keys (exactly 8-space indented) count -- a nested dict
    # (e.g. status_history's own "status"/"reason" keys) is indented deeper
    # and must not be confused with the record's own top-level fields.
    written_keys = set(re.findall(r'^ {8}"([\w]+)":', match.group(1), re.MULTILINE))
    missing = schema_keys - written_keys
    extra = written_keys - schema_keys
    if missing or extra:
        parts = []
        if missing:
            parts.append(
                "schema requires but apply_add never writes: " + ", ".join(sorted(missing))
            )
        if extra:
            parts.append("apply_add writes but schema doesn't require: " + ", ".join(sorted(extra)))
        return False, "; ".join(parts)
    return (
        True,
        f"schema's {len(schema_keys)} required plugin keys match apply_add()'s record exactly",
    )


CHECKS = [
    check_frontmatter,
    check_referenced_files,
    check_bash_grants,
    check_cli_bootstrap_check_roundtrip,
    check_schema_conformance,
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
