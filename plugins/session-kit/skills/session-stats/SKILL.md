---
name: session-stats
description: >-
  Shows token usage, model distribution, turn count, duration, tool usage,
  tool errors, and frustration signals (correction phrases, stuck tool-call
  loops) for a Claude Code session. Use when the user asks about token usage,
  session cost, model breakdown, what tool errors happened, or whether they
  got stuck in a loop -- "session stats", "how much did this session use",
  "what tool errors happened", "was I stuck in a loop". For the full session
  profile (tasks, messages, summary) rather than usage stats alone, use
  session-detail instead.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*) Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py":*)
---

# Session Stats

Show detailed statistics for a single session.

## When to Use

- Wants a token-usage/cost/model breakdown for one session, and nothing more
- "session stats", "how much did this session use", "model breakdown"
- Wants to know what tool errors happened in a session, or whether they got stuck in a repeated
  tool-call loop or pushed back with a correction — "what tool errors happened", "was I stuck in a
  loop", "did I get frustrated in that session"

## When NOT to Use

- The full session profile (tasks, messages, summary), not just usage stats → use `session-detail` instead

## Step 1: Resolve the session

If the user provides a session ID or path, use it directly. Otherwise, find the current session:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" current
```

Use the `path` field from the result. This resolves the live session directly (via its own session
ID), not by matching the current directory against a project name — safe even when the current
working directory doesn't match where the session actually started (e.g. a worktree created mid-session).

## Step 2: Run the stats script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" stats <session-jsonl-path>
```

For tool errors or frustration signals instead of (or alongside) usage stats, run the matching
subcommand on the same session path:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" errors <session-jsonl-path>
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" irritation <session-jsonl-path>
```

## Step 3: Present results

Each subcommand outputs its own JSON object. Present as a visual summary:

- **`stats`** — duration and turns as headline stats; token usage as a breakdown (input, output,
  cache read, cache create) with totals; model distribution as a list showing which models were used
  and how many turns each; tool usage as a ranked list (most used first)
- **`errors`** — a list of tool errors (timestamp, tool name, truncated error content); report the
  count first, then the list
- **`irritation`** — correction phrases (timestamp, matched phrase, excerpt) and stuck tool-call
  loops (tool name, consecutive-call count); report both counts, then the details

Note: Cost estimation is not available. Report raw token counts and model names only.

`irritation`'s correction-phrase matching is a simple substring heuristic (case-insensitive, phrases
like "wrong", "stop", "undo") — it can false-positive on unrelated uses of those words. Present matches
as signals to review, not confirmed frustration.

## Testing & Validation

No `evals/` suite — this skill's branching logic (`get_stats`/`get_errors`/`get_irritation_signals`) is
confined to `scripts/session_transcript.py`, directly tested via `tests/test_session_transcript.py`; the
skill body itself is a straight-line resolve→run→present flow with no prose-level judgment calls worth a
comparison eval.

**Verify this skill activates on:**
- "session stats"
- "how much did this session use"
- "what models were used in this session"
- "what tool errors happened in that session"
- "was I stuck in a loop"

**Verify it does NOT activate on:**
- "show me everything about this session" (full profile) → `session-detail`
- "my session crashed, help me continue" (interruption recovery, not error listing) → `session-recover`

**Quality gates:**
- [ ] Step 1's command includes `--format json` so `path` is actually resolvable
- [ ] `irritation` results are presented as signals to review, never as confirmed frustration
- [ ] `errors` entries attribute the correct `tool_name` via `tool_use_id` matching, not silently "unknown"
