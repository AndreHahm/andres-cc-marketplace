# Triage answers: PR #660 and PR #661

Simulated exercise. No GitHub, git or shell command was run; the answers are what the skill's text says to do.

## PR #660 (actions/checkout 4.1.0 to 4.2.0, github_actions)

### What step 3 tells the user about the added packages

- The old and new versions are clean (no advisories listed for either).
- Compatibility is `unknown`. GitHub Actions have no declared-constraint metadata, so this check always returns `unknown` for them. It says nothing either way.
- `added_packages` has status `not_checked`. No `--head-lock` was passed because this ecosystem has no lockfile, so the skill cannot say which packages the PR adds, or whether any is vulnerable.
- `adds_vulnerable_package` is `null`. Null means no data. It is not "safe" and not "clean". Step 3.7 requires the user to be told what was not checked, and that the `Dependency review` read in 6.4 is the remaining check.
- Rules (a) to (d) do not fire. The new version is not vulnerable, compatibility is not `false`, rule (c) has no exact `false` signal to act on, and rule (d) does not fire on `null`. The recommendation is therefore the normal merge path, with the added-package gap disclosed.
- The bump is minor, so no breaking-change confirmation is needed.

### What 6.4 does about the null signal, before 6.5

1. Run `head-runs 660`. Its `head_sha` must equal the `headRefOid` read in 6.1, and `head_incomplete` must be empty.
2. Run `pr-checks 660`. Every row must be `pass` or `skipping`.
3. Run `dependency-review 660`. An empty `items` list means the repository runs no such check. Normally the skill would say "carry on, only step 3's lockfile comparison covered the packages the PR adds". That sentence cannot be used here, because step 3 did not cover them (`not_checked`).
4. Because `adds_vulnerable_package` is `null` for this head, 6.4 requires an `AskUserQuestion` before 6.5. It asks whether to go on or skip the PR, names the packages that were not checked, says that the repository has no `Dependency review` check to fall back on, and says that a clean result would not clear the null.
5. Do not proceed to 6.5 unless the user chooses "go on". Skipping is also a valid answer.

## PR #661 (delta 1.0.0 to 1.1.0, uv)

### What 6.1 does before 6.4

1. Re-read live state with `pr-view 661 --fields state,mergeStateStatus,headRefOid,baseRefName,files,commits`.
2. `state` is `OPEN`, so the PR stays in the run.
3. `headRefOid` is unchanged (`ffff...`), so the rule that re-runs `assess` after a head change does not fire. The head-lock assessment still describes the head.
4. `baseRefName` is now `release/1.x`. It matches `^[A-Za-z0-9._/@+=-]+$`, so the PR is not skipped for that reason.
5. Re-run step 2's suspicious-PR check on the fresh `files` and `commits` data: expected paths, commit authors, and the 100-entry truncation limit. The ecosystem and classification are unchanged by a retarget.

### The gap the retarget creates

- Step 3 fetched the base `uv.lock` from `main`. The compatibility and added-package results were computed against that lock.
- The PR now targets `release/1.x`, so the step 3 results may not describe the base the merge would land on.
- The skill's text re-runs `assess` only on a head change, not a base change, so it does not spell this case out. Do not guess.
- Two things also need the user's decision, because the approval was given for a plan built on `main`:
  - Someone retargeted the PR with no push, so a merge would now land on `release/1.x`, not `main`.
  - The user approved merging against the `main`-based plan.
- Stop at 6.1 and ask via `AskUserQuestion`, with two options:
  - Re-fetch the base lock with `--role base --ref release/1.x`, re-run `assess` with `--head-lock`, and apply rules (a), (b) and (d) to the new result before 6.4.
  - Proceed on the `main`-based result, with the retarget disclosed.
- Only after that answer continue to 6.2 to 6.4 (6.3 uses the new `mergeStateStatus`, which the retarget may have changed).
