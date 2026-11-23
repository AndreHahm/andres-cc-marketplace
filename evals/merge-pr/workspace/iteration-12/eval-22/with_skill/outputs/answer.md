# merge-pr 903: simulated walkthrough

**Verdict: the merge cannot proceed.** The PR fails step 2's required "Review outcomes recorded" check. The PR has review threads, the base branch uses the outcomes ledger, and `.claude/review-outcomes/pr-903.json` is not in the PR's changed files. Steps 3 through 8 never run.

## Assumptions (stated, not verified)

- The invocation `merge-pr 903` is digits-only, so it passes step 1's argument validation. The PR-reference portion is non-empty, so step 1's origin-identity check is skipped.
- Step 1's `headRefName`/`baseRefName` pass the `^[A-Za-z0-9._/@+=-]+$` allowlist.
- The checkout matches the PR (same as the stated data), so step 1.5 can run its scan. The scenario gives no session open items, so I treat step 1.5 as finding nothing and report that explicitly.
- No `--bypass-codex-review`, `--expected-head-sha`, or `--stop-on-review-findings` was passed.

## Steps, in order

1. **Step 1: resolve and validate the PR.** Run `gh pr view 903 --json number,isDraft,headRefName,baseRefName,isCrossRepository,headRefOid,reviews,statusCheckRollup,mergeable,mergeStateStatus,url`. Derive `{owner}/{repo}` from `url`. Validate `headRefName` and `baseRefName`. The PR is not draft (given).

2. **Step 1.5: session open-issues check.** Confirm `isCrossRepository` is false, that `origin` matches the PR's repository, that the branch matches `headRefName`, and that `git rev-parse HEAD` equals `headRefOid`. Then scan this session's open items and classify each as touched or untouched against the paginated files list. Nothing is found, so state that and move on. No push happens here.

3. **Step 1.6: PR-body currency check.** Read the body and compare it with the real state. If anything is stale, propose one edit. Nothing is stale in this scenario, so no edit is made. State "no body edit needed."

4. **Step 2: readiness checks, all six must pass.**
   - **Not draft:** passes.
   - **Status checks:** resolve the required list as the union of the branch-protection REST contexts and the ruleset `required_status_checks` contexts, then classify every required context as passing, failing, pending, or missing. The scenario says every other readiness check passes, so this passes.
   - **No outstanding change requests:** passes.
   - **No merge conflicts:** `mergeable` must be `MERGEABLE`. Passes.
   - **Not behind base:** `behind_by` must be 0 via the compare endpoint, since the PR is not cross-repository. Passes.
   - **Review outcomes recorded: FAILS.** This is the blocking check.
     - `gh api -X GET repos/{owner}/{repo}/contents/.claude/review-outcomes -f ref=<baseRefName>` returns 200, so the repository uses the ledger.
     - The `reviewThreads` query finds 4 threads, all resolved. The check counts resolved threads too, so the PR "had review findings."
     - The PR therefore passes only if `.claude/review-outcomes/pr-903.json` is in the changed-file list as an added or modified file. That file is not in the list, so the check fails.
     - For completeness, the procedure also requires that file to hold at least one entry at the head, and that the local `.claude/review-ledger.local.json` hold no unpromoted entry for PR 903. Neither can rescue the result, because the first condition already failed.
     - The procedure says "Otherwise stop." The message to the user should say the outcomes were not recorded or not promoted, and that the user should record them with `handling-review-findings` (promote before the last push), then re-run `merge-pr`.
   - **Unresolved threads (advisory):** the count is 0 and is disclosed at step 5 if it ever gets there. It does not affect the outcome here.
   - **mergeStateStatus (advisory):** disclosed at step 5 only. Not reached.

5. **Stop.** Per step 2, a failed readiness check stops the run before the rights check. Report that `review outcomes recorded` failed, name the missing file, and give the remediation above.

6. **Steps 3 to 8: not reached.** The merge-rights check, the bypass path (not applicable), the confirmation prompt, the settings read, the merge command, the post-merge verification, and the finishing-work offer all do not run. No `gh pr merge` is issued, and the merge does not proceed.

## What would change the outcome

- If `handling-review-findings` records the outcomes into `.claude/review-outcomes/pr-903.json` and that file lands in the PR's changes (added or modified), with at least one entry at the head and no unpromoted local ledger entry for PR 903, step 2 would pass on the next run.
- The rest of the flow (merge-rights tiers, confirmation, merge with `--match-head-commit`, branch-deletion verification) would then apply as normal.

## Result

The merge cannot proceed. The blocking reason is the missing `.claude/review-outcomes/pr-903.json`, not any of the other readiness signals, which all pass.
