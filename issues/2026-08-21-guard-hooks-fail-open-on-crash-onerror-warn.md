## Summary
All 5 of `git-kit`'s `PreToolUse` guard hooks (`guard-raw-commit.sh`, `guard-raw-pr-ops.sh`, `guard-raw-branch-create.sh`, `guard-raw-pr-review.sh`, `guard-raw-destructive-cleanup.sh`) are registered with `onError: "warn"` while each script itself runs under `set -euo pipefail` — meaning an unexpected crash inside any of them (not the deliberate, JSON-emitting deny path, but a genuine script failure) causes the security gate to fail **open**: the guarded raw command goes through unguarded, with only a hidden warning logged as evidence.

## Environment
- **Product/Service**: `git-kit`'s `hooks/hooks.json` PreToolUse registrations
- **Region/Version**: this repo, found during `plugin-lifecycle-downstream`'s Phase 5 audit of `feat/review-findings-handling` (commit `2e74f82` base)

## Reproduction Steps
1. Trigger any raw command one of the 5 guard scripts is meant to intercept (e.g. a raw `gh api repos/*/pulls/*/comments/*/replies` call with no valid marker).
2. Cause the guard script itself to fail unexpectedly before it reaches its deny branch — e.g. a transient `git rev-parse` edge case, a `jq`/`date` hiccup, or an unbound-variable slip not already handled by the script's explicit guards.
3. Observe: per `hook-development`'s own `references/how-hooks-work.md`, `onError: "warn"` means "Hook fails → Error logged as warning → Claude continues → Plugin not affected" — the raw command is allowed through, not denied.

## Expected Behavior
A blocking security gate should fail closed on an unexpected internal error — either deny by default on any non-zero exit that isn't the script's own deliberate JSON-deny path, or emit a generic "guard could not verify this command" deny via a `trap` before exiting on an unhandled error.

## Actual Behavior
`onError: "warn"` on all 5 registrations means any crash inside the guard script is silently logged and the guarded command proceeds — the intended block never happens.

## Impact
**Major** — this is the security-gate equivalent of a null check that swallows the exception: the mechanism exists specifically to hard-block certain raw git/gh commands, but its own internal-failure path bypasses that exact protection. Not exploitable by a passive bug (requires an actual crash to trigger), but any crash — accidental or engineered — silently defeats the gate with no visible signal beyond a warning most sessions won't notice.

## Additional Context
- Found by `hook-reviewer` during a scoped audit of `plugins/git-kit/hooks/scripts/guard-raw-pr-review.sh` (this session's own change to that file was unrelated to this finding — the `onError`/`set -e` combination is pre-existing and shared by all 5 sibling guards, unchanged this session).
- `hooks/hooks.json` registers all 5 under the same `PreToolUse` matcher with `"onError": "warn"`.
- `hook-development/references/how-hooks-work.md` documents `onError: "fail"` as the correct choice "for critical validation" where "Claude stops (for blocking hooks)" — this repo's own docs already name the right fix.
- Suggested follow-ups (not implemented as part of this issue):
  - Change `onError` to `"fail"` for all 5 registrations, or
  - If `"warn"` must stay (per `how-hooks-work.md`'s cascade-prevention note), add a `trap` in each script that emits the deny JSON with a generic "guard could not verify this command" reason on any unexpected exit, so a crash still produces a decision rather than silence.
  - Either way, treat this as a batch fix across all 5 scripts + `hooks.json`, not a fix to just one — they share the same registration shape.
