## Summary
`hooks-schema-check.sh` flags a "Missing 'matcher' field" error on hook events that don't support
matchers at all, producing false positives on otherwise-correct `hooks.json` files

## Environment
- **Product/Service**: `plugin-devkit`'s `hooks-schema-check.sh` (`plugins/plugin-devkit/hooks/hooks-schema-check.sh`, mirrored at `.claude/hooks/hooks-schema-check.sh`)
- **Region/Version**: n/a

## Reproduction Steps
1. Run `hooks-schema-check.sh` against `plugins/context-kit/hooks/hooks.json`.
2. Observe two errors: `Stop[0]: Missing 'matcher' field` and `UserPromptSubmit[0]: Missing 'matcher' field`.
3. Check `hook-development/SKILL.md`'s own "Matchers" section: it documents a table of events with
   "No matcher support — always fires", listing exactly `Stop`, `UserPromptSubmit`, `TeammateIdle`,
   `TaskCreated`, `TaskCompleted`, `WorktreeCreate`, `WorktreeRemove`, `CwdChanged`.
4. Confirm both flagged entries are on that no-matcher-support list — omitting `matcher` there is
   correct, documented behavior, not a defect in the checked file.

## Expected Behavior
`hooks-schema-check.sh` should not require `matcher` on an event type that `hook-development`'s own
documentation states doesn't support matchers.

## Actual Behavior
The checker requires `matcher` unconditionally on every event type, producing a false-positive error
for `Stop`/`UserPromptSubmit` (and presumably the other five no-matcher-support events too).

## Impact
**Low-Medium** — false positives only; no real `hooks.json` is actually broken by this. But it adds
noise to every schema-check run against a `hooks.json` using one of these event types, and risks
training reviewers/agents to distrust or ignore real schema-check failures.

## Additional Context
Found as a drive-by while fixing GitHub issues #358/#359 in this session — unrelated to that fix,
filed separately per this repo's own convention for drive-by findings.

Suggested fix direction (not mandated): in `hooks-schema-check.sh`'s per-event validation logic, skip
the matcher-required check for event types on `hook-development`'s own no-matcher-support list (or
cross-reference that same list so the two never drift apart).

Suggested labels: `t: bug`, `s: triage`, `a: ai-setup`, and an appropriate `p:` tier per
`docs/github-label-taxonomy.md` (likely `p: low` or `p: medium` — validation noise, not a live break).
