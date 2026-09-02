---
name: session-search
description: >-
  Searches Claude Code sessions across all projects by literal, case-insensitive
  keyword. Use when the user wants to find a previous session, locate past work,
  search for something they discussed before, or cannot remember which project a
  conversation was in. Also use when the user says "find that session where" or
  "search sessions". For searching stored memory file content instead of session
  transcripts, use session-memory-search.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*)
---

# Session Search

Search across all Claude Code sessions by keyword.

## When to Use

- Wants to find a previous session or locate past work by content
- "find that session where...", "search sessions", "cannot remember which project"

## When NOT to Use

- Searching stored memory file content, not session transcripts → use `session-memory-search` instead

## Step 1: Run the search

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" search "<query>" --limit 20 --context 1 --format json
```

To filter by project:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" search "<query>" --project "<filter>" --limit 20 --context 1 --format json
```

To filter by date:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" search "<query>" --since "2026-04-01" --limit 20 --format json
```

`--format json` is required — without it, the command prints a human-readable table with no context lines, instead of the NDJSON Step 2 needs.

The match is a literal, case-insensitive substring search — not a regex engine. Special characters in the query are treated literally, not as regex syntax.

## Step 2: Present results

The script outputs newline-delimited JSON (one match per line). Group results by session and present:

- **Session ID** and **project** as headers
- **Matching text** with timestamp
- **Context** (lines before/after) if available
- **Resume command**: `claude --resume <session-id>`

If no results, suggest broadening the search or trying different keywords.

## Testing & Validation

**Verify this skill activates on:**
- "find that session where I fixed the login bug"
- "search my sessions for X"
- "which project did I discuss Y in"

**Verify it does NOT activate on:**
- "search my memories for X" → `session-memory-search`

**Quality gates:**
- [ ] Step 1's command includes `--format json`
- [ ] Query is never described as supporting regex syntax
