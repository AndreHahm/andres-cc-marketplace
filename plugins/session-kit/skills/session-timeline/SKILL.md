---
name: session-timeline
description: >-
  Shows a chronological timeline of all Claude Code sessions for a project.
  Use when the user wants a chronological, visual view of session cadence,
  gaps, or patterns over time — "session timeline", "what's the history of
  this project", "show me patterns in my work". For a simple sortable
  inventory (not chronological pattern analysis), use session-list instead.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*) Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py":*)
---

# Session Timeline

Show chronological history of sessions for a project.

## When to Use

- Wants a chronological/pattern-oriented view of session activity for a project (cadence, gaps, session-length trends)
- "session timeline", "what's the history of this project", "patterns in my work"

## When NOT to Use

- A simple sortable inventory (not chronological pattern analysis) → use `session-list` instead
- Wants a session's full profile (summary + tasks + messages), not just its bare chronological event
  list → use `session-detail` instead. `session-detail` covers the holistic view; this skill's
  single-session mode (Step 1, Option B below) covers only the timestamped event list itself.

## Step 1: Choose scope — project timeline, or one session's own events

**Option A — cross-session, project-level timeline** (the default: cadence/gaps/patterns across all
sessions in a project):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" timeline --project "$(basename $(pwd))" --format json
```

To show only recent sessions:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" timeline --project "$(basename $(pwd))" --since "2026-04-01" --format json
```

`--format json` is required — without it, the command prints a human-readable table instead of the
JSON array Step 2 needs to parse. If this returns an empty timeline unexpectedly (e.g. the current
directory doesn't match where a relevant session actually started — a worktree created mid-session,
for instance), run
`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" current` to check whether a live session
exists for a differently-named project before concluding there's no history yet.

**Option B — one session's own detailed, event-by-event timeline** (the user names a specific session,
or asks for "this session's events"/"a detailed timeline of this session" — bare chronological events
only, no summary or task context; Option A's `timeline` command only ever returns one coarse bar per
*session*, never individual events within one):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" current
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" messages <session-jsonl-path> --limit 200 --include-tools
```
Use the `path` field from `current` (or a session ID the user gave) as `<session-jsonl-path>`. This is
what actually satisfies an "event-level"/"detailed" framing scoped to one session — reaching only for
Option A's project-level command when the user asked about one session's own events produces the same
coarse bar chart regardless of how the request was phrased, which isn't what was asked.

## Step 2: Present the timeline

**Option A output:** a JSON array of sessions in chronological order (`session_id`, `project`, `date`, `messages`, `duration_minutes`, `size_bytes`, `path` — no branch field). Present as a visual timeline:

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

**Option B output:** a JSON array of message/tool-call entries, each with a `timestamp`. Present each
entry in chronological order, one line per event:

```
14:32:07  user       "fix the login bug"
14:32:41  assistant  [text] "I'll look at the auth handler first"
14:32:52  assistant  [tool] Read auth.py
14:35:10  assistant  [text] "Found the issue..."
```

## Testing & Validation

Eval suite: `evals/session-timeline/` — 3 scenarios, `skill-tester` Quick Workflow blind comparison.
Evals 1-2 passed. Eval 3 ("detailed timeline of this session's events") originally found a real gap:
a faithful reading of the prior Step 1/Step 2 text produced only a `session_store.py`-driven,
session-level timeline, with `session_transcript.py` invoked only conditionally for per-session branch
resolution, never as a path toward event-level detail. Step 1/2 were restructured to add Option B (one
session's own event-by-event timeline via `session_transcript.py messages <path> --limit 200
--include-tools`), routing an event-level/single-session request there instead of Option A's
project-level `timeline` command. Re-verified via a genuinely blind nested-Agent dispatch (given only
the current SKILL.md and the eval prompt, no hints): both assertions passed — the agent invoked Option
B and produced a real chronological, event-level listing. See
`evals/session-timeline/workspace/iteration-2/eval-3/with_skill/grading.json`'s `critical_note` for the
full re-verification record.

**Last dated run record:** `evals/session-timeline/workspace/iteration-2/eval-{1,2,3}/with_skill/grading.json`
— evals 1-2 and eval 3's original run 2026-09-02; eval 3 re-verified after the fix on 2026-09-03.
`scripts/smoke_test.py` structural self-check also passing as of the same date.

**Verify this skill activates on:**
- "session timeline"
- "what's the history of this project"
- "show me patterns in my work"

**Verify it does NOT activate on:**
- "list my sessions" / "how many sessions do I have" → `session-list`
- "show session details for X" → `session-detail`

**Quality gates:**
- [ ] Option A's command includes `--format json`
- [ ] The illustrative Option A timeline never claims a branch column the data doesn't contain
- [ ] A request for one session's own event-level detail uses Option B (`session_transcript.py
      messages`), not Option A's project-level `timeline` command
