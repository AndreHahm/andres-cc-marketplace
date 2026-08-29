## Summary
A regression test that runs a tampered copy of a script must place that copy beside the original (not a generic temp directory), or the copy's own relative imports/asset resolution can break and produce a vacuous pass for the wrong reason — not a named convention anywhere in the repo.

## Environment
- **Product/Service**: `codex-kit` plugin (source instance: a stop-review-gate hook's own smoke test)
- **Region/Version**: this repo, found during PR #112 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A regression test tampers with a copy of a hook script to verify the hook's own catch-path/error-handling behavior.
2. The tampered copy is placed under the OS temp directory rather than beside the original script.
3. The original script has relative imports/asset references (e.g. `./lib/...`) that only resolve correctly from its own directory.
4. Run the tampered copy: Node/the interpreter exits during module loading (before the catch path under test ever runs) because the relative imports can't resolve from the temp location.
5. The test's own "non-zero exit means regression detected" assertion still reports a pass — for a reason completely unrelated to the code path it was meant to exercise.

## Expected Behavior
A tampered-copy regression test should place the copy beside the original script (removing it in a `finally` block) so relative imports/asset resolution stay intact, ensuring the test actually reaches and exercises the intended code path.

## Actual Behavior
The tampered copy under the OS temp directory crashed during module loading; the test's assertion still passed, but vacuously — it never reached the catch-path logic it claimed to verify.

## Impact
[Severity: Medium] A vacuously-passing regression test provides false confidence — it would not catch a real regression in the logic it's supposed to guard. The specific instance was already fixed in `codex-kit`'s PR #112 (commit `53b04cac0a`), confirmed the controlled-negative test now fails for the intended reason after the fix. This issue is about the *general* convention: no `.claude/rules/*.md` file currently states "a tampered-copy regression test must run beside the original, not a generic temp directory" — any other test built the same way (copy to temp dir, tamper, run) could reproduce the same vacuous-pass failure mode.

## Additional Context
Mined from PR #112's own review history (`coderabbitai[bot]`; 28 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #112` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/112#discussion_r3843129384
