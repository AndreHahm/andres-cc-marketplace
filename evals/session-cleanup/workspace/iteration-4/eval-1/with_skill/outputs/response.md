# Task 1 (plan only; every result and answer below is simulated)

## Ordered tool calls

1. Bash (read-only; deletes nothing). You named no age, so I use the skill's 30-day example:
   `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" cleanup --older-than 30d --min-messages 3`
   Simulated result: 3 candidates, total_size_bytes 92160 (90 KB).
2. Show the reply below (full list first).
3. AskUserQuestion (one call, three questions):
   - Q1 header "Old": "Delete these 2 sessions at least 30 days old (80 KB)?" Options: "Delete both" / "Select some" (I ask which to skip) / "Keep all"
   - Q2 header "Short/empty": "Separately: delete this 1 recent empty session outside the 30-day age (10 KB)?" Options: "Delete it" / "Keep it"
   - Q3 header "Tasks": "For any session you delete, also delete its associated tasks?" Options: "No, keep tasks (default)" / "Yes, delete tasks"
   Simulated answers: "Keep all", "Keep it", "No, keep tasks (default)".
4. No deletion call: the user declined. No cleanup happened, so Step 4's orphan check is not run.

If a group were approved: one `delete-session <session-id>` call per approved ID through the script, one at a time, each reported; `--delete-tasks` only if Q3 is yes; then `orphan-task-lists`, with its own confirmation. Never `rm`.

## Reply to the user

I searched for sessions older than 30 days (my default, since you gave no age) and sessions with fewer than 3 messages at any age. Nothing has been deleted.

| # | Session ID | Project | Reason | Messages | Age | Size |
|---|-----------|---------|--------|----------|-----|------|
| 1 | aaa111 | /home/jane/projects/app | old | 120 | 75d | 70 KB |
| 2 | bbb222 | /home/jane/projects/app | empty | 0 | 45d | 10 KB |
| 3 | ccc333 | /home/jane/projects/site | empty | 0 | 4d | 10 KB |

Total reclaimable: 90 KB. By reason: 1 `old`, 2 `empty`.

- At least 30 days old: #1 and #2 (#2 is labeled `empty`, but it is also old enough; the script reports one reason per session).
- Recent and empty: #3 only. I ask about it separately.

After your simulated answers: nothing was deleted. Tell me if you want a different age.
