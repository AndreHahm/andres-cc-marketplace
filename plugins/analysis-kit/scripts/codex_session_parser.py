#!/usr/bin/env python3
"""Defensive parser for a Codex CLI session/transcript file.

Codex's on-disk session format is not independently confirmed the way
Claude Code's own session JSONL format is (see session_parser.py's
docstring, which was grounded against a real file). This script does not
guess at an unconfirmed schema -- it attempts a small number of plausible
parses (JSON array/object, then line-delimited JSON) and only emits a
normalized result when the parsed structure actually contains fields this
script can identify with reasonable confidence (a role-and-content shape,
or a role-and-text shape). Anything else is reported as an explicit
unparseable/unknown-format error rather than a fabricated best guess.

On success, emits the same normalized event-list shape as
session_parser.py's per-session result, so a calling skill can treat
either script's output identically.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


class UnrecognizedFormatError(Exception):
    pass


def _normalize_record(record: dict, sequence: int) -> dict | None:
    role = record.get("role") or record.get("author") or record.get("speaker")
    content = record.get("content") or record.get("text") or record.get("message")
    timestamp = record.get("timestamp") or record.get("time") or record.get("ts")
    usage = record.get("usage") if isinstance(record.get("usage"), dict) else None

    if role is None and content is None:
        return None

    return {
        "sequence": sequence,
        "timestamp": timestamp,
        "role": role,
        "is_subagent": bool(record.get("is_subagent", False)),
        "tool_calls": [],
        "text_length": len(content) if isinstance(content, str) else 0,
        "usage": {
            "input_tokens": usage.get("input_tokens") if usage else None,
            "output_tokens": usage.get("output_tokens") if usage else None,
            "cache_read_input_tokens": usage.get("cache_read_input_tokens") if usage else None,
            "cache_creation_input_tokens": usage.get("cache_creation_input_tokens") if usage else None,
        } if usage else None,
    }


def parse_codex_session(path: Path) -> dict:
    raw = path.read_text(encoding="utf-8")

    records: list[dict] = []
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, list):
            records = [r for r in parsed if isinstance(r, dict)]
        elif isinstance(parsed, dict):
            for key in ("events", "messages", "entries", "transcript"):
                if isinstance(parsed.get(key), list):
                    records = [r for r in parsed[key] if isinstance(r, dict)]
                    break
            if not records:
                records = [parsed]
    except json.JSONDecodeError:
        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(record, dict):
                records.append(record)

    if not records:
        raise UnrecognizedFormatError("file did not parse as JSON, a JSON array/object, or line-delimited JSON")

    events = []
    sequence = 0
    for record in records:
        sequence += 1
        normalized = _normalize_record(record, sequence)
        if normalized:
            events.append(normalized)

    if not events:
        raise UnrecognizedFormatError(
            "parsed records did not contain a recognizable role/content or role/text shape"
        )

    timestamps = [e["timestamp"] for e in events if e["timestamp"]]

    return {
        "provenance": {
            "source_file": str(path),
            "session_id": None,
            "timestamp_range": {
                "start": min(timestamps) if timestamps else None,
                "end": max(timestamps) if timestamps else None,
            },
            "lines_parsed": len(records),
            "lines_skipped": len(records) - len(events),
        },
        "events": events,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--session-file", required=True, help="Path to the Codex session/transcript file")
    args = parser.parse_args()

    path = Path(args.session_file).resolve()
    if not path.is_file():
        json.dump({"error": "file_not_found", "detail": str(path)}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 1

    try:
        result = parse_codex_session(path)
    except UnrecognizedFormatError as exc:
        json.dump({"error": "unparseable_or_unknown_format", "detail": str(exc)}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 1
    except (OSError, UnicodeDecodeError) as exc:
        json.dump({"error": "read_error", "detail": str(exc)}, sys.stdout, indent=2)
        sys.stdout.write("\n")
        return 1

    json.dump(result, sys.stdout, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
