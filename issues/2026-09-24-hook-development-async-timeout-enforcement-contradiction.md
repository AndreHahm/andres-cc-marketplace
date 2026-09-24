## Summary
`hook-development`'s `advanced-hooks.md` claims an async command hook's timeout is "still enforced,"
directly contradicting the official Claude Code hooks documentation, which states the timeout is *not*
enforced for a command hook run with `async: true`.

## Environment
- **Product/Service**: `plugin-devkit`'s `hook-development` skill
  (`plugins/plugin-devkit/skills/hook-development/references/advanced-hooks.md`, and its
  `.claude/skills/hook-development/references/advanced-hooks.md` mirror copy)
- **Region/Version**: this repo, found 2026-09-24 while running a `skill-tester` eval for the PR
  fixing issue #376 (`hook-development` timeout unit docs)

## Reproduction Steps
1. Read `advanced-hooks.md`'s "Async, Non-Blocking Format-and-Log" pattern section (around line 398).
2. Its "Characteristics" list states: "Timeout still enforced but doesn't slow Claude Code" for a
   command hook configured with `async: true`.
3. Compare against the official Claude Code hooks documentation
   (`code.claude.com/docs/en/hooks.md`, "Common fields" table, `timeout` field description).

## Expected Behavior
`advanced-hooks.md`'s claim about async-hook timeout enforcement should match the official docs.

## Actual Behavior
The official docs state the opposite: "Claude Code doesn't enforce it on a command hook you run with
`async: true`." Verified live via two separate fetches against that URL in this session, both
confirming the same exact quote.

## Impact
**Medium** — documentation-only, but could mislead someone authoring an async hook into believing a
long-running background script will still be killed at the configured timeout, when in fact Claude
Code does not enforce any timeout on it at all.

## Additional Context
This line is pre-existing content, untouched by the currently-open PR for issue #376 (that PR only
touched the `timeout` field's *unit*, not this enforcement claim) — filed as a separate issue rather
than folded into that PR.

Suggested fix direction (not mandated): correct or remove the "Timeout still enforced but doesn't slow
Claude Code" characteristic, replacing it with accurate wording (e.g. "Timeout is not enforced for
async hooks — the process is not killed if it runs long; async only removes the blocking wait, not the
timeout guarantee"), and sweep the rest of `advanced-hooks.md` and the wider `hook-development` skill
for the same claim in case it recurs elsewhere.

**Related, not a duplicate:** #376 — same skill, different fact (timeout *unit*, not *enforcement*).

Suggested labels: `t: bug`, `t: documentation`, `s: triage`, `p: medium`, `a: ai-setup`
