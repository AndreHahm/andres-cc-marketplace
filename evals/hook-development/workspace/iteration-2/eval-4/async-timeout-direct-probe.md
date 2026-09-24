# Direct probe: async command-hook timeout enforcement (issue #388)

**Why this file exists:** eval-4's own prompt ("Timeout field unit and defaults") never asks about
async hooks, so its `with_skill` response doesn't exercise the corrected claim in
`advanced-hooks.md`'s Pattern 9. This is a supplementary, targeted probe — dispatched separately,
after the #388 fix — that directly forces engagement with that claim, giving a non-vacuous
confirmation that the fixed skill content is what the model actually surfaces. Referenced from
`with_skill/grading.json`'s assertion 5 evidence field instead of describing this only in prose.

**Re-run 2026-09-24:** this probe was run twice. The first run (superseded, no longer quoted here)
captured the async-timeout line's first corrected wording, which this branch's own
`cross-model-review` pass then found self-contradictory and further corrected. This file now holds
only the second run, against the final wording, so nothing here quotes stale text.

## Prompt given to the agent

> I'm configuring a PostToolUse command hook with `async: true` and a `timeout: 5`. If my script
> runs for 30 seconds, will Claude Code kill it at the 5-second timeout, or does the timeout not
> apply to async hooks?
>
> (Agent instructed to read hook-development's SKILL.md and references first, then answer directly
> as if a user asked it, quoting the current characteristic line verbatim.)

## Agent's full answer

No — Claude Code will not kill your script at 5 seconds. When `async: true` is set on a command
hook, the `timeout` field is not enforced at all.

From the hook-development skill's own reference material:

- `references/advanced-hooks.md`, Pattern 9 ("Async Hook for Slow Operations"), under
  **Characteristics**:
  > "Timeout is not enforced — the process isn't killed if it runs long; `async: true` removes both
  > the blocking wait and the timeout guarantee"

- SKILL.md's Hook Handler Fields table (Command-only fields) states the same thing more concisely:
  > `async` — "`true` = background, non-blocking, command hooks only. Cannot block, cannot return
  > decisions, and delivers output on a later turn — never use for safety gates"

So with `async: true` and `timeout: 5`, your 30-second script will run to completion in the
background — Claude Code won't wait for it, won't block on it, and won't kill it at 5 seconds. The
`timeout` value becomes effectively meaningless for an async hook (you could remove it and behavior
would be unchanged). This is also why the skill's own type-decision guidance says async hooks
"cannot block, cannot return decisions" — they're for side effects only (logging, metrics,
notifications, file I/O), never for anything that needs to actually enforce a time limit or gate an
action.

If you need the 5-second timeout to actually be enforced (i.e., the process killed if it overruns),
you need a synchronous (blocking) command hook instead — drop `async: true`, and the timeout will be
enforced as documented in the Hook Handler Fields table.

**Source verified:** answered directly from
`plugins/plugin-devkit/skills/hook-development/SKILL.md` and
`plugins/plugin-devkit/skills/hook-development/references/advanced-hooks.md` (Pattern 9). No files
were modified for this probe — a read-only lookup task.
