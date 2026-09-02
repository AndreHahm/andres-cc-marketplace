---
name: session-diff
description: >-
  Compares two Claude Code sessions — shows what changed in files, tools used,
  branches, and topics. Use when the user says "what changed between sessions",
  "diff sessions", "compare yesterday and today", or wants to understand how
  work evolved across sessions.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*) Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py":*)
---

# Session Diff

Compare two sessions to see what changed.

## When to Use

- Wants to compare two specific sessions' files, tools, branches, or topics
- "what changed between sessions", "diff sessions", "compare yesterday and today"

## Step 1: Resolve the two sessions

If the user names two session IDs or paths, resolve each directly:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" session-detail <session-id>
```

Use the `session.path` field from each result.

If the user did not name specific sessions (e.g. "compare yesterday and today"), list recent sessions in the current project and let the user pick, or infer from the dates if unambiguous:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" list --project "$(basename $(pwd))" --limit 2 --format json
```

`--format json` is required for the `list` fallback — without it, there is no `path` field to extract. If the project has fewer than 2 sessions, tell the user there's nothing to diff yet.

## Step 2: Run the diff

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" diff <session-a.jsonl> <session-b.jsonl>
```

## Step 3: Interpret and present

The script outputs raw structural data. Your job is to synthesize the narrative:

- **What was the focus of each session?** (use `first_user_messages`)
- **Files added/dropped/common** between sessions
- **Branch changes** (did they switch branches?)
- **Tool usage shifts** (more editing? more reading? more testing?)
- **Continuity** — does session B pick up where A left off?

Present as a side-by-side comparison with your interpretation.

## Testing & Validation

**Verify this skill activates on:**
- "what changed between sessions X and Y"
- "diff sessions"
- "compare yesterday and today"

**Verify it does NOT activate on:**
- "show session details for X" (single session) → `session-detail`

**Quality gates:**
- [ ] Step 1 actually resolves user-named session IDs/paths rather than unconditionally listing the 2 most recent sessions
- [ ] The `list` fallback includes `--format json`
