#!/usr/bin/env python3
"""
Pre-Compact State Capture Hook

Fires before context compaction to capture current state (active plan,
current task) so post-compact-restore.py can surface it afterwards.

PreCompact hooks cannot block or otherwise prevent compaction — Claude
Code's own docs list PreCompact as one of the events "Exit code 2 isn't
honored for", with no `decision` output field it supports either, so this
hook is capture-only. (An earlier version of this hook attempted an
opt-in "block compaction while a plan is still DRAFT" feature; removed
after Codex's automated review, 2026-09-11, confirmed against this
repo's own plugin-devkit/hook-development docs and the official Claude
Code hooks reference that PreCompact has no supported blocking
mechanism — the printed JSON was silently ignored and compaction always
proceeded regardless.)
Fail-open on any internal error.

Plan/log directories are opt-in via CONTEXT_KIT_PLANS_DIR and
CONTEXT_KIT_SESSION_LOGS_DIR (unset by default — this plugin doesn't assume
any particular project's plan/log convention; both features are simply
inert until configured).

Hook Event: PreCompact
Returns: exit 0 in all cases; stdout is block JSON or empty.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# Colors for terminal output
CYAN = "\033[0;36m"
GREEN = "\033[0;32m"
YELLOW = "\033[0;33m"
NC = "\033[0m"  # No color


def get_session_dir(session_id: str = "") -> Path:
    """Get the session directory for storing state files.

    Scoped by BOTH project and session: without `session_id`, two
    concurrent Claude Code sessions in the same project (an explicitly
    supported pattern — worktrees, multiple terminals) would share one
    pre-compact-state.json and race each other's capture/restore. An
    empty `session_id` falls back to a shared "default" bucket rather
    than crashing — a degraded-but-safe fallback, not the normal path.
    """
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    project_hash = (
        hashlib.sha256(project_dir.encode()).hexdigest()[:8] if project_dir else "default"
    )
    session_hash = hashlib.sha256(session_id.encode()).hexdigest()[:8] if session_id else "default"

    session_dir = Path.home() / ".claude" / "sessions" / f"{project_hash}-{session_hash}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def _configured_dir(env_var: str, project_dir: str) -> Path | None:
    """Resolve an opt-in directory from an env var (absolute, or relative to
    project_dir). Returns None if the env var is unset — the caller's
    feature stays inert rather than falling back to an invented default."""
    raw = os.environ.get(env_var, "")
    if not raw:
        return None
    path = Path(raw)
    return path if path.is_absolute() else Path(project_dir) / path


def _is_contained_regular_file(path: Path, base_dir: Path) -> bool:
    """True only if `path` is a regular file (not a symlink) whose resolved
    location stays within `base_dir`'s own resolved boundary.

    CONTEXT_KIT_PLANS_DIR/CONTEXT_KIT_SESSION_LOGS_DIR are project-controlled
    directories a plan/log's *.md entry could be a symlink inside — reading
    or appending through it would then follow the link anywhere on disk
    (CWE-59, found by CodeRabbit's automated review, 2026-09-11). `is_symlink()`
    rejects the symlink entry itself; the resolved-path containment check
    additionally rejects a regular file reached only through a symlinked
    parent directory.
    """
    if path.is_symlink():
        return False
    try:
        resolved = path.resolve(strict=True)
        resolved_base = base_dir.resolve(strict=True)
    except OSError:
        return False
    return resolved == resolved_base or resolved_base in resolved.parents


def find_active_plan(project_dir: str) -> dict | None:
    """Find the most recent non-completed plan."""
    plans_dir = _configured_dir("CONTEXT_KIT_PLANS_DIR", project_dir)
    if plans_dir is None or not plans_dir.exists():
        return None

    plan_files = sorted(
        (p for p in plans_dir.glob("*.md") if _is_contained_regular_file(p, plans_dir)),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )

    # Scan every plan file, not just the N most recently modified — a completed
    # plan touched more recently than an older still-active one must not shadow
    # it (found live by Codex review: slicing before filtering silently returned
    # None whenever the 3 newest files all happened to be completed).
    for plan_file in plan_files:
        try:
            content = plan_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        # Parse the plan's Status FIELD (e.g. "**Status:** DRAFT"), not a
        # whole-file substring — a DRAFT plan whose body merely mentions
        # "APPROVED" or "COMPLETED" (a checklist item, or the legend
        # "Status (DRAFT/APPROVED/COMPLETED)") must not be mis-classified.
        m = re.search(
            r"^\s*\**\s*status\s*\**\s*:\s*\**\s*"
            r"(draft|approved|completed|implemented|in[ -]?progress)",
            content,
            re.IGNORECASE | re.MULTILINE,
        )
        v = m.group(1).lower() if m else "in_progress"
        if v.startswith(("completed", "implemented")):
            continue  # skip finished plans
        status = (
            "approved"
            if v.startswith("approved")
            else ("draft" if v.startswith("draft") else "in_progress")
        )

        # Find current task (first unchecked item)
        current_task = None
        for line in content.split("\n"):
            if "- [ ]" in line:
                current_task = line.replace("- [ ]", "").strip()
                break

        return {
            "plan_path": str(plan_file),
            "plan_name": plan_file.name,
            "status": status,
            "current_task": current_task,
        }

    return None


def save_state(state: dict, session_id: str = "") -> None:
    """Save state to the session directory."""
    state_file = get_session_dir(session_id) / "pre-compact-state.json"
    state["timestamp"] = datetime.now().isoformat()

    try:
        state_file.write_text(json.dumps(state, indent=2), encoding="utf-8")
    except OSError as e:
        print(f"Warning: Could not save pre-compact state: {e}", file=sys.stderr)


def append_to_session_log(project_dir: str, trigger: str) -> None:
    """Append compaction note to session log, if CONTEXT_KIT_SESSION_LOGS_DIR
    is configured and a log file already exists there."""
    logs_dir = _configured_dir("CONTEXT_KIT_SESSION_LOGS_DIR", project_dir)
    if logs_dir is None or not logs_dir.exists():
        return

    log_files = sorted(
        (p for p in logs_dir.glob("*.md") if _is_contained_regular_file(p, logs_dir)),
        key=lambda f: f.stat().st_mtime,
        reverse=True,
    )
    if not log_files:
        return

    try:
        with open(log_files[0], "a", encoding="utf-8") as f:
            f.write("\n\n---\n")
            f.write(f"**Context compaction ({trigger}) at {datetime.now().strftime('%H:%M')}**\n")
    except OSError:
        pass


def format_compaction_message(plan_info: dict | None) -> str:
    """Format the pre-compaction message."""
    lines = []
    lines.append(f"\n{YELLOW}⚡ Context compaction starting{NC}")
    lines.append("")

    if plan_info:
        lines.append(f"{GREEN}Current state saved:{NC}")
        lines.append(f"  Plan: {plan_info['plan_name']} ({plan_info['status']})")
        if plan_info.get("current_task"):
            lines.append(f"  Next task: {plan_info['current_task']}")

    lines.append("")
    lines.append(f"{CYAN}State will be restored after compaction.{NC}")
    lines.append("")

    return "\n".join(lines)


def main() -> int:
    """Main hook entry point."""
    # Read hook input
    try:
        hook_input = json.load(sys.stdin)
    except (OSError, json.JSONDecodeError):
        hook_input = {}

    trigger = hook_input.get("trigger", "auto")
    session_id = hook_input.get("session_id", "") or ""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")

    if not project_dir:
        return 0

    # Gather state
    plan_info = find_active_plan(project_dir)

    # Build state object
    state = {
        "trigger": trigger,
        "plan_path": plan_info["plan_path"] if plan_info else None,
        "plan_status": plan_info["status"] if plan_info else None,
        "current_task": plan_info.get("current_task") if plan_info else None,
    }

    # Save state for restoration
    save_state(state, session_id)

    # Append note to session log (no-op unless CONTEXT_KIT_SESSION_LOGS_DIR is configured)
    append_to_session_log(project_dir, trigger)

    # Print to stderr (PreCompact normally ignores stdout; stderr is
    # shown to user)
    print(format_compaction_message(plan_info), file=sys.stderr)

    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        # Fail open — never block Claude due to a hook bug
        sys.exit(0)
