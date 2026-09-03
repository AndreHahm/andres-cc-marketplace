---
name: session-export
description: >-
  Exports a Claude Code session as a clean, readable markdown transcript.
  Use when the user wants to export a session, create a transcript, save
  session history to a file, or says "export this session".
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*) Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py":*)
---

# Session Export

Export a session as a clean transcript.

## When to Use

- Wants to export a session, create a transcript, or save session history to a file
- "export this session", "create a transcript"

## When NOT to Use

- Wants to see session details in the conversation, not a file/transcript output → use `session-detail`
  instead

## Step 1: Resolve the session

If no session specified, use the current one:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" current
```

Use the `path` field from the result. This resolves the live session directly (via its own session
ID), not by matching the current directory against a project name — safe even when the current
working directory doesn't match where the session actually started (e.g. a worktree created mid-session).

## Step 2: Export

To print to conversation:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" export <session-jsonl-path> --format md
```

To save to file, use an absolute path outside this repository (or one the user explicitly names) — a bare relative filename resolves against the current working directory, which is often a repo root, and would leave an untracked file behind:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" export <session-jsonl-path> --format md --output "$HOME/session-transcript.md"
```

For plain text:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" export <session-jsonl-path> --format txt --output "$HOME/session-transcript.txt"
```

Tool calls are summarized (tool name only, not full input JSON) by default; pass `--no-include-tools` to omit them entirely.

### Including the session's task list (optional)

If the user wants the export to also include the session's tracked tasks, run:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" tasks <session-jsonl-path>
```
This returns each task's current, fused status (create/update events already merged into one entry per
task) — not the raw event stream, so a task that was later completed shows `"status": "completed"`, not
a stale/missing status from its original create event. If the user specifically asked for *pending*
tasks (e.g. "my pending task list"), filter the result to `status == "pending"` before appending it.

Append the result as a `## Tasks` section: directly under the transcript when presenting inline, or
appended to the same file after the transcript itself has been written when `--output` was used. Don't
silently drop the request just because the `export` subcommand itself has no task-inclusion flag — this
`tasks` subcommand, scoped to the same session path already resolved in Step 1, is the documented way to
satisfy it.

## Step 3: Present

If written to file, confirm the path and line count. If inline, present the transcript directly.

The exported transcript contains verbatim user messages, file paths, and (if included) tool call summaries from the original session — review before sharing outside the immediate context.

## Testing & Validation

Eval suite: `evals/session-export/` — 3 scenarios, `skill-tester` Quick Workflow blind comparison. Evals
1-2 passed. Eval 3 ("export this session, including my pending task list") originally found a real gap:
this skill's own workflow never documented how to include task-list data in an export — the underlying
`session_transcript.py` `export` subcommand has no task-inclusion flag, and the separate `tasks`
subcommand this plugin's shared scripts do provide was never referenced anywhere in this skill's Export
steps. Fixed by adding the "Including the session's task list (optional)" subsection under Step 2, and
independently re-verified via a blind re-run: a fresh agent given only this SKILL.md's content and the
eval-3 prompt, with no hint of what was being tested, correctly ran the `tasks` subcommand and appended
its result as a labeled `## Tasks` section. See
`evals/session-export/workspace/iteration-2/eval-3/with_skill/grading.json` for the full analysis —
all 3 assertions now pass.

**Last dated run record:** `evals/session-export/workspace/iteration-2/eval-{1,2,3}/with_skill/grading.json`
— evals 1-2 and eval 3's original run 2026-09-02; eval 3 re-verified after the fix on 2026-09-03.
`scripts/smoke_test.py` structural self-check also passing as of 2026-09-03.

**Verify this skill activates on:**
- "export this session"
- "create a transcript of this conversation"
- "save my session history to a file"

**Verify it does NOT activate on:**
- "show session details for X" (no file output wanted) → `session-detail`

**Quality gates:**
- [ ] Step 1's `current` call needs no `--format` flag — the command always emits JSON
- [ ] `--output` examples never use a bare relative filename
- [ ] A request to include the task list uses `session_transcript.py tasks`, appended as a labeled
      section — never silently dropped because `export` itself has no task-inclusion flag
