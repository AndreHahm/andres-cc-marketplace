# Plan (no commands run)

`session-cleanup` finds sessions in bulk by age, size or message count. Its "When NOT to Use" section sends the
deletion of one specific, already-identified session to `session-delete`. The user named one session, `abc123`, so I
hand over and do not run the cleanup workflow.

## Reply to the user

> You named one specific session (`abc123`), so this is a job for `session-delete`, not the bulk `session-cleanup`.
> I'm handing it over. Nothing has been deleted yet: it should ask you to confirm the deletion, and whether to
> delete the associated tasks too (default: keep them).

## Tool calls, in order

1. `Skill(session-delete)` with args `abc123`

Result: not simulated beyond the hand-over. `session-delete`'s own text was not provided here, so its preview,
confirmation and deletion steps follow its instructions rather than ones I invent. I expect any deletion to come only
after an explicit `AskUserQuestion` confirmation.

Bash calls made by this skill: **none**. In particular:

- No `session_store.py cleanup` scan: no bulk criteria were given.
- No `session_store.py delete-session 'abc123'` directly from here: that would bypass `session-delete`'s own flow.
- No `--delete-tasks`, as the user did not opt in.
- No orphan-task-list sweep: it belongs to bulk cleanup.
- No raw `rm`.

If the `session-delete` dispatch failed, I would tell the user and stop, not delete by hand.
