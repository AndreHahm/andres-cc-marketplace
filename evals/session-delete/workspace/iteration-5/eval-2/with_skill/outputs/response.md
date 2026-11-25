# Reply shown to the user

Finding and bulk-deleting old sessions is outside `session-delete`, which removes one session you have already
named. `session-cleanup` is the skill for finding sessions by criteria (old, empty, tiny) and deleting them, so I'm
handing your request to it. Nothing has been deleted, and nothing may be deleted without your explicit confirmation.

If you only want one particular session removed, give me its ID and I'll preview it here first.

# Tool calls, in order

1. `Skill(session-cleanup)` with args: `Find and delete all my old sessions.`

   "Old" has no cutoff in your request. I don't pick one here; settling it, listing candidates and confirming
   deletion belong to `session-cleanup`.

No Bash calls from `session-delete`: no `session-detail` (there is no session ID to preview), no `delete-session`,
no loop over sessions, and no `rm`.

If the `session-cleanup` dispatch fails, I stop and tell you; I don't reimplement bulk deletion with this skill.

# Simulation notes

Plan only: the `Skill` call was not made, and no command result or user answer was simulated. I was not given
`session-cleanup`'s text, so I don't list its commands.
