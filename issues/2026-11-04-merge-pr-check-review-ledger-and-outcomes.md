## Summary
`merge-pr` does not check the review ledger or `.claude/review-outcomes/`, so a PR can reach the merge step with its review outcomes never recorded.

## Environment
- **Product/Service**: git-kit, `plugins/git-kit/skills/merge-pr/SKILL.md`, with `handling-review-findings` and `plugins/git-kit/scripts/git-review-ledger.py`
- **Region/Version**: current `main`

## Reproduction Steps
1. Fix a PR's review findings without going through to the end of `handling-review-findings`.
2. Run `merge-pr` on that PR.
3. Readiness passes, with no mention of the missing `.claude/review-outcomes/pr-<N>.json`.

## Expected Behavior
`merge-pr`'s readiness checks cover the review ledger and the PR's `review-outcomes` file, so unrecorded outcomes surface while they can still be added.

## Actual Behavior
Recording lives only in `handling-review-findings`: dispositions in its fix self-review (`references/fix-self-review.md` 4e) and promotion when step 8 ends with no trigger posted. When that skill does not run, or does not reach that point, nothing records the outcomes and nothing notices. `merge-pr`, its references and its test scenarios never mention the ledger or the outcomes files.

PR #638 is one instance: its CodeRabbit findings were fixed without the ledger, and `merge-pr` reported the PR ready. The gap was caught only because the maintainer asked at the merge confirmation, and the file was then added in `b0e89c0b`.

## Impact
**Low** - Merging is unaffected, but the outcomes corpus that #586 builds its evals from silently loses entries, and they are hard to add afterwards because a merged PR leaves `main` unable to take a direct commit.

## Additional Context
**To decide:**
1. Blocking check or advisory disclosure. `merge-pr` has both kinds in its step 2, and a PR with no findings needs no outcomes file, so a blocking check needs a reliable way to tell the two cases apart.
2. What the check compares. A missing `pr-<N>.json` alone can't show whether a PR had findings, and the working ledger is local and gitignored, so it may be absent in another session or checkout.
3. Timing. Promotion has to land before the PR's last push, and that records-only commit moves the head SHA, so CI and the Codex review run again (see #639). A check at merge time should fire before readiness is confirmed, not after.

**Not a claim of how often this happens:** some recently merged PRs have no outcomes file, but that alone doesn't show findings were missed.

**Related, not duplicates:** #578 (built the ledger), #586 (uses the corpus), #610 (per-PR outcomes files), #639 (cost of re-running CI).
