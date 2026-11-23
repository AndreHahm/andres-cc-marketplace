# merge-pr 902 (simulated, no real calls made)

## Step 1: Resolve the PR

- `$ARGUMENTS` is `902`, digits-only, so it passes validation. No flags were given.
- Run `gh pr view 902 --json number,isDraft,headRefName,baseRefName,isCrossRepository,headRefOid,reviews,statusCheckRollup,mergeable,mergeStateStatus,url`.
- Derive `{owner}/{repo}` from the returned `url` field, not from `gh repo view`.
- The PR-reference portion was non-empty, so the bare-`gh pr view` origin-identity check is skipped.
- Validate `headRefName` and `baseRefName` against `^[A-Za-z0-9._/@+=-]+$` before use.

## Step 1.5: Session open-issues check

- Run the checkout-identity check first. `isCrossRepository` must be `false`. Compare `git remote get-url origin` (not `gh repo view`) with the PR's `{owner}/{repo}`, compare `git branch --show-current` with `headRefName`, and compare `git rev-parse HEAD` with `headRefOid`.
- The simulation gives no local checkout facts, so I cannot confirm this. If any of the four comparisons fails, I would skip the scan and tell the user to run `gh pr checkout 902` first.
- If the checkout matches, scan this session for unaddressed findings and TODOs, and classify each as touched or untouched using the paginated `gh api repos/{owner}/{repo}/pulls/902/files --paginate`. The simulation gives no session findings, so I would report "nothing found" explicitly.

## Step 2: Readiness checks

### Building the required-check list

1. Call `gh api repos/{owner}/{repo}/branches/main/protection --jq '.required_status_checks.contexts'`. This returns the 9 classic branch-protection contexts. This is the only source the skill uses for the gate list.
2. Do not use `gh pr checks 902` output as the list. It can omit a required context that has not started yet.
3. If this call failed, I would stop and report that the list could not be resolved.
4. The ruleset requirement (`Codacy Static Code Analysis`, `CodeRabbit`, `SonarCloud Code Analysis`) is not returned by the classic protection endpoint. The skill's step 2 does not read rulesets.

### Classifying the 9 classic contexts

Each context is checked against `statusCheckRollup` into one of four states: passing, failing, pending or missing. The simulation says all 9 are passing for the head, so all 9 classify as passing.

### Classifying the ruleset contexts (disclosure only)

These are not part of the skill's gate list, but the same four-state rules would classify them as follows:

- `CodeRabbit`: passing (a CheckRun/StatusContext entry with a success state).
- `SonarCloud Code Analysis`: passing.
- `Codacy Static Code Analysis`: **missing**. No entry with that name appears in `statusCheckRollup`. Missing is kept distinct from pending and failing.

I would not add these to the gate on my own, because the skill's list comes only from the classic endpoint. But the missing Codacy context is a real merge blocker that GitHub will enforce through the ruleset, so I would not present this PR as cleanly mergeable. I would surface it explicitly (see step 5 below).

### The other four checks

- Not draft: `isDraft` is `false`. Pass.
- No outstanding change requests: no reviewer's latest review is `CHANGES_REQUESTED`. Pass.
- No merge conflicts: `mergeable` is `MERGEABLE`. Pass. If it had been `UNKNOWN`, I would poll up to 5 times.
- Not behind base: `gh api repos/{owner}/{repo}/compare/main...<headRefName> --jq '.behind_by'` must return `0`. The simulation says behind-base passes, so I treat it as `0` for this run.

### Advisory disclosures (never block)

- `mergeStateStatus`: fetch and disclose the raw value. The simulation does not give it. If it reads `BLOCKED`, that is consistent with the missing Codacy ruleset context.
- Unresolved review-thread count: run the paginated `reviewThreads` GraphQL query, with a fresh `gh-pr-review` marker before each page. The simulation does not give it. If it cannot be determined, report "unknown", never `0`.
- No `--stop-on-review-findings` flag was given, so the review-finding read does not run.

### Result of step 2

All five gate checks pass against the resolved list. The skill therefore does not stop here, and the bypass path does not apply because there is no failing `Publish Codex policy result` entry.

## Step 3: Merge-rights check

Yes, I continue to the merge-rights check. Step 2 passed, and step 3 always runs before anything else that could write. Follow `references/merge-rights-check.md` exactly, passing the step-1 `{owner}/{repo}` into each tier. I did not open that reference in this baseline, so I would apply its three tiers as written when running it live.

If it returns `MERGE NOT ALLOWED`, I would stop. If the reason is a missing `.github/CODEOWNERS`, I would ask via `AskUserQuestion` whether to invoke `Skill(manage-codeowners)`.

## Step 4: Bypass

Not applicable. No `--bypass-codex-review` flag, and `Publish Codex policy result` is not the failing check.

## Step 5: Confirm

If step 3 returns `MERGE ALLOWED`, I would ask via `AskUserQuestion` before any merge. The prompt would show:

- PR 902, its title, and the readiness summary.
- The advisory values: the `mergeStateStatus` value, and the unresolved-thread count, even if it is 0.
- The ruleset discrepancy: `Codacy Static Code Analysis` is required by the `main` ruleset and is missing from this head's checks, so GitHub may reject the merge.
- A note that a local branch-delete error (`fatal: 'main' is already used by worktree`) can occur even when the merge succeeds.

I would not merge unless the user explicitly says yes. Given the missing Codacy context, I would recommend the user resolve it before confirming.

## Steps 6-8 (not reached in this run)

- Step 6 would read `pr_merge_type` and `merge_auto_delete_branch`.
- Step 7 would run the rebase pre-check, the final recheck, the marker write and `gh pr merge 902 --<strategy> --match-head-commit <headRefOid> --delete-branch`, then verify the result. It runs only after an explicit yes at step 5.
- Step 8 would offer `finishing-work` after a successful merge.

## Summary

- Required-check list: 9 classic contexts, from `repos/{owner}/{repo}/branches/main/protection`.
- Classic contexts: all passing.
- Ruleset context `Codacy Static Code Analysis`: missing. `CodeRabbit` and `SonarCloud` are passing.
- Gate result: pass. Continue to step 3, the merge-rights check.
- Disclosure: the ruleset requires Codacy, which never ran for this head, so the merge is likely to be blocked at step 5.
