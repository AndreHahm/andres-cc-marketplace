#!/usr/bin/env python3
"""Core JSONL parser for Claude Code sessions.

Reads a single session JSONL file and provides structured data extraction.

Usage as CLI:
  python3 session_transcript.py stats <session.jsonl>
  python3 session_transcript.py tasks <session.jsonl>
  python3 session_transcript.py export <session.jsonl> [--format md|txt] [--include-tools]
                                        [--output FILE]
  python3 session_transcript.py resume <session.jsonl>
  python3 session_transcript.py diff <session-a.jsonl> <session-b.jsonl>
  python3 session_transcript.py messages <session.jsonl> [--offset N] [--limit N] [--include-tools]
  python3 session_transcript.py errors <session.jsonl>
  python3 session_transcript.py irritation <session.jsonl>
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, NoReturn

sys.path.insert(0, str(Path(__file__).resolve().parent))

from formatters import parse_timestamp, to_json, truncate  # noqa: E402

# Correction phrases indicating the user is pushing back on prior assistant work.
CORRECTION_PHRASES = ["wrong", "stop", "undo", "revert", "no,", "that's not"]

# Consecutive identical tool calls at or above this count are treated as a stuck loop.
STUCK_LOOP_THRESHOLD = 3

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def read_lines(path: str) -> list[dict]:
    """Read a JSONL file line by line, skipping malformed lines.

    Logs a warning to stderr for each skipped line.
    """
    with open(path, encoding="utf-8") as f:
        content = f.read()

    results = []
    for i, raw_line in enumerate(content.split("\n")):
        line = raw_line.strip()
        if not line:
            continue
        try:
            results.append(json.loads(line))
        except json.JSONDecodeError:
            sys.stderr.write(
                to_json({"warning": f"Skipped malformed line {i + 1}", "file": path}) + "\n"
            )

    return results


def extract_user_text(msg_obj: dict) -> str:
    """Extract text content from a user message object.

    Handles string, dict, and array content formats.
    """
    content = msg_obj.get("message", "")

    if isinstance(content, dict):
        content = content.get("content", "")

    if isinstance(content, str):
        return content.strip()

    if isinstance(content, list):
        parts = []
        for part in content:
            if isinstance(part, dict) and part.get("type") == "text":
                parts.append(str(part.get("text", "")).strip())
        return " ".join(parts)

    return ""


def is_system_message(text: str) -> bool:
    """Check if a user message is a system/command injection, not real user input."""
    return text.startswith("<local-command") or text.startswith("<command-name>")


def message_dict(obj: dict) -> dict:
    """The record's `message` field as a dict, or {} if it isn't one.

    `message` is a dict for every real assistant record, but not guaranteed --
    extract_user_text() already treats a bare-string `message` as a possible shape
    for user records. `(obj.get("message") or {}).get(...)` crashes with
    AttributeError on that shape (a non-empty string is truthy, so `or {}` never
    triggers); this coerces any non-dict value to {} first.
    """
    msg = obj.get("message")
    return msg if isinstance(msg, dict) else {}


# ---------------------------------------------------------------------------
# Exported functions
# ---------------------------------------------------------------------------


def parse_session(path: str) -> dict:
    """Parse a full session JSONL into structured data."""
    messages_by_type: dict[str, list[dict]] = {}
    all_messages: list[dict] = []
    session_id: str | None = None
    timestamps: list[str] = []

    for obj in read_lines(path):
        msg_type = obj.get("type")
        if msg_type is None:
            continue

        if session_id is None:
            session_id = obj.get("sessionId")

        ts = obj.get("timestamp")
        if ts:
            timestamps.append(ts)

        entry = {"type": msg_type, "timestamp": ts, "uuid": obj.get("uuid"), "raw": obj}

        all_messages.append(entry)
        messages_by_type.setdefault(msg_type, []).append(entry)

    stem = Path(path).stem

    return {
        "session_id": session_id or stem,
        "path": path,
        "message_count": len(all_messages),
        "messages_by_type": messages_by_type,
        "messages": all_messages,
        "first_timestamp": timestamps[0] if timestamps else None,
        "last_timestamp": timestamps[-1] if timestamps else None,
    }


def get_stats(path: str) -> dict:
    """Extract token usage, model distribution, tool counts, and duration."""
    token_counts = {"input": 0, "output": 0, "cache_read": 0, "cache_create": 0}
    models: dict[str, int] = {}
    tool_counts: dict[str, int] = {}
    user_count = 0
    assistant_count = 0
    is_resumed = False
    timestamps: list[str] = []
    session_id: str | None = None
    cwd: str | None = None

    for obj in read_lines(path):
        msg_type = obj.get("type")
        ts = obj.get("timestamp")
        if ts:
            timestamps.append(ts)
        if session_id is None:
            session_id = obj.get("sessionId")
        if cwd is None and obj.get("cwd"):
            cwd = obj.get("cwd")

        if msg_type == "user":
            text = extract_user_text(obj)
            if text and not is_system_message(text):
                user_count += 1
        elif msg_type == "assistant":
            assistant_count += 1
            msg = message_dict(obj)

            # Resumed session detection.
            # Claude Code's --resume/--continue creates a NEW JSONL file with no standard
            # metadata linking back to the parent session (no resumed_from, no parent_session_id).
            # We detect resumed sessions heuristically using three signals (in order of
            # reliability):
            #
            # 1. (Used here) An assistant message with model:"<synthetic>", isApiErrorMessage:false,
            #    and content text "No response requested." — a resume bridge message injected by
            #    Claude Code to maintain message chain continuity.
            # 2. A type:"last-prompt" entry with lastPrompt:"continue" — written when the user
            #    runs `claude --continue`.
            # 3. The startup triplet (custom-title + agent-name + permission-mode) appearing
            #    mid-file rather than only at the start — indicates a CLI reconnection.
            #
            # Signal #1 is the most reliable and sufficient on its own.
            if msg.get("model") == "<synthetic>" and not msg.get("isApiErrorMessage"):
                resume_content = msg.get("content") or []
                if isinstance(resume_content, list):
                    for block in resume_content:
                        if (
                            isinstance(block, dict)
                            and block.get("type") == "text"
                            and block.get("text") == "No response requested."
                        ):
                            is_resumed = True

            model = msg.get("model") or "unknown"
            models[model] = models.get(model, 0) + 1

            usage = msg.get("usage") or {}
            token_counts["input"] += usage.get("input_tokens") or 0
            token_counts["output"] += usage.get("output_tokens") or 0
            token_counts["cache_read"] += usage.get("cache_read_input_tokens") or 0
            token_counts["cache_create"] += usage.get("cache_creation_input_tokens") or 0

            content = msg.get("content") or []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_name = block.get("name") or "unknown"
                        tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1

    # Duration
    duration_minutes = 0.0
    first_ts_str: str | None = None
    last_ts_str: str | None = None

    if timestamps:
        first_ts_str = str(timestamps[0])
        last_ts_str = str(timestamps[-1])
        first_dt = parse_timestamp(timestamps[0])
        last_dt = parse_timestamp(timestamps[-1])
        if first_dt and last_dt:
            duration_minutes = round(((last_dt - first_dt).total_seconds() / 60) * 10) / 10

    # Sort tools by count descending
    sorted_tools = dict(sorted(tool_counts.items(), key=lambda kv: kv[1], reverse=True))

    stem = Path(path).stem

    return {
        "session_id": session_id or stem,
        "turns": user_count + assistant_count,
        "user_messages": user_count,
        "assistant_messages": assistant_count,
        "duration_minutes": duration_minutes,
        "models": models,
        "tokens": token_counts,
        "tools": sorted_tools,
        "first_message": first_ts_str,
        "last_message": last_ts_str,
        "cwd": cwd,
        "is_resumed": is_resumed,
    }


def get_errors(path: str) -> dict:
    """List tool errors from a session: timestamps, tool names, and error content.

    Two-pass: assistant tool_use blocks map tool-use IDs to tool names, then user
    tool_result blocks with is_error resolve each error to its originating tool.
    """
    tool_names: dict[str, str] = {}
    errors: list[dict] = []

    for obj in read_lines(path):
        msg_type = obj.get("type")
        content = message_dict(obj).get("content") or []
        if not isinstance(content, list):
            continue

        if msg_type == "assistant":
            for block in content:
                if isinstance(block, dict) and block.get("type") == "tool_use":
                    tool_names[block.get("id", "")] = block.get("name", "unknown")
        elif msg_type == "user":
            for block in content:
                if not (isinstance(block, dict) and block.get("type") == "tool_result"):
                    continue
                if not block.get("is_error"):
                    continue
                result_content = block.get("content", "")
                if isinstance(result_content, list):
                    result_content = " ".join(
                        str(b.get("text", "")) for b in result_content if isinstance(b, dict)
                    )
                errors.append(
                    {
                        "timestamp": obj.get("timestamp"),
                        "tool_name": tool_names.get(block.get("tool_use_id", ""), "unknown"),
                        "error_content": truncate(str(result_content), 500),
                    }
                )

    return {"error_count": len(errors), "errors": errors}


def get_irritation_signals(path: str) -> dict:
    """Detect user frustration signals: correction phrases and stuck tool-call loops.

    Correction phrases are case-insensitive substring matches against a fixed list
    ("wrong", "stop", "undo", etc.) in user message text. A stuck loop is 3+
    consecutive identical tool calls (same tool name and input) in assistant messages,
    with no genuine human message in between -- a bare tool-result entry (the normal,
    expected gap between one tool call and the next) doesn't break the run, but a real
    user-authored message does, since that means a human turn happened between the
    calls rather than the assistant retrying unattended.
    """
    corrections: list[dict] = []
    stuck_loops: list[dict] = []
    run_key: tuple[str, str] | None = None
    run_length = 0

    def flush_run() -> None:
        nonlocal run_key, run_length
        if run_key is not None and run_length >= STUCK_LOOP_THRESHOLD:
            stuck_loops.append({"tool_name": run_key[0], "count": run_length})
        run_key = None
        run_length = 0

    for obj in read_lines(path):
        msg_type = obj.get("type")

        if msg_type == "user":
            text = extract_user_text(obj)
            if text and not is_system_message(text):
                flush_run()
                lower = text.lower()
                for phrase in CORRECTION_PHRASES:
                    if phrase in lower:
                        corrections.append(
                            {
                                "timestamp": obj.get("timestamp"),
                                "phrase": phrase,
                                "excerpt": truncate(text, 200),
                            }
                        )
                        break

        elif msg_type == "assistant":
            content = message_dict(obj).get("content") or []
            if not isinstance(content, list):
                continue
            for block in content:
                if not (isinstance(block, dict) and block.get("type") == "tool_use"):
                    continue
                key = (
                    block.get("name", "unknown"),
                    json.dumps(block.get("input", {}), sort_keys=True),
                )
                if key == run_key:
                    run_length += 1
                else:
                    flush_run()
                    run_key = key
                    run_length = 1

    flush_run()

    return {
        "correction_count": len(corrections),
        "corrections": corrections,
        "stuck_loop_count": len(stuck_loops),
        "stuck_loops": stuck_loops,
    }


def get_tasks(path: str) -> list[dict]:
    """Extract tasks from TaskCreate/TaskUpdate tool_use blocks."""
    tasks = []

    for obj in read_lines(path):
        if obj.get("type") != "assistant":
            continue
        content = message_dict(obj).get("content") or []
        if not isinstance(content, list):
            continue

        for block in content:
            if not isinstance(block, dict) or block.get("type") != "tool_use":
                continue
            name = block.get("name", "")
            inp = block.get("input") or {}

            if name == "TaskCreate":
                tasks.append(
                    {
                        "action": "create",
                        "description": inp.get("description", ""),
                        "subject": inp.get("subject", ""),
                        "session_id": obj.get("sessionId"),
                        "timestamp": obj.get("timestamp"),
                    }
                )
            elif name == "TaskUpdate":
                tasks.append(
                    {
                        "action": "update",
                        # Real TaskUpdate input has been observed using both "taskId" and
                        # "task_id" across sessions -- Claude Code's own docs note it may
                        # repair misformatted input keys without that repair showing up in
                        # the raw tool_use stream, so this reads either defensively rather
                        # than assuming one casing. Reading only "taskId" (the prior
                        # behavior) silently dropped every update whose real input used
                        # "task_id" instead, since the lookup below matches on this value.
                        "task_id": inp.get("taskId") or inp.get("task_id"),
                        "status": inp.get("status", ""),
                        "session_id": obj.get("sessionId"),
                        "timestamp": obj.get("timestamp"),
                    }
                )

    return tasks


def merge_task_events(
    raw_tasks: list[dict], task_list_id: str, default_status: str | None = None
) -> list[dict]:
    """
    Fold a raw create/update event stream (from get_tasks()) into one entry per
    task: each "create" gets a synthetic id, later "update" events for that id
    are folded into it, and orphan updates (no matching create) are dropped.

    default_status, when given, is applied to a create that never received an
    explicit status of its own -- without it, a create-only task carries no
    status field at all, which silently excludes it from any status-filtered view.
    """
    created: dict[str, dict] = {}
    merged: list[dict] = []
    next_id = 1
    for t in raw_tasks:
        entry = dict(t)
        entry["taskListId"] = task_list_id
        entry["source"] = "jsonl"
        if t.get("action") == "create":
            task_id = str(next_id)
            next_id += 1
            entry["id"] = task_id
            entry["task_id"] = task_id
            if default_status and not entry.get("status"):
                entry["status"] = default_status
            created[task_id] = entry
            merged.append(entry)
        elif t.get("action") == "update" and t.get("task_id") in created:
            if t.get("status"):
                created[t["task_id"]]["status"] = t["status"]
        # Skip orphan updates (no matching create)
    return merged


def get_messages(path: str, type_filter: str | None = None) -> list[dict]:
    """Get messages, optionally filtered by type."""
    messages = []

    for obj in read_lines(path):
        msg_type = obj.get("type")
        if type_filter and msg_type != type_filter:
            continue
        if msg_type not in ("user", "assistant", "system"):
            continue

        entry: dict[str, Any] = {
            "type": msg_type,
            "timestamp": obj.get("timestamp"),
            "uuid": obj.get("uuid"),
        }

        if msg_type == "user":
            entry["text"] = extract_user_text(obj)
            if not entry["text"]:
                continue
        elif msg_type == "assistant":
            msg = message_dict(obj)
            text_parts = []
            tool_names = []
            content = msg.get("content") or []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            tool_names.append(block.get("name", ""))
            entry["text"] = " ".join(text_parts)
            entry["tools"] = tool_names
            entry["model"] = msg.get("model") or "unknown"

        messages.append(entry)

    return messages


def get_messages_paginated(
    path: str,
    offset: int = 0,
    limit: int = 100,
    type_filter: str | None = None,
    include_tools: bool = False,
) -> dict:
    """Get paginated messages from a session.

    Optionally includes tool call details (name + truncated input).
    """
    all_messages = []

    for obj in read_lines(path):
        msg_type = obj.get("type")
        if type_filter and msg_type != type_filter:
            continue
        if msg_type not in ("user", "assistant", "system"):
            continue

        entry: dict[str, Any] = {
            "type": msg_type,
            "timestamp": obj.get("timestamp"),
            "uuid": obj.get("uuid"),
        }

        if msg_type == "user":
            entry["text"] = extract_user_text(obj)
            # Skip tool_result-only messages (system-injected, not real user input)
            if not entry["text"]:
                continue
        elif msg_type == "assistant":
            msg = message_dict(obj)
            text_parts = []
            tool_names = []
            tool_details_list = []
            content = msg.get("content") or []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict):
                        if block.get("type") == "text":
                            text_parts.append(block.get("text", ""))
                        elif block.get("type") == "tool_use":
                            tool_names.append(block.get("name", ""))
                            if include_tools:
                                tool_details_list.append(
                                    {
                                        "name": block.get("name") or "unknown",
                                        "input": truncate(
                                            json.dumps(block.get("input") or {}), 200
                                        ),
                                    }
                                )
            entry["text"] = " ".join(text_parts)
            entry["tools"] = tool_names
            if include_tools and tool_details_list:
                entry["toolDetails"] = tool_details_list
            entry["model"] = msg.get("model") or "unknown"

        all_messages.append(entry)

    total = len(all_messages)
    paged = all_messages[offset : offset + limit]

    return {
        "messages": paged,
        "total": total,
        "hasMore": offset + limit < total,
        "offset": offset,
    }


def export_transcript(path: str, fmt: str = "md", include_tools: bool = True) -> str:
    """Export session as clean markdown or plain text transcript."""
    messages = get_messages(path)
    lines: list[str] = []

    if fmt == "md":
        lines.append("# Session Transcript\n")

    for msg in messages:
        ts = msg.get("timestamp") or ""
        if isinstance(ts, str) and len(ts) > 16:
            ts = ts[:16]

        if msg["type"] == "user":
            text = msg.get("text") or ""
            if is_system_message(text):
                continue
            if fmt == "md":
                lines.append(f"## User ({ts})\n")
                lines.append(f"{text}\n")
            else:
                lines.append(f"[{ts}] User: {text}\n")
        elif msg["type"] == "assistant":
            text = msg.get("text") or ""
            tool_list = msg.get("tools") or []
            model = msg.get("model") or ""

            if fmt == "md":
                lines.append(f"## Assistant ({ts}) [{model}]\n")
                if text:
                    lines.append(f"{text}\n")
                if include_tools and tool_list:
                    lines.append(f"*Tools used: {', '.join(tool_list)}*\n")
            else:
                lines.append(f"[{ts}] Assistant [{model}]: {text}")
                if include_tools and tool_list:
                    lines.append(f"  Tools: {', '.join(tool_list)}")
                lines.append("")

    return "\n".join(lines)


# Tools whose file_path input means the file was actually changed, not just read --
# a Read/Glob/Grep call also carries a file_path input, and including those would
# misreport a session that only inspected a file as having modified it.
MUTATING_FILE_TOOLS = {"Write", "Edit", "NotebookEdit"}


def get_resume_data(path: str) -> dict:
    """Extract data needed to resume/continue a past session."""
    stats = get_stats(path)
    tasks = merge_task_events(get_tasks(path), stats["session_id"], default_status="pending")
    files: set[str] = set()
    last_branch: str | None = None
    last_user_messages: list[str] = []
    git_commits: list[str] = []

    for obj in read_lines(path):
        msg_type = obj.get("type")
        branch = obj.get("gitBranch")
        if branch:
            # Track the last-observed branch in file order, not the alphabetically
            # greatest one -- a session that starts on "main" and ends on "feature/x"
            # must report "feature/x" as where the work actually left off.
            last_branch = branch

        if msg_type == "user":
            text = extract_user_text(obj)
            if text and not is_system_message(text):
                last_user_messages.append(truncate(text, 300))
        elif msg_type == "assistant":
            content = message_dict(obj).get("content") or []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        inp = block.get("input") or {}
                        name = block.get("name", "")
                        fp = inp.get("file_path", "")
                        if fp and name in MUTATING_FILE_TOOLS:
                            files.add(fp)
                        if name == "Bash":
                            cmd = inp.get("command", "")
                            if "git commit" in cmd:
                                git_commits.append(truncate(cmd, 200))

    return {
        "session_id": stats["session_id"],
        "project": str(Path(path).parent),
        "date_range": f"{stats['first_message']} - {stats['last_message']}",
        "branch": last_branch or "unknown",
        "files_modified": sorted(files),
        "last_user_messages": last_user_messages[-5:],
        "tool_calls_summary": stats["tools"],
        "tasks": tasks,
        "git_commits": git_commits,
    }


def get_diff_data(path: str) -> dict:
    """Extract data from a single session for diffing against another."""
    stats = get_stats(path)
    files: set[str] = set()
    branches: set[str] = set()
    first_user_messages: list[str] = []

    for obj in read_lines(path):
        branch = obj.get("gitBranch")
        if branch:
            branches.add(branch)

        if obj.get("type") == "user":
            text = extract_user_text(obj)
            if text and not is_system_message(text) and len(first_user_messages) < 3:
                first_user_messages.append(truncate(text, 200))
        elif obj.get("type") == "assistant":
            content = message_dict(obj).get("content") or []
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        name = block.get("name", "")
                        fp = (block.get("input") or {}).get("file_path", "")
                        if fp and name in MUTATING_FILE_TOOLS:
                            files.add(fp)

    return {
        "id": stats["session_id"],
        "date": stats["first_message"],
        "messages": stats["turns"],
        "files": sorted(files),
        "branches": sorted(branches),
        "tools": stats["tools"],
        "first_user_messages": first_user_messages,
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _exit_with_error(err: Any, code: int) -> NoReturn:
    sys.stderr.write(to_json({"error": str(err), "code": code}) + "\n")
    sys.exit(code)


def _handle_os_error(err: OSError, path_hint: str) -> None:
    if isinstance(err, FileNotFoundError):
        _exit_with_error(f"File or directory not found: {err}", 2)
    elif isinstance(err, PermissionError):
        _exit_with_error(f"Permission denied: {err}", 2)
    else:
        _exit_with_error(err, 3)


def main() -> None:
    # Windows' default console codepage can't encode arbitrary Unicode (e.g. non-ASCII
    # characters in a user's message text); force UTF-8 so print()/stderr never crash on it.
    sys.stdout.reconfigure(encoding="utf-8")  # ty: ignore[unresolved-attribute]
    sys.stderr.reconfigure(encoding="utf-8")  # ty: ignore[unresolved-attribute]

    args = sys.argv[1:]
    command = args[0] if args else None

    if not command:
        sys.stderr.write(
            "Usage: python3 session_transcript.py "
            "<stats|tasks|export|resume|diff|messages|errors|irritation> ...\n"
        )
        sys.exit(1)

    try:
        if command == "stats":
            session_path = args[1] if len(args) > 1 else None
            if not session_path:
                _exit_with_error("Missing session path", 2)
            print(to_json(get_stats(session_path)))
        elif command == "tasks":
            session_path = args[1] if len(args) > 1 else None
            if not session_path:
                _exit_with_error("Missing session path", 2)
            # get_tasks() returns the raw create/update event stream -- a TaskCreate
            # commonly has no status of its own, and an unfused stream can't tell a
            # completed task from a still-pending one. Fuse it into one current-state
            # entry per task before printing, same as session_store.py's own JSONL
            # fallback already does when aggregating tasks.
            raw_tasks = get_tasks(session_path)
            merged = merge_task_events(raw_tasks, Path(session_path).stem, default_status="pending")
            print(to_json(merged))
        elif command == "export":
            session_path = args[1] if len(args) > 1 else None
            if not session_path:
                _exit_with_error("Missing session path", 2)

            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument("--format", choices=["md", "txt"], default="md")
            parser.add_argument(
                "--include-tools", dest="include_tools", action="store_true", default=True
            )
            parser.add_argument("--no-include-tools", dest="include_tools", action="store_false")
            parser.add_argument("--output", default=None)
            opts, _ = parser.parse_known_args(args[2:])

            transcript = export_transcript(session_path, opts.format, opts.include_tools)
            if opts.output:
                with open(opts.output, "w", encoding="utf-8") as f:
                    f.write(transcript)
                print(
                    json.dumps(
                        {
                            "status": "ok",
                            "path": opts.output,
                            "lines": len(transcript.rstrip("\n").split("\n")),
                        }
                    )
                )
            else:
                print(transcript)
        elif command == "resume":
            session_path = args[1] if len(args) > 1 else None
            if not session_path:
                _exit_with_error("Missing session path", 2)
            print(to_json(get_resume_data(session_path)))
        elif command == "diff":
            session_a = args[1] if len(args) > 1 else None
            session_b = args[2] if len(args) > 2 else None
            if not session_a or not session_b:
                _exit_with_error("Missing session paths", 2)

            data_a = get_diff_data(session_a)
            data_b = get_diff_data(session_b)
            files_a = set(data_a["files"])
            files_b = set(data_b["files"])

            result = {
                "session_a": data_a,
                "session_b": data_b,
                "files_added": sorted(files_b - files_a),
                "files_dropped": sorted(files_a - files_b),
                "files_common": sorted(files_a & files_b),
            }
            print(to_json(result))
        elif command == "messages":
            session_path = args[1] if len(args) > 1 else None
            if not session_path:
                _exit_with_error("Missing session path", 2)

            parser = argparse.ArgumentParser(add_help=False)
            parser.add_argument("--offset", type=int, default=0)
            parser.add_argument("--limit", type=int, default=100)
            parser.add_argument(
                "--include-tools", dest="include_tools", action="store_true", default=False
            )
            opts, _ = parser.parse_known_args(args[2:])

            result = get_messages_paginated(
                session_path, offset=opts.offset, limit=opts.limit, include_tools=opts.include_tools
            )
            print(to_json(result))
        elif command == "errors":
            session_path = args[1] if len(args) > 1 else None
            if not session_path:
                _exit_with_error("Missing session path", 2)
            print(to_json(get_errors(session_path)))
        elif command == "irritation":
            session_path = args[1] if len(args) > 1 else None
            if not session_path:
                _exit_with_error("Missing session path", 2)
            print(to_json(get_irritation_signals(session_path)))
        else:
            _exit_with_error(f"Unknown command: {command}", 3)
    except OSError as err:
        _handle_os_error(err, args[1] if len(args) > 1 else "")
    except SystemExit:
        raise
    except Exception as err:  # noqa: BLE001
        _exit_with_error(err, 3)


if __name__ == "__main__":
    main()
