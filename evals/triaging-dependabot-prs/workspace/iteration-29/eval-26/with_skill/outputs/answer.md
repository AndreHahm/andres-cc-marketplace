# Triage of dependabot PRs #660 and #661

Procedure followed: `plugins/git-kit/skills/triaging-dependabot-prs/SKILL.md`, with `references/advisory-and-compatibility.md` and `references/ordering-and-checks.md`. No commands were run, no comments posted, and no GitHub state changed.

## PR #660: actions/checkout 4.1.0 to 4.2.0 (github_actions)

### What step 3 tells the user about the added packages

- A `github_actions` PR has no lockfile, so `assess` ran without `--lock` and without `--head-lock`. Step 3.4 (fetching lockfiles) does not apply.
- `added_packages.status` is `not_checked`. Nothing was compared, so the packages the PR adds are unknown. The result is not a clean bill for them.
- `adds_vulnerable_package` is `null`, which means no data. It must not be read as "safe".
- Per step 3.7, the `github_actions` case is special: say only that this PR has no lockfile to compare. The remaining check is the `Dependency review` read at step 6.4.
- Old and new versions are clean (`status` ok, no advisories). Compatibility is `unknown` for every GitHub Action, because actions carry no declared-constraint metadata. `new_compatible` is therefore `null`, not `true`, and no compatibility claim should be made.
- Rules applied: rule (a) does not fire, because `new_vulnerable_not_safer_than_old` is `false` (no advisories on the new version). Rule (b) does not fire, because `new_compatible` is not `false`. Rule (c) does not fire, because `newest_compatible` is `unknown`. Rule (d) does not fire, because `adds_vulnerable_package` is `null`, not `true`. The recommendation is therefore not held by any rule, but the report must say the advisory result is clean for the bumped version only, and that compatibility and added packages were not checked.
- The PR is a pin-only change, so the ecosystem rules in `ordering-and-checks.md` (the actions pin exemption) apply. The user answered yes to the advisory and compatibility checks, so the opt-in is not a reason to skip step 3.

### What 6.4 does about the null signal before 6.5

- Step 6.4 first reads `head-runs 660`. If `head_sha` differs from the `headRefOid` read at 6.1, return to 6.1. If `head_incomplete` is non-empty, or `truncated` is true, treat CI as unfinished and ask (wait, skip, or go on). The head is unchanged, so this is only a check that the run list is complete.
- With `head-runs` clean, read `pr-checks 660`. Both are reported clean, so carry on.
- Then read `dependency-review 660`. The items list is empty, which means the repository runs no such check. Carry on, and say so.
- The `adds_vulnerable_package` null is the one case where 6.4 asks nothing. The rule says a `github_actions` PR is the exception: it has no lockfile, adds no package through one, and its null (`added_packages.status` `not_checked`) asks nothing at 6.4. Do not ask the user about it here, and do not treat it as a pass either.
- The report must still state the gap: added packages were not checked, and the empty `Dependency review` means no check ran that could cover them.
- Proceed to 6.5 (Codex policy check; for a clean head nothing is needed), then 6.6 (merge via `Skill(merge-pr)` with `--expected-head-sha` set to the head SHA read at 6.1 and confirmed by `head-runs` at 6.4). Note that merge-pr asks its own merge confirmation.

## PR #661: delta 1.0.0 to 1.1.0 (uv)

### What 6.1 does before 6.4

- Re-read live state with `pr-view 661 --fields state,mergeStateStatus,headRefOid,baseRefName,files,commits`.
- `headRefOid` is unchanged (`ffff...`), but `baseRefName` changed from `main` to `release/1.x`. Step 3 compared the lockfiles against `main`, so the earlier assessment is for the wrong base.
- Step 6.1 says: when `baseRefName` now differs from the base whose lockfile step 3 fetched, re-fetch the base and head lockfiles and re-run `assess` for the new head and base before 6.4. The retarget is compared with that branch's lockfile. Nothing is pushed to the head.
- Concretely: validate `baseRefName` against `^[A-Za-z0-9._/@+=-]+$` (`release/1.x` passes) and `headRefOid` against 40 lowercase hex (passes). Fetch `uv-lock --role base --ref release/1.x --dir <scratchpad>` and `uv-lock --role head --ref ffff...`, then run `assess --ecosystem uv --dep delta --old 1.0.0 --new 1.1.0 --lock <base path> --head-lock <head path>`. Apply rules (a), (b) and (d) to the new result. The base lockfile may have moved, so compatibility can change.
- If the new result gives a new close or hold recommendation, tell the user and send the PR to 6.2 with it. If the re-fetch or re-run is declined or fails, treat `adds_vulnerable_package` as `null` for the new base and say so; step 6.4 then asks wait/skip/go on about the unchecked added packages.
- Re-run the step 2 suspicious-PR check on the fresh `files` and `commits` data (author must still be `dependabot[bot]`, and paths must stay within `pyproject.toml` and `uv.lock`).
- Also tell the user about the retarget. The plan approved at step 5 was for a PR against `main`. Merge-pr will merge into `release/1.x`, and the user should know that before any write. The skill's text does not require a new plan approval for this, but the change is material.
- Only after this re-check does 6.4 run (`head-runs`, `pr-checks`, `dependency-review`).
