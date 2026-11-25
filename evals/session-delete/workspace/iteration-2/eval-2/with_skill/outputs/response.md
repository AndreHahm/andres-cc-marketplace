# Task 2: find and delete all my old sessions

Nothing was run. No script result or answer needed simulating in this skill.

## Ordered tool calls

1. `Skill(session-cleanup)` with the user's request (not executed in this test). This request names no specific
   session; it is a bulk, criteria-based search, which session-delete excludes.

No `session-detail`, `delete-session`, AskUserQuestion or `rm` call is made from session-delete. I did not read
session-cleanup, so its steps are not simulated here.

## Reply to the user

Finding and deleting old sessions in bulk is handled by `session-cleanup`; `session-delete` removes one session
you have already identified. I'm handing this request to `session-cleanup`. Nothing has been deleted.
