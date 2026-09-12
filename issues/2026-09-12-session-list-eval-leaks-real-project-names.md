## Summary
`session-kit`'s `session-list` eval output (already on `main`, from PR #284) persists real local
project directory names — the same account-metadata redaction gap already fixed elsewhere in
`workmanagement-kit`'s own eval outputs.

## Environment
- **Product/Service**: `session-kit` (`session-list` skill)
- **Region/Version**: this repo, `main`, file added by commit `7de4a793` (PR #284)

## Reproduction Steps
1. Open `evals/session-list/workspace/iteration-1/eval-2/with_skill/outputs/output.md`.
2. Note the `path` fields already use a placeholder username (`devuser`), showing a prior partial
   redaction pass happened — but the `project` fields (e.g. `ggsad`) are real project/repository
   directory names, not placeholders.

## Expected Behavior
Per the same redaction convention `FOUNDATION_CONTRACTS.md` documents for `workmanagement-kit`'s own
eval outputs (and the precedent set by GitHub issue #251): any tracked eval artifact narrating a
real local-environment run should have account/environment-identifying values — including project
directory names — replaced with placeholders before being committed.

## Actual Behavior
The username portion of local paths was redacted (`devuser`), but the `project` field (multiple
real project names, e.g. `ggsad`) was left as real values in a tracked, committed file.

## Impact
**Medium** — this discloses the names of real local project directories on the machine that ran the
eval, similar in kind (though a different specific value) to the account-metadata leaks already
found and fixed in `workmanagement-kit`'s own eval outputs during this same review cycle (PR #314).

## Additional Context
Found live while verifying a related Codex finding on PR #314 (a different, `workmanagement-kit`
eval leaking a real Linear team ID and a list of real GitHub repository names) — this file is
unrelated to that PR (already merged on `main` via PR #284, a `session-kit` change) and is filed
here as a separate, out-of-scope-for-that-PR follow-up rather than fixed inline.

**Suggested next step** (not prescribing the fix): redact the `project` field's real values the
same way the `path` field's username was already redacted, and sweep the rest of
`evals/session-list/` (and any other `session-kit` eval output) for the same pattern.
