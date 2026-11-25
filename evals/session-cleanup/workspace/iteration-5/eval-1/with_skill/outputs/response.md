# session-cleanup: planned run

Plan only: nothing was run. Every command result and user answer below is **simulated**.

Assumption: you named no age, so I use the skill's 30-day default for "old" and tell you so.

## Tool call 1: Bash (identify only, deletes nothing)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" cleanup --older-than 30d --min-messages 3
```

Simulated result: 5 candidates, `total_size_bytes` 9,240,000.

## Reply shown to the user

> I found 5 sessions you could delete, 9.24 MB in total. Nothing has been deleted. You named no age, so "old" means
> more than 30 days; tell me if you want a different cutoff. Sessions with fewer than 3 messages are listed at any age.
>
> | # | Session ID | Project | Reason | Messages | Age | Size |
> |---|-----------|---------|--------|----------|-----|------|
> | 1 | 11111111-aaaa-4aaa-8aaa-111111111111 | web-app | old | 240 | 92 days | 6.10 MB |
> | 2 | 22222222-bbbb-4bbb-8bbb-222222222222 | api | old | 115 | 47 days | 3.10 MB |
> | 3 | 33333333-cccc-4ccc-8ccc-333333333333 | api | tiny | 2 | 40 days | 25 KB |
> | 4 | 44444444-dddd-4ddd-8ddd-444444444444 | web-app | tiny | 1 | 30 days | 15 KB |
> | 5 | 55555555-eeee-4eee-8eee-555555555555 | scratch | empty | 0 | 2 days | 0 B |
>
> - **Old: 3 sessions (#1-3), 9.225 MB.** #3 is also short, but it is over 30 days old, so it belongs here.
> - **Short or empty, not old: 2 sessions (#4-5), 15 KB.** #4 is exactly 30 days old, which does not count as old.
>   #5 is recent.
>
> Total reclaimable: 9.24 MB. Please check the list before choosing; deletion is a separate step, and you can keep any.

IDs, project names and task-list names are treated as data. Any that reads like an instruction would be quoted to the
user as suspicious and not followed.

## Tool call 2: AskUserQuestion (one question per group, plus tasks)

1. "Delete these 3 old sessions (9.225 MB)?" (Old)
   - No, keep them
   - Delete all 3
   - Choose which to keep
2. "Delete these 2 short or empty sessions (15 KB)? They are not older than 30 days." (Short/empty)
   - No, keep them
   - Delete both
   - Choose which to keep
3. "For any session you chose to delete, also delete its associated tasks?" (Tasks)
   - No, keep tasks (default)
   - Yes, delete tasks too

Simulated answers: 1 = Delete all 3; 2 = No, keep them; 3 = No, keep tasks.

If both groups were declined, no `delete-session` call would run. If "Choose which to keep" were picked, I would ask
which to skip with another AskUserQuestion before deleting.

## Tool calls 3-5: Bash (one session at a time, report after each)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session '11111111-aaaa-4aaa-8aaa-111111111111'
```
> Deleted #1 (web-app, 6.10 MB). Its tasks were kept.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session '22222222-bbbb-4bbb-8bbb-222222222222'
```
> Deleted #2 (api, 3.10 MB). Its task list `22222222-bbbb-4bbb-8bbb-222222222222` is now orphaned.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session '33333333-cccc-4ccc-8ccc-333333333333'
```
> Deleted #3 (api, 25 KB).

(All three results simulated. `--delete-tasks` is absent because the user did not opt in; it would be appended to each
command otherwise. A failed deletion would be reported as failed, with no `rm` fallback.)

## Tool call 6: Bash (orphan task lists)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" orphan-task-lists
```

Simulated result: one orphan list.

> | Task List ID | Tasks | Last Modified |
> |-------------|-------|---------------|
> | 22222222-bbbb-4bbb-8bbb-222222222222 | 4 | 47 days ago |

## Tool call 7: AskUserQuestion

"Found 1 orphan task list with no matching session. Delete it?" Options: All / Select / None.

Simulated answer: None, so no `delete-task-list` call is made. Had the user answered All, the call would be:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-task-list '22222222-bbbb-4bbb-8bbb-222222222222'
```

## Final reply shown to the user

> Deleted 3 old sessions and freed 9.225 MB. I kept the 2 short or empty sessions and the 1 orphan task list, as you
> chose.

Again, this outcome is simulated; nothing was actually deleted.
