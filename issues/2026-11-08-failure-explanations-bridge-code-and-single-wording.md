## Summary
Failure explanations: have the review bridge emit a stable `code` and `facts`, and keep the sandbox-failure wording in one place.

## Environment
- **Product/Service**: `plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs` and `scripts/marketplace_ci/review.py`
- **Region/Version**: branch `fix/windows-reviewer-sandbox-latch` (Part A leftovers of #676)
- **Browser/OS**: not platform-specific

## Reproduction Steps
1. Read `classify_failure` and `FAILURE_CATALOGUE` in `scripts/marketplace_ci/review.py`.
2. Read the sandbox-failure handling in `bridge-invoke.mjs`.
3. Compare where the sandbox-failure wording is defined.

## Expected Behavior
The bridge reports a stable machine-readable `code` (and `facts`) per failure. `review.py` consumes it and keeps a single definition of the wording.

## Actual Behavior
- The bridge does not emit the `code` and `facts` fields that the #676 plan proposed, so `classify_failure` works from error text.
- The sandbox-failure wording is defined in two places: `review.py` and `bridge-invoke.mjs`.

## Impact
**Low** - Failures are already explained in plain words. Text matching can drift out of step with the bridge's messages, and two copies of the wording can diverge.

## Additional Context
- Deliberately left out of the #676 PR (Part A) to keep it to the Python side. Recorded here so it is not silently dropped.
- Suggested labels: enhancement, `p: low`.
- Related: #676.
