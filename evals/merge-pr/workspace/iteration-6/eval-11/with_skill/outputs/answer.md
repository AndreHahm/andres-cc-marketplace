# merge-pr — Step 2 Evaluation (Simulated)

## Inputs given

- `isCrossRepository`: `false`
- `baseRefName`: `main`
- `headRefName`: `feat/thing`
- `gh api repos/{owner}/{repo}/compare/main...feat/thing --jq '.behind_by'` → `4`

## Reasoning

Per the skill's step 2, the "Not behind base" check is one of five required readiness checks and is
only skipped when `isCrossRepository` is `true` (fork scenario). Here `isCrossRepository` is `false`, so
the check is not skipped — it must actually run and its result must be evaluated.

The compare API call succeeded (no error) and returned `behind_by: 4`. The skill requires this to
resolve to exactly `0` for the check to pass. A value of `4` means `feat/thing` is 4 commits behind
`main`. Per the skill's explicit instructions, this is a **required, blocking gate** — even though
GitHub's own `REBASE`/`SQUASH` merge strategies could mechanically absorb a stale branch at the later
merge step, this skill deliberately does not allow that; it requires the branch be explicitly
resynced first.

## Conclusion

**Readiness: FAILS.** The "not behind base" check fails (`behind_by = 4`, not `0`).

Per the skill's instructions, I stop here and do **not** proceed to step 3 (the merge-rights check) —
the skill explicitly says "never proceed to the rights check on an out-of-sync branch."

## What I tell the user

I would report:

- The PR is **not ready to merge**.
- Specifically, the "not behind base" readiness check failed: `feat/thing` is **4 commits behind
  `main`**.
- This is a required, blocking gate in this skill — it does not get waived just because a
  rebase/squash merge could technically absorb the drift at merge time.
- Recommended next step: resync the branch using `/sync-branch` (the `git-rebase-sync` skill) to bring
  `feat/thing` up to date with `main`, then re-run the merge-readiness check.
- I do not proceed to check merge rights (step 3), since step 2 explicitly gates on all five checks
  passing first, and this PR is not ready.

## Do I proceed to step 3?

**No.** Stop at step 2. The skill's own language is unambiguous: "If non-zero, stop and tell the user
how many commits behind, and point at `/sync-branch` (`git-rebase-sync`) to resync — never proceed to
the rights check on an out-of-sync branch."
