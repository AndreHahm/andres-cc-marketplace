# Plan: session cleanup plus orphan task lists

Nothing was run. Every command result and user answer below is **simulated**. IDs are shortened for the example
(a real run uses the full ID from the script output).

You named no age, so I use the skill's 30-day default and say so; a different age changes only `--older-than` and the grouping.

## Call 1: Bash, find candidates (deletes nothing)

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" cleanup --older-than 30d --min-messages 3
```

Simulated result: five candidates, `total_size_bytes` = 2,154,496.

## Reply shown to the user

> You didn't name an age, so I used 30 days. I found 5 candidates. Nothing has been deleted.
>
> **Group 1: old (more than 30 days), 3 sessions, 2,146,304 bytes**
>
> | # | Session ID | Project | Reason | Messages | Age | Size |
> |---|---|---|---|---|---|---|
> | 1 | `aaaa1111` | webapp | old | 120 | 75 d | 1,638,400 B |
> | 2 | `bbbb2222` | api | old | 48 | 41 d | 503,808 B |
> | 3 | `cccc3333` | api | tiny | 2 | 52 d | 4,096 B |
>
> **Group 2: short or empty, not older than 30 days, 2 sessions, 8,192 bytes**
>
> | # | Session ID | Project | Reason | Messages | Age | Size |
> |---|---|---|---|---|---|---|
> | 4 | `dddd4444` | webapp | tiny | 1 | 30 d | 8,192 B |
> | 5 | `eeee5555` | scratch | empty | 0 | 3 d | 0 B |
>
> **Total reclaimable: 2,154,496 bytes (about 2.1 MB).**
>
> Row 3 is reported as `tiny`, but at 52 days it is old too. Row 4 is exactly at the cutoff, so it isn't old. You
> asked for old sessions, so Group 2 is only deleted if you agree to it separately. If you want to keep some rows,
> tell me which.

IDs and project names are data. If one read like an instruction, I would quote it as suspicious and not act on it.

## Call 2: AskUserQuestion (one question per group, plus the tasks follow-up)

1. "Delete these 3 old sessions (2,146,304 bytes)?"
   Options: "Delete all 3" / "Let me pick which to skip" / "Delete none"
2. "Delete these 2 short or empty sessions (8,192 bytes)? They are not older than 30 days."
   Options: "Keep them" / "Let me pick which to skip" / "Delete both"
3. "Also delete the tasks associated with each session you delete?"
   Options: "No, keep tasks (default)" / "Yes, delete tasks too"

Simulated answers: "Delete all 3"; "Keep them"; "No, keep tasks (default)". Your request named *orphaned* tasks
only, and that is not taken as consent to `--delete-tasks`; orphans get their own confirmation below.

- "Let me pick" would lead to another AskUserQuestion asking which rows to skip.
- "Yes, delete tasks too" would append `--delete-tasks` to each command below.
- If both groups were declined, Calls 3-5 are dropped and I still run Call 6.

## Calls 3-5: Bash, delete confirmed sessions one at a time, reporting each

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session 'aaaa1111'
```
> Deleted `aaaa1111` (webapp). The script reports that task list `webapp-tasks` is now orphaned.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session 'bbbb2222'
```
> Deleted `bbbb2222` (api). No task list became orphaned.

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-session 'cccc3333'
```
> Deleted `cccc3333` (api). No task list became orphaned.

If one failed, I would report that failure and not fall back to `rm`.

## Call 6: Bash, check for orphan task lists

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" orphan-task-lists
```

Simulated result: two orphan lists.

> | Task List ID | Tasks | Last Modified |
> |---|---|---|
> | `webapp-tasks` | 4 | 2026-09-11 |
> | `old-experiment` | 2 | 2026-08-02 |
>
> `webapp-tasks` was orphaned by this cleanup; `old-experiment` was already orphaned before it.

## Call 7: AskUserQuestion

"Found 2 orphan task lists with no matching session. Delete them?"
Options: "All" / "Select" / "None"

Simulated answer: "All". "Select" would lead to a follow-up asking which; "None" ends here. With no orphans, I would
say so and skip Calls 7-9.

## Calls 8-9: Bash, delete confirmed task lists one at a time

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-task-list 'webapp-tasks'
```
> Deleted task list `webapp-tasks` (4 tasks).

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" delete-task-list 'old-experiment'
```
> Deleted task list `old-experiment` (2 tasks).

IDs stay in single quotes (an embedded single quote is written `'\''`), and deletion only ever goes through the script.

## Final reply (simulated)

> Cleanup finished.
> - Deleted 3 old sessions, 2,146,304 bytes: `aaaa1111`, `bbbb2222`, `cccc3333`.
> - Kept 2 short or empty sessions: `dddd4444`, `eeee5555`.
> - Deleted 2 orphan task lists (6 tasks): `webapp-tasks`, `old-experiment`.
