---
name: codex-session-lookup
description: "Look up or inspect Codex CLI's own session/history files. Use when asked to find a Codex session, resume a specific Codex session, or inspect a Codex session file's metadata."
allowed-tools: ["Bash(python3:*)"]
---

# Codex session lookup (utility)

Read-only. Operates on Codex CLI's own local state under `~/.codex/`, not on Claude Code sessions. Direct port of Wave 8's `codex-session` skill — no behavioral changes.

## Find a session by query or recency

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/codex-session-lookup/scripts/find_session_id.py" --query "<text>"
python3 "${CLAUDE_PLUGIN_ROOT}/skills/codex-session-lookup/scripts/find_session_id.py" --last 5
```

Searches `~/.codex/history.jsonl`; outputs tab-separated `session_id`, timestamp, and a truncated prompt (140 chars, use `--full` for the complete text).

## Inspect a session file

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/codex-session-lookup/scripts/inspect_session_file.py" <path-to-rollout-file> [--id-only]
```

Reads a `~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl` (or `.json`) file and prints its session metadata (id, timestamp, cwd), or just the session ID with `--id-only`.

Useful alongside `codex-rescue`/`codex-verify`/`codex-research`'s session-resume paths and `/codex-kit:transfer`'s output when a `codex resume <session-id>` command needs manual recovery.
