# merge-pr — Step 7(e) walkthrough for PR #142

**Note:** This is a simulated exercise. No `gh`/API calls were actually made. Everything below
describes what I would do, per the merge-pr skill's own step 7, given the stated facts.

## Given facts

- `pr_merge_type` resolved to REBASE (I ran `gh pr merge 142 --rebase --delete-branch`).
- `merge_auto_delete_branch` = `true`.
- The merge command exited **non-zero**, with local stderr:
  `fatal: 'main' is already used by worktree '/repo'`
- I then ran `gh pr view 142 --json state,mergeCommit` (per step 7(e), regardless of the merge
  command's exit code) and confirmed `state` = `MERGED`.
- `isCrossRepository` = `false` (captured back in step 1's `gh pr view` JSON).
- `{owner}/{repo}` was derived from the PR's `url` in step 1.
- `headRefName` was likewise captured in step 1's JSON (referred to below as `<headRefName>`,
  since no real PR/repo exists in this exercise to substitute a literal value).

## What step 7(e) says to check next

Step 7(e) is explicit that a non-zero exit from the merge command doesn't necessarily mean the
merge failed — `fatal: 'main' is already used by worktree` is the named example of exactly this:
the git-level, local-checkout side of `gh pr merge` can fail (because the default branch is
checked out in another worktree) even though the remote merge already succeeded via the API.

So before reporting anything, the required next check is:

```
gh pr view 142 --json state,mergeCommit
```

I already ran this (per the given facts) and got `state: MERGED`. That result is what routes me
into one specific branch of step 7(e)'s decision tree below — I don't stop at "the command failed"
just because the exit code was non-zero.

## Which branch of step 7(e) applies, and why

Step 7(e) branches on `state` / `isCrossRepository` / `merge_auto_delete_branch`:

- ❌ `state` still `OPEN` → not this case; `state` is `MERGED`.
- ❌ `state` MERGED, `isCrossRepository` **true** → not this case; `isCrossRepository` is `false`.
- ✅ **`state` MERGED, `isCrossRepository` **false**, `merge_auto_delete_branch` **true**** →
  **this is the applicable branch.** All three conditions match the given facts exactly:
  the merge landed (`state: MERGED`), the head branch lives in this same repo, not a fork
  (`isCrossRepository: false`), and branch auto-deletion is configured on
  (`merge_auto_delete_branch: true`).
- (The remaining two branches — `MERGED`/not-cross-repo/delete=false, and
  `MERGED`/cross-repo/delete=false — don't apply for the same reasons as above.)

## What this branch requires

Per this branch's instructions, I must **not** assume the remote branch is already gone just
because `state` is `MERGED` — this holds "whether the merge command exited zero or non-zero."
Given the stderr I saw (`fatal: 'main' is already used by worktree '/repo'`), this is precisely
the scenario the skill calls out by name: the local-checkout conflict stops `gh`'s local half of
the operation, which silently skips the remote branch deletion too — a failure that would show up
as a zero exit code in the general case, and here shows up with a non-zero exit and this specific
stderr. Either way, the fix is the same: verify explicitly rather than trust the exit code or the
`state` field alone.

So the next command to run is:

```
git ls-remote --heads origin <headRefName>
```

## What I'd do based on that command's result

- **Empty output** → the remote branch is already gone; `--delete-branch` did take effect despite
  the local stderr. Nothing further to do for branch deletion.
- **Non-empty output** (the case this task asks about) → this confirms `--delete-branch` did
  *not* actually take effect remotely, exactly as predicted by the local-checkout-conflict
  failure mode. I would finish the job by explicitly deleting the remote ref via the API rather
  than the git CLI (which is what just failed locally):

  ```
  gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<headRefName>
  ```

  where `{owner}/{repo}` is the same owner/repo pair derived from the PR's `url` back in step 1,
  and `<headRefName>` is PR #142's head branch name from that same step-1 JSON.

## Final report (per step 7's closing instruction)

Regardless of which of the two outcomes above occurs, step 7 requires reporting, in every branch:
merge commit / method used (rebase, as configured — no strategy deviation here since the
rebase-compatibility pre-check in 7(a) would have already caught any merge-commit blocker before
this point), whether the strategy differed from the configured `pr_merge_type` (it did not), and
whether the branch was ultimately deleted (and by which mechanism — `--delete-branch` itself, or
the `gh api -X DELETE` fallback, per whichever of the two outcomes above actually occurred).

After that report, per step 8, I would ask via `AskUserQuestion` whether to run `finishing-work`
now.
