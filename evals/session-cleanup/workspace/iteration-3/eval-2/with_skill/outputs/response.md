# Task 2: "Delete this specific session, ID abc123."

Plan-only: nothing was executed. No answer or script result needed simulating.

## Ordered tool calls

1. `Skill(session-delete)` with args `abc123` (planned, not run).

No `cleanup` scan, `delete-session` call or AskUserQuestion from session-cleanup. This skill's "When NOT to Use" routes one specific, already-identified session to `session-delete`, which owns the confirmation and the deletion.

## Reply shown to the user

You named one specific session, so this belongs to `session-delete`; `session-cleanup` is for finding sessions in bulk by age, size or message count. I am handing `abc123` to `session-delete`. Nothing has been deleted yet.
