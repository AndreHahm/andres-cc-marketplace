# merge-pr — Step 2, "No merge conflicts" bullet

## Scenario data

- `mergeable`: `CONFLICTING`
- `baseRefName`: `main`
- `headRefName`: `fix/typo`

## Checks performed for this bullet

1. Resolve `mergeable` from the already-fetched PR data (per the skill, either the data from
   step 1's `gh pr view`, or a fresh re-fetch if this is a rerun). Here it is `CONFLICTING`.
2. Classify against the 3-value enum:
   - `MERGEABLE` → check passes, move on.
   - `UNKNOWN` → not a pass; GitHub is still computing mergeability. Poll
     `gh pr view $ARGUMENTS --json mergeable` until it reaches a terminal value
     (`MERGEABLE` or `CONFLICTING`). If it's still `UNKNOWN` after polling, stop and report
     that mergeability could not be determined.
   - `CONFLICTING` → not a pass. Stop immediately and report the conflict. **No polling is
     needed in this branch** — `CONFLICTING` is already a terminal value, unlike `UNKNOWN`.
3. Since the value here is `CONFLICTING` (already terminal, no polling required), stop this
   check as failed and report it.
4. Per the skill's overall step-2 instruction, since this check failed, **stop the readiness
   evaluation entirely** — do not proceed to check "not behind base," and do not proceed to
   step 3 (the merge-rights check). A not-ready PR never reaches the rights check.

## What I tell the user

I report the PR as **not ready to merge**, specifically because of merge conflicts:

> This PR (`fix/typo` → `main`) has merge conflicts with `main` and can't be merged as-is.
> GitHub reports `mergeable: CONFLICTING`.
>
> To reproduce and resolve the conflict locally:
> 1. Fetch both branches: `git fetch origin fix/typo main`
> 2. Check out the PR branch: `git checkout fix/typo`
> 3. Attempt the merge to surface the conflict locally: `git merge origin/main`
>
> Once `git status` shows unmerged paths, run the `resolving-merge-conflicts` skill to work
> through resolving them.

I do **not** report on the remaining readiness checks (status checks, outstanding change
requests, "not behind base") for this pass — the skill says to stop as soon as one check fails
and report exactly which one failed, its state, and why, rather than continuing to evaluate the
rest.

## Do I point the user directly at `resolving-merge-conflicts` with nothing else?

**No.** I give them something to do first, not a bare pointer to the skill. Specifically:

- `merge-pr` detects the conflict **remotely**, via GitHub's own computed `mergeable` field. It
  never fetches or merges locally itself.
- `resolving-merge-conflicts`'s own precondition is a **local working tree already showing
  unmerged paths** (i.e., something `git status` reports), not a remote signal alone. Handing the
  user that skill immediately, with nothing else, would point them at a skill that has nothing to
  act on yet — there's no local conflict state for it to resolve.
- So the correct order is: (1) tell the user how to reproduce the conflict locally — fetch
  `headRefName` (`fix/typo`) and `baseRefName` (`main`), check out `fix/typo`, then run
  `git merge origin/main` — and only (2) once that local `git merge` actually leaves `git status`
  showing unmerged paths, run `resolving-merge-conflicts` to resolve them.

This matches the skill's own instructions verbatim for the `CONFLICTING` branch of the mergeable
check.
