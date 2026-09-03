#!/usr/bin/env python3
"""Session discovery and cross-session operations.

Scans ~/.claude/projects/ to find, list, search, and analyze sessions.

Usage as CLI:
  python3 session_store.py list [--project FILTER] [--sort recency|size|duration] [--limit N]
                                 [--since DATE] [--until DATE] [--format json|table]
  python3 session_store.py search "<query>" [--project FILTER] [--since DATE] [--until DATE]
                                 [--limit N] [--context N] [--format json|table]
  python3 session_store.py timeline [--project FILTER] [--since DATE] [--until DATE]
                                 [--format json|table]
  python3 session_store.py cleanup [--older-than 30d] [--min-messages N]
  python3 session_store.py tasks [--status pending|completed|in_progress|all] [--task-list ID]
                                 [--since DATE] [--until DATE] [--format json|table]
  python3 session_store.py task-lists
  python3 session_store.py delete-session <id> [--delete-tasks]
  python3 session_store.py delete-task <task-list-id> <task-id>
  python3 session_store.py delete-task-list <task-list-id>
  python3 session_store.py orphan-task-lists
  python3 session_store.py session-detail <id>
  python3 session_store.py current

Global overrides (any command): --projects-base PATH --tasks-base PATH
--format json is the same as --json; both default to table for
list/search/timeline/tasks -- every other command always prints JSON.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import sys
from pathlib import Path
from typing import Any, NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent))

from formatters import (  # noqa: E402
    format_duration,
    format_size,
    parse_date_boundary,
    parse_timestamp,
    render_table,
    to_json,
    to_ndjson,
    truncate,
)
from session_transcript import (  # noqa: E402
    extract_user_text,
    get_stats,
    get_tasks,
    merge_task_events,
    message_dict,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DEFAULT_PROJECTS_BASE = str(Path.home() / ".claude" / "projects")
DEFAULT_TASKS_BASE = str(Path.home() / ".claude" / "tasks")

VALID_ID_RE = re.compile(r"\A[a-zA-Z0-9_-]+\Z")

# ---------------------------------------------------------------------------
# Path encoding/decoding
# ---------------------------------------------------------------------------


def encode_project_path(path: str) -> str:
    """Encode a filesystem path to Claude's project directory name.

    Claude Code encodes every path separator as "-" -- ":" and "\\" too on
    Windows (e.g. "C:\\Dev\\proj" -> "C--Dev-proj"), not just "/".
    """
    return re.sub(r"[/\\:]", "-", path)


_WINDOWS_DRIVE_RE = re.compile(r"\A([A-Za-z])--(.*)\Z")


def decode_project_path(encoded: str) -> str:
    """Decode a Claude project directory name back to a filesystem path.

    Best-effort and display-only, never used for filesystem I/O: the encoding
    is lossy (encode_project_path collapses "/", "\\", and ":" all to "-"), so
    a real hyphen inside a path segment is indistinguishable from an encoded
    separator and can't be losslessly recovered. Windows drive-letter paths
    (e.g. "C--Dev-Repos-foo") are recognized and rendered with the correct
    drive prefix and backslash separators, but any segment containing a
    genuine hyphen (like a repo named "andres-cc-marketplace") still renders
    with that hyphen split into extra path segments.

    Never raises: a rejected ".." sequence here would abort every caller that
    lists multiple sessions (list_sessions/search/timeline/cleanup all call
    this once per session), for a value that's never used for filesystem I/O
    in the first place -- one oddly-named project (e.g. a real directory
    literally named "v1..v2") would otherwise break listing for every other
    project too, not just itself.
    """
    drive_match = _WINDOWS_DRIVE_RE.match(encoded)
    if drive_match:
        drive, rest = drive_match.group(1), drive_match.group(2)
        decoded = f"{drive}:\\" + rest.replace("-", "\\")
    elif encoded.startswith("-"):
        decoded = "/" + encoded[1:].replace("-", "/")
    else:
        decoded = encoded.replace("-", "/")
    return decoded


# ---------------------------------------------------------------------------
# ID validation
# ---------------------------------------------------------------------------


def is_valid_id(id_str: str) -> bool:
    """Validate that an ID is safe for path construction (no traversal)."""
    return len(id_str) > 0 and bool(VALID_ID_RE.match(id_str))


def _assert_path_within_base(target_path: str, base_dir: str) -> None:
    """Verify a resolved path stays within the expected base directory.

    Uses realpath (resolves symlinks), not just abspath (lexical only) -- a
    symlinked entry inside base_dir that points outside it must still be caught.
    """
    resolved_target = os.path.realpath(target_path)
    resolved_base = os.path.realpath(base_dir)
    if resolved_target != resolved_base and not resolved_target.startswith(resolved_base + os.sep):
        raise ValueError("Path traversal detected")


# ---------------------------------------------------------------------------
# Session resolution
# ---------------------------------------------------------------------------


def _find_session_files_by_id(session_id: str, base: str) -> list[str]:
    """Search every project directory under base for a `<session_id>.jsonl` file.

    A session ID is a globally-unique UUID, so this search needs no project/cwd
    context at all -- it's the same mechanism step 3 of resolve_session() below
    reuses via CLAUDE_CODE_SESSION_ID, since that's more robust than matching a
    project directory name against the current cwd.
    """
    matches: list[str] = []
    if os.path.isdir(base):
        for entry in sorted(os.listdir(base)):
            entry_path = os.path.join(base, entry)
            if not os.path.isdir(entry_path):
                continue
            candidate = os.path.join(entry_path, f"{session_id}.jsonl")
            if os.path.exists(candidate):
                matches.append(candidate)
    return matches


def resolve_session(
    identifier: str | None = None, cwd: str | None = None, projects_base: str | None = None
) -> str:
    """
    Resolve a session identifier to a JSONL file path.

    Resolution chain:
    1. Full path to .jsonl -> use directly
    2. UUID -> search projects for matching filename
    3. None -> the live session's own CLAUDE_CODE_SESSION_ID, if set
    4. None -> most recent .jsonl in cwd's project dir

    Step 3 exists because a session's JSONL is stored under whichever project
    directory it actually *started* in -- if cwd later changes (e.g. a worktree
    created mid-session via starting-work), step 4's cwd-based match finds
    nothing even though the live session obviously exists. CLAUDE_CODE_SESSION_ID
    identifies it directly, sidestepping the cwd mismatch entirely.

    Raises ValueError instead of exiting (CLI catches and exits with code 2).
    """
    base = projects_base or DEFAULT_PROJECTS_BASE

    # 1. Full path
    if identifier and (identifier.endswith(".jsonl") or "/" in identifier):
        if os.path.exists(identifier):
            return identifier
        raise ValueError(f"Session file not found: {identifier}")

    # 2. UUID search
    if identifier:
        matches = _find_session_files_by_id(identifier, base)
        if len(matches) > 1:
            raise ValueError(
                f"Ambiguous session ID: {identifier} matches {len(matches)} files across different "
                f"projects ({', '.join(matches)}). Specify the full path instead."
            )
        if matches:
            return matches[0]
        raise ValueError(
            f"No session found with ID: {identifier}. Run session-list to see available sessions."
        )

    # 3. Live session's own ID via environment
    env_session_id = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if env_session_id and is_valid_id(env_session_id):
        env_matches = _find_session_files_by_id(env_session_id, base)
        if len(env_matches) == 1:
            return env_matches[0]
        # Ambiguous (shouldn't happen for a real UUID) or not yet written to disk --
        # fall through to the cwd heuristic below rather than erroring here.

    # 4. Most recent in cwd project
    if cwd:
        encoded = encode_project_path(cwd)
        proj_dir = os.path.join(base, encoded)
        if os.path.isdir(proj_dir):
            jsonl_files = [
                os.path.join(proj_dir, name)
                for name in os.listdir(proj_dir)
                if name.endswith(".jsonl")
            ]
            jsonl_files.sort(key=lambda p: os.stat(p).st_mtime, reverse=True)
            if jsonl_files:
                return jsonl_files[0]

    raise ValueError(
        "No session specified and could not find current session. Provide a session ID or path."
    )


# ---------------------------------------------------------------------------
# Session summary (private helper)
# ---------------------------------------------------------------------------


def _get_session_summary(session_path: str) -> dict | None:
    try:
        stat = os.stat(session_path)
        size = stat.st_size
    except OSError:
        return None

    session_id = re.sub(r"\.jsonl$", "", os.path.basename(session_path))
    parent_name = os.path.basename(os.path.dirname(session_path))

    if size == 0:
        return {
            "sessionId": session_id,
            "project": decode_project_path(parent_name),
            "date": None,
            "started": None,
            "lastActivity": None,
            "messages": 0,
            "durationMinutes": 0,
            "sizeBytes": 0,
            "path": session_path,
        }

    msg_count = 0
    first_ts: str | None = None
    last_ts: str | None = None

    try:
        with open(session_path, encoding="utf-8") as f:
            content = f.read()
        for raw_line in content.split("\n"):
            line = raw_line.strip()
            if not line:
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg_count += 1
            ts = obj.get("timestamp")
            if ts:
                if first_ts is None:
                    first_ts = ts
                last_ts = ts
    except OSError:
        return None

    duration_minutes = 0.0
    date_str: str | None = None

    if first_ts:
        first_dt = parse_timestamp(first_ts)
        last_dt = parse_timestamp(last_ts)
        if first_dt:
            date_str = first_dt.date().isoformat()
        if first_dt and last_dt:
            duration_minutes = round(((last_dt - first_dt).total_seconds() / 60) * 10) / 10

    return {
        "sessionId": session_id,
        "project": decode_project_path(parent_name),
        "date": date_str,
        "started": first_ts,
        "lastActivity": last_ts,
        "messages": msg_count,
        "durationMinutes": duration_minutes,
        "sizeBytes": size,
        "path": session_path,
    }


# ---------------------------------------------------------------------------
# list_sessions
# ---------------------------------------------------------------------------


def list_sessions(
    project_filter: str | None = None,
    sort: str = "recency",
    limit: int | None = 20,
    since: str | None = None,
    until: str | None = None,
    projects_base: str | None = None,
) -> list[dict]:
    """List all sessions, optionally filtered and sorted. limit=None returns all of them."""
    base = projects_base or DEFAULT_PROJECTS_BASE

    if not os.path.isdir(base):
        return []

    sessions = []

    for entry in os.listdir(base):
        entry_path = os.path.join(base, entry)
        if not os.path.isdir(entry_path):
            continue
        if project_filter and project_filter.lower() not in entry.lower():
            continue
        for fname in os.listdir(entry_path):
            if not fname.endswith(".jsonl"):
                continue
            summary = _get_session_summary(os.path.join(entry_path, fname))
            if summary:
                sessions.append(summary)

    since_dt = parse_date_boundary(since) if since else None
    until_dt = parse_date_boundary(until, end_of_day=True) if until else None

    def keep(s: dict) -> bool:
        ts = parse_timestamp(s["lastActivity"] or s["started"])
        if not ts:
            return not since_dt and not until_dt
        if since_dt and ts < since_dt:
            return False
        if until_dt and ts > until_dt:
            return False
        return True

    filtered = [s for s in sessions if keep(s)]

    if sort == "recency":
        filtered.sort(key=lambda s: s["lastActivity"] or "", reverse=True)
    elif sort == "size":
        filtered.sort(key=lambda s: s["sizeBytes"], reverse=True)
    elif sort == "duration":
        filtered.sort(key=lambda s: s["durationMinutes"], reverse=True)

    return filtered[:limit]


# ---------------------------------------------------------------------------
# search_sessions
# ---------------------------------------------------------------------------


def search_sessions(
    query: str,
    project_filter: str | None = None,
    since: str | None = None,
    until: str | None = None,
    limit: int = 20,
    context: int = 0,
    projects_base: str | None = None,
) -> list[dict]:
    """Search across all sessions for matching content."""
    base = projects_base or DEFAULT_PROJECTS_BASE

    if not os.path.isdir(base):
        return []

    pattern = re.compile(re.escape(query), re.IGNORECASE)

    since_dt = parse_date_boundary(since) if since else None
    until_dt = parse_date_boundary(until, end_of_day=True) if until else None

    results: list[dict] = []

    for entry in sorted(os.listdir(base)):
        entry_path = os.path.join(base, entry)
        if not os.path.isdir(entry_path):
            continue
        if project_filter and project_filter.lower() not in entry.lower():
            continue

        for fname in sorted(os.listdir(entry_path)):
            if not fname.endswith(".jsonl"):
                continue

            jsonl_path = os.path.join(entry_path, fname)
            lines_data: list[dict] = []

            try:
                with open(jsonl_path, encoding="utf-8") as f:
                    content = f.read()
                for raw_line in content.split("\n"):
                    line = raw_line.strip()
                    if not line:
                        continue
                    try:
                        lines_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
            except OSError:
                continue

            for i, obj in enumerate(lines_data):
                if since_dt or until_dt:
                    ts = parse_timestamp(obj.get("timestamp"))
                    if ts:
                        if since_dt and ts < since_dt:
                            continue
                        if until_dt and ts > until_dt:
                            continue

                searchable = ""
                if obj.get("type") == "user":
                    searchable = extract_user_text(obj)
                elif obj.get("type") == "assistant":
                    content_blocks = message_dict(obj).get("content") or []
                    if isinstance(content_blocks, list):
                        for block in content_blocks:
                            if isinstance(block, dict) and block.get("type") == "text":
                                searchable += f"{block.get('text', '')} "

                if not searchable or not pattern.search(searchable):
                    continue

                ctx_before: list[str] = []
                ctx_after: list[str] = []

                if context > 0:
                    for j in range(max(0, i - context), i):
                        prev = lines_data[j]
                        if prev.get("type") == "user":
                            ctx_before.append(truncate(extract_user_text(prev), 100))
                    for j in range(i + 1, min(len(lines_data), i + 1 + context)):
                        nxt = lines_data[j]
                        if nxt.get("type") == "user":
                            ctx_after.append(truncate(extract_user_text(nxt), 100))

                results.append(
                    {
                        "sessionId": re.sub(r"\.jsonl$", "", os.path.basename(jsonl_path)),
                        "project": decode_project_path(entry),
                        "timestamp": obj.get("timestamp"),
                        "type": obj.get("type"),
                        "match": truncate(searchable.strip(), 200),
                        "contextBefore": ctx_before,
                        "contextAfter": ctx_after,
                    }
                )

                if len(results) >= limit:
                    return results

    return results


# ---------------------------------------------------------------------------
# get_timeline
# ---------------------------------------------------------------------------


def get_timeline(
    project_filter: str | None = None,
    since: str | None = None,
    until: str | None = None,
    projects_base: str | None = None,
) -> list[dict]:
    """Chronological list of sessions for a project."""
    # A hardcoded numeric limit here would silently drop a project's oldest sessions
    # once it passed that count, with no truncation indicator surfaced anywhere --
    # "chronological list" means all of them, not a capped recent window.
    sessions = list_sessions(
        project_filter=project_filter,
        sort="recency",
        limit=None,
        since=since,
        until=until,
        projects_base=projects_base,
    )
    return list(reversed(sessions))


# ---------------------------------------------------------------------------
# find_cleanup_candidates
# ---------------------------------------------------------------------------


def find_cleanup_candidates(
    older_than: str | None = None, min_messages: int = 3, projects_base: str | None = None
) -> list[dict]:
    """Find sessions that are candidates for cleanup."""
    import time

    base = projects_base or DEFAULT_PROJECTS_BASE

    if not os.path.isdir(base):
        return []

    max_age_days: int | None = None
    if older_than:
        # Same "Nd/Nw/Nm" shorthand parse_date_boundary (formatters.py) already supports
        # elsewhere in this file's own --since/--until handling -- kept consistent rather
        # than accepting only "d" here. "m" uses a flat 30-day approximation (not
        # parse_date_boundary's calendar-month subtraction), which is fine for a coarse
        # cleanup threshold.
        m = re.match(r"^(\d+)([dwm])$", older_than)
        if m:
            n, unit = int(m.group(1)), m.group(2)
            max_age_days = n * {"d": 1, "w": 7, "m": 30}[unit]

    candidates: list[dict] = []
    now = time.time()

    for entry in os.listdir(base):
        entry_path = os.path.join(base, entry)
        if not os.path.isdir(entry_path):
            continue

        for fname in os.listdir(entry_path):
            if not fname.endswith(".jsonl"):
                continue

            jsonl_path = os.path.join(entry_path, fname)
            summary = _get_session_summary(jsonl_path)
            if not summary:
                continue

            try:
                file_mtime = os.stat(jsonl_path).st_mtime
            except OSError:
                continue

            age_days = int((now - file_mtime) / 86400)

            reason: str | None = None
            if summary["sizeBytes"] == 0:
                reason = "empty"
            elif summary["messages"] < min_messages:
                reason = "tiny"
            elif max_age_days is not None and age_days > max_age_days:
                reason = "old"

            if reason:
                candidates.append(
                    {
                        "path": jsonl_path,
                        "sessionId": summary["sessionId"],
                        "project": summary["project"],
                        "reason": reason,
                        "messages": summary["messages"],
                        "ageDays": age_days,
                        "sizeBytes": summary["sizeBytes"],
                    }
                )

    return candidates


# ---------------------------------------------------------------------------
# read_task_list
# ---------------------------------------------------------------------------


def read_task_list(task_list_id: str, tasks_base: str | None = None) -> list[dict]:
    """
    Read all tasks from a single task list directory.
    Skips .lock, .highwatermark, and any non-JSON-task files.

    Validates task_list_id the same way delete_task/delete_task_list do -- this
    function is reachable from the CLI's own --task-list flag with no other
    validation in that path, so an unvalidated value like "../../somedir" would
    otherwise let os.path.join walk outside tasks_base and read arbitrary .json
    files elsewhere on disk back to the caller.
    """
    if not is_valid_id(task_list_id):
        raise ValueError(f"Invalid task list ID: {task_list_id}")

    base = tasks_base or DEFAULT_TASKS_BASE
    task_dir = os.path.join(base, task_list_id)
    _assert_path_within_base(task_dir, base)

    if not os.path.isdir(task_dir):
        return []

    tasks: list[dict] = []

    files = sorted(name for name in os.listdir(task_dir) if name.endswith(".json"))

    for file_name in files:
        task_path = os.path.join(task_dir, file_name)
        try:
            with open(task_path, encoding="utf-8") as f:
                task = json.load(f)
            if not isinstance(task, dict):
                continue
            task["taskListId"] = task_list_id
            task["source"] = "filesystem"
            tasks.append(task)
        except (OSError, json.JSONDecodeError):
            pass

    return tasks


# ---------------------------------------------------------------------------
# delete_task
# ---------------------------------------------------------------------------


def delete_task(task_list_id: str, task_id: str, tasks_base: str | None = None) -> dict:
    """
    Delete a single task JSON file from a task list.
    Raises if ID is invalid or task doesn't exist.
    """
    if not is_valid_id(task_list_id):
        raise ValueError(f"Invalid task list ID: {task_list_id}")
    if not is_valid_id(task_id):
        raise ValueError(f"Invalid task ID: {task_id}")

    base = tasks_base or DEFAULT_TASKS_BASE
    task_path = os.path.join(base, task_list_id, f"{task_id}.json")
    _assert_path_within_base(task_path, base)

    if not os.path.exists(task_path):
        raise ValueError(f"Task not found: {task_list_id}/{task_id}")

    os.unlink(task_path)

    task_dir = os.path.join(base, task_list_id)
    remaining = len([name for name in os.listdir(task_dir) if name.endswith(".json")])

    return {"deleted": True, "taskPath": task_path, "taskListNowEmpty": remaining == 0}


# ---------------------------------------------------------------------------
# delete_task_list
# ---------------------------------------------------------------------------


def delete_task_list(task_list_id: str, tasks_base: str | None = None) -> dict:
    """
    Delete an entire task list directory.
    Raises if ID is invalid or directory doesn't exist.
    """
    if not is_valid_id(task_list_id):
        raise ValueError(f"Invalid task list ID: {task_list_id}")

    base = tasks_base or DEFAULT_TASKS_BASE
    task_dir = os.path.join(base, task_list_id)
    _assert_path_within_base(task_dir, base)

    if not os.path.isdir(task_dir):
        raise ValueError(f"Task list not found: {task_list_id}")

    task_count = len([name for name in os.listdir(task_dir) if name.endswith(".json")])

    shutil.rmtree(task_dir)

    return {"deleted": True, "path": task_dir, "taskCount": task_count}


# ---------------------------------------------------------------------------
# delete_session
# ---------------------------------------------------------------------------


def delete_session(
    session_id: str,
    projects_base: str | None = None,
    tasks_base: str | None = None,
    delete_orphaned_tasks: bool = False,
) -> dict:
    """
    Delete a session JSONL file. Finds any matching task lists and optionally
    deletes them too. Uses resolve_session() to find the file.
    """
    if not is_valid_id(session_id):
        raise ValueError(f"Invalid session ID: {session_id}")

    p_base = projects_base or DEFAULT_PROJECTS_BASE
    t_base = tasks_base or DEFAULT_TASKS_BASE

    session_path = resolve_session(session_id, projects_base=p_base)
    _assert_path_within_base(session_path, p_base)

    orphaned_task_lists: list[str] = []
    if os.path.isdir(t_base):
        task_dir = os.path.join(t_base, session_id)
        if os.path.isdir(task_dir):
            orphaned_task_lists.append(session_id)

    # Delete the task-list cascade before the session file: if this raises, the
    # session file is left intact and the error reflects the true on-disk state,
    # rather than reporting a failure after the session was already unlinked.
    orphaned_tasks_deleted = False
    if delete_orphaned_tasks and orphaned_task_lists:
        for list_id in orphaned_task_lists:
            delete_task_list(list_id, tasks_base=t_base)
        orphaned_tasks_deleted = True

    os.unlink(session_path)

    return {
        "deleted": True,
        "sessionPath": session_path,
        "orphanedTaskLists": orphaned_task_lists,
        "orphanedTasksDeleted": orphaned_tasks_deleted,
    }


# ---------------------------------------------------------------------------
# find_orphan_task_lists
# ---------------------------------------------------------------------------


def find_orphan_task_lists(
    projects_base: str | None = None, tasks_base: str | None = None
) -> list[dict]:
    """Find task lists that have no matching session JSONL file across any project."""
    import datetime as _dt

    p_base = projects_base or DEFAULT_PROJECTS_BASE
    t_base = tasks_base or DEFAULT_TASKS_BASE

    if not os.path.isdir(t_base):
        return []

    all_session_ids: set[str] = set()
    if os.path.isdir(p_base):
        for proj_entry in os.listdir(p_base):
            proj_dir = os.path.join(p_base, proj_entry)
            if not os.path.isdir(proj_dir):
                continue
            for fname in os.listdir(proj_dir):
                if fname.endswith(".jsonl"):
                    all_session_ids.add(re.sub(r"\.jsonl$", "", fname))

    orphans: list[dict] = []
    for entry in os.listdir(t_base):
        entry_path = os.path.join(t_base, entry)
        if not os.path.isdir(entry_path):
            continue
        if not is_valid_id(entry):
            # A directory name that isn't a safe ID can't be round-tripped through
            # delete_task_list()'s own validation -- skip it rather than surface it
            # as a "delete this" candidate the caller has no safe way to act on.
            continue
        if entry in all_session_ids:
            continue

        task_count = len([name for name in os.listdir(entry_path) if name.endswith(".json")])
        if task_count == 0:
            continue

        mtime = _dt.datetime.fromtimestamp(os.stat(entry_path).st_mtime, tz=_dt.UTC).isoformat()
        orphans.append(
            {
                "taskListId": entry,
                "taskCount": task_count,
                "lastModified": mtime,
                "path": entry_path,
            }
        )

    return orphans


# ---------------------------------------------------------------------------
# get_session_detail
# ---------------------------------------------------------------------------


def get_session_detail(
    session_id: str, projects_base: str | None = None, tasks_base: str | None = None
) -> dict:
    """
    Get detailed session info: summary, stats (tokens, tools, models),
    and associated task lists with their tasks.
    """
    if not is_valid_id(session_id):
        raise ValueError(f"Invalid session ID: {session_id}")

    p_base = projects_base or DEFAULT_PROJECTS_BASE
    t_base = tasks_base or DEFAULT_TASKS_BASE

    session_path = resolve_session(session_id, projects_base=p_base)

    summary = _get_session_summary(session_path)
    if not summary:
        raise ValueError(f"Could not read session: {session_id}")

    stats = get_stats(session_path)

    task_lists: list[dict] = []
    if os.path.isdir(t_base):
        task_dir = os.path.join(t_base, session_id)
        if os.path.isdir(task_dir):
            tasks = read_task_list(session_id, t_base)
            task_lists.append({"taskListId": session_id, "tasks": tasks})

    # Fallback: extract tasks from JSONL if none found in filesystem
    if not task_lists or all(not tl["tasks"] for tl in task_lists):
        try:
            raw_tasks = get_tasks(session_path)
            if raw_tasks:
                merged = merge_task_events(raw_tasks, session_id)
                if merged:
                    existing_idx = next(
                        (i for i, tl in enumerate(task_lists) if tl["taskListId"] == session_id),
                        None,
                    )
                    if existing_idx is not None:
                        task_lists[existing_idx]["tasks"] = merged
                    else:
                        task_lists.append({"taskListId": session_id, "tasks": merged})
        except Exception:  # noqa: BLE001 — JSONL parsing errors shouldn't break session detail
            pass

    return {"session": summary, "stats": stats, "taskLists": task_lists}


# ---------------------------------------------------------------------------
# list_task_lists
# ---------------------------------------------------------------------------


def list_task_lists(tasks_base: str | None = None) -> list[dict]:
    """List all task lists in ~/.claude/tasks/."""
    import datetime as _dt

    base = tasks_base or DEFAULT_TASKS_BASE

    if not os.path.isdir(base):
        return []

    result: list[dict] = []

    entries = sorted(
        (name for name in os.listdir(base) if os.path.isdir(os.path.join(base, name))),
    )

    for entry in entries:
        task_dir = os.path.join(base, entry)
        task_count = len([name for name in os.listdir(task_dir) if name.endswith(".json")])

        if task_count == 0:
            continue

        hwm_path = os.path.join(task_dir, ".highwatermark")
        highwatermark: int | None = None
        if os.path.exists(hwm_path):
            try:
                with open(hwm_path, encoding="utf-8") as f:
                    highwatermark = int(f.read().strip())
            except (OSError, ValueError):
                pass

        mtime = _dt.datetime.fromtimestamp(os.stat(task_dir).st_mtime, tz=_dt.UTC).isoformat()

        result.append(
            {
                "taskListId": entry,
                "taskCount": task_count,
                "lastModified": mtime,
                "highwatermark": highwatermark,
            }
        )

    result.sort(key=lambda tl: tl["lastModified"], reverse=True)
    return result


# ---------------------------------------------------------------------------
# aggregate_tasks
# ---------------------------------------------------------------------------


def aggregate_tasks(
    status_filter: str = "all",
    task_list_id: str | None = None,
    since: str | None = None,
    until: str | None = None,
    tasks_base: str | None = None,
    projects_base: str | None = None,
) -> list[dict]:
    """Aggregate tasks from the Tasks filesystem (primary) and session JSONL (fallback)."""
    t_base = tasks_base or DEFAULT_TASKS_BASE
    all_tasks: list[dict] = []

    # Primary: Read from ~/.claude/tasks/
    if task_list_id:
        all_tasks.extend(read_task_list(task_list_id, t_base))
    elif os.path.isdir(t_base):
        for entry in os.listdir(t_base):
            if os.path.isdir(os.path.join(t_base, entry)):
                all_tasks.extend(read_task_list(entry, t_base))

    # Fallback: Read from session JSONL (for older sessions)
    p_base = projects_base or DEFAULT_PROJECTS_BASE
    if os.path.isdir(p_base):
        known_ids = {t.get("taskListId") for t in all_tasks}
        for entry in os.listdir(p_base):
            proj_dir = os.path.join(p_base, entry)
            if not os.path.isdir(proj_dir):
                continue
            for fname in os.listdir(proj_dir):
                if not fname.endswith(".jsonl"):
                    continue
                stem = re.sub(r"\.jsonl$", "", fname)
                # A requested task_list_id scopes this fallback too -- without this
                # check, a --task-list request still scanned every other session's
                # JSONL and appended their tasks, since known_ids only ever contains
                # the one requested list's own filesystem-sourced tasks.
                if task_list_id and stem != task_list_id:
                    continue
                if stem in known_ids:
                    continue
                try:
                    raw_tasks = get_tasks(os.path.join(proj_dir, fname))
                    all_tasks.extend(merge_task_events(raw_tasks, stem, default_status="pending"))
                except Exception:  # noqa: BLE001
                    pass

    # Exclude tasks with invalid/missing status
    valid_statuses = {"in_progress", "pending", "completed"}
    valid_tasks = [t for t in all_tasks if t.get("status") in valid_statuses]

    # Date filtering (applies to JSONL-sourced tasks with timestamps)
    since_dt = parse_date_boundary(since) if since else None
    until_dt = parse_date_boundary(until, end_of_day=True) if until else None

    date_filtered = valid_tasks
    if since_dt or until_dt:

        def keep(t: dict) -> bool:
            ts = parse_timestamp(t.get("timestamp"))
            if not ts:
                return True  # filesystem tasks without timestamps pass through
            if since_dt and ts < since_dt:
                return False
            if until_dt and ts > until_dt:
                return False
            return True

        date_filtered = [t for t in valid_tasks if keep(t)]

    if status_filter != "all":
        return [t for t in date_filtered if t.get("status") == status_filter]

    return date_filtered


# ---------------------------------------------------------------------------
# Chart aggregation: daily tokens
# ---------------------------------------------------------------------------


def get_daily_token_aggregation(
    since: str | None = None,
    until: str | None = None,
    project_filter: str | None = None,
    projects_base: str | None = None,
) -> dict:
    sessions = list_sessions(
        projects_base=projects_base,
        project_filter=project_filter,
        since=since,
        until=until,
        sort="recency",
        limit=9999,
    )

    buckets: dict[str, dict[str, int]] = {}

    for s in sessions:
        if not s["date"]:
            continue
        try:
            stats = get_stats(s["path"])
            existing = buckets.setdefault(
                s["date"], {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0}
            )
            existing["input"] += stats["tokens"]["input"]
            existing["output"] += stats["tokens"]["output"]
            existing["cache_read"] += stats["tokens"]["cache_read"]
            existing["cache_create"] += stats["tokens"]["cache_create"]
        except Exception as err:  # noqa: BLE001 -- one corrupt session shouldn't break the whole chart
            sys.stderr.write(f"get_daily_token_aggregation: skipping {s['path']}: {err}\n")

    labels = sorted(buckets.keys())
    return {
        "labels": labels,
        "datasets": {
            "input": [buckets[d]["input"] for d in labels],
            "output": [buckets[d]["output"] for d in labels],
            "cache_read": [buckets[d]["cache_read"] for d in labels],
            "cache_create": [buckets[d]["cache_create"] for d in labels],
        },
    }


# ---------------------------------------------------------------------------
# Chart aggregation: model distribution
# ---------------------------------------------------------------------------


def get_model_distribution(
    since: str | None = None,
    until: str | None = None,
    project_filter: str | None = None,
    projects_base: str | None = None,
) -> list[dict]:
    sessions = list_sessions(
        projects_base=projects_base,
        project_filter=project_filter,
        since=since,
        until=until,
        sort="recency",
        limit=9999,
    )

    model_map: dict[str, dict[str, Any]] = {}

    for s in sessions:
        try:
            stats = get_stats(s["path"])
            total_tokens = (
                stats["tokens"]["input"]
                + stats["tokens"]["output"]
                + stats["tokens"]["cache_read"]
                + stats["tokens"]["cache_create"]
            )

            total_msgs = sum(stats["models"].values())
            for model, count in stats["models"].items():
                if model in ("unknown", "<synthetic>"):
                    continue
                existing = model_map.setdefault(model, {"tokens": 0, "sessions": set()})
                proportion = count / total_msgs if total_msgs > 0 else 0
                existing["tokens"] += round(total_tokens * proportion)
                existing["sessions"].add(s["sessionId"])
        except Exception as err:  # noqa: BLE001 -- one corrupt session shouldn't break the whole chart
            sys.stderr.write(f"get_model_distribution: skipping {s['path']}: {err}\n")

    entries = sorted(
        (
            {"model": model, "tokens": data["tokens"], "sessions": len(data["sessions"])}
            for model, data in model_map.items()
        ),
        key=lambda e: e["tokens"],
        reverse=True,
    )

    # entries' dict-literal shape (model: str, tokens: int, sessions: int) isn't a TypedDict, so ty
    # widens every value to their union across keys rather than tracking "tokens" as int alone.
    total_tokens_all = sum(e["tokens"] for e in entries)  # ty: ignore[no-matching-overload]
    if total_tokens_all == 0:
        return entries

    threshold = total_tokens_all * 0.03
    main: list[dict] = []
    other_tokens = 0

    for entry in entries:
        if entry["tokens"] >= threshold:
            main.append(entry)
        else:
            other_tokens += entry["tokens"]  # ty: ignore[unsupported-operator]

    if other_tokens > 0:
        other_sessions: set[str] = set()
        for entry in entries:
            if entry["tokens"] < threshold:
                data = model_map.get(entry["model"])
                if data:
                    other_sessions.update(data["sessions"])
        main.append({"model": "Other", "tokens": other_tokens, "sessions": len(other_sessions)})

    return main


# ---------------------------------------------------------------------------
# Chart aggregation: activity heatmap
# ---------------------------------------------------------------------------


def get_activity_heatmap(
    since: str | None = None,
    until: str | None = None,
    project_filter: str | None = None,
    projects_base: str | None = None,
) -> dict:
    sessions = list_sessions(
        projects_base=projects_base,
        project_filter=project_filter,
        since=since,
        until=until,
        sort="recency",
        limit=9999,
    )

    grid = [[0] * 24 for _ in range(7)]
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    hour_labels = [f"{i:02d}" for i in range(24)]

    for s in sessions:
        ts = parse_timestamp(s["started"] or s["lastActivity"])
        if not ts:
            continue
        day = ts.weekday()  # Python: 0=Mon .. 6=Sun (matches target directly)
        hour = ts.hour
        grid[day][hour] += 1

    max_value = max((v for row in grid for v in row), default=0)

    return {"grid": grid, "maxValue": max_value, "dayLabels": day_labels, "hourLabels": hour_labels}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _exit_with_error(err: Any, code: int) -> NoReturn:
    sys.stderr.write(to_json({"error": str(err), "code": code}) + "\n")
    sys.exit(code)


def _to_output_session(s: dict) -> dict:
    return {
        "session_id": s["sessionId"],
        "project": s["project"],
        "date": s["date"],
        "started": s["started"],
        "last_activity": s["lastActivity"],
        "messages": s["messages"],
        "duration_minutes": s["durationMinutes"],
        "size_bytes": s["sizeBytes"],
        "path": s["path"],
    }


def main() -> None:  # noqa: C901 — mirrors the original CLI's flat dispatch shape
    # Windows' default console codepage can't encode arbitrary Unicode (e.g. non-ASCII
    # characters in a user's message text); force UTF-8 so print()/stderr never crash on it.
    sys.stdout.reconfigure(encoding="utf-8")  # ty: ignore[unresolved-attribute]
    sys.stderr.reconfigure(encoding="utf-8")  # ty: ignore[unresolved-attribute]

    argv = sys.argv[1:]

    def get_flag(flag: str) -> str | None:
        if flag in argv:
            idx = argv.index(flag)
            if idx + 1 < len(argv):
                return argv[idx + 1]
        return None

    def get_flag_int(flag: str, default: int) -> int:
        v = get_flag(flag)
        if v is None:
            return default
        try:
            return int(v)
        except ValueError:
            return default

    since = get_flag("--since")
    until = get_flag("--until")
    format_flag = get_flag("--format") or ("json" if "--json" in argv else "table")
    projects_base = get_flag("--projects-base")
    tasks_base = get_flag("--tasks-base")

    # The subcommand must be argv[0] -- scanning for "the first token that doesn't
    # start with -" would misidentify a flag's own value (e.g. a session/task-list
    # ID starting with a dash-like token) as the subcommand.
    command = argv[0] if argv and not argv[0].startswith("-") else None

    if not command:
        sys.stderr.write(
            "Usage: python3 session_store.py <list|search|timeline|cleanup|tasks|task-lists|"
            "delete-session|delete-task|delete-task-list|orphan-task-lists|session-detail|"
            "current> ...\n"
        )
        sys.exit(1)

    try:
        if command == "list":
            project = get_flag("--project")
            sort = get_flag("--sort") or "recency"
            limit = get_flag_int("--limit", 20)
            sessions = list_sessions(
                project_filter=project,
                sort=sort,
                limit=limit,
                since=since,
                until=until,
                projects_base=projects_base,
            )
            out = [_to_output_session(s) for s in sessions]
            if format_flag == "table":
                print(
                    render_table(
                        out,
                        [
                            {"key": "session_id", "label": "SESSION ID", "width": 12},
                            {"key": "project", "label": "PROJECT", "width": 30},
                            {"key": "date", "label": "DATE"},
                            {"key": "messages", "label": "MSGS", "align": "right"},
                            {
                                "key": "duration_minutes",
                                "label": "DURATION",
                                "align": "right",
                                "format": lambda v: format_duration(v * 60),
                            },
                            {
                                "key": "size_bytes",
                                "label": "SIZE",
                                "align": "right",
                                "format": format_size,
                            },
                        ],
                    )
                )
            else:
                print(to_json(out))

        elif command == "search":
            cmd_idx = argv.index("search")
            query = argv[cmd_idx + 1] if cmd_idx + 1 < len(argv) else None
            if not query or query.startswith("-"):
                _exit_with_error("Missing search query", 2)
            project = get_flag("--project")
            limit = get_flag_int("--limit", 20)
            context = get_flag_int("--context", 0)
            results = search_sessions(
                query,
                project_filter=project,
                since=since,
                until=until,
                limit=limit,
                context=context,
                projects_base=projects_base,
            )
            out = [
                {
                    "session_id": r["sessionId"],
                    "project": r["project"],
                    "timestamp": r["timestamp"],
                    "type": r["type"],
                    "match": r["match"],
                    "context_before": r["contextBefore"],
                    "context_after": r["contextAfter"],
                }
                for r in results
            ]
            if format_flag == "table":
                print(
                    render_table(
                        out,
                        [
                            {"key": "session_id", "label": "SESSION ID", "width": 12},
                            {"key": "project", "label": "PROJECT", "width": 30},
                            {"key": "timestamp", "label": "TIMESTAMP", "width": 20},
                            {"key": "match", "label": "MATCH", "width": 60},
                        ],
                    )
                )
            else:
                print(to_ndjson(out) if out else to_json([]))

        elif command == "timeline":
            project = get_flag("--project")
            timeline = get_timeline(
                project_filter=project, since=since, until=until, projects_base=projects_base
            )
            out = [_to_output_session(s) for s in timeline]
            if format_flag == "table":
                print(
                    render_table(
                        out,
                        [
                            {"key": "session_id", "label": "SESSION ID", "width": 12},
                            {"key": "project", "label": "PROJECT", "width": 30},
                            {"key": "date", "label": "DATE"},
                            {"key": "messages", "label": "MSGS", "align": "right"},
                            {
                                "key": "duration_minutes",
                                "label": "DURATION",
                                "align": "right",
                                "format": lambda v: format_duration(v * 60),
                            },
                            {
                                "key": "size_bytes",
                                "label": "SIZE",
                                "align": "right",
                                "format": format_size,
                            },
                        ],
                    )
                )
            else:
                print(to_json(out))

        elif command == "cleanup":
            older_than = get_flag("--older-than")
            min_messages = get_flag_int("--min-messages", 3)
            candidates = find_cleanup_candidates(
                older_than=older_than, min_messages=min_messages, projects_base=projects_base
            )
            out = [
                {
                    "path": c["path"],
                    "session_id": c["sessionId"],
                    "project": c["project"],
                    "reason": c["reason"],
                    "messages": c["messages"],
                    "age_days": c["ageDays"],
                    "size_bytes": c["sizeBytes"],
                }
                for c in candidates
            ]
            total_size = sum(c["sizeBytes"] for c in candidates)
            print(
                to_json(
                    {"candidates": out, "total_size_bytes": total_size, "count": len(candidates)}
                )
            )

        elif command == "tasks":
            status = get_flag("--status") or "all"
            task_list_id = get_flag("--task-list")
            tasks = aggregate_tasks(
                status_filter=status,
                task_list_id=task_list_id,
                since=since,
                until=until,
                tasks_base=tasks_base,
                projects_base=projects_base,
            )
            out = []
            for t in tasks:
                t2 = dict(t)
                t2["task_list_id"] = t2.pop("taskListId", None)
                out.append(t2)
            if format_flag == "table":
                print(
                    render_table(
                        out,
                        [
                            {"key": "status", "label": "STATUS", "width": 12},
                            {"key": "subject", "label": "SUBJECT", "width": 40},
                            {"key": "task_list_id", "label": "SESSION", "width": 12},
                        ],
                    )
                )
            else:
                print(to_json(out))

        elif command == "task-lists":
            lists = list_task_lists(tasks_base)
            out = [
                {
                    "task_list_id": tl["taskListId"],
                    "task_count": tl["taskCount"],
                    "last_modified": tl["lastModified"],
                    "highwatermark": tl["highwatermark"],
                }
                for tl in lists
            ]
            print(to_json(out))

        elif command == "delete-session":
            cmd_idx = argv.index("delete-session")
            session_id = argv[cmd_idx + 1] if cmd_idx + 1 < len(argv) else None
            if not session_id or session_id.startswith("-"):
                _exit_with_error("Missing session ID", 2)
            delete_tasks = "--delete-tasks" in argv
            try:
                result = delete_session(
                    session_id,
                    projects_base=projects_base,
                    tasks_base=tasks_base,
                    delete_orphaned_tasks=delete_tasks,
                )
            except ValueError as err:
                _exit_with_error(err, 2)
            print(
                to_json(
                    {
                        "deleted": result["deleted"],
                        "session_path": result["sessionPath"],
                        "orphaned_task_lists": result["orphanedTaskLists"],
                        "orphaned_tasks_deleted": result["orphanedTasksDeleted"],
                    }
                )
            )

        elif command == "delete-task":
            cmd_idx = argv.index("delete-task")
            task_list_id = argv[cmd_idx + 1] if cmd_idx + 1 < len(argv) else None
            task_id = argv[cmd_idx + 2] if cmd_idx + 2 < len(argv) else None
            if not task_list_id or task_list_id.startswith("-"):
                _exit_with_error("Missing task list ID", 2)
            if not task_id or task_id.startswith("-"):
                _exit_with_error("Missing task ID", 2)
            try:
                result = delete_task(task_list_id, task_id, tasks_base=tasks_base)
            except ValueError as err:
                _exit_with_error(err, 2)
            print(
                to_json(
                    {
                        "deleted": result["deleted"],
                        "task_path": result["taskPath"],
                        "task_list_now_empty": result["taskListNowEmpty"],
                    }
                )
            )

        elif command == "delete-task-list":
            cmd_idx = argv.index("delete-task-list")
            task_list_id = argv[cmd_idx + 1] if cmd_idx + 1 < len(argv) else None
            if not task_list_id or task_list_id.startswith("-"):
                _exit_with_error("Missing task list ID", 2)
            try:
                result = delete_task_list(task_list_id, tasks_base=tasks_base)
            except ValueError as err:
                _exit_with_error(err, 2)
            print(
                to_json(
                    {
                        "deleted": result["deleted"],
                        "path": result["path"],
                        "task_count": result["taskCount"],
                    }
                )
            )

        elif command == "orphan-task-lists":
            orphans = find_orphan_task_lists(projects_base=projects_base, tasks_base=tasks_base)
            print(
                to_json(
                    [
                        {
                            "task_list_id": o["taskListId"],
                            "task_count": o["taskCount"],
                            "last_modified": o["lastModified"],
                            "path": o["path"],
                        }
                        for o in orphans
                    ]
                )
            )

        elif command == "session-detail":
            cmd_idx = argv.index("session-detail")
            session_id = argv[cmd_idx + 1] if cmd_idx + 1 < len(argv) else None
            if not session_id or session_id.startswith("-"):
                _exit_with_error("Missing session ID", 2)
            try:
                detail = get_session_detail(
                    session_id, projects_base=projects_base, tasks_base=tasks_base
                )
            except ValueError as err:
                _exit_with_error(err, 2)
            print(
                to_json(
                    {
                        "session": _to_output_session(detail["session"]),
                        "stats": detail["stats"],
                        "task_lists": [
                            {"task_list_id": tl["taskListId"], "tasks": tl["tasks"]}
                            for tl in detail["taskLists"]
                        ],
                    }
                )
            )

        elif command == "current":
            try:
                session_path = resolve_session(cwd=os.getcwd(), projects_base=projects_base)
            except ValueError as err:
                _exit_with_error(err, 2)
            summary = _get_session_summary(session_path)
            if summary is None:
                _exit_with_error(f"Could not read session file: {session_path}", 2)
            print(to_json(_to_output_session(summary)))

        else:
            _exit_with_error(f"Unknown command: {command}", 3)

    except FileNotFoundError as err:
        _exit_with_error(f"File or directory not found: {err}", 2)
    except PermissionError as err:
        _exit_with_error(f"Permission denied: {err}", 2)
    except SystemExit:
        raise
    except Exception as err:  # noqa: BLE001
        _exit_with_error(err, 3)


if __name__ == "__main__":
    main()
