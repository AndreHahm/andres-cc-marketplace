# merge-pr 902 (simulated): step-by-step

Assumptions: the exercise data is taken as given. No `gh` or `git` call is made and no repository file is edited. Steps 1.5 and 1.6 run before step 2 in the skill's order. I treat them as having nothing to act on here, because the exercise supplies no session open items and no body drift.

## Step 1: resolve and validate the PR

- `$ARGUMENTS` is `902`, which is digits-only, so it passes validation. No `--bypass-codex-review`, `--expected-head-sha` or `--stop-on-review-findings` was given.
- Because an explicit PR number was given, the origin-vs-`gh repo view` identity check is skipped (it applies only to a bare, implicit target).
- Fetch the PR (`gh pr view 902 --json ...`) and take `{owner}/{repo}` from its `url` field. Validate `headRefName` and `baseRefName` (`main`) against `^[A-Za-z0-9._/@+=-]+$`.
- The PR is not draft and is not cross-repository (per the exercise data).

## Step 2: build the required-check list (union of two calls)

1. Classic protection: `gh api repos/{owner}/{repo}/branches/main/protection --jq '.required_status_checks.contexts'`. This yields the 9 classic contexts.
2. Rulesets: `gh api -X GET repos/{owner}/{repo}/rules/branches/main --paginate --jq '.[] | select(.type == "required_status_checks") | .parameters.required_status_checks[].context'`. This yields `Codacy Static Code Analysis`, `CodeRabbit` and `SonarCloud Code Analysis`.

The required list is the union, each name once. It is 9 names plus any ruleset name not already among the 9. The exercise does not say whether `CodeRabbit` or `SonarCloud Code Analysis` overlap with the classic 9, so the final count is 9 to 12. Both calls succeeded, so there is no "could not resolve" stop. Integration IDs are not compared, only names.

Do not use `gh pr checks` output as the completeness source.

## Step 2: classify each context against `statusCheckRollup`

- The 9 classic contexts: all passing (per the exercise). Each is classified as passing.
- `CodeRabbit`: an entry exists and is passing, so it is passing.
- `SonarCloud Code Analysis`: an entry exists and is passing, so it is passing.
- `Codacy Static Code Analysis`: no entry at all in `statusCheckRollup` for the head. This is **missing**, not pending and not failing. Nothing has started for the current head commit, so it is never collapsed into pending or failing.

If several entries shared a name, I would group by source and take the latest `startedAt` per group. The exercise shows no duplicates, so this does not change the result.

## Step 2: decide whether to continue

- Required rule: every required context must be passing.
- The `--bypass-codex-review` exception applies only when `Publish Codex policy result` is the sole non-passing required context. Here the non-passing context is `Codacy Static Code Analysis`, and no bypass flag was given, so the exception does not apply.
- Other readiness checks (not draft, no change requests, no conflicts, not behind base, review outcomes recorded) pass per the exercise. The advisory disclosures (`mergeStateStatus`, unresolved-thread count) are only computed once the required checks pass, so they are not reported as a result of this stop.

**Result: NOT READY. Stop at step 2.**

Report to the user, in the skill's wording: "1 required context missing: Codacy Static Code Analysis (required by the `main` ruleset) — never ran for the current head commit." Say that 9 classic contexts and 2 ruleset contexts are passing.

## Step 3: merge-rights check

Do not run it. Step 2 says "Stop here — do not proceed to the rights check on a not-ready PR." The bypass path is not open, and the rights check never grants anything that could substitute for a missing required check.

## What I would not do

- No `--bypass-codex-review` attestation (it is not applicable to Codacy and not requested).
- No merge marker, no `gh pr merge`, no `AskUserQuestion` merge confirmation, and no `finishing-work` offer, since no merge happens.
- No `gh pr comment`, label or PATCH.
- I would not attempt to retrigger Codacy myself. I would tell the user to check whether the Codacy check is configured to run on this head, then re-run `merge-pr 902` once it reports.
