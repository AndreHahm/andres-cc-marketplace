---
name: session-detail
description: >-
  Shows detailed information about a Claude Code session, including a session
  summary, associated tasks, and conversation messages (token/model/tool usage
  shown as a brief part of this overview). Use when the user says "show
  session", "session details", "what happened in session X". For a dedicated
  token-usage/cost/model breakdown only, use session-stats instead. If the session is only described
  by topic/content and not yet identified, use session-search first.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*) Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py":*)
---

# Session Detail

Show comprehensive details about a single session.

## When to Use

- Wants the full picture of one session: summary, tasks, and message transcript
- "show session", "session details", "what happened in session X"

## When NOT to Use

- A dedicated token-usage/cost/model breakdown only, not the full profile → use `session-stats` instead
- Cross-session task aggregation → use `session-tasks` instead
- The target session isn't yet identified — described by content/topic rather than an ID or clear
  reference (e.g. "what happened in the session where I fixed the login bug") → use `session-search`
  first to locate it; use `session-detail` once a specific session is identified.
- Wants a portable recovery document for a *different* session, not live detail here → use
  `session-resume` instead.
- Wants a comparison between two sessions, not detail on one → use `session-diff` instead.
- Wants only a bare chronological, event-by-event timeline for one session (no summary or task
  context) → use `session-timeline`'s single-session mode (its Step 1, Option B) instead.
- Wants a file/transcript export, not detail shown in the conversation → use `session-export` instead.

## Step 1: Get session detail

If no session ID is given, resolve the live session directly (safe even when the current working
directory doesn't match where the session actually started — e.g. a worktree created mid-session):

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" current
```

Otherwise:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" session-detail <session-id>
```

This returns: session summary (including the `path` field), token usage (input/output/cache), models used, tools called, and associated task lists with their tasks. This command always prints JSON — no `--format` flag needed.

## Step 2: Present summary

Show a formatted summary:

- **Session**: ID, project, date, duration
- **Tokens**: input, output, cache read, cache create
- **Models**: which models were used and how many turns each
- **Tools**: top tools used with counts
- **Tasks**: associated task lists and task status summary

## Note on resumed sessions

If `is_resumed` is true in the stats, this session was started via `claude --resume` or `claude --continue`. The JSONL only contains messages from the resumed portion — earlier context from the parent session is not included. Mention this to the user so they understand why the transcript may appear to start mid-conversation.

## Step 3: Show messages (optional)

If the user wants to see the conversation, use the `path` field from Step 1's `session` object:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" messages <session-path> --limit 20
```

For more messages, increase `--offset` and `--limit`:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" messages <session-path> --offset 20 --limit 20
```

To include tool call details:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" messages <session-path> --include-tools --limit 20
```

## Testing & Validation

Eval suite: `evals/session-detail/` — 3 scenarios, `skill-tester` Quick Workflow blind comparison, all
passed. Eval 3 verified a cross-session task query correctly redirects to `session-tasks` instead of
being answered directly.

**Last dated run record:** `evals/session-detail/workspace/iteration-2/eval-{1,2,3}/with_skill/grading.json`,
2026-09-03. `scripts/smoke_test.py` structural self-check also passing as of the same date.

**Verify this skill activates on:**
- "show session details for X"
- "what happened in session X"
- "give me the full picture of this session"

**Verify it does NOT activate on:**
- "how many tokens did this session use" (narrow usage only) → `session-stats`
- "what tasks are pending across my sessions" → `session-tasks`
- "what happened in the session where I fixed the login bug" (session identified by content, not yet
  located) → `session-search`

**Quality gates:**
- [ ] `<session-path>` in Step 3 is explicitly derived from Step 1's `session.path` field
