# Cherry-picking "login-retry-backoff" (shipped with PR #57)

This is a simulated exercise — no `gh`/`git` commands are actually run below. This describes exactly
what I would do, per the `git-worktrees` skill's "Resolving a Cherry-Pick Commit List" section.

## Which resolution path applies

The request names a PR number explicitly ("shipped with PR #57"), so this is **Path 2: By PR number**,
not Path 1 (feature/skill name alone) and not Path 3 (explicit SHA/range). Path 2 is the most reliable
of the three because GitHub's own PR record is authoritative — it doesn't depend on my search terms
matching commit messages (Path 1) or on a human having correctly typed/recalled SHAs (Path 3).

## Step-by-step procedure I would follow

1. **Do not guess, recall, or hand-type a commit list.** I would not try to remember a SHA from earlier
   in the conversation, and I would not assume a local branch named something like `login-retry-backoff`
   or `feature/login-retry-backoff` is an accurate stand-in for what actually merged in PR #57 — a local
   branch can have diverged (additional commits since merge, a rebase, or squash-merge history that no
   longer matches the PR's original commit list) and is not a substitute for GitHub's own record.

2. **Resolve the authoritative commit list directly from GitHub.** I would run one of:
   - `gh pr view 57 --json commits`
   - `gh api repos/{owner}/{repo}/pulls/57/commits`

   Either call returns the actual list of commit SHAs GitHub recorded as belonging to PR #57 — this is
   the skill's documented source of truth for a PR-number-based cherry-pick request, "strictly more
   reliable than reconstructing the list from memory or from a local branch that may have since
   diverged."

3. **Check how the PR was merged.** If PR #57 was squash-merged, the "commits" GitHub lists on the PR
   are the original pre-squash commits, but what actually landed on the base branch is a single squash
   commit not directly returned by that same endpoint — in that case the correct cherry-pick target is
   the one squash commit on the base branch (findable via `gh pr view 57 --json mergeCommit` or by
   locating the merge commit associated with the PR), not the pre-squash list. If it was a regular merge
   commit, the commits endpoint's list is exactly right. I would check the PR's merge method before
   assuming which shape applies, rather than assuming a normal multi-commit list.

4. **Show the resolved list back to the user for confirmation before cherry-picking anything.** Per the
   skill: "All three paths converge on one resolved commit list — show it back to the user for
   confirmation before any `git cherry-pick` runs." I would present the SHA(s), their commit messages,
   and (if squash-merged) which single commit that resolves to, and wait for explicit confirmation.

5. **Only after confirmation, run the actual cherry-pick** (`git cherry-pick <sha>` or
   `git cherry-pick --no-commit <sha>` per Strategy C in `references/merge-worktree.md`), and hand any
   resulting conflicts off to `resolving-merge-conflicts` if the resolution goes beyond "resolve
   conflicts if any."

## Direct answer to "do you ever type out or recall a commit SHA list from memory, or from a local
branch you assume matches?"

No. The skill explicitly forbids that for exactly this scenario. Because the request names a PR number,
I resolve the commit list from GitHub's own PR record (`gh pr view 57 --json commits` /
`gh api repos/{owner}/{repo}/pulls/57/commits`), not from memory and not from an assumed-matching local
branch. A hand-typed or remembered SHA list, or trusting a local branch that merely happens to be named
after the feature, is precisely the failure mode this section of the skill exists to prevent — a local
branch can have diverged since the PR merged, and memory/guesswork has no way to verify that the SHAs
actually correspond to what shipped in PR #57. The only exception the skill allows for typing/recalling
SHAs at all is Path 3 (an explicit SHA/range given by the user), and even then those SHAs must still be
verified (`git merge-base --is-ancestor`, tree-hash comparison for redundant rebase-replay duplicates)
before being trusted — not used as-is.
