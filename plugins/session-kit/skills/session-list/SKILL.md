---
name: session-list
description: >-
  Lists all Claude Code sessions for a project or globally, sorted by recency,
  size, or duration. Use when the user asks how many sessions they have, wants
  to see recent sessions, says "list sessions", or wants a session inventory.
  For a chronological, pattern-oriented view (gaps, cadence, session-length
  trends) rather than a flat sorted table, use session-timeline instead.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*)
---

# Session List

List all sessions, optionally filtered by project and sorted.

## When to Use

- "list sessions", "how many sessions do I have", "show recent sessions"
- Wants a sortable inventory of sessions (by recency, size, or duration)

## When NOT to Use

- A chronological, pattern-oriented view (gaps, cadence, session-length trends) → use `session-timeline` instead
- Detail on one already-identified session (tokens, tasks, messages) → use `session-detail` instead

## Step 1: Run the listing script

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" list --limit 20 --format json
```

To filter by project:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" list --project "<filter>" --limit 20 --format json
```

To sort by size or duration instead of recency:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" list --sort size --limit 20 --format json
```

`--format json` is required — without it, the command prints a human-readable table with no `path` field, which the rest of this workflow needs.

## Step 2: Present results

The script outputs a JSON array. Present as a markdown table:

| # | Session ID | Project | Date | Messages | Duration | Size |
|---|-----------|---------|------|----------|----------|------|

To highlight the current session in the table, run
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" current` separately and mark whichever listed
row's `session_id` matches its result — the `list` output itself carries no current-session marker.
Show the resume command: `claude --resume <session-id>`.

If the user asks for more detail on a specific session (tasks, full message transcript), use the `session-detail` skill; for a narrow token/model/tool-usage breakdown only, use `session-stats`.

## Testing & Validation

Eval suite: `evals/session-list/` — 3 scenarios, `skill-tester` Quick Workflow blind comparison. Eval 2
(4/4) and eval 3 (2/2) passed fully. Eval 1 (3/4) recorded one assertion failure: the run expected the
default `list` call to filter to the current project, but Step 1's own default command has no `--project`
filter by design (this skill lists globally by default, per its own description — filtering is opt-in,
shown as the second example). Whether that eval assertion or the skill's own default is the one that
should change is an open design question, not a fixed defect — noted here rather than silently claimed as
a clean pass. Eval 3 verified a chronological-framing request correctly redirects to `session-timeline`
instead of being answered with this skill's own default view.

**Last dated run record:** `evals/session-list/workspace/iteration-1/eval-{1,2,3}/with_skill/grading.json`,
2026-09-03. `scripts/smoke_test.py` structural self-check also passing as of the same date.

**Verify this skill activates on:**
- "list my sessions"
- "how many sessions do I have"
- "show me recent sessions for this project"

**Verify it does NOT activate on:**
- "show me all sessions" (chronological/pattern framing) → `session-timeline`
- "show session details for X" → `session-detail`

**Quality gates:**
- [ ] Step 1's command includes `--format json` so Step 2 can parse `path`/`session_id`/etc.
- [ ] Presented table matches the documented columns
