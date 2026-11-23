# merge-pr 900 (no flags): simulated baseline walkthrough

Assumptions, taken from the task facts: PR 900 is not cross-repository, the checkout matches the PR (origin, branch, and local HEAD equal `headRefOid`), and no `--bypass-codex-review`, `--expected-head-sha` or `--stop-on-review-findings` was given. Items:
- **A**: a reviewer Minor the agent parked under the PR body's `## Open Items` without asking the user.
- **B**: an item the user answered "leave it for later" to in an earlier AskUserQuestion.
- **C**: an ordinary, unaddressed security-reviewer Minor in a gate script.
- **D**: a new Minor raised by the security-reviewer pass on C's fix, in the same file.

Nothing was run. This is a description of the procedure only.

## Step 1: resolve and validate

- Validate `900` as digits-only. Run `gh pr view 900 --json number,isDraft,headRefName,baseRefName,isCrossRepository,headRefOid,reviews,statusCheckRollup,mergeable,mergeStateStatus,url`.
- Derive `{owner}/{repo}` from the returned `url`. The origin-vs-PR check is skipped because the PR reference was explicit.
- Validate `headRefName` and `baseRefName` against `^[A-Za-z0-9._/@+=-]+$`.

## Step 1.5: session open-issues check (runs before step 2)

1. **Identity check.** `isCrossRepository` is false. `origin`, the current branch and `git rev-parse HEAD` all match step 1. The check passes, so scanning and fixing may proceed.
2. **Scan.** A, B and C are all open issues raised this session and not yet fixed or declined. B is additionally flagged as user-deferred.
3. **Classify.** Resolve the changed-file list with `gh api repos/{owner}/{repo}/pulls/900/files --paginate`, not `gh pr view --json files`. A, B and C all sit in files the PR changes, so all three are touched. None is untouched, so no `github-issue-lifecycle` filing occurs.
4. **Decide per item** (no `--expected-head-sha`, so fixing is allowed):
   - **A**: not user-deferred. The agent parked it itself, and that is not a decision the user made. It is fixed without a question. The summary should disclose that the agent had parked it under Open Items without asking. Once fixed, its Open Items entry should be removed or updated. The skill text does not spell out that PR-body edit, so I flag it as a judgment call.
   - **B**: user-deferred and touched. Per `disclose-before-overriding-decisions.md`, this is the only item that needs a question. One `AskUserQuestion` with "fix now" and "leave deferred". The user answers "fix now", so B is fixed.
   - **C**: an ordinary, not-deferred touched item. It is fixed without a question.
5. **Fix each item.** For each one: apply the fix, verify it (for C, a gate script, run it against fixtures, per `require-tests-for-behavior-changes.md`), then `Skill(commit)` with an explicit push request.
   - C changes a gate's pass/fail logic, so `require-security-review-before-new-gate.md` applies. Dispatch `security-reviewer` on the file before C's fix ships. That pass raises D, a Minor in the same file.
   - **D**: a reviewer finding raised this session on a touched file, not deferred. It gets the same treatment: fixed without a question, verified, committed and pushed. The skill text does not say how many security-reviewer rounds a gate fix gets. My judgment: run one more pass on D's fix, since it again changes gate logic. Stop when that pass returns no new findings, and disclose that stopping rule.
6. **Push count.** The text says "commit and push it" per touched issue, so each fixed item gets its own commit and push. That gives **4 pushes** (A, B, C, D). I read the text literally; batching C and D into one commit would be a deviation I would disclose. A `--expected-head-sha` run would have pushed nothing here.
7. **Summary.** Before step 2, report what was found, fixed, and left open. Nothing is left open. The report also discloses that A was self-parked, and that B was deferred and then fixed on the user's answer.

**Questions asked in step 1.5: one `AskUserQuestion` (round 1), for B only.** A, C and D need no question. Each push happens right after its own fix and verification, before the next item. None of these pushes restarts the run.

## Step 2: readiness, after the last push

- **Do not restart from step 1.** Step 1's identity and argument checks stay valid. The pushes made `headRefOid` stale, so step 2 must re-fetch: `gh pr view 900 --json isDraft,reviews,statusCheckRollup,mergeable,mergeStateStatus,headRefName,baseRefName,isCrossRepository,headRefOid`. Re-validate the refreshed `headRefName` and `baseRefName` before any use.
- Classify against the fresh data:
  - Not draft.
  - Required contexts from `repos/{owner}/{repo}/branches/<baseRefName>/protection`, each classified as passing, failing, pending or missing. All must pass.
  - No `CHANGES_REQUESTED` from any reviewer's latest review.
  - `mergeable` is `MERGEABLE`, with bounded polling if `UNKNOWN`.
  - Not behind base: `gh api repos/{owner}/{repo}/compare/<baseRefName>...<headRefName> --jq '.behind_by'` must be `0`.
- The bypass exception is available on this first step-2 run, but no bypass reason was given, so it does not apply.
- The four new commits will almost certainly leave `Publish Codex policy result` pending on the new head. Step 2 then stops and reports that. It does not poll for CI. The user re-invokes once CI settles.
- Advisory disclosures, computed once the five gates pass: `mergeStateStatus` and the unresolved-thread count (paginated GraphQL, with a fresh `gh-pr-review` marker before every page).

## Step 3: merge rights

Follow `references/merge-rights-check.md` with step 1's `{owner}/{repo}`. Stop if `MERGE NOT ALLOWED`. Step 4 is skipped because there is no bypass.

## Step 4: skipped (no bypass path)

## Step 5: confirmation (round 2)

One `AskUserQuestion` showing the PR number, title, readiness summary, both advisory disclosures (`mergeStateStatus` value and unresolved-thread count, even if zero or `CLEAN`), and the worktree branch-delete note. Proceed only on an explicit yes. This is the second and last question before the merge.

## Step 6: settings

Read `pr_merge_type` (default `REBASE`) and `merge_auto_delete_branch` (default `true`) from `.claude/git-kit.local.json` if set, else the tracked `git-kit.settings.json`.

## Step 7: pre-check, final recheck, merge

- **(a)** If the strategy is `REBASE`, count merge commits in the PR. Ask via `AskUserQuestion` if any exist.
- **(b)** Immediately before the marker, re-run the full step-2 check without the bypass exception. Re-fetch `headRefOid`. Write the `gh-pr-merge` marker, then run `gh pr merge 900 --<strategy> --match-head-commit <headRefOid> --delete-branch`.
- **(c)** If the strategy is squash, state the commit count that will collapse.
- **(d)** Only on a rejected merge: `AskUserQuestion` for an alternate strategy, a full recheck, a fresh marker, then retry.
- **(e)** Check `gh pr view 900 --json state,mergeCommit` regardless of exit code. Then run `git ls-remote --heads origin <headRefName>` to confirm the branch is gone, and finish the deletion if not.

## Step 8: post-merge sync (round 3, optional)

After a successful merge, one `AskUserQuestion`: run `finishing-work` now with PR 900, or skip.

## Summary of asks and pushes

- **Questions:** 2 before the merge (B in step 1.5, confirmation in step 5), plus one in step 7(a) only if merge commits exist, plus step 8 after the merge.
- **Pushes:** 4, one per fixed item (A, B, C, D), each right after its own fix and verification.
- **After the last push:** the step-1.5 summary, then step 2 re-fetches fresh data. The run does not restart from step 1, and it does not re-run step 1.5's identity check or scan. Step 2 then runs once, as its first pass in this invocation.
