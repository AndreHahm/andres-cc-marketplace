# Task 1: "Find old and empty sessions I could delete to save disk space."

Plan-only: nothing was executed. The script result and the answer are simulated.

## Ordered tool calls

1. Bash (read-only; finds candidates, deletes nothing):

   ```bash
   python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" cleanup --older-than 30d --min-messages 3
   ```

   Simulated result: `candidates` with 3 entries, `total_size_bytes` = 1264640.
   The user gave no thresholds, so I use the skill's 30 days / 3 messages and say so.

2. Show the reply below (full list and total) before asking anything.

3. AskUserQuestion:
   - Question 1, "Delete these 3 sessions (1.2 MB)?" Options: "Keep all" (delete nothing) / "Delete all 3" / "Select which to keep" (I ask which ones to skip)
   - Question 2, "If sessions are deleted, also delete their associated tasks?" Options: "No, keep tasks (default)" / "Yes, delete tasks too"
   - Simulated answers: "Keep all" and "No, keep tasks (default)".

4. No `delete-session` call, and so no post-cleanup orphan check.

## Reply shown to the user

I searched for sessions older than 30 days or with fewer than 3 messages. This search deletes nothing.

| # | Session ID | Project | Reason | Messages | Age | Size |
|---|-----------|---------|--------|----------|-----|------|
| 1 | 11111111-aaaa | /home/jane/webapp | Older than 30 days | 84 | 72d | 1.2 MB |
| 2 | 22222222-bbbb | /home/jane/webapp | Empty | 0 | 12d | 2 KB |
| 3 | 33333333-cccc | /home/jane/notes | Fewer than 3 messages | 2 | 5d | 4 KB |

**Total reclaimable: 1.2 MB.** Row 1 holds a real conversation; review it before choosing deletion.

(After the simulated "Keep all") Nothing was deleted.
