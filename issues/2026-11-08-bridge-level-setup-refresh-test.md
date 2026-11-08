## Summary
No bridge-level test checks that a setup-refresh envelope ends in exit 1 with `isolation_profile_unavailable`.

## Environment
- **Product/Service**: `codex-review-bridge` (`plugins/codex-kit/skills/codex-review-bridge/scripts/bridge-invoke.mjs`) and its smoke test `codex-review-bridge-total-inspection-failure.mjs`
- **Region/Version**: found in PR #681, head `f55c605f98d0616afd8c2430119818d74473424b` (follow-up to #652)
- **Browser/OS**: Windows and POSIX

## Reproduction Steps
1. Read the smoke test: it calls `isTotalInspectionFailure` directly with synthetic envelopes.
2. Break how `main()` reports the failure (the category string or the exit code) while leaving the detector alone.
3. Run the smoke test.

## Expected Behavior
A test fails when `main()` stops reporting `isolation_profile_unavailable` with exit 1 for a zero-finding setup-refresh envelope.

## Actual Behavior
The assertions cover the detector only, so a regression in the failure category or the exit status from `main()` would not be caught. Not reproduced; reasoned from the test.

## Impact
**Low** - Test coverage only. Adding it needs a fake `codex` that returns a chosen envelope through the exec library's output-file flow (a `.cmd` stand-in on Windows), which is why it was not added in the PR.

## Additional Context
- Found in PR #681 (https://github.com/AndreHahm/andres-cc-marketplace/pull/681), head `f55c605f98d0616afd8c2430119818d74473424b`.
- Reviewer: CodeRabbit, severity Trivial (nitpick), value rated Low. Thread: the nitpick in review https://github.com/AndreHahm/andres-cc-marketplace/pull/681 on `plugins/codex-kit/scripts/smoke-tests/codex-review-bridge-total-inspection-failure.mjs` line 149 (no inline thread to link).
- The `isTotalInspectionFailure` wording itself is covered; a paraphrase case ("setup refresh failed") was added to the smoke test in the same PR.
