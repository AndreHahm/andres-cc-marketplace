# Conflicts That Exist Only on the Remote (Clean Tree)

If `git status` shows uncommitted changes, ask the user to commit or stash first -- `git-rebase-sync` needs
a clean tree before it can start the rebase.

Applies when `git status` shows no unmerged paths and no rebase, merge or cherry-pick in progress, but the
user reports a PR that conflicts with its base. The PR number is data: it must match `^[0-9]{1,9}$` (the script's own limit) before `<number>` goes into any command below, otherwise stop and ask. Nothing is on disk yet, so do not start a trial merge or a
plain merge to put it there. Preview instead, with no change to the worktree or index (`git fetch`
updates remote-tracking refs and `git merge-tree` writes objects, nothing more):

```bash
"${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-conflict-preview.sh" view <number>
git fetch origin
git rev-parse HEAD
git branch --show-current
git remote get-url origin
"${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-conflict-preview.sh" merge-tree <baseRefName>
```

`<baseRefName>` is the PR's own base branch, which need not be the repository default: use it for the
preview and pass it to `git-rebase-sync` as its explicit base argument together with the PR number,
`<baseRefName> --pr <number>` (without a base, that skill rebases onto the repository default branch;
without `--pr`, it cannot run its PR preflight). It is data from GitHub, and git accepts ref names containing shell
metacharacters such as a semicolon, so use it in a command only after checking it matches
`^[A-Za-z0-9_][A-Za-z0-9._/-]*$`; on any other name, stop and ask the user. The preview merges your local
`HEAD`. Compare `git branch --show-current` with the PR's `headRefName` too: an alias branch at the PR's
exact commit passes the commit comparison, yet `git-rebase-sync` would then push to the alias's own name,
creating or rewriting a different remote branch and leaving the PR unchanged. Compare `git rev-parse HEAD`
with the PR's `headRefOid`: if they differ (unpushed commits, a stale
or unrelated branch), stop and ask the user to confirm that this local branch is the one intended, before
reporting a file list or routing on. The list then describes the local branch, not the PR as GitHub sees
it, and a rebase of a stale branch followed by `--force-with-lease` after a fresh fetch can overwrite
commits that exist only on the PR.

- Fork PRs are not supported here. `git-rebase-sync` ends by pushing `origin HEAD:<branch>`, and for a fork
  PR checked out from the base repository's clone, `origin` is the base repository, so the push could
  create or overwrite a same-named branch there while the fork PR stays unchanged. Stop, with an
  unsupported-case message, when `isCrossRepository` is true, or when `git remote get-url origin` (with
  the GitHub host prefix, HTTPS or SSH form, and the `.git` suffix removed) is not the
  `owner/repo` in the PR's `url`.
- `mergeable: CONFLICTING` / `mergeStateStatus: DIRTY` confirms the remote conflict. `UNKNOWN` means
  GitHub has not computed it yet -- rely on the `git merge-tree` result and say so.
- `git merge-tree` neither touches the worktree or index nor creates a commit. Exit status 1 means
  conflicts: the conflicted file names follow the tree OID on the output. Exit status 0 means a clean
  merge. Any other status is an error with unspecified output -- report it, don't guess. A clean merge
  together with `mergeable` other than `CONFLICTING` means there is no conflict to resolve: tell the user
  and stop, without routing to `git-rebase-sync`.
- The preview is advisory. A rebase replays the branch's commits one at a time, while `merge-tree` merges
  only the two tips, so the rebase can stop on different files or hunks.
- Tell the user plainly that the conflicts exist only on the remote and appear on disk only once the
  rebase starts. Report which files will conflict, then invoke `Skill(git-rebase-sync)` with
  `<baseRefName> --pr <number>`; it starts the rebase from this clean tree and surfaces the conflicts as it
  goes. Steps 2-7 of this skill do not apply afterwards.
- Never create a merge commit on a PR branch that merges by rebase. Check
  `gh repo view --json mergeCommitAllowed,rebaseMergeAllowed,squashMergeAllowed` if the merge method is
  unclear, and ask the user only if it still is.
- If the user already named this skill and `git-rebase-sync` (e.g. "resolve conflicts, then sync onto
  main"), route directly -- don't re-ask what they already answered. `git-rebase-sync`'s own
  history-rewrite confirmations (backup, rebase, force-push) still apply.
