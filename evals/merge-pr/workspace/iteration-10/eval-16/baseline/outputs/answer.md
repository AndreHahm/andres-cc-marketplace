# merge-pr 812 --stop-on-review-findings: step 7 onward (simulated)

## Note on the flag

The skill I am following does not define a `--stop-on-review-findings` flag. Step 1 recognizes only three
parts of `$ARGUMENTS`: the PR reference, `--bypass-codex-review "<reason>"` and `--expected-head-sha <sha>`.
The PR reference `812` is valid (digits only). The extra flag has no behavior attached to it anywhere in
the skill, so it changes nothing below. I would tell the user that this skill version ignores the flag and
does not stop on a late reviewer finding.

## Step 6 (already resolved)

`pr_merge_type` = `MERGE`. `merge_auto_delete_branch` is not given, so I use the default `true`.

## Step 7(a): rebase-compatibility pre-check

Skipped. It runs only when `pr_merge_type` is `REBASE`, and here it is `MERGE`.

## Step 7(b): final recheck, marker, merge

1. **Final recheck (the full step-2 readiness check, without the bypass exception).** These reads happen:
   - `gh pr view 812 --json isDraft,reviews,statusCheckRollup,mergeable,mergeStateStatus,headRefName,baseRefName,isCrossRepository,headRefOid`,
     then re-validate `headRefName`/`baseRefName` against `^[A-Za-z0-9._/@+=-]+$`.
   - The branch-protection required-check list:
     `gh api repos/{owner}/{repo}/branches/<baseRefName>/protection --jq '.required_status_checks.contexts'`.
   - Not-behind-base: `gh api repos/{owner}/{repo}/compare/<baseRefName>...<headRefName> --jq '.behind_by'`
     (same-repository PR).
   - Unresolved review-thread count: `bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review merge-pr`
     right before each `gh api graphql` `reviewThreads` page.

   Results, using the scenario's facts: not draft; every required check passes; no `CHANGES_REQUESTED` review;
   `MERGEABLE`; behind_by 0; 0 unresolved threads; the head SHA is unchanged.

   **The step-2 check does not read conversation comments.** Its `reviews` field covers review states only,
   and the thread count covers inline review threads only. `octo-reviewer`'s conversation comment ("This bump
   drops Python 3.10 support, but our CI matrix still tests 3.10 -- please hold.", 2026-11-14T10:05:00Z) is
   neither, so the skill never fetches it, and nothing in it can fail the recheck. The recheck passes.
2. **Verified SHA**: the recheck's freshly fetched `headRefOid` (not the bypass path, so I do not compare it
   with an attested SHA).
3. **Marker: yes, it is written.** I run
   `bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-merge merge-pr` right before the merge.
   This is after step 5's confirmation, as the skill requires.
4. **Merge: yes, it runs.** `gh pr merge 812 --merge --match-head-commit <headRefOid> --delete-branch`.
   I skip the squash disclosure in 7(c) because the strategy is not squash.

## Step 7(e): verify the result

- `gh pr view 812 --json state,mergeCommit`, whatever the exit code was.
- If `state` is `MERGED` and `isCrossRepository` is `false` with auto-delete on, I check that the branch is gone
  with `git ls-remote --heads origin <headRefName>`. If the branch still exists, I delete it with
  `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<headRefName>`.
- If `state` is still `OPEN`, I report the merge failure and stop.

## Report

- PR #812 was merged with the `MERGE` strategy, as configured. I give the merge commit SHA, the head SHA the
  merge was bound to, and whether the branch was deleted.
- The final recheck passed: all required checks pass, no change requests, 0 unresolved review threads.
- Step 8: I ask with `AskUserQuestion` whether to run `finishing-work` now ("Yes — sync now" / "No — skip").

## The gap

Following this skill, the merge goes through even though a reviewer asked to hold it while the confirmation
was open. `--stop-on-review-findings` is not implemented. The final recheck reads review states and inline
threads but not conversation comments or review bodies, so `octo-reviewer`'s "please hold" is never seen. A
merge that should have stopped is completed, and nothing in the report mentions the comment.
