# Session Timeline Skill — Test Output

## User task
"Just give me a simple sorted list of my sessions, I don't care about patterns or gaps."

## Decision
Declined to run `session-timeline` and redirected to `session-list` instead.

## Reasoning
The `session-timeline` skill's own scope explicitly excludes this request. Its description states:
"For a simple sortable inventory (not chronological pattern analysis), use session-list instead."
The "When NOT to Use" section repeats this: "A simple sortable inventory (not chronological pattern
analysis) -> use session-list instead."

The user's phrasing ("simple sorted list," "I don't care about patterns or gaps") maps directly onto
that excluded case — they explicitly disclaimed interest in the cadence/gap/pattern analysis that
`session-timeline` exists to provide. Running the timeline script (`session_store.py timeline`) would
have produced a chronological, pattern-oriented view the user said they didn't want, so the correct
behavior per the skill's own routing guidance was to decline and point to the right tool rather than
force the request through this skill.

## Command run
None. The timeline script (`python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session_store.py" timeline --project
"$(basename $(pwd))" --format json`) was intentionally not executed, since it belongs to the excluded
use case.

## Response given to the user

> It sounds like you just want a straightforward sorted list, not a cadence/gaps/pattern view — that's
> exactly what `session-timeline` says *not* to use itself for. Let's use **session-list** instead,
> which gives a simple sortable inventory of your sessions. Want me to run that?
