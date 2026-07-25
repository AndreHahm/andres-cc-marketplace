#!/usr/bin/env python3
# /// script
# requires-python = ">=3.8"
# ///
# Reads/updates plugin-rulebook/assets/agent-cost-history.json -- a
# best-effort registry of observed Agent() dispatch cost (tokens,
# duration), used to surface a rough estimate in an R26 AskUserQuestion
# gate before dispatching an expensive action. See overhead-and-cost-rules.md
# "Cost-Tier Estimation Before Dispatch" for when to call this.
#
# Usage:
#   agent-cost-tracker.py estimate <agent-name>
#   agent-cost-tracker.py record <agent-name> <tokens> <duration_ms> [note]

import json
import os
import sys
from pathlib import Path

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "assets" / "agent-cost-history.json"


def load_registry():
    if not REGISTRY_PATH.exists():
        return {"_meta": {"schema_version": 1, "last_updated": "", "note": ""}, "agents": {}}
    try:
        return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        print(f"Registry file is corrupt ({exc}) -- back it up and re-seed: {REGISTRY_PATH}", file=sys.stderr)
        sys.exit(1)


def save_registry(registry, today):
    registry["_meta"]["last_updated"] = today
    tmp_path = REGISTRY_PATH.with_suffix(".json.tmp")
    tmp_path.write_text(json.dumps(registry, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp_path, REGISTRY_PATH)


def cmd_estimate(agent_name):
    registry = load_registry()
    entry = registry.get("agents", {}).get(agent_name)
    if not entry:
        print(f"No historical data yet for '{agent_name}'.")
        return
    minutes = entry["avg_duration_ms"] / 1000 / 60
    print(
        f"~{entry['avg_tokens']:,} tokens / ~{minutes:.1f} min based on "
        f"{entry['observations']} observation(s) "
        f"(range: {entry['min_tokens']:,}-{entry['max_tokens']:,} tokens, "
        f"{entry['min_duration_ms'] / 1000 / 60:.1f}-{entry['max_duration_ms'] / 1000 / 60:.1f} min)"
        + (f" -- {entry['note']}" if entry.get("note") else "")
    )


def cmd_record(agent_name, tokens, duration_ms, note, today):
    try:
        tokens = int(tokens)
        duration_ms = int(duration_ms)
    except ValueError:
        print(f"tokens and duration_ms must be integers, got: {tokens!r}, {duration_ms!r}", file=sys.stderr)
        sys.exit(1)
    registry = load_registry()
    agents = registry.setdefault("agents", {})
    entry = agents.get(agent_name)
    if entry is None:
        entry = {
            "observations": 1,
            "avg_tokens": tokens,
            "avg_duration_ms": duration_ms,
            "min_tokens": tokens,
            "max_tokens": tokens,
            "min_duration_ms": duration_ms,
            "max_duration_ms": duration_ms,
        }
    else:
        n = entry["observations"]
        entry["avg_tokens"] = round((entry["avg_tokens"] * n + tokens) / (n + 1))
        entry["avg_duration_ms"] = round((entry["avg_duration_ms"] * n + duration_ms) / (n + 1))
        entry["observations"] = n + 1
        entry["min_tokens"] = min(entry["min_tokens"], tokens)
        entry["max_tokens"] = max(entry["max_tokens"], tokens)
        entry["min_duration_ms"] = min(entry["min_duration_ms"], duration_ms)
        entry["max_duration_ms"] = max(entry["max_duration_ms"], duration_ms)
    if note:
        entry["note"] = note
    agents[agent_name] = entry
    save_registry(registry, today)
    print(f"Recorded: {agent_name} now has {entry['observations']} observation(s), "
          f"avg {entry['avg_tokens']:,} tokens / {entry['avg_duration_ms'] / 1000 / 60:.1f} min.")


def main():
    if len(sys.argv) < 3:
        print("Usage: agent-cost-tracker.py estimate <agent-name>", file=sys.stderr)
        print("       agent-cost-tracker.py record <agent-name> <tokens> <duration_ms> [note]", file=sys.stderr)
        sys.exit(1)

    mode = sys.argv[1]
    agent_name = sys.argv[2]

    if mode == "estimate":
        cmd_estimate(agent_name)
    elif mode == "record":
        if len(sys.argv) < 5:
            print("Usage: agent-cost-tracker.py record <agent-name> <tokens> <duration_ms> [note]", file=sys.stderr)
            sys.exit(1)
        tokens = sys.argv[3]
        duration_ms = sys.argv[4]
        note = " ".join(sys.argv[5:]) if len(sys.argv) > 5 else ""
        import datetime
        today = datetime.date.today().isoformat()
        cmd_record(agent_name, tokens, duration_ms, note, today)
    else:
        print(f"Unknown mode: {mode}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
