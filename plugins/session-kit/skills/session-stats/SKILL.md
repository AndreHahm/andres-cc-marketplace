---
name: session-stats
description: >-
  Shows token usage, model distribution, turn count, duration, and tool usage
  for a Claude Code session. Use when the user asks about token usage, session
  cost, model breakdown, or says "session stats" or "how much did this session
  use". For the full session profile (tasks, messages, summary) rather than
  usage stats alone, use session-detail instead.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*) Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py":*)
---

# Session Stats

Show detailed statistics for a single session.

## When to Use

- Wants a token-usage/cost/model breakdown for one session, and nothing more
- "session stats", "how much did this session use", "model breakdown"

## When NOT to Use

- The full session profile (tasks, messages, summary), not just usage stats → use `session-detail` instead

## Step 1: Resolve the session

If the user provides a session ID or path, use it directly. Otherwise, find the current session:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" list --project "$(basename $(pwd))" --limit 1 --format json
```

Use the `path` field from the first result. `--format json` is required — without it, the command's table output has no `path` field.

## Step 2: Run the stats script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" stats <session-jsonl-path>
```

## Step 3: Present results

The script outputs a JSON object. Present as a visual summary:

- **Duration and turns** as headline stats
- **Token usage** as a breakdown (input, output, cache read, cache create) with totals
- **Model distribution** as a list showing which models were used and how many turns each
- **Tool usage** as a ranked list (most used first)

Note: Cost estimation is not available. Report raw token counts and model names only.

## Testing & Validation

**Verify this skill activates on:**
- "session stats"
- "how much did this session use"
- "what models were used in this session"

**Verify it does NOT activate on:**
- "show me everything about this session" (full profile) → `session-detail`

**Quality gates:**
- [ ] Step 1's command includes `--format json` so `path` is actually resolvable
