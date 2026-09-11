## Summary
Add an eval-fixture exemption to `.secretlintignore` so `scan-staged-files.sh` stops flagging legitimate skill-tester eval fixtures containing intentionally-fake secret-shaped content

## Environment
- **Product/Service**: `andres-cc-marketplace` repo tooling — `.secretlintignore` and `plugins/git-kit/scripts/scan-staged-files.sh` (the `commit` skill's step 7 sensitive-filename check)
- **Region/Version**: N/A

## Reproduction Steps
1. Write a `skill-tester` Quick Workflow eval fixture for a skill that detects credential/token/secret exposure, with a filename containing one of the fixed sensitive-filename substrings (e.g. `session-transcript-credential.md`) and deliberately-fake secret-shaped content inside it (e.g. `AKIAFAKEEXAMPLE1234`).
2. Stage the fixture and run `git-kit`'s `commit` skill (or `scan-staged-files.sh` directly).
3. Observe the fixture gets flagged via the `*credential*` filename pattern.

## Expected Behavior
A skill-tester eval fixture under `evals/**/` that intentionally contains fake secret-shaped content for testing purposes should not need a manual override every time such an eval is committed.

## Actual Behavior
`scan-staged-files.sh`'s sensitive-filename patterns (`*secret*`, `*credential*`, `*password*`, `*token*`, etc.) match the fixture by filename alone. Since issue #295 (fixed via PR #299), the script also consults `.secretlintignore` as an exemption signal — that mechanism works correctly, but `.secretlintignore` currently has no entry covering `evals/` fixtures, so the flag still fires and requires a manual `AskUserQuestion` override each time.

## Error Details
~~~
scan-staged-files.sh flagged: evals/analyzing-security-and-privacy/workspace/iteration-1/eval-1/session-transcript-credential.md
(matched via the `*credential*` pattern in the sensitive-filename check)
~~~

## Visual Evidence
N/A

## Impact
**Low** — false positive only, no security exposure. Workaround exists (confirm and proceed past the flag via `AskUserQuestion`), but it will recur for every future `skill-tester` eval scenario that exercises credential/token/secret-detection skills.

## Additional Context
Related, not a duplicate: #295 (closed via PR #299) fixed the general mechanism — making `scan-staged-files.sh` consult `.secretlintignore` at all. This issue is narrower: that consulted file simply has no entry yet for eval-fixture files.

Proposed fix: add either a broad `/evals` entry or a narrower `evals/**/session-transcript-*.md`-style pattern to `.secretlintignore`. Per `.secretlintignore`'s own header comment/convention, it only lists entries verified (via a real `secretlint` run) to actually need the exemption, and prefers narrower filename-pattern entries over a blanket directory exemption where that's sufficient — the fix here should follow that same discipline rather than adding an unverified blanket entry.

Live reproduction: while committing `analysis-kit`'s new `analyzing-security-and-privacy` skill (Wave 2 Group 3), the fixture `evals/analyzing-security-and-privacy/workspace/iteration-1/eval-1/session-transcript-credential.md` (a synthetic transcript built to test that skill's own credential-exposure detection logic) was flagged this way.

**Second occurrence, same session:** the local issue-draft file for this very issue was itself flagged (filename contains `secretlintignore`), with no secret content — see the follow-up comment on the filed issue. The fix here should likely also cover `issues/` drafts that legitimately discuss secret-scanning tooling by name, not just `evals/` fixtures.
