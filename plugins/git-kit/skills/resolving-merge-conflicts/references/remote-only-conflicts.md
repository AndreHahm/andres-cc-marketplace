# Conflicts That Exist Only on the Remote (Clean Tree)

If `git status` shows uncommitted changes, ask the user to commit or stash first -- `git-rebase-sync` needs
a clean tree before it can start the rebase.

Applies when `git status` shows no unmerged paths and no rebase, merge or cherry-pick in progress, but the
user reports a PR that conflicts with its base. Nothing is on disk yet, so do not start a trial merge or a
plain merge to put it there. Preview instead, with no change to the worktree or index (`git fetch`
updates remote-tracking refs and `git merge-tree` writes objects, nothing more):

```bash
gh pr view <number> --json mergeable,mergeStateStatus
git fetch origin
git merge-tree --write-tree --name-only origin/<base> HEAD
```

- `mergeable: CONFLICTING` / `mergeStateStatus: DIRTY` confirms the remote conflict. `UNKNOWN` means
  GitHub has not computed it yet -- rely on the `git merge-tree` result and say so.
- `git merge-tree` neither touches the worktree or index nor creates a commit. Exit status 1 means
  conflicts: the conflicted file names follow the tree OID on the output. Exit status 0 means a clean
  merge. Any other status is an error with unspecified output -- report it, don't guess.
- The preview is advisory. A rebase replays the branch's commits one at a time, while `merge-tree` merges
  only the two tips, so the rebase can stop on different files or hunks.
- Tell the user plainly that the conflicts exist only on the remote and appear on disk only once the
  rebase starts. Report which files will conflict, then route to `git-rebase-sync`, which starts the
  rebase from this clean tree and surfaces the conflicts as it goes.
- Never create a merge commit on a PR branch that merges by rebase. Check
  `gh repo view --json mergeCommitAllowed,rebaseMergeAllowed,squashMergeAllowed` if the merge method is
  unclear, and ask the user only if it still is.
- If the user already named this skill and `git-rebase-sync` (e.g. "resolve conflicts, then sync onto
  main"), route directly -- don't re-ask what they already answered. `git-rebase-sync`'s own
  history-rewrite confirmations (backup, rebase, force-push) still apply.
