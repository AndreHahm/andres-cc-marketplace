## Summary
A fixture loader accepted `null`/non-object elements inside its `reviews`/`comments`/`issue_comments` arrays — a later normalization step then crashed with an uncaught `AttributeError`, an exception type the caller's error handling wasn't built to catch.

## Environment
- **Product/Service**: `analysis-kit` plugin — `pr_review_fetcher.py` (`load_fixture`/`normalize`)
- **Region/Version**: this repo, found during PR #179 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Construct a fixture file: `{"reviews": [null], "comments": []}`.
2. Call `load_fixture` on this fixture — it passes validation despite containing a `null` array element.
3. `normalize()` then calls `.get` on that `None` value, raising an uncaught `AttributeError`.
4. `main`'s own error handling only catches `FetchError`, so the `AttributeError` propagates as an unhandled crash instead of a clean, reported error.

## Expected Behavior
An input loader should validate every element of an array field against the shape later code assumes ("is a JSON object"), raising the caller's own expected exception type (`FetchError`) on a null or malformed element — never let a later processing step be the one to discover the bad input, with an exception type the caller wasn't built to catch.

## Actual Behavior
A malformed fixture crashed with a Python traceback instead of a clean `FetchError` message, which the CLI's own error handling was specifically designed to present cleanly.

## Impact
[Severity: Medium] A fixture-driven test/dev path that crashes ungracefully on malformed input is a real usability gap for anyone hand-editing or generating fixtures. Fixed in `analysis-kit`'s PR #179 (commit `3a7a5b5`): `load_fixture` now validates every element of `reviews`/`comments`/`issue_comments` is a JSON object, raising `FetchError` on a null or non-object element instead of letting `normalize()` crash with an uncaught `AttributeError`. Covered by two new tests.

## Additional Context
Mined from PR #179's own review history (`coderabbitai[bot]`; 25 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #179` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/179#discussion_r3885947293
