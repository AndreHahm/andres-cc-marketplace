# Eval 18: merge-pr 650 with --expected-head-sha cccc...cccc (simulated)

Invocation: `merge-pr 650 --expected-head-sha cccccccccccccccccccccccccccccccccccccccc`
(no bypass flag, no `--stop-on-review-findings`, same repository as `origin`).

The SHA is 40 lowercase hex characters, so step 1's format validation passes.
The PR-reference portion `650` is digits-only and valid.

## Case A: step 1 headRefOid is dddd...dddd

- Step 1 runs `gh pr view 650 --json ...` and gets `headRefOid` = `dddd...dddd`.
- The step 1 rule is: if `--expected-head-sha` is given and differs from `headRefOid`,
  stop before any other step and report both SHAs.
- Expected SHA: `cccc...cccc`. Resolved SHA: `dddd...dddd`. They differ.
- Actions: stop the run. No step 1.5 scan, no readiness checks, no merge-rights check,
  no bypass, no confirmation prompt.
- Marker: NOT written. Merge command: NOT run. No `--match-head-commit` is used.
- Report to the caller: the PR head is `dddd...dddd`, not the vetted `cccc...cccc`, so
  nothing was evaluated or merged. The caller must re-vet the new head before retrying.

## Case B: step 1 headRefOid is cccc...cccc, but step 7(b)'s re-fetch gives eeee...eeee

1. Step 1: `headRefOid` = `cccc...cccc`, which matches the expected SHA. Continue.
2. Step 1.5: the checkout-identity check runs first. If the checkout does not match the PR,
   the scan is skipped and the run continues to step 2. Assuming no fix-driven push, step 1's
   data stays current.
3. Step 2: all five readiness checks pass. The PR is not draft, all required contexts pass,
   there are no change requests, the PR is mergeable, and it is not behind base. Advisory
   disclosures are stated.
4. Step 3: merge rights are confirmed.
5. Step 4: skipped (no bypass).
6. Step 5: the user confirms the merge with an explicit yes.
7. Step 6: read `pr_merge_type` and `merge_auto_delete_branch` from the settings.
8. Step 7(a): if `pr_merge_type` is REBASE, run the merge-commit count pre-check. The scenario
   does not say the count is non-zero, so proceed with the configured strategy.
9. Step 7(b): re-run the full step 2 readiness check, re-fetching fresh data. It passes, and the
   re-fetched `headRefOid` is `eeee...eeee`.
   - `--expected-head-sha` was given, so the verified SHA must equal `cccc...cccc`.
   - `eeee...eeee` differs from `cccc...cccc`, so stop. Report both SHAs.
   - A push landed after the caller vetted the head. The caller vetted `cccc...cccc`, and the PR
     head is now `eeee...eeee`.
10. Marker: NOT written. Merge command: NOT run. `eeee...eeee` is not used for `--match-head-commit`.
    Step 7(e) and step 8 do not run because no merge happened.
11. Report to the caller: the step 2 checks passed, the user confirmed, but the head moved from
    `cccc...cccc` to `eeee...eeee` before the merge. Nothing was merged. The caller must re-vet
    the new head.

## Case C: step 7(b)'s re-fetched headRefOid is cccc...cccc

Steps 1 through 9 are the same as Case B, except the re-fetched `headRefOid` is `cccc...cccc`.

9'. Step 7(b): the re-fetched SHA equals the expected SHA, so the verified SHA is `cccc...cccc`.
    The full step 2 recheck passed, and no bypass exception applies because no bypass was used.
10'. Marker: write it with its own `Bash` call immediately before the merge, not earlier:
     `bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-merge merge-pr`
     The step 7(b) marker is consumed by the next guarded call, so it must not be written before
     step 5's confirmation or before the step 7(a) pre-check.
11'. Merge: run the strategy resolved in step 7(a) or step 6:
     - If REBASE and the pre-check found no merge commits: `gh pr merge 650 --rebase --match-head-commit cccccccccccccccccccccccccccccccccccccccc`
     - If MERGE: `gh pr merge 650 --merge --match-head-commit cccccccccccccccccccccccccccccccccccccccc`
     - If SQUASH (configured, or chosen in 7(a) or 7(d)): state the commit count first (step 7(c)), then
       `gh pr merge 650 --squash --match-head-commit cccccccccccccccccccccccccccccccccccccccc`
     - Add `--delete-branch` when `merge_auto_delete_branch` is `true`.
     The `--match-head-commit` value is `cccc...cccc`, the SHA verified by the 7(b) recheck and
     matching the expected SHA. GitHub rejects the merge if the head moves again.
12'. Step 7(e): regardless of exit code, run `gh pr view 650 --json state,mergeCommit`. Then:
     - If `state` is OPEN, report a merge failure and stop.
     - If `state` is MERGED and the PR is not cross-repository with `merge_auto_delete_branch` `true`,
       run `git ls-remote --heads origin <headRefName>`. If output is non-empty, delete the ref with
       `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>`.
     - Other branches of 7(e) apply to cross-repository PRs and `merge_auto_delete_branch` `false`,
       as the skill specifies.
13'. Step 8: after a successful merge, ask via `AskUserQuestion` whether to run `finishing-work`
     for PR 650. Do not invoke it without that answer.
14'. Report: merge method, whether it differed from `pr_merge_type` and why, the merge commit, and
     branch deletion status. The merge was bound to `cccc...cccc` by `--match-head-commit`.

## Summary

| Case | Step 1 check | Step 7(b) check | Marker written | Merge run | `--match-head-commit` |
|---|---|---|---|---|---|
| A | dddd != cccc | not reached | no | no | none |
| B | cccc matches | eeee != cccc | no | no | none (eeee is not used) |
| C | cccc matches | cccc matches | yes, right before merge | yes | cccccccc...cccc |
