---
name: session-tasks
description: >-
  Aggregates tasks across Claude Code task lists and sessions — shows pending,
  in-progress, and completed tasks with dependencies. Use when the user asks
  "what tasks are pending", "show my tasks", "orphaned tasks", "task dependencies",
  or wants a cross-session task inventory.
allowed-tools: Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py":*) Bash(python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py":*)
---

# Session Tasks

Aggregate tasks from the Tasks filesystem (`~/.claude/tasks/`) and session JSONL.

## When to Use

- Wants a cross-session/cross-task-list task inventory, filtered by status or dependencies
- "what tasks are pending", "show my tasks", "task dependencies"

## When NOT to Use

- Task detail for one specific session → use `session-detail` instead (this skill aggregates across all task lists/sessions)

## List all task lists

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" task-lists
```

This includes each list's `last_modified` timestamp — needed for the orphaned-task check below. This command always prints JSON.

## All tasks across all task lists

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" tasks --format json
```

`--format json` is required — the default table view only has `status`/`subject`/`task_list_id`, not `description`, `blockedBy`/`blocks`, `activeForm`, or `source`, all of which the presentation below needs.

## Filter by status

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" tasks --status pending --format json
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" tasks --status in_progress --format json
```

## Tasks from a specific task list

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" tasks --task-list <task-list-id> --format json
```

## Fallback: tasks from a session JSONL (legacy)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_transcript.py" tasks <session-jsonl-path>
```

## Present results

Group tasks by status:
1. **In Progress** tasks first (actively being worked on — check `activeForm` for current activity)
2. **Pending** tasks (need attention — check `blockedBy` for dependencies)
3. **Completed** tasks

For each task show: subject, description, status, task list ID, dependencies.

If tasks have `blocks`/`blockedBy` relationships, show a dependency summary:
- "Task 2 (Add tests) is blocked by Task 1 (Setup project)"

**Orphaned tasks**: tasks aren't self-tagged with an age — cross-reference each task's `task_list_id` against `task-lists`' own `last_modified` field. Flag a task as orphaned if its status is "pending" or "in_progress" and its owning task list's `last_modified` is more than 7 days old.

The `source` field indicates whether the task came from the filesystem (`"filesystem"`) or was extracted from session JSONL (`"jsonl"`).

## Testing & Validation

**Verify this skill activates on:**
- "what tasks are pending"
- "show my tasks across all sessions"
- "which tasks are orphaned"

**Verify it does NOT activate on:**
- "what tasks are in this session" (single session) → `session-detail`

**Quality gates:**
- [ ] `tasks` invocations include `--format json`
- [ ] "Orphaned" is computed by cross-referencing `task-lists`' `last_modified`, never asserted as a field the `tasks` output itself carries
