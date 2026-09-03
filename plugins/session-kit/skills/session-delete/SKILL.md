---
name: session-delete
description: >-
  Deletes a Claude Code session file, with optional cleanup of associated task
  lists and tasks. Warns about orphaned tasks before deleting. Use when the
  user has already named or identified one specific session to remove —
  "delete session <id>", "remove session". For finding and bulk-deleting
  sessions by criteria (old/empty/tiny), use session-cleanup instead.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*) Bash(ls:*)
---

# Session Delete

Delete a session and optionally its associated tasks.

## When to Use

- User has already named or identified one specific session to delete
- "delete session <id>", "remove session"

## When NOT to Use

- Finding and bulk-deleting sessions by criteria (old/empty/tiny) → use `session-cleanup` instead

## Step 1: Preview what will be deleted

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" session-detail <session-id>
```

Show the session summary, token usage, and associated task lists.
Also show the file path (`session.path`) so the user can inspect it manually if desired: `ls -la "<path>"`.

## Step 2: Confirm before deleting

**NEVER delete without an explicit `AskUserQuestion` confirmation — never a printed "(yes/no)" prompt.** A printed question is not a real turn boundary; `AskUserQuestion` is. Present:

- Session ID and project
- File path (for manual inspection)
- Number of associated task lists and tasks that will become orphans

Ask via `AskUserQuestion`: "Delete this session?" with a follow-up on whether to also delete associated tasks (default: do **not** delete tasks unless the user opts in).

## Step 3: Execute deletion

If user confirms, delete with or without tasks:

```bash
# Delete session only (tasks become orphans)
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session <session-id>

# Delete session and associated tasks
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session <session-id> --delete-tasks
```

Always delete through this script, not a manual `rm` — it validates the ID, keeps the deletion contained to the projects directory, and reports orphaned task lists. A manual `rm` skips all of that.

## Step 4: Report result

Show what was deleted: session file path, and if tasks were deleted, how many.

## Safety

- Never delete without an explicit `AskUserQuestion` confirmation — never a printed "(yes/no)" prompt
- Always show what will be deleted first
- Always show the file path for manual inspection
- Default to NOT deleting associated tasks unless user opts in
- Delete only through the script (Step 3) — never suggest a raw `rm` on a session file

## Testing & Validation

Eval suite: `evals/session-delete/` — 2 scenarios, `skill-tester` Quick Workflow blind comparison, both
passed.

**Last dated run record:** `evals/session-delete/workspace/iteration-1/eval-{1,2}/with_skill/grading.json`,
2026-09-02. `scripts/smoke_test.py` structural self-check also passing as of the same date.

**Verify this skill activates on:**
- "delete session abc-123"
- "remove this session"

**Verify it does NOT activate on:**
- "clean up old sessions" (bulk, criteria-based) → `session-cleanup`

**Quality gates:**
- [ ] Deletion is always gated by a real `AskUserQuestion` call, never a printed "(yes/no)" prompt
- [ ] No raw `rm` shortcut is offered as a deletion path
