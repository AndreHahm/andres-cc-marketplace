#!/usr/bin/env python3
"""Deterministic parser for Claude Code's own local session JSONL files.

Locates and parses session transcripts under `~/.claude/projects/<encoded-cwd>/`,
where <encoded-cwd> replaces every ":" and path separator in the project's
absolute path with "-" (e.g. "C:\\Dev\\Repos\\foo" -> "C--Dev-Repos-foo").
This encoding was confirmed against real session directories on disk, not
guessed.

Emits a light normalized event list plus light provenance (source file,
session id, timestamp range, parse counts) -- deliberately no per-event
byte-offset/ID provenance system. Malformed lines are skipped and counted,
never fabricated into a result. Fields the source line doesn't carry stay
null/omitted, matching this plugin's existing token_time_aggregator.py
honesty convention.

Session JSONL line shapes actually observed (subset relevant to this parser):
  {"type": "user", "message": {"role": "user", "content": ...}, "timestamp": ..., "sessionId": ..., "isSidechain": bool, "uuid": ..., "parentUuid": ...}
  {"type": "assistant", "message": {"role": "assistant", "content": [...], "usage": {...}}, "timestamp": ..., ...}
  {"type": "queue-operation", ...} / {"type": "attachment", ...}  -- not events this script emits, skipped
content blocks within message.content can include {"type": "tool_use", "name": ..., "input": ...}
and {"type": "tool_result", "tool_use_id": ..., "content": ...}.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

EMITTED_TYPES = {"user", "assistant"}


def encode_project_path(project_root: Path) -> str:
    raw = str(project_root.resolve())
    encoded = []
    for ch in raw:
        if ch in (":", "\\", "/"):
            encoded.append("-")
        else:
            encoded.append(ch)
    return "".join(encoded)


def claude_projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def discover_session_files(project_root: Path) -> list[Path]:
    encoded = encode_project_path(project_root)
    session_dir = claude_projects_dir() / encoded
    if not session_dir.is_dir():
        return []
    return sorted(session_dir.glob("*.jsonl"), key=lambda p: p.stat().st_mtime)


def _parse_ts(ts: str | None) -> datetime | None:
    if not ts:
        return None
    try:
        return datetime.fromisoformat(ts.replace("Z", "+00:00"))
    except ValueError:
        return None


def _extract_tool_calls(content) -> list[dict]:
    calls = []
    if not isinstance(content, list):
        return calls
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "tool_use":
            calls.append({"tool_name": block.get("name"), "tool_use_id": block.get("id")})
    return calls


def _extract_text_len(content) -> int:
    if isinstance(content, str):
        return len(content)
    if not isinstance(content, list):
        return 0
    total = 0
    for block in content:
        if isinstance(block, dict) and block.get("type") == "text":
            total += len(block.get("text", "") or "")
    return total


def parse_session_file(path: Path, since: datetime | None, until: datetime | None) -> dict:
    events = []
    lines_parsed = 0
    lines_skipped = 0
    session_id = None
    timestamps: list[datetime] = []
    sequence = 0

    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                lines_skipped += 1
                continue

            record_type = record.get("type")
            if record_type not in EMITTED_TYPES:
                lines_parsed += 1
                continue

            ts = _parse_ts(record.get("timestamp"))
            if since and ts and ts < since:
                lines_parsed += 1
                continue
            if until and ts and ts > until:
                lines_parsed += 1
                continue

            message = record.get("message") or {}
            role = message.get("role")
            content = message.get("content")
            usage = message.get("usage") if record_type == "assistant" else None

            sequence += 1
            event = {
                "sequence": sequence,
                "timestamp": record.get("timestamp"),
                "role": role,
                "is_subagent": bool(record.get("isSidechain", False)),
                "tool_calls": _extract_tool_calls(content),
                "text_length": _extract_text_len(content),
                "usage": {
                    "input_tokens": usage.get("input_tokens") if usage else None,
                    "output_tokens": usage.get("output_tokens") if usage else None,
                    "cache_read_input_tokens": usage.get("cache_read_input_tokens") if usage else None,
                    "cache_creation_input_tokens": usage.get("cache_creation_input_tokens") if usage else None,
                } if usage else None,
            }
            events.append(event)
            lines_parsed += 1
            if record.get("sessionId"):
                session_id = record["sessionId"]
            if ts:
                timestamps.append(ts)

    def _iso(dt: datetime) -> str:
        return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "provenance": {
            "source_file": str(path),
            "session_id": session_id,
            "timestamp_range": {
                "start": _iso(min(timestamps)) if timestamps else None,
                "end": _iso(max(timestamps)) if timestamps else None,
            },
            "lines_parsed": lines_parsed,
            "lines_skipped": lines_skipped,
        },
        "events": events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-root", default=".", help="Project root used to locate the session directory (default: current directory)")
    parser.add_argument("--session-file", default=None, help="Parse this specific session JSONL file instead of auto-discovering")
    parser.add_argument("--since", default=None, help="ISO date/datetime lower bound (inclusive) on event timestamps")
    parser.add_argument("--until", default=None, help="ISO date/datetime upper bound (inclusive) on event timestamps")
    args = parser.parse_args()

    since = _parse_ts(args.since + "T00:00:00Z" if args.since and "T" not in args.since else args.since)
    until = _parse_ts(args.until + "T23:59:59Z" if args.until and "T" not in args.until else args.until)

    if args.session_file:
        files = [Path(args.session_file).resolve()]
    else:
        files = discover_session_files(Path(args.project_root))

    if not files:
        json.dump({
            "provenance": {"source_file": None, "session_id": None, "timestamp_range": {"start": None, "end": None}, "lines_parsed": 0, "lines_skipped": 0},
            "events": [],
            "error": "no_session_files_found",
        }, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 1

    results = []
    for f in files:
        try:
            results.append(parse_session_file(f, since, until))
        except (OSError, UnicodeDecodeError) as exc:
            results.append({
                "provenance": {"source_file": str(f), "session_id": None, "timestamp_range": {"start": None, "end": None}, "lines_parsed": 0, "lines_skipped": 0},
                "events": [],
                "error": str(exc),
            })

    all_events = [e for r in results for e in r["events"]]
    total_input = sum(e["usage"]["input_tokens"] or 0 for e in all_events if e.get("usage") and e["usage"].get("input_tokens") is not None)
    total_output = sum(e["usage"]["output_tokens"] or 0 for e in all_events if e.get("usage") and e["usage"].get("output_tokens") is not None)

    json.dump({
        "sessions": results,
        "summary": {
            "session_files": len(files),
            "event_count": len(all_events),
            "assistant_turns": sum(1 for e in all_events if e["role"] == "assistant"),
            "tool_calls": sum(len(e["tool_calls"]) for e in all_events),
            "total_input_tokens": total_input,
            "total_output_tokens": total_output,
        },
    }, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
