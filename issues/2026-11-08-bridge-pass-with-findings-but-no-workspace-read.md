## Summary
A Codex pass that reports findings but could not read the workspace is counted as complete, and its slice can be skipped in a later round.

## Environment
- **Product/Service**: `codex-review-bridge` (`isTotalInspectionFailure` in `plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs`) and `cross-model-review`'s scoped rounds
- **Region/Version**: found in PR #681, head `357a7fafc436f89aaac8c85e90070eb3fe4810a5` (follow-up to #652)
- **Browser/OS**: Windows, local Codex CLI with the intermittent sandbox setup failure

## Reproduction Steps
1. Run a Codex pass on Windows while the sandbox setup refresh fails (`helper_unknown_error`).
2. The reviewer returns findings taken from the embedded diff and a note that no workspace file could be read.
3. Check how `cross-model-review` records the pass and whether a later round may skip its slice.

## Expected Behavior
The findings are kept, the pass is marked incomplete (it could not check anything outside the embedded diff), and a later round does not skip its slice until a pass really inspected the workspace.

## Actual Behavior
`isTotalInspectionFailure` returns true only for a zero-finding envelope, so a pass with findings is counted as complete. Not reproduced as a skipped slice; reasoned from the code.

## Impact
**Low-Medium** - Coverage can be overstated for the files outside the embedded diff. The zero-findings-only rule is deliberate: a pass with findings must never be rewritten into a failure, and the earlier security review relied on that. Changing it touches the bridge's pass/fail logic and the planner's completed-slice bookkeeping, so it needs its own design and security review.

## Additional Context
- Found in PR #681 (https://github.com/AndreHahm/andres-cc-marketplace/pull/681), head `357a7fafc436f89aaac8c85e90070eb3fe4810a5`.
- Reviewer: CodeRabbit, round 2, severity Minor by its label. Thread: https://github.com/AndreHahm/andres-cc-marketplace/pull/681#discussion_r4507838044
- In round one of the local gate on this PR, all four Codex passes hit the flake and still returned useful findings from the embedded diff, so the findings must be kept whichever way this is decided.
