# merge-pr step 7 — post-merge verification (simulated, no real gh/git calls made)

## Scenario

- Step 7 ran `gh pr merge 160 --rebase --delete-branch`, exit code 0.
- `merge_auto_delete_branch` = `true` (from step 6).
- `isCrossRepository` = `false` (from step 1).

## What I would check next

Per step 7(e), the exit code of the merge command is never treated as sufficient on its own —
"**Regardless of this command's exit code**, check `gh pr view $ARGUMENTS --json state,mergeCommit`
next before reporting anything." So the first thing I'd do, even though the command exited 0
with no error, is re-fetch state:

```
gh pr view 160 --json state,mergeCommit
```

This is required because a zero exit doesn't guarantee `--delete-branch`'s own follow-through
actually completed (step 7(e)'s own text: "a zero exit doesn't guarantee `--delete-branch`'s own
follow-through actually completed either").

Assuming that call reports `state: "MERGED"` (a non-zero exit here with `state` still `OPEN` would
instead be reported as an actual merge failure and stop — not this scenario), I then branch on
`state` / `isCrossRepository` / `merge_auto_delete_branch` together. With `state = MERGED`,
`isCrossRepository = false`, `merge_auto_delete_branch = true`, this lands in the specific branch of
step 7(e):

> "don't assume the remote branch is actually gone just because `state` is `MERGED` — always verify
> with `git ls-remote --heads origin <headRefName>` ... whether the merge command itself exited zero
> or non-zero."

## Do I ever run `git ls-remote --heads origin <headRefName>` here, given the clean exit?

**Yes — unconditionally, regardless of the exit code being 0.** The skill is explicit that this
check is never skipped just because the merge command reported success (step 7(e)'s opening line,
and the Testing & Validation section's own worked case: "`gh pr merge --delete-branch` exits 0 →
`git ls-remote --heads origin <headRefName>` returns empty; step 7 proceeds straight to reporting,
no `gh api -X DELETE` call" — and the very next bullet covers exactly the non-empty-despite-exit-0
case). So I would run:

```
git ls-remote --heads origin <headRefName>
```

using `headRefName` from step 1's original fetch (already validated against
`^[A-Za-z0-9._/@+=-]+$` at step 1, before any use here or elsewhere in the skill).

## If that check came back non-empty despite the clean exit

This is explicitly named in the skill as "a silent server-side deletion failure with no local error
to signal it" — `--delete-branch` didn't actually take effect even though `gh pr merge` itself
exited 0. Per step 7(e):

> "Non-empty output → `--delete-branch` didn't actually take effect. This includes, but isn't
> limited to, the same local-checkout-conflict failure `finishing-work`'s step 1.5 documents and
> fixes ... a silent failure behind a zero exit code is the same underlying defect, just without the
> local error to notice. Finish the job it should have done:
> `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<branch>`."

So I would finish the deletion myself:

```
gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<headRefName>
```

with `{owner}/{repo}` resolved from step 1's already-resolved `url` field (never a fresh
`gh repo view`, per step 1's note), and `<headRefName>` the same already-validated value used in the
`ls-remote` call above.

Finally, per step 7's closing instruction ("Report the result in every branch above..."), I would
report: the merge commit/method used (rebase, as configured — no strategy change here since this
scenario has no merge-commit pre-check failure or rejection-fallback in play), and that the branch
was deleted via the `gh api -X DELETE` fallback because the local `--delete-branch` flag's
server-side effect had silently failed despite the merge command's own clean exit.

## Summary

- The `git ls-remote --heads origin <headRefName>` check always runs in this branch (`MERGED`,
  non-cross-repository, `merge_auto_delete_branch: true`) — the merge command's own zero exit code
  is explicitly *not* trusted as proof the branch is gone.
- A non-empty result triggers a fallback deletion via `gh api -X DELETE repos/{owner}/{repo}/git/refs/heads/<headRefName>`, completing the branch deletion `--delete-branch` was supposed to do.
- This whole sequence happens only after first re-confirming `state` via a fresh
  `gh pr view $ARGUMENTS --json state,mergeCommit` call, per step 7(e)'s opening instruction.

(No real `gh`/`git` commands were executed for this exercise — this is a description of exactly
what step 7 of the `merge-pr` skill directs, applied to the stated scenario.)
