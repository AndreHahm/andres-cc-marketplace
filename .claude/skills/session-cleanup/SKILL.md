---
name: session-cleanup
description: >-
  Finds old, empty, or tiny Claude Code session files that are candidates for
  deletion. Use when the user wants to bulk-find sessions by criteria (age,
  size, message count) — "clean up old sessions", "free disk space", "session
  storage usage". For deleting one specific, already-identified session, use
  session-delete instead.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*)
---

# Session Cleanup

Find session files that are candidates for cleanup.

## When to Use

- Wants to bulk-find sessions by criteria (age, size, message count)
- "clean up old sessions", "free disk space", "session storage usage"

## When NOT to Use

- Deleting one specific, already-identified session → use `session-delete` instead

## Step 1: Identify candidates

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" cleanup --min-messages 3
```

To also find old sessions (`Nd`/`Nw`/`Nm` — days, weeks, or months):
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" cleanup --older-than 30d --min-messages 3
```

## Step 2: Present candidates

The `cleanup` command only *identifies* candidates — it never deletes anything on its own. It outputs a JSON object with `candidates` array and `total_size_bytes`. Present as a table:

| # | Session ID | Project | Reason | Messages | Age | Size |
|---|-----------|---------|--------|----------|-----|------|

Show the total reclaimable space.

## Step 3: Confirm before deleting

**NEVER delete without an explicit `AskUserQuestion` confirmation — never a printed "(yes/no)" prompt.** Present the list and ask via `AskUserQuestion`: "Delete these N sessions ([total size])?" — with a follow-up on whether to also delete each session's associated tasks (default: do **not** delete tasks unless the user opts in, matching `session-delete`'s own convention).

If confirmed, delete each session one at a time using the same command `session-delete` uses:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session <session-id>
```

If the user opted in to also deleting associated tasks, add `--delete-tasks`:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session <session-id> --delete-tasks
```

This will also report any task lists that become orphaned (deleted immediately if `--delete-tasks` was
used, otherwise reported for Step 4 below). Delete through this script only — never a manual `rm`, which
skips ID validation and the orphan-task report.

Report each deletion. If the user wants to keep some, ask which ones to skip.

## Step 4: Check for orphan task lists

After cleanup, check for task lists that no longer have matching sessions:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" orphan-task-lists
```

If orphans are found, present them:

| Task List ID | Tasks | Last Modified |
|-------------|-------|---------------|

Ask via `AskUserQuestion`: "Found N orphan task lists with no matching session. Delete them?" (options: all / select / none).

If confirmed, delete using:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-task-list <task-list-id>
```

Delete through this script only. Do not suggest a manual `rm -r` on a task-list directory — the directory name comes from the filesystem, not from validated input, and interpolating it into a shell command is unsafe.

## Safety

- The `cleanup` command only identifies candidates — deletion always happens as a separate, explicitly `AskUserQuestion`-confirmed `delete-session`/`delete-task-list` call (Steps 3-4), never automatically
- Always show the full list before asking for confirmation
- Delete one file at a time, reporting each
- Delete only through the script — never a raw `rm`/`rm -r`
- If in doubt, suggest the user review the list first

## Testing & Validation

Eval suite: `evals/session-cleanup/` — 3 scenarios, `skill-tester` Quick Workflow blind comparison, all
passed. Eval 3 verified the `--delete-tasks` variant is gated by the same real `AskUserQuestion`
confirmation as session deletion, with no raw `rm` used.

**Last dated run record:** `evals/session-cleanup/workspace/iteration-2/eval-{1,2,3}/with_skill/grading.json`,
2026-09-03. `scripts/smoke_test.py` structural self-check also passing as of the same date.

**Verify this skill activates on:**
- "clean up old sessions"
- "free disk space"
- "what's using up my session storage"

**Verify it does NOT activate on:**
- "delete session abc-123" (one specific, already-identified session) → `session-delete`

**Quality gates:**
- [ ] Deletion is always gated by a real `AskUserQuestion` call, never a printed "(yes/no)" prompt
- [ ] No raw `rm`/`rm -r` shortcut is offered as a deletion path
- [ ] The Safety section's claim about what `cleanup` does matches what Step 3 actually does
