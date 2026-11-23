# merge-pr 904 --bypass-codex-review "Tier-1 change reviewed manually by the maintainer"

Simulated run. No gh/git calls were made and no repository file was edited.

## Step 1 - Resolve and validate the PR

- `$ARGUMENTS` PR reference is `904` (digits only, accepted). No `--expected-head-sha` was given, so the head-pin checks are skipped.
- The bypass reason is written to a scratchpad file and never placed on a command line.
- `gh pr view 904 --json ...` returns the PR data (not draft, head matches the checkout, `isCrossRepository` false). The PR-reference was explicit, so the origin-identity check is skipped.
- `headRefName` and `baseRefName` are validated against `^[A-Za-z0-9._/@+=-]+$`.

## Step 1.5 - Session open-issues check (the one open item)

1. Verify the checkout matches the PR: `isCrossRepository` is false, origin resolves to the PR's base `owner/repo`, the current branch equals `headRefName`, and `git rev-parse HEAD` equals `headRefOid`. All four match, so scanning proceeds.
2. Scan the session. The one item is an unaddressed reviewer Minor against a file the PR changes. It is not one the user deferred, so it is not on the "deferred" path.
3. Classify it as **touched**. The file appears in the PR's changed-file list from `gh api repos/{owner}/{repo}/pulls/904/files --paginate`.
4. No `--expected-head-sha` was given, so the run fixes touched issues now:
   - Apply the fix to the Minor.
   - Verify it under `.claude/rules/require-tests-for-behavior-changes.md` (a test if the change alters behavior, or a re-read against the issue if it does not).
   - Commit and push via `Skill(commit)`, explicitly requesting the push. The push moves the PR head.
5. Because that push changed the head, step 2 must re-fetch fresh data rather than reuse step 1's snapshot.
6. Report a summary of what was found and fixed before continuing. Nothing is filed, since the item was touched and fixed.

If the fix had been a user-deferred item, it would instead be surfaced with `AskUserQuestion` ("fix now" or "leave deferred") and not auto-fixed.

## Step 2 - Readiness (after the fix-driven re-fetch)

- Re-fetch with `gh pr view 904 --json isDraft,reviews,statusCheckRollup,mergeable,mergeStateStatus,headRefName,baseRefName,isCrossRepository,headRefOid` and re-validate the ref names.
- Not draft: pass.
- Required contexts come from the REST branch-protection endpoint. Classify each against `statusCheckRollup`. Every context passes except `Publish Codex policy result`, which fails.
- Because `--bypass-codex-review` was given and that is the only non-passing required context, the bypass exception applies. Status checks are provisionally satisfied and the run records the PR as being on the bypass path. The exception applies only the first time step 2 runs its classification in this invocation. The post-1.5 re-fetch is that first classification, so it is available here. It is spent once step 4 has run.
- No outstanding change requests: pass. No merge conflicts (`mergeable` is `MERGEABLE`): pass. Not behind base (`behind_by` is 0 for a same-repo PR): pass.
- Advisory disclosures are computed for step 5: `mergeStateStatus` value, and the unresolved-thread count via the paginated GraphQL query (each page with a fresh `gh-pr-review` marker).

## Step 3 - Merge rights

Follow `references/merge-rights-check.md` (three tiers) with step 1's `{owner}/{repo}`. The result must be `MERGE ALLOWED`. The bypass never substitutes for this check.

## Step 4 - Bypass attestation and re-verification

a. Screen the reason "Tier-1 change reviewed manually by the maintainer" against the full protocol. It has no bot-trigger mention and no ticket, personnel, host, or credential-shaped content, so it passes.

b. Resolve the head SHA with `gh pr view 904 --json headRefOid` and the actor with `gh api user --jq '.login'`. Confirm the SHA equals the one step 2 classified against (the post-fix head). Re-check the actor's write, maintain, or admin permission. Write the reason to a scratchpad file, build the attestation JSON with `jq -n --rawfile`, and write the comment body to a second scratchpad file. Then run `git-write-marker.sh gh-pr-review merge-pr` and, as the very next call, `gh pr comment 904 --body-file <scratchpad>`.

c. Capture the baseline `startedAt` for the `Publish Codex policy result` CheckRun before touching labels. Confirm the label `s: codex review bypassed` exists. If it is already present, remove it and re-add it so the `labeled` event fires. Otherwise add it.

d. Poll `statusCheckRollup` (up to 20 attempts, 15 seconds apart) until a `Publish Codex policy result` run has a `startedAt` strictly later than the baseline and `status` `COMPLETED`. An entry at or before the baseline is the pre-label result and is ignored. If the bound runs out, stop and report that the replacement check never completed.

e. Re-run the full step 2 with the bypass exception **disabled**. Every required context must now genuinely pass, including `Publish Codex policy result`. If anything still fails, report why and stop. A fresh bypass would need step 4 repeated against the current head.

## Step 5 - Confirm

Use `AskUserQuestion` to show PR 904, its title, the readiness summary, a note that the Codex check was bypassed and why, the `mergeStateStatus` value, and the unresolved-thread count (even if zero). Note also that the step-1.5 fix was pushed and that a local branch-deletion error can appear in a worktree even when the merge succeeds. Proceed only on explicit yes.

## Step 6 - Settings

Read `pr_merge_type` (default `REBASE`) and `merge_auto_delete_branch` (default `true`) from `.claude/git-kit.local.json` or the git-tracked default.

## Step 7 - Pre-check, recheck, merge

a. If the strategy is `REBASE`, count merge commits in the PR's history. If there are any, ask the user between Merge and Squash before attempting a rebase merge.

b. Immediately before the merge, re-run the full step 2 with no bypass exception. Confirm the head equals step 4(b)'s attested `head_sha`. Write the `gh-pr-merge merge-pr` marker right before the call, then run `gh pr merge 904 --<strategy> --match-head-commit <verified SHA> [--delete-branch]`.

c. If squash is chosen, disclose how many commits collapse into one.

d. On a rejected rebase, ask for an alternate strategy, re-run the full recheck, rewrite the marker, and retry with the same head binding.

e. Regardless of exit code, check `gh pr view 904 --json state,mergeCommit`. If the PR is `MERGED` and not cross-repository with auto-delete on, verify the remote branch with `git ls-remote --heads origin <headRefName>` and delete it only if it still exists.

## Step 8

Offer the post-merge sync (`finishing-work`). Nothing is deleted by the skill itself.

## Ending

The run ends in one of three ways. It stops early if the attestation fails or the replacement check does not complete. It stops at step 2 or step 4(e) if a required context still fails. Otherwise it merges after an explicit yes at step 5 and finishes with the step 7(e) verification and the step 8 offer.

## Notes

- The step-1.5 fix push means step 4(b)'s head-SHA check must use the post-fix head. This plan does.
- Ambiguity: step 2's text says the bypass exception is spent after its first run. I read the post-1.5 re-fetch as that first classification, so the exception is still available. A stricter reading would consider the first pass to be the pre-1.5 one. The skill text does not settle it, so I flag it here.
