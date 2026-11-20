#!/usr/bin/env python3
"""
Validate a handoff document for completeness and quality.

Checks:
- No TODO placeholders remaining
- Required sections present and populated
- No potential secrets detected
- Referenced files exist
- v2 handoffs (with frontmatter): frontmatter keys and closed values, Resume Card
- Quality scoring

Usage:
    python validate_handoff.py <handoff-file>
    python validate_handoff.py .claude/handoffs/2026-01-15-143022-auth.md
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

# Repository-location variables (`git rev-parse --local-env-vars`). An inherited one, such as the
# GIT_INDEX_FILE a git hook exports, would make a git call read another repository than cwd's.
GIT_LOCAL_ENV_VARS = (
    "GIT_ALTERNATE_OBJECT_DIRECTORIES GIT_CONFIG GIT_CONFIG_PARAMETERS GIT_CONFIG_COUNT "
    "GIT_OBJECT_DIRECTORY GIT_DIR GIT_WORK_TREE GIT_IMPLICIT_WORK_TREE GIT_GRAFT_FILE "
    "GIT_INDEX_FILE GIT_NO_REPLACE_OBJECTS GIT_REPLACE_REF_BASE GIT_PREFIX GIT_SHALLOW_FILE "
    "GIT_COMMON_DIR"
).split()


def git_env() -> dict[str, str]:
    """The current environment without git's repository-location variables."""
    return {k: v for k, v in os.environ.items() if k not in GIT_LOCAL_ENV_VARS}


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

# Recommended sections for a v2 handoff (one with frontmatter)
RECOMMENDED_SECTIONS = [
    "Critical Files",
    "Decisions Made",
    "Assumptions Made",
    "Potential Gotchas & Key Patterns",
]

# Recommended sections for an older handoff without frontmatter, so its score does not change
LEGACY_RECOMMENDED_SECTIONS = [
    "Architecture Overview",
    "Critical Files",
    "Files Modified",
    "Decisions Made",
    "Assumptions Made",
    "Potential Gotchas",
]

# v2 frontmatter: flat "key: value" lines between "---" markers (no PyYAML: these scripts run on
# bare python3). STATE_CONTEXT_MODE is the default context mode per state; "blocked" depends on
# whether a PR is open (see expected_context_mode).
FRONTMATTER_KEYS = (
    "created",
    "project",
    "branch",
    "head",
    "pr",
    "platform",
    "continues_from",
    "state",
    "context_mode",
)
STATE_CONTEXT_MODE = {
    "implementing": "none",
    "pr-draft": "review",
    "in-review": "review",
    "ready-to-merge": "ship",
    "ready-to-publish": "ship",
    "blocked": None,
    "done": "admin",
}
CONTEXT_MODES = ("none", "review", "ship", "admin")
RESUME_CARD_MAX_LINES = 15
# The card's "- Label: value" lines, as the scaffold and references/handoff-template.md write them.
RESUME_CARD_LABELS = ("State", "Next step", "Branch and PR", "Blockers", "User constraints")

# A reference with no "/" counts as a file only if its last suffix is one of these, so code
# names such as `os.geteuid`, `json.loads` or `code.claude.com` are not reported as missing.
# A reference with a "/" is always checked.
FILE_EXTENSIONS = frozenset(
    "md markdown txt rst py pyc pyi ipynb sh bash zsh ps1 bat cmd js mjs cjs ts tsx jsx "
    "json jsonl jsonc yml yaml toml ini cfg conf env lock xml html htm css scss csv tsv sql "
    "log patch diff exe dll so png jpg jpeg gif svg webp pdf zip gz tar tgz go rs java kt rb "
    "php c h cpp hpp cs swift lua pem crt proto graphql gql vue svelte properties gradle kts "
    "scala dart tf tfvars hcl cc cxx hh hxx mdx".split()
)


def parse_frontmatter(content: str) -> tuple[dict[str, str] | None, list[str]]:
    """Return (fields, malformed lines) of a leading "---" frontmatter block.

    fields is None when the content does not start with a closed block (an older handoff).
    A line that is not a flat "key: value" pair (no colon, an indented or nested line) is
    returned as malformed and its value is not used.
    """
    lines = content.split("\n")
    if not lines or lines[0].rstrip() != "---":
        return None, []
    try:
        end = next(i for i in range(1, len(lines)) if lines[i].rstrip() == "---")
    except StopIteration:
        return None, []
    fields: dict[str, str] = {}
    malformed: list[str] = []
    for line in lines[1:end]:
        if not line.strip():
            continue
        match = re.fullmatch(r"([a-z_]+):[ \t]*(.*?)\s*", line)
        if not match:
            malformed.append(line)
            continue
        fields[match.group(1)] = match.group(2)
    return fields, malformed


def expected_context_mode(state: str, pr: str | None) -> str | None:
    """The default context mode for a state, or None for an unknown state."""
    if state == "blocked":
        return "none" if pr in (None, "", "none") else "review"
    return STATE_CONTEXT_MODE.get(state)


def check_frontmatter(fields: dict[str, str], malformed: list[str]) -> tuple[list[str], list[str]]:
    """Check v2 frontmatter. Returns (problems, notes); notes do not lower the score."""
    problems = [f"malformed line: {line.strip()[:40]}" for line in malformed]
    notes = []
    problems += [f"missing key: {key}" for key in FRONTMATTER_KEYS if key not in fields]
    state = fields.get("state", "")
    mode = fields.get("context_mode", "")
    # A present but empty value says nothing; absence is written as "none", never left blank.
    for key in FRONTMATTER_KEYS:
        if key in fields and not fields[key]:
            problems.append(f"empty value: {key}")
    # An unfilled "[TODO: ...]" value is already reported by check_todos.
    if state and "[TODO" not in state and state not in STATE_CONTEXT_MODE:
        problems.append(f"unknown state: {state[:40]}")
    if mode and "[TODO" not in mode and mode not in CONTEXT_MODES:
        problems.append(f"unknown context_mode: {mode[:40]}")
    if state in STATE_CONTEXT_MODE and mode in CONTEXT_MODES:
        expected = expected_context_mode(state, fields.get("pr"))
        if mode != expected:
            notes.append(
                f"context_mode '{mode}' differs from the '{expected}' that state '{state}' "
                "implies; the handoff must state the reason for the override"
            )
    return problems, notes


def check_resume_card(content: str) -> list[str]:
    """Check that the Resume Card is the first section after the H1 and is short enough."""
    first_h2 = re.search(r"^##\s+(.+?)\s*$", content, re.MULTILINE)
    if not first_h2 or first_h2.group(1) != "Resume Card":
        if re.search(r"^##\s+Resume Card\s*$", content, re.MULTILINE):
            return ["Resume Card is not the first section after the title"]
        return ["Resume Card missing"]
    rest = content[first_h2.end() :]
    next_heading = re.search(r"^#{1,6}\s", rest, re.MULTILINE)
    card = rest[: next_heading.start()] if next_heading else rest
    lines = [line for line in card.split("\n") if line.strip()]
    if len(lines) > RESUME_CARD_MAX_LINES:
        return [f"Resume Card has {len(lines)} lines (at most {RESUME_CARD_MAX_LINES})"]
    missing = [
        label
        for label in RESUME_CARD_LABELS
        if not re.search(rf"^\s*-\s*{re.escape(label)}:[ \t]*\S", card, re.MULTILINE)
    ]
    if missing:
        return [f"Resume Card has no filled line for: {', '.join(missing)}"]
    return []


def section_extent(content: str, heading: re.Match) -> str:
    """The text of a section: up to the next heading of the same or a higher level."""
    level = len(heading.group(1))
    start = heading.end()
    for nxt in re.finditer(r"\n(#{1,6})\s+", content[start:]):
        if len(nxt.group(1)) <= level:
            return content[start : start + nxt.start()]
    return content[start:]


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
        pattern = rf"(?:^|\n)(#{{1,6}})\s*{re.escape(section)}(?=\s*$)"
        match = re.search(pattern, content, re.IGNORECASE | re.MULTILINE)
        if not match:
            missing.append(f"{section} (missing)")
        else:
            # Check if section has meaningful content (not just placeholder). Subsections
            # count (v2's Important Context has User Constraints and Learnings under it).
            section_content = section_extent(content, match).strip()

            # 50 chars minimum: roughly 1-2 sentences, enough to convey meaningful context
            if len(section_content) < 50 or "[TODO" in section_content:
                missing.append(f"{section} (incomplete)")

    return len(missing) == 0, missing


def check_recommended_sections(content: str, sections: list[str] | None = None) -> list[str]:
    """Check which recommended sections are missing (default: the v2 list)."""
    missing = []
    for section in RECOMMENDED_SECTIONS if sections is None else sections:
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
            env=git_env(),
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

    A reference is tried as written (relative to base_path, and a bare name also relative to each
    of extra_dirs), then matched against the repo's file list: a bare name matches any file with
    that name, and a partial path matches the end of a path on a "/" boundary (so
    "rulebook/SKILL.md" never matches "plugin-rulebook/SKILL.md"). Outside a git repo there is no
    list, so a reference not found as written is "missing".
    """
    path = PurePosixPath(ref)  # collapses "a//b" and "a/./b" to "a/b"
    # An absolute path is never a project file, and a "../" segment must not walk outside
    # base_path, so "../../etc/passwd" is never verified by an unrelated file.
    if path.is_absolute() or ".." in path.parts:
        return "missing"
    ref = str(path)
    bare = "/" not in ref
    for root in (base_path, *(extra_dirs if bare else ())):
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
    # it. Such an exact entry decides the reference (it is missing: the direct check above
    # failed), and any other match counts only if that file exists on disk now.
    if not bare and ref in repo_files:
        return "missing"
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
            # Skip a leading-"/" match: an absolute path is not a project file. A URL can't
            # reach here (none of the patterns accepts ":"), so a local path that merely
            # starts with "http" (http/client.py) is checked like any other. No "/"
            # requirement: a root-level reference such as "README.md" must still be checked.
            if not filepath or filepath.startswith("/"):
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
    frontmatter_problems: list | None = None,
    card_problems: list | None = None,
) -> tuple[int, str]:
    """Calculate overall quality score (0-100).

    Scoring rationale:
    - Start at 100, deduct for issues
    - TODOs remaining (-30): Indicates incomplete work, major blocker
    - Missing required sections (-10 each): Core context gaps
    - Secrets detected (-20): Security risk, must be fixed
    - Missing file refs (-5 each, max -20): Stale references
    - Missing recommended (-2 each): Nice-to-have completeness
    - v2 frontmatter problems (-10): a reader cannot trust state or context_mode
    - v2 Resume Card problem (-5): the load step reads the card first
    """
    score = 100
    if frontmatter_problems:
        score -= 10
    if card_problems:
        score -= 5

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
    fields, malformed = parse_frontmatter(content)
    if fields is None:
        # An older handoff: no frontmatter or card checks, and the old recommended list.
        frontmatter_problems, frontmatter_notes, card_problems = [], [], []
        # A file that opens a "---" block but never closes it is a broken v2 handoff, not an
        # older one; without this it would skip every v2 check and could still report READY.
        if content.split("\n", 1)[0].rstrip() == "---":
            frontmatter_problems = ["frontmatter block is not closed"]
        missing_recommended = check_recommended_sections(content, LEGACY_RECOMMENDED_SECTIONS)
    else:
        frontmatter_problems, frontmatter_notes = check_frontmatter(fields, malformed)
        card_problems = check_resume_card(content)
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
        frontmatter_problems,
        card_problems,
    )

    return {
        "filepath": str(path),
        "score": score,
        "rating": rating,
        "has_frontmatter": fields is not None,
        "frontmatter_problems": frontmatter_problems,
        "frontmatter_notes": frontmatter_notes,
        "card_problems": card_problems,
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

    # v2 frontmatter and Resume Card
    if result["has_frontmatter"] or result["frontmatter_problems"]:
        if result["frontmatter_problems"]:
            print("\n[FAIL] Frontmatter problems:")
            for problem in result["frontmatter_problems"]:
                print(f"       - {problem}")
        else:
            print("\n[PASS] Frontmatter complete")
        for note in result["frontmatter_notes"]:
            print(f"\n[INFO] {note}")
        for problem in result["card_problems"]:
            print(f"\n[FAIL] {problem}")

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
        and not result["frontmatter_problems"]
        and not result["card_problems"]
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
