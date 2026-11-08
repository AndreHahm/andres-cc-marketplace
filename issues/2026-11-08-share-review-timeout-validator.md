## Summary
codex-kit parses `CODEX_KIT_REVIEW_TIMEOUT_MS` separately in the bridge and in the guardrails fallback, so the two rules can drift apart again.

## Environment
- **Product/Service**: codex-kit (`codex-review-bridge`, `codex-windows-guardrails`) and `scripts/marketplace_ci/review.py`
- **Region/Version**: Node.js and Python; found while fixing #660

## Reproduction Steps
1. Open `plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs` (around lines 635-643) and `plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs` (around lines 884-891).
2. Compare how each reads `CODEX_KIT_REVIEW_TIMEOUT_MS`.
3. Open `scripts/marketplace_ci/review.py` (`_per_call_seconds`, around lines 1723-1729) and compare its parse of the same variable.

## Expected Behavior
One definition of what a valid `CODEX_KIT_REVIEW_TIMEOUT_MS` is (a positive integer no greater than 2147483647), used by every reader, so a change to the rule lands everywhere at once.

## Actual Behavior
- The bridge and the fallback each carry their own copy of the same check and the same message. They match today, but nothing keeps them matching.
- That is how #660 happened: PR #659 added the upper bound to `guarded-dispatch.mjs` only, and the bridge stayed unbounded until #660.
- `runCodexExec` (`plugins/codex-kit/scripts/lib/codex-exec.mjs`) now also rejects `timeoutMs` above 2147483647, so the timer itself is protected. The two parsers can still diverge on a later change, for example a lower bound, a unit change, or accepting a suffix.
- `_per_call_seconds` in `review.py` is a third parse. Its comment says it must agree with the bridge, but it has no upper bound: 2147483648 is read there as a valid budget, while the bridge now rejects it.

## Error Details
~~~
None. No user-visible failure today; this is a drift risk.
~~~

## Visual Evidence
None.

## Impact
**Low** - Maintenance and drift risk only. There is no current user-visible bug, since both Node parsers and `runCodexExec` enforce the same bound after #660.

## Additional Context
- **Proposal:** one exported validator (for example `parseReviewTimeoutMs` in `plugins/codex-kit/scripts/lib/`) used by both Node scripts, with its own smoke test. Decide separately whether `review.py` mirrors the bound or asks `node`.
- **Constraints to check first:**
  - `bridge-invoke.mjs` and `codex-exec.mjs` are in `FALLBACK_FILES` in `plugins/git-kit/scripts/git-codex-parity-review.py`. A new shared module the fallback imports would need to be listed there too.
  - The guardrails fallback is meant to run from a verified snapshot of the files it needs (#650). Importing a shared module may conflict with keeping it self-contained.
- **Acceptance:**
  - One definition of the rule.
  - Both scripts reject 2147483648 and accept 2147483647 and 600000, with the same message.
  - `codex-review-bridge-trust-boundary.mjs` and `codex-windows-guardrails-preflight.mjs` pass.
  - The fallback file list is updated if needed.
- The change touches the fallback's integrity file list, so a `security-reviewer` pass is advisable.
- Related: #660 (the bridge fix), #659 (the fallback fix), #650, #568.
