# Scenario

- Step 6 resolved `merge_auto_delete_branch: true`.
- Step 1 resolved `isCrossRepository: true` (the PR's head branch lives in a contributor's fork).
- `gh pr merge 150 --rebase --delete-branch` exited non-zero, local stderr:
  `fatal: 'main' is already used by worktree '/repo'`.
- Per step 7(e), that non-zero exit is checked regardless of what it reports — a local side effect (e.g.
  `gh` trying to check out the default branch locally after `--delete-branch`) can fail the command even
  though the remote merge already succeeded, so the exit code alone is never trusted either way.
- I already ran `gh pr view 150 --json state,mergeCommit` (this is step 7(e)'s mandatory next check,
  which I've now performed) and confirmed `state` is `MERGED`.

# What I check next

1. **Classify against step 7(e)'s branch table using the three facts now in hand: `state`,
   `isCrossRepository`, `merge_auto_delete_branch`.**
   - `state` is `MERGED` (not `OPEN`) — so this is not the "actual merge failure" branch. The
     `fatal: 'main' is already used by worktree` stderr is the exact cosmetic/local-side-effect error
     step 5's confirmation prompt already warned about ("branch deletion may report a local git error
     ... even though the merge itself succeeds") — it does not by itself mean anything failed.
   - `isCrossRepository` is `true`. Per the skill's own branch table, this specific combination —
     `state: MERGED` + `isCrossRepository: true` — is called out as its own branch, and it applies
     **regardless of `merge_auto_delete_branch`'s value and regardless of the local `--delete-branch`
     step's own exit code**. So `merge_auto_delete_branch: true` does not push this into the
     "verify/delete the remote branch" branch — the fork branch alone is dispositive.

2. **Report the result**, per step 7(e)'s closing instruction ("report the result in every branch
   above"): the merge commit and method used (`--rebase`, matching the configured `pr_merge_type`, no
   strategy change occurred so no reason to disclose one), and that branch deletion for `headRefName` was
   **skipped** because the branch lives in the contributor's fork and isn't this skill's to delete.

3. **Do not do anything further with `headRefName` in this repository's API/remote namespace** — see
   below for why.

# Do I run `git ls-remote --heads origin <headRefName>`? **No.**

# Do I run `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>`? **No.**

Both are explicitly forbidden by the skill in this exact combination:

> `state` is `MERGED`, `isCrossRepository` is `true` (the PR came from a fork): never run the
> `git ls-remote`/`gh api -X DELETE` fallback at all, regardless of `merge_auto_delete_branch` or the
> local `--delete-branch` step's own exit code — `{owner}/{repo}` resolves to this repository, not the
> fork the branch actually lives in, so a same-named branch here (e.g. a fork's own `main`) would be
> misread as "still needs deleting" and targeted for deletion in the wrong repo. Report that the branch
> lives in the contributor's fork and isn't this skill's to delete.

Why this matters concretely in this scenario:

- **`{owner}/{repo}` is always derived from step 1's resolved PR `url` field** — i.e., the base
  repository this PR was opened against, not the fork the head branch actually lives in. `origin` in
  this checkout also points at the base repository, not the fork. So `git ls-remote --heads origin
  <headRefName>` would be querying the wrong repository's refs entirely — it can't tell me anything
  about whether the contributor's fork branch still exists, only whether *this* repo happens to have a
  same-named branch.
- That's not just uninformative, it's actively misleading: if a branch with the same name as
  `headRefName` happens to exist in this repository for an unrelated reason (e.g. both the fork and this
  repo have a branch literally called `main`, or a coincidentally-named feature branch), the check would
  come back non-empty and look exactly like "the `--delete-branch` step silently failed, run the
  fallback delete" — leading straight into `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>`
  against the **wrong repository's own ref**, deleting a branch this skill has no business touching and
  that has nothing to do with the actual PR.
- The `merge_auto_delete_branch: true` setting only controls whether `--delete-branch` was passed to the
  original `gh pr merge` call (step 7(b)) and whether the fallback-verification logic applies *when
  it's safe to apply it* (i.e., not cross-repository). It never overrides the cross-repository guard —
  the skill is explicit that this branch of the logic fires "regardless of `merge_auto_delete_branch`."
- Because the branch is the contributor's own fork branch, deleting it (or even verifying its
  non-existence) is outside this repository's remote entirely and isn't something `gh api -X DELETE
  repos/{owner}/{repo}/...` against *this* repo could correctly do even if I wanted to — the correct
  owner/repo for that branch is the fork's, which this skill never resolves or touches.

# What I do instead

- Treat the `fatal: 'main' is already used by worktree '/repo'` stderr as the already-anticipated,
  cosmetic local error (per step 5's disclosure) — not evidence of a real problem, and not something
  that changes the branch classification once `state` is confirmed `MERGED`.
- Report to the user: PR #150 merged via rebase (commit `<mergeCommit.oid>` from the `gh pr view` JSON),
  and that branch deletion was skipped because the branch lives in the contributor's fork — not this
  skill's to delete, regardless of `merge_auto_delete_branch` being `true`.
- Proceed to step 8: ask via `AskUserQuestion` whether to run `finishing-work` now to sync local `main`
  and check for cleanup, passing PR #150's number so `finishing-work` binds its own merge-confirmation
  check to this exact PR rather than re-resolving the current branch's PR.
