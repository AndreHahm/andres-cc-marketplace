# Task 2 (plan only)

## Ordered tool calls

1. Skill(session-delete) with args `abc123` (planned, not run).

session-cleanup is not used: no `cleanup` command, AskUserQuestion or `delete-session` call from it. Its "When NOT to Use" sends one specific, already-identified session to `session-delete`, which owns the confirmation. Nothing about that skill's own calls is simulated, because I did not read it.

## Reply to the user

You named one specific session (abc123), so this is a job for `session-delete`, not the bulk `session-cleanup` search. I'm handing it over; nothing has been deleted yet, and you'll be asked to confirm before anything is.
