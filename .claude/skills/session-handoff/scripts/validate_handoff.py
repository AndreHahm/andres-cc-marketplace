#!/usr/bin/env python3
"""
Validate a handoff document for completeness and quality.

Checks:
- No TODO placeholders remaining
- Required sections present and populated
- No potential secrets detected
- Referenced files exist
- Quality scoring

Usage:
    python validate_handoff.py <handoff-file>
    python validate_handoff.py .claude/handoffs/2026-01-15-143022-auth.md
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

# Secret detection patterns
# API key/password/secret/token accept an unquoted value too (e.g. DATABASE_PASSWORD=correct-horse-
# battery-staple), not just a quoted one -- handoffs are explicitly intended to be committed/shared,
# so a quote-only check leaves a direct credential-leak path.
SECRET_PATTERNS = [
    (r'["\']?[a-zA-Z_]*api[_-]?key["\']?\s*[:=]\s*(?:["\'][^"\']{10,}["\']|\S{10,})', "API key"),
    (r'["\']?[a-zA-Z_]*password["\']?\s*[:=]\s*(?:["\'][^"\']+["\']|\S+)', "Password"),
    (r'["\']?[a-zA-Z_]*secret["\']?\s*[:=]\s*(?:["\'][^"\']{10,}["\']|\S{10,})', "Secret"),
    (r'["\']?[a-zA-Z_]*token["\']?\s*[:=]\s*(?:["\'][^"\']{20,}["\']|\S{20,})', "Token"),
    (r'["\']?[a-zA-Z_]*private[_-]?key["\']?\s*[:=]', "Private key"),
    (r"-----BEGIN [A-Z]+ PRIVATE KEY-----", "PEM private key"),
    (r"mongodb(\+srv)?://[^/\s]+:[^@\s]+@", "MongoDB connection string with password"),
    (r"postgres(?:ql)?://[^/\s]+:[^@\s]+@", "PostgreSQL connection string with password"),
    (r"mysql://[^/\s]+:[^@\s]+@", "MySQL connection string with password"),
    (r"Bearer\s+[a-zA-Z0-9_\-\.]+", "Bearer token"),
    (r"ghp_[a-zA-Z0-9]{36}", "GitHub personal access token"),
    (r"sk-[a-zA-Z0-9]{48}", "OpenAI API key"),
    (r"xox[baprs]-[a-zA-Z0-9-]+", "Slack token"),
]

# Required sections for a complete handoff
REQUIRED_SECTIONS = [
    "Current State Summary",
    "Important Context",
    "Immediate Next Steps",
]

# Recommended sections
RECOMMENDED_SECTIONS = [
    "Architecture Overview",
    "Critical Files",
    "Files Modified",
    "Decisions Made",
    "Assumptions Made",
    "Potential Gotchas",
]

# A reference with no "/" counts as a file only if its last suffix is one of these, so code
# names such as `os.geteuid`, `json.loads` or `code.claude.com` are not reported as missing.
# A reference with a "/" is always checked.
FILE_EXTENSIONS = frozenset(
    "md markdown txt rst py pyc pyi ipynb sh bash zsh ps1 bat cmd js mjs cjs ts tsx jsx "
    "json jsonl jsonc yml yaml toml ini cfg conf env lock xml html htm css scss csv tsv sql "
    "log patch diff exe dll so png jpg jpeg gif svg webp pdf zip gz tar tgz go rs java kt rb "
    "php c h cpp hpp cs swift lua pem crt proto graphql gql vue svelte properties gradle kts "
    "scala dart tf tfvars hcl".split()
)


def check_todos(content: str) -> tuple[bool, list[str]]:
    """Check for remaining TODO placeholders."""
    todos = re.findall(r"\[TODO:[^\]]*\]", content)
    return len(todos) == 0, todos


def check_required_sections(content: str) -> tuple[bool, list[str]]:
    """Check that required sections exist and have content."""
    missing = []
    for section in REQUIRED_SECTIONS:
        # Look for section header
        # #{1,6}: the template nests required sections at varying heading depths
        # (e.g. "### Important Context" under "## Context for Resuming Agent") --
        # matching only h1/h2 here would make some required sections unmatchable.
        # (?=\s*$) (with MULTILINE, zero-width): require the heading line to end right
        # after the section name, so e.g. "## Important Context Draft" doesn't satisfy
        # "Important Context" -- a lookahead so match.end() still lands right after the
        # section name itself, same as before this boundary check was added.
        pattern = rf"(?:^|\n)#{{1,6}}\s*{re.escape(section)}(?=\s*$)"
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if not match:
            missing.append(f"{section} (missing)")
        else:
            # Check if section has meaningful content (not just placeholder)
            section_start = match.end()
            next_section = re.search(r"\n#{1,6}\s+", content[section_start:])
            section_end = section_start + next_section.start() if next_section else len(content)
            section_content = content[section_start:section_end].strip()

            # 50 chars minimum: roughly 1-2 sentences, enough to convey meaningful context
            if len(section_content) < 50 or "[TODO" in section_content:
                missing.append(f"{section} (incomplete)")

    return len(missing) == 0, missing


def check_recommended_sections(content: str) -> list[str]:
    """Check which recommended sections are missing."""
    missing = []
    for section in RECOMMENDED_SECTIONS:
        # #{1,6}: the template nests required sections at varying heading depths
        # (e.g. "### Important Context" under "## Context for Resuming Agent") --
        # matching only h1/h2 here would make some required sections unmatchable.
        # (?=\s*$) (with MULTILINE, zero-width): require a complete heading name match --
        # see check_required_sections' matching comment above for why.
        pattern = rf"(?:^|\n)#{{1,6}}\s*{re.escape(section)}(?=\s*$)"
        if not re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
            missing.append(section)
    return missing


def scan_for_secrets(content: str) -> list[tuple[str, str]]:
    """Scan content for potential secrets."""
    findings = []
    for pattern, description in SECRET_PATTERNS:
        matches = re.findall(pattern, content, re.IGNORECASE)
        if matches:
            findings.append((description, f"Found {len(matches)} potential match(es)"))
    return findings


def list_repo_files(base_path: str) -> list[str] | None:
    """List tracked and untracked (not ignored) files under base_path, or None outside a git repo.

    One fixed git command with no handoff-derived argument: every reference string stays in
    Python, never on a command line.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            capture_output=True,
            cwd=base_path,
            timeout=10,
        )
    except (subprocess.TimeoutExpired, FileNotFoundError, NotADirectoryError):
        return None
    if result.returncode != 0:
        return None
    return [p for p in result.stdout.decode("utf-8", "replace").split("\0") if p]


def resolve_reference(
    ref: str, base_path: str, repo_files: list[str] | None, extra_dirs: tuple[str, ...] = ()
) -> str:
    """Classify one file reference as "verified" or "missing".

    A reference is tried as written (relative to base_path, then to each of extra_dirs), then
    matched against the repo's file list: a bare name matches any file with that name, and a
    partial path matches the end of a path on a "/" boundary (so "rulebook/SKILL.md" never
    matches "plugin-rulebook/SKILL.md"). Outside a git repo there is no list, so a reference
    not found as written is "missing".
    """
    ref = ref.removeprefix("./")
    # A leading "/" is filtered by the caller; a "../" segment must not walk outside base_path,
    # so an untrusted reference like "../../etc/passwd" is never verified by an unrelated file.
    if ".." in Path(ref).parts:
        return "missing"
    for root in (base_path, *extra_dirs):
        base = Path(root).resolve()
        candidate = (base / ref).resolve()
        try:
            candidate.relative_to(base)
        except ValueError:
            return "missing"
        if candidate.exists():
            return "verified"
    if repo_files is None:
        return "missing"
    # The list includes index entries, so a tracked file deleted but not yet staged is still in
    # it: a match counts only if that file exists on disk now.
    suffix = "/" + ref
    base = Path(base_path)
    if any((f == ref or f.endswith(suffix)) and (base / f).is_file() for f in repo_files):
        return "verified"
    return "missing"


def check_file_references(
    content: str, base_path: str, extra_dirs: tuple[str, ...] = ()
) -> tuple[list[str], list[str]]:
    """Check if referenced files exist. Returns (existing, missing)."""
    # Extract file paths from content (look for common patterns)
    # Pattern 1: | path/to/file | in tables
    # Pattern 2: `path/to/file` in code
    # Pattern 3: path/to/file:123 with line numbers

    patterns = [
        r"\|\s*([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)\s*\|",  # Table cells
        r"`([a-zA-Z0-9_\-./]+\.[a-zA-Z]+(?::\d+)?)`",  # Inline code
        r"(?:^|\s)([a-zA-Z0-9_\-./]+\.[a-zA-Z]+:\d+)",  # With line numbers
    ]

    found_files = set()
    for pattern in patterns:
        matches = re.findall(pattern, content)
        for match in matches:
            # Remove line numbers
            filepath = match.split(":")[0]
            # Skip obvious non-files, and a leading-"/" match -- pathlib's "/" operator
            # resets to the right-hand side for an absolute path, so an unfiltered
            # leading-"/" match would silently check the real filesystem root instead
            # of base_path. No "/" requirement: a root-level file reference (e.g.
            # "README.md", no slash) must still be checked, or it silently bypasses
            # validation entirely.
            if not filepath or filepath.startswith(("http", "/")):
                continue
            if "/" not in filepath and filepath.rsplit(".", 1)[-1].lower() not in FILE_EXTENSIONS:
                continue
            found_files.add(filepath)

    existing = []
    missing = []
    repo_files = list_repo_files(base_path) if found_files else None

    for filepath in sorted(found_files):
        if resolve_reference(filepath, base_path, repo_files, extra_dirs) == "verified":
            existing.append(filepath)
        else:
            missing.append(filepath)

    return existing, missing


def calculate_quality_score(
    todos_clear: bool,
    required_complete: bool,
    missing_required: list,
    missing_recommended: list,
    secrets_found: list,
    files_missing: list,
) -> tuple[int, str]:
    """Calculate overall quality score (0-100).

    Scoring rationale:
    - Start at 100, deduct for issues
    - TODOs remaining (-30): Indicates incomplete work, major blocker
    - Missing required sections (-10 each): Core context gaps
    - Secrets detected (-20): Security risk, must be fixed
    - Missing file refs (-5 each, max -20): Stale references
    - Missing recommended (-2 each): Nice-to-have completeness
    """
    score = 100

    # Deductions with justifications
    if not todos_clear:
        # -30: TODOs indicate unfinished work; next agent will lack critical info
        score -= 30
    if not required_complete:
        # -10 per section: Required sections are essential for handoff continuity
        score -= 10 * len(missing_required)
    if secrets_found:
        # -20: Security risk; handoffs may be shared or stored in repos
        score -= 20
    if files_missing:
        # -5 per file (max 4): Indicates stale refs; cap at -20 to avoid over-penalizing
        score -= 5 * min(len(files_missing), 4)

    # -2 per section: Recommended but not critical; minor impact on handoff quality
    score -= 2 * len(missing_recommended)

    score = max(0, score)

    # Rating thresholds based on handoff usability:
    # 90+: Comprehensive, ready to use immediately
    # 70-89: Usable with minor gaps
    # 50-69: Needs work before reliable handoff
    # <50: Too incomplete to be useful
    if score >= 90:
        rating = "Excellent - Ready for handoff"
    elif score >= 70:
        rating = "Good - Minor improvements suggested"
    elif score >= 50:
        rating = "Fair - Needs attention before handoff"
    else:
        rating = "Poor - Significant work needed"

    return score, rating


def validate_handoff(filepath: str) -> dict:
    """Run all validations on a handoff file."""
    path = Path(filepath)

    if not path.exists():
        return {"error": f"File not found: {filepath}"}

    content = path.read_text(encoding="utf-8")
    base_path = path.parent.parent.parent  # Go up from .claude/handoffs/

    # Run checks
    todos_clear, remaining_todos = check_todos(content)
    required_complete, missing_required = check_required_sections(content)
    missing_recommended = check_recommended_sections(content)
    secrets_found = scan_for_secrets(content)
    # The handoff's own directory is also tried, so a bare reference to a sibling handoff
    # (gitignored, so absent from the repo file list) resolves.
    existing_files, missing_files = check_file_references(
        content, str(base_path), extra_dirs=(str(path.parent),)
    )

    # Calculate score
    score, rating = calculate_quality_score(
        todos_clear,
        required_complete,
        missing_required,
        missing_recommended,
        secrets_found,
        missing_files,
    )

    return {
        "filepath": str(path),
        "score": score,
        "rating": rating,
        "todos_clear": todos_clear,
        "remaining_todos": remaining_todos[:5],  # Limit output
        "todo_count": len(remaining_todos) if not todos_clear else 0,
        "required_complete": required_complete,
        "missing_required": missing_required,
        "missing_recommended": missing_recommended,
        "secrets_found": secrets_found,
        "files_verified": len(existing_files),
        "files_missing": missing_files[:5],  # Limit output
    }


def print_report(result: dict):
    """Print a formatted validation report."""
    if "error" in result:
        print(f"Error: {result['error']}")
        return False

    print(f"\n{'=' * 60}")
    print("Handoff Validation Report")
    print(f"{'=' * 60}")
    print(f"File: {result['filepath']}")
    print(f"\nQuality Score: {result['score']}/100 - {result['rating']}")
    print(f"{'=' * 60}")

    # TODOs
    if result["todos_clear"]:
        print("\n[PASS] No TODO placeholders remaining")
    else:
        print(f"\n[FAIL] {result['todo_count']} TODO placeholders found:")
        for todo in result["remaining_todos"]:
            print(f"       - {todo[:50]}...")

    # Required sections
    if result["required_complete"]:
        print("\n[PASS] All required sections complete")
    else:
        print("\n[FAIL] Missing/incomplete required sections:")
        for section in result["missing_required"]:
            print(f"       - {section}")

    # Secrets
    if not result["secrets_found"]:
        print("\n[PASS] No potential secrets detected")
    else:
        print("\n[WARN] Potential secrets detected:")
        for secret_type, detail in result["secrets_found"]:
            print(f"       - {secret_type}: {detail}")

    # File references
    if result["files_missing"]:
        print(f"\n[WARN] {len(result['files_missing'])} referenced file(s) not found:")
        for f in result["files_missing"]:
            print(f"       - {f}")
    else:
        print(f"\n[INFO] {result['files_verified']} file reference(s) verified")

    # Recommended sections
    if result["missing_recommended"]:
        print("\n[INFO] Consider adding these sections:")
        for section in result["missing_recommended"]:
            print(f"       - {section}")

    print(f"\n{'=' * 60}")

    # Final verdict
    if (
        result["score"] >= 70
        and not result["secrets_found"]
        and result["todos_clear"]
        and result["required_complete"]
    ):
        print("Verdict: READY for handoff")
        return True
    elif result["secrets_found"]:
        print("Verdict: BLOCKED - Remove secrets before handoff")
        return False
    else:
        print("Verdict: NEEDS WORK - Complete required sections")
        return False


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # ty: ignore[missing-union-attribute]
    sys.stderr.reconfigure(encoding="utf-8")  # ty: ignore[missing-union-attribute]

    if len(sys.argv) < 2:
        print("Usage: python validate_handoff.py <handoff-file>")
        print("Example: python validate_handoff.py .claude/handoffs/2026-01-15-143022-auth.md")
        sys.exit(1)

    filepath = sys.argv[1]
    result = validate_handoff(filepath)
    success = print_report(result)

    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
