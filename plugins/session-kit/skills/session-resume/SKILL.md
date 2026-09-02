---
name: session-resume
description: >-
  Generates a context recovery prompt from a past Claude Code session so a new
  session can pick up where it left off. Use when the user says "resume from",
  "pick up where I left off", "continue that session", "context recovery", or
  wants to start a new session with context from an old one.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*) Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py":*)
---

# Session Resume

Generate a context-recovery document from a past session.

## When to Use

- Wants to pick up a past session's work in a new session
- "resume from", "pick up where I left off", "continue that session", "context recovery"

## When NOT to Use

- Wants to stay in the *original* session's own context (not a synthesized recovery prompt) → suggest the native `claude --resume`/`claude --continue` CLI flags instead (see Step 3)
- Wants live inspection of a session, not a resume prompt → use `session-detail` instead
- An explicit handoff document already exists for this work → use `session-handoff`'s RESUME workflow
  instead of synthesizing a recovery prompt from raw transcript. This skill reconstructs context
  retroactively from a past session's own JSONL when nothing was ever explicitly saved;
  `session-handoff` loads a document someone deliberately wrote and validated during an active session.
- Wants to continue the work directly in *this* conversation rather than receive a portable document
  → use `session-recover` instead. This skill always produces a document for review or handoff
  elsewhere; `session-recover` continues in-place, regardless of whether the prior session ended
  cleanly or was interrupted (though interruption recovery is its most common trigger).

## Step 1: Resolve the session

If the user provides a session ID, resolve it. Otherwise, show recent sessions and ask which one:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" list --project "$(basename $(pwd))" --limit 5 --format json
```

`--format json` is required — without it, the command's table output has no `path` field. If this
returns nothing (e.g. the current directory doesn't match where a relevant session actually started —
a worktree created mid-session, for instance), try
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" list --limit 5 --format json` (no `--project`
filter) to browse recent sessions across all projects instead.

## Step 2: Extract resume data

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" resume <session-jsonl-path>
```

## Step 3: Synthesize context recovery prompt

The script outputs raw session data. Synthesize into a structured context document:

### Context Recovery Template

```markdown
# Continuing: [project name] — [branch]

## What was being worked on
[Synthesize from last_user_messages and tool_calls_summary]

## Key files
[List files_modified with brief context on what was done to each]

## Decisions made
[Infer from the session flow — what approaches were chosen]

## Pending work
[List any tasks with status "pending"]

## Last state
[What was the user's last intent? What should happen next?]

## Git commits made
[List any commits from the session]
```

Also offer: `claude --resume <session-id>` as an alternative if the user wants to continue in the original session context directly.

This document may contain verbatim user messages and local file paths from the original session — review before sharing outside the immediate context.

### Resumed sessions

When a user runs `claude --resume <session-id>` or `claude --continue`, Claude Code creates a **new JSONL file** with a new session ID. The previous session's context is loaded into memory but does not appear in the new file. There is no standard metadata linking the two sessions.

This means a resumed session's transcript will appear to start mid-conversation — the first message may reference context that only existed in the parent session. The `is_resumed` flag in session stats indicates when this has been detected, so the context recovery prompt should note that earlier context may be missing.

### Difference from live inspection
This skill works **retroactively** on any past session, even ones that ended abruptly, and produces a portable recovery document. Live inspection of a session's current state is `session-detail`'s job instead.

## Testing & Validation

**Verify this skill activates on:**
- "resume from my last session"
- "pick up where I left off"
- "give me context recovery for session X"

**Verify it does NOT activate on:**
- "show me the details of this session" → `session-detail`

**Quality gates:**
- [ ] Step 1's command includes `--format json`
- [ ] "Pending work" section only lists tasks whose `status` field is actually populated (via `merge_task_events`'s default)
