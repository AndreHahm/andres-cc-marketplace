#!/usr/bin/env python3
"""
Smart scaffold generator for handoff documents.

Creates a new handoff document with auto-detected metadata:
- Frontmatter: creation time (UTC), project path, git branch and HEAD, platform,
  handoff chain link
- Resume Card and the v2 sections
- Unpushed Changes: uncommitted, untracked and unpushed files

Usage:
    python create_handoff.py [task-slug] [--continues-from <previous-handoff>]
    python create_handoff.py "implementing-auth"
    python create_handoff.py "auth-part-2" --continues-from 2026-01-15-143022-auth.md
    python create_handoff.py  # auto-generates slug from timestamp
"""

from __future__ import annotations

import argparse
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

# Sibling-script import, same pattern as check_staleness.py.
sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_handoff import git_env  # noqa: E402

# A filename with any of these characters is never written into the handoff's Markdown table.
UNSAFE_NAME = re.compile(r"[\x00-\x1f\x7f|`]")


def run_cmd(cmd: list[str], cwd: str | None = None, strip: bool = True) -> tuple[bool, str]:
    """Run a command and return (success, output).

    strip=False keeps the output as is, for NUL-separated listings (-z), where stripping
    whitespace would cut a leading or trailing space off the first or last filename.
    """
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, cwd=cwd, env=git_env(), timeout=10
        )
        return result.returncode == 0, result.stdout.strip() if strip else result.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False, ""


def get_git_info(project_path: str) -> dict:
    """Gather git information from the project."""
    info = {
        "is_git_repo": False,
        "branch": None,
        "head": None,
        "changed_files": [],
        "has_upstream": False,
        "listing_failed": False,
        "unpushed_commits": 0,
    }

    # Check if git repo
    success, _ = run_cmd(["git", "rev-parse", "--git-dir"], cwd=project_path)
    if not success:
        return info

    info["is_git_repo"] = True

    success, branch = run_cmd(["git", "branch", "--show-current"], cwd=project_path)
    if success and branch:
        info["branch"] = branch

    success, head = run_cmd(["git", "rev-parse", "HEAD"], cwd=project_path)
    if success and head:
        info["head"] = head

    # Uncommitted (unstaged, staged and untracked) files, then files in commits not yet pushed.
    # Without an upstream the last command fails; has_upstream records that, and listing_failed
    # records a failure of any other command, so the scaffold never claims a clean state it could
    # not check.
    # -z gives NUL-separated, unquoted paths, so a non-ASCII name is listed as itself rather than
    # C-quoted. Every path is relative to the repository root (git diff always is; ls-files gets
    # --full-name), so a project in a subdirectory of the repository gets one path base. The
    # project's own handoffs (<prefix>.claude/handoffs/) are left out: they are not work to push.
    success, prefix = run_cmd(["git", "rev-parse", "--show-prefix"], cwd=project_path)
    handoffs_dir = (prefix if success else "") + ".claude/handoffs/"
    changed: list[str] = []
    for cmd in (
        ["git", "diff", "--name-only", "-z"],
        ["git", "diff", "--name-only", "-z", "--cached"],
        # ":/" makes ls-files repository-wide like the diffs; without it, it lists only files
        # under a subdirectory project and could miss untracked work elsewhere in the repository.
        ["git", "ls-files", "-z", "--full-name", "--others", "--exclude-standard", "--", ":/"],
        ["git", "diff", "--name-only", "-z", "@{upstream}...HEAD"],
    ):
        success, output = run_cmd(cmd, cwd=project_path, strip=False)
        if cmd[-1] == "@{upstream}...HEAD":
            info["has_upstream"] = success
        elif not success:
            info["listing_failed"] = True
        if success and output:
            changed += [
                f
                for f in output.split("\0")
                if f and f not in changed and not f.startswith(handoffs_dir)
            ]
    info["changed_files"] = changed

    # Commits whose changes cancel out (a commit and its revert) leave no file in the diff above,
    # so count unpushed commits directly.
    if info["has_upstream"]:
        success, count = run_cmd(
            ["git", "rev-list", "--count", "@{upstream}..HEAD"], cwd=project_path
        )
        if success and count.isdigit():
            info["unpushed_commits"] = int(count)
        else:
            info["listing_failed"] = True

    return info


def detect_platform() -> str:
    """The frontmatter platform value: linux, windows or macos."""
    if sys.platform.startswith("win"):
        return "windows"
    if sys.platform == "darwin":
        return "macos"
    return "linux"


def find_previous_handoffs(project_path: str) -> list[dict]:
    """Find existing handoffs in the project."""
    handoffs_dir = Path(project_path) / ".claude" / "handoffs"
    if not handoffs_dir.exists():
        return []

    handoffs = []
    for filepath in handoffs_dir.glob("*.md"):
        # Extract title from file
        try:
            content = filepath.read_text(encoding="utf-8")
            match = re.search(r"^#\s+(?:Handoff:\s*)?(.+)$", content, re.MULTILINE)
            title = match.group(1).strip() if match else filepath.stem
        except Exception:
            title = filepath.stem

        # Parse date from filename
        date_match = re.match(r"(\d{4}-\d{2}-\d{2})-(\d{6})", filepath.name)
        if date_match:
            try:
                date = datetime.strptime(
                    f"{date_match.group(1)} {date_match.group(2)}", "%Y-%m-%d %H%M%S"
                )
            except ValueError:
                date = None
        else:
            date = None

        handoffs.append(
            {
                "filename": filepath.name,
                "path": str(filepath),
                "title": title,
                "date": date,
            }
        )

    # Sort by date, most recent first
    handoffs.sort(key=lambda x: x["date"] or datetime.min, reverse=True)
    return handoffs


def get_previous_handoff_info(project_path: str, continues_from: str | None = None) -> dict:
    """Get information about the previous handoff for chaining."""
    handoffs = find_previous_handoffs(project_path)

    if continues_from:
        # Find specific handoff
        for h in handoffs:
            if continues_from in h["filename"]:
                return {
                    "exists": True,
                    "filename": h["filename"],
                    "title": h["title"],
                }
        return {"exists": False, "filename": continues_from, "title": "Not found"}

    elif handoffs:
        # Suggest most recent
        most_recent = handoffs[0]
        return {
            "exists": True,
            "filename": most_recent["filename"],
            "title": most_recent["title"],
            "suggested": True,
        }

    return {"exists": False}


def generate_handoff(
    project_path: str, slug: str | None = None, continues_from: str | None = None
) -> str:
    """Generate a handoff document with pre-filled metadata."""

    # Generate timestamp and filename
    now = datetime.now()
    created = now.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    file_timestamp = now.strftime("%Y-%m-%d-%H%M%S")

    if not slug:
        slug = "handoff"

    # Sanitize slug
    slug = slug.lower().replace(" ", "-").replace("_", "-")
    slug = "".join(c for c in slug if c.isalnum() or c == "-")

    filename = f"{file_timestamp}-{slug}.md"

    # Create handoffs directory
    handoffs_dir = Path(project_path) / ".claude" / "handoffs"
    handoffs_dir.mkdir(parents=True, exist_ok=True)

    filepath = handoffs_dir / filename

    # Gather git info
    git_info = get_git_info(project_path)

    # Get previous handoff info for chaining
    prev_handoff = get_previous_handoff_info(project_path, continues_from)

    branch = git_info["branch"] or "[TODO: branch name; not a git repo or detached HEAD]"
    head = git_info["head"] or "none"

    # continues_from: an explicitly named, existing handoff is written as fact; the most recent
    # handoff found without --continues-from is only a suggestion the author must confirm.
    if prev_handoff.get("exists") and not prev_handoff.get("suggested"):
        continues_line = prev_handoff["filename"]
    elif prev_handoff.get("exists"):
        continues_line = f"[TODO: {prev_handoff['filename']} or none]"
    elif continues_from:
        continues_line = f"[TODO: {continues_from} not found; an existing handoff filename or none]"
    else:
        continues_line = "none"

    # Unpushed Changes: only uncommitted or unpushed files (optional section)
    changed = git_info["changed_files"]
    if changed:
        # A git filename can hold a line break, "|" or a backtick, which would end the table row
        # or cell and put text of the filename's choosing into the handoff. Such names are never
        # written; a TODO counts them instead, so the author lists them by hand.
        listed = [f for f in changed if not UNSAFE_NAME.search(f)]
        unsafe = len(changed) - len(listed)
        rows = "\n".join(f"| {f} | [TODO: what changed and why] |" for f in listed[:10])
        if len(listed) > 10:
            rows += f"\n| ... and {len(listed) - 10} more files | |"
        unpushed_section = f"| File | Change |\n|------|--------|\n{rows}" if listed else ""
        if unsafe:
            note = (
                f"[TODO: {unsafe} changed file(s) have a line break, '|', a backtick or a "
                "control character in the name and are not listed; describe them, or none]"
            )
            unpushed_section = f"{unpushed_section}\n\n{note}" if listed else note
    else:
        unpushed_section = "None: everything is committed and pushed."
    if not git_info["is_git_repo"]:
        # Nothing could be checked, so never claim everything is committed and pushed.
        unpushed_section = "[TODO: not a git repository; list files changed this session, or none]"
    elif git_info["listing_failed"]:
        # Some changes could not be listed, so never claim everything is committed.
        failed = "[TODO: a git listing command failed; add uncommitted and unpushed files, or none]"
        unpushed_section = f"{unpushed_section}\n\n{failed}" if changed else failed
    elif not git_info["has_upstream"]:
        # Unpushed commits could not be listed, so never claim everything is pushed.
        no_upstream = "[TODO: the branch has no upstream; add files from unpushed commits, or none]"
        unpushed_section = f"{unpushed_section}\n\n{no_upstream}" if changed else no_upstream
    elif git_info["unpushed_commits"] and not changed:
        # Local commits exist even though no file differs from the upstream.
        unpushed_section = (
            f"[TODO: {git_info['unpushed_commits']} unpushed commit(s) with no net file change; "
            "push them or say why not]"
        )

    # Generate the document
    content = f"""---
created: {created}
project: {project_path}
branch: {branch}
head: {head}
pr: [TODO: PR number, or none]
platform: {detect_platform()}
continues_from: {continues_line}
state: [TODO: implementing|pr-draft|in-review|ready-to-merge|ready-to-publish|blocked|done]
context_mode: [TODO: derived from state, see SKILL.md CREATE Step 2 item 5]
---

# Handoff: [TASK_TITLE - replace this]

## Resume Card

- State: [TODO: the state value, in a few words of context]
- Next step: [TODO: Immediate Next Steps item 1, verbatim]
- Branch and PR: {branch}, [TODO: PR number or none]
- Blockers: [TODO: none, or each blocker in one line]
- User constraints: [TODO: the user's standing instructions in one line each, or none]

## Current State Summary

[TODO: Write one paragraph on what was being worked on, current status, and where it left off]

## Codebase Understanding

### Critical Files

| File | Role | Why it matters |
|------|------|----------------|
| [TODO: Add critical files; the role column carries the architecture] | | |

## Work Completed

### Work Not Visible in Git

- [TODO: Issues filed, comments posted, runs left pending, or none]

### Unpushed Changes

{unpushed_section}

### Decisions Made

| Decision | Options Considered | Rationale | Decided by |
|----------|-------------------|-----------|------------|
| [TODO: Document key decisions] | | | [user or agent] |

## Pending Work

### Immediate Next Steps

1. [TODO: Most critical next action]
2. [TODO: Second priority]
3. [TODO: Third priority]

### Blockers/Open Questions

- [ ] [TODO: List any blockers or open questions]

### Deferred Items

- [TODO: Items deferred and why]

## Context for Resuming Agent

### Important Context

[TODO: This is the MOST IMPORTANT section - write critical information the next agent MUST know]

#### User Constraints

- [TODO: The user's standing instructions for this work, verbatim, or none]

#### Learnings

- [TODO: Process and tool behavior found this session, e.g. a guard that rejects a chained
  marker-and-commit call; or none]

### Assumptions Made

- [TODO: List assumptions made during this session]

### Potential Gotchas & Key Patterns

- [TODO: Codebase facts and conventions, e.g. a generated mirror that must not be edited by hand]

Environment: [optional: running processes and required env var NAMES only, never values; or none]

## Related Resources

- [optional: only links not findable from the PR or Critical Files; or none]

---

**Security Reminder**: Run `validate_handoff.py` before finalizing to check for secret exposure, and
redact personal or confidential details before sharing this handoff.
"""

    # Write the file. file_timestamp has one-second resolution -- two concurrent
    # invocations with the same slug in that second would otherwise race on the same
    # filename. Reserve the path atomically with exclusive creation ("x" mode: fails
    # with FileExistsError instead of overwriting) and retry with the next numeric
    # suffix on collision, rather than checking .exists() first and writing
    # separately -- that check-then-write gap is exactly where two concurrent callers
    # could both pass the check and the second write would still clobber the first.
    suffix = 2
    while True:
        try:
            with open(filepath, "x", encoding="utf-8") as f:
                f.write(content)
            break
        except FileExistsError:
            filepath = handoffs_dir / f"{file_timestamp}-{slug}-{suffix}.md"
            suffix += 1

    return str(filepath)


def main():
    sys.stdout.reconfigure(encoding="utf-8")  # ty: ignore[missing-union-attribute]
    sys.stderr.reconfigure(encoding="utf-8")  # ty: ignore[missing-union-attribute]

    parser = argparse.ArgumentParser(
        description="Create a new handoff document with smart scaffolding"
    )
    parser.add_argument(
        "slug",
        nargs="?",
        default=None,
        help="Short identifier for the handoff (e.g., 'implementing-auth')",
    )
    parser.add_argument(
        "--continues-from",
        dest="continues_from",
        help="Filename of previous handoff this continues from",
    )

    args = parser.parse_args()

    # Get project path (current working directory)
    project_path = os.getcwd()

    # Check for existing handoffs to suggest chaining
    if not args.continues_from:
        prev_handoffs = find_previous_handoffs(project_path)
        if prev_handoffs:
            print(f"Found {len(prev_handoffs)} existing handoff(s).")
            print(f"Most recent: {prev_handoffs[0]['filename']}")
            print("Use --continues-from <filename> to link handoffs.\n")

    # Generate handoff
    filepath = generate_handoff(project_path, args.slug, args.continues_from)

    print(f"Created handoff document: {filepath}")
    print("\nNext steps:")
    print(f"1. Open {filepath}")
    print("2. Replace [TODO: ...] placeholders with actual content")
    print("3. Focus especially on 'Important Context' and 'Immediate Next Steps'")
    print(f"4. Run: python validate_handoff.py {filepath}")
    print("   (Checks for completeness and accidental secrets)")

    return filepath


if __name__ == "__main__":
    main()
