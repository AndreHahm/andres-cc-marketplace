# Direct probe: async command-hook timeout enforcement (issue #388)

**Why this file exists:** eval-4's own prompt ("Timeout field unit and defaults") never asks about
async hooks, so its `with_skill` response doesn't exercise the corrected claim in
`advanced-hooks.md`'s Pattern 9. This is a supplementary, targeted probe — dispatched separately,
after the #388 fix — that directly forces engagement with that claim, giving a non-vacuous
confirmation that the fixed skill content is what the model actually surfaces. Referenced from
`with_skill/grading.json`'s assertion 5 evidence field instead of describing this only in prose.

## Prompt given to the agent

> I'm configuring a PostToolUse command hook with `async: true` and a `timeout: 5`. If my script
> runs for 30 seconds, will Claude Code kill it at the 5-second timeout, or does the timeout not
> apply to async hooks?
>
> (Agent instructed to read hook-development's SKILL.md and references first, then answer directly
> as if a user asked it.)

## Agent's full answer

No — Claude Code will not kill your script at 5 seconds. With `async: true`, the `timeout` value is
not enforced against the running process.

Per the hook-development skill's own reference material (`references/advanced-hooks.md`, Pattern 9:
"Async Hook for Slow Operations"), which documents exactly this combination:

> **Timeout is not enforced — the process isn't killed if it runs long; `async: true` only removes
> the blocking wait, not the timeout guarantee.**

So concretely, for your case:
- Claude Code will not wait for your hook to finish before continuing (that's what `async: true` buys
  you — the blocking wait is removed).
- Your 30-second script will keep running in the background to completion; it will not be killed at
  the 5-second mark despite `timeout: 5`.
- The `timeout` field's normal killing behavior only applies to synchronous (blocking) command hooks.
  Once you set `async: true`, that guarantee goes away — the field stops being a hard cap on
  wall-clock runtime.

Practical implications also called out by the same pattern/skill:
- Async hooks cannot block tool execution and cannot return a decision — use them only for side
  effects (logging, metrics, webhooks, notifications, file I/O), never as a safety/validation gate.
- Pair `async: true` with `onError: "warn"` since background failures don't affect Claude's execution
  anyway.
- If you actually need the 5-second cap enforced, don't use `async: true` — a synchronous command
  hook is where `timeout` acts as a real kill switch.

**Source verified:** read `plugins/plugin-devkit/skills/hook-development/SKILL.md` (Hook Handler
Fields table, describing `async` as background/non-blocking) and
`plugins/plugin-devkit/skills/hook-development/references/advanced-hooks.md` (Pattern 9, lines
~370-401), which contains the explicit statement quoted above.

## Note on wording drift

The quoted line above ("only removes the blocking wait, not the timeout guarantee") is the *first*
corrected wording, which this session's own `cross-model-review` pass (Codex, high confidence)
subsequently found self-contradictory and superseded with: "`async: true` removes both the blocking
wait and the timeout guarantee." This probe's substance — that the timeout is not enforced for async
hooks — is unaffected by that later wording refinement; the probe was not re-run against the final
wording.
