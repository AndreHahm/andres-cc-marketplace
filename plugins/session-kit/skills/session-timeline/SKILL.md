---
name: session-timeline
description: >-
  Shows a chronological timeline of all Claude Code sessions for a project.
  Use when the user wants a chronological, visual view of session cadence,
  gaps, or patterns over time — "session timeline", "what's the history of
  this project", "show me patterns in my work". For a simple sortable
  inventory (not chronological pattern analysis), use session-list instead.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*)
---

# Session Timeline

Show chronological history of sessions for a project.

## When to Use

- Wants a chronological/pattern-oriented view of session activity for a project (cadence, gaps, session-length trends)
- "session timeline", "what's the history of this project", "patterns in my work"

## When NOT to Use

- A simple sortable inventory (not chronological pattern analysis) → use `session-list` instead
- Detail on one specific session → use `session-detail` instead

## Step 1: Run the timeline script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" timeline --project "$(basename $(pwd))" --format json
```

To show only recent sessions:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" timeline --project "$(basename $(pwd))" --since "2026-04-01" --format json
```

`--format json` is required — without it, the command prints a human-readable table instead of the JSON array Step 2 needs to parse.

## Step 2: Present the timeline

The script outputs a JSON array of sessions in chronological order (`session_id`, `project`, `date`, `messages`, `duration_minutes`, `size_bytes`, `path` — no branch field). Present as a visual timeline:

```
2026-04-08  ████░░░░  45m  (12 messages)
2026-04-09  ██████░░  1h 20m  (34 messages)
2026-04-10  ██░░░░░░  15m  (8 messages)
2026-04-11  ████████  2h 10m  (56 messages)
```

If branch changes matter to the user, resolve them per-session via `session_transcript.py diff`/`resume` (which extract `gitBranch` from the JSONL) rather than assuming the timeline data carries a branch — it doesn't.

Identify patterns:
- Daily cadence or sporadic?
- Long sessions vs short?
- Gaps in activity?

## Testing & Validation

**Verify this skill activates on:**
- "session timeline"
- "what's the history of this project"
- "show me patterns in my work"

**Verify it does NOT activate on:**
- "list my sessions" / "how many sessions do I have" → `session-list`
- "show session details for X" → `session-detail`

**Quality gates:**
- [ ] Step 1's command includes `--format json`
- [ ] The illustrative timeline never claims a branch column the data doesn't contain
