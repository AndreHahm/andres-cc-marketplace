(Simulated exercise — no real `gh`/`git` calls were made; this describes exactly what I would do per step 7 of merge-pr's SKILL.md.)

## What I check next

Step 7 is explicit that the `gh pr merge` exit code is not sufficient evidence of anything, in either direction:

> "**Regardless of this command's exit code**, check `gh pr view $ARGUMENTS --json state,mergeCommit` next before reporting anything — a non-zero exit here doesn't necessarily mean the merge failed... and a zero exit doesn't guarantee `--delete-branch`'s own follow-through actually completed either — so this check, and the branch-deletion verification below, are never skipped just because the merge command itself reported success."

So even though `gh pr merge 160 --rebase --delete-branch` exited 0, I do **not** treat that as proof the merge (or the branch deletion) actually succeeded. I run:

```
gh pr view 160 --json state,mergeCommit
```

- If `state` is `OPEN` → that's an actual merge failure; report it and stop (the `git ls-remote` fallback never runs in this branch).
- If `state` is `MERGED` (the case here, since the command reported success) → proceed to the branch-deletion verification below.

## Do I run `git ls-remote --heads origin <headRefName>` here?

**Yes — unconditionally in this scenario.** Step 7 says:

> "when `merge_auto_delete_branch` is `true` (so `--delete-branch` was passed) **and `isCrossRepository` (from step 1) is `false`**... don't assume the remote branch is actually gone just because `state` is `MERGED` — always verify with `git ls-remote --heads origin <headRefName>`... **whether the merge command itself exited zero or non-zero.**"

Both preconditions are met:
- `merge_auto_delete_branch` is `true` → `--delete-branch` was passed.
- `isCrossRepository` is `false` → this is the repo's own branch, not a fork's, so the fallback is allowed to run at all.

The skill deliberately does not gate this check on the exit code — a zero exit only means the `gh` command itself didn't error locally; it says nothing about whether the server-side branch deletion actually took effect. So I run:

```
git ls-remote --heads origin <headRefName>
```

using the `headRefName` value already validated against `^[A-Za-z0-9._/@+=-]+$` back in step 1.

## If `git ls-remote` comes back non-empty

This is exactly the case the Testing & Validation section names explicitly:

> "`gh pr merge --delete-branch` exits 0, but `git ls-remote --heads origin <headRefName>` returns non-empty (a silent server-side deletion failure with no local error to signal it) → step 7 still catches this, since the check runs regardless of exit code, and completes the deletion via `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>`"

So I would not report the merge as fully done yet. I'd finish the job `--delete-branch` should have done:

```
gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<headRefName>
```

(reusing the already-validated `headRefName`; `{owner}/{repo}` resolved from this repository since `isCrossRepository` is `false`).

After that, I'd report to the user: the merge succeeded (rebase, PR #160, now `MERGED`), but automatic remote-branch deletion silently failed despite the clean exit code, so I completed it manually via the API delete-ref call. Only then would I move to step 8's post-merge `finishing-work` offer.
