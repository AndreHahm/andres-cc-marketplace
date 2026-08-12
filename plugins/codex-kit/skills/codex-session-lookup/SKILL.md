---
name: codex-session-lookup
description: >-
  Look up or inspect Codex CLI's own session/history files — this only
  locates a session ID or reads its metadata; it never resumes anything
  itself. Use when asked to find a Codex session, locate a session ID to
  resume manually, or inspect a Codex session file's metadata. To actually
  continue a prior rescue/verify/research task, use that component's own
  `--resume`/`--resume-last`.
allowed-tools: ["Bash(python3 */codex-session-lookup/scripts/find-session-id.py:*)", "Bash(python3 */codex-session-lookup/scripts/inspect-session-file.py:*)"]
---

# Codex session lookup (utility)

Read-only. Operates on Codex CLI's own local state under `~/.codex/`, not on Claude Code sessions. Direct port of Wave 8's `codex-session` skill — no behavioral changes.

## Find a session by query or recency

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/codex-session-lookup/scripts/find-session-id.py" --query "<text>"
python3 "${CLAUDE_PLUGIN_ROOT}/skills/codex-session-lookup/scripts/find-session-id.py" --limit 5
```

Searches `~/.codex/history.jsonl`; outputs tab-separated `session_id`, timestamp, and a truncated prompt (140 chars, use `--full` for the complete text).

## Inspect a session file

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/skills/codex-session-lookup/scripts/inspect-session-file.py" <path-to-rollout-file> [--id-only]
```

Reads a `~/.codex/sessions/<YYYY>/<MM>/<DD>/rollout-*.jsonl` (or `.json`) file and prints its session metadata (id, timestamp, cwd), or just the session ID with `--id-only`.

Useful alongside `codex-rescue`/`codex-verify`/`codex-research`'s session-resume paths and `/codex-kit:transfer`'s output when a `codex resume <session-id>` command needs manual recovery.

---

## Testing & Validation

**Verify this skill activates on:**
- "find my most recent codex session about the login refactor"
- "resume a specific codex session", "inspect a codex session file's metadata"

**Verify it does NOT activate on:**
- Looking up a Claude Code session (this operates only on Codex CLI's own `~/.codex/` state)

**Concrete scenarios to check:**
1. `find-session-id.py --query "<text>"` against a real `~/.codex/history.jsonl` → tab-separated `session_id`/timestamp/truncated-prompt output, never full untruncated prompt text unless `--full` is passed.
2. `inspect-session-file.py <path> --id-only` → prints only the session ID, no other metadata.
3. A malformed or missing rollout file path → a clear error, not a silent empty result.

**Current test coverage:**
- `evals/codex-session-lookup/evals.json` — 1 defined scenario (query against `history.jsonl`, correctly identified as Codex CLI's own state, not Claude Code's). Definition only — not yet run and graded.
- No persisted smoke test exists for this skill's Python scripts; they can be run directly against a real `~/.codex/` directory for a quick manual check.

**Quality gates:**
- [ ] Never touches Claude Code's own session files — only `~/.codex/`
- [ ] Truncates prompt text to 140 chars unless `--full` is explicitly passed
- [ ] Both scripts are invoked only via their scoped `allowed-tools` grant, never a bare `python3`
