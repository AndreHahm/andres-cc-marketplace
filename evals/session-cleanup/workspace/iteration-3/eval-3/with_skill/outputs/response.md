# Task 3: "Clean up old sessions and also remove any now-orphaned task entries."

Plan-only: nothing was executed. Every script result and every answer is simulated.

## Ordered tool calls

1. Bash (read-only):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" cleanup --older-than 30d --min-messages 3
   ```

   Simulated result: 2 candidates, 40 KB total.

2. Show the candidate table (reply part 1).

3. AskUserQuestion:
   - "Delete these 2 sessions (40 KB)?" Options: "Delete both" / "Select which to keep" / "Cancel". Simulated answer: "Delete both".

4. AskUserQuestion (follow-up; default is not to delete tasks):
   - "Also delete each session's associated tasks?" Options: "No, keep tasks (default)" / "Yes, delete tasks too". Simulated answer: "Yes, delete tasks too" (the user agrees to everything).

5. Bash, one session at a time, reporting each:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session 11111111-aaaa --delete-tasks
   ```

   Simulated result: deleted, with its associated tasks.

6. Bash:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session 22222222-bbbb --delete-tasks
   ```

   Simulated result: deleted; no associated tasks.

7. Bash:

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" orphan-task-lists
   ```

   Simulated result: 1 orphan task list, `list-old-001` (not covered by steps 5-6).

8. Show the orphan table (reply part 2).

9. AskUserQuestion:
   - "Found 1 orphan task list with no matching session. Delete it?" Options: "All" / "Select" / "None". Simulated answer: "All".

10. Bash:

    ```bash
    python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-task-list list-old-001
    ```

    Simulated result: deleted.

## Reply shown to the user

**Part 1, before any deletion**

I used a 30-day age threshold and also included sessions with fewer than 3 messages:

| # | Session ID | Project | Reason | Messages | Age | Size |
|---|-----------|---------|--------|----------|-----|------|
| 1 | 11111111-aaaa | /home/jane/webapp | Older than 30 days | 14 | 64d | 36 KB |
| 2 | 22222222-bbbb | /home/jane/notes | Fewer than 3 messages | 1 | 41d | 4 KB |

**Total reclaimable: 40 KB.** I will ask before deleting sessions, and separately about their tasks.

**Part 2, after the session deletions**

- Deleted session 11111111-aaaa and its associated tasks
- Deleted session 22222222-bbbb (no associated tasks)

| Task List ID | Tasks | Last Modified |
|-------------|-------|---------------|
| list-old-001 | 3 | 2026-08-02 |

This list has no matching session. I will ask before deleting it.

**Part 3, after the orphan confirmation**

Done: 2 sessions (40 KB) and 1 orphan task list deleted, each through the script.
