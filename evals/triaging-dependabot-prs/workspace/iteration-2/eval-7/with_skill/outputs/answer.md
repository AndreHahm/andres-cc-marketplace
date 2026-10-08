# PR #109: re-check after `@dependabot rebase` shows no change

## Situation
- I posted `@dependabot rebase` on PR #109 at head SHA `aaaa111`.
- The user asked for a re-check, so I returned to step 6.1 and re-read the PR (`gh pr view 109 --json state,mergeStateStatus,headRefOid,baseRefName,files,commits`).
- The fresh read shows `headRefOid` is still `aaaa111` and `mergeStateStatus` is still `BEHIND`.
- The state is `OPEN`, so the PR was not merged or closed by someone else.

## What I do
1. I do not post `@dependabot rebase` again. Step 6.3 says that if a rebase comment was already posted for this head SHA and the SHA is unchanged, I must not post again. An unchanged SHA means dependabot has not acted yet. A rebase would have changed the head SHA and re-run CI.
2. I do not rebase or push by hand, and I do not use `git-sync-branch` or any other workaround. Rebases go only through the `@dependabot rebase` comment.
3. I call `AskUserQuestion` with three options: wait and re-check later, skip this PR for now, or stop the run. This is the "offer wait / skip / stop" that step 6.3 prescribes.
   - **Wait:** I re-read the live state (back to 6.1) when the user says to. If the SHA has changed, I continue to 6.4 (required CI) on the new head.
   - **Skip:** I record PR #109 as skipped or pending, with the reason "rebase requested, dependabot has not acted yet", and move to the next PR.
   - **Stop:** I go to the wrap-up table (step 7).
4. I run no `gh` write, no marker script and no `merge-pr` call. `merge-pr` would refuse a BEHIND branch anyway.

## Effect on the rebase-comment cap
- The cap is at most two posted `@dependabot rebase` comments per PR, counted across 6.3 and 6.7.
- Only a comment that was actually posted counts toward it. The re-check posted nothing, so the count is unchanged.
- So far one rebase comment has been posted on #109, which leaves one more allowed.
- The unchanged-SHA case is a wait, not a retry. Waiting does not use up the second comment.
- If the head SHA changes later (dependabot rebased) and the PR is behind or conflicted again, for example after another merge, a second rebase comment is allowed. That one needs its own user approval and the marker-then-comment sequence, and it reaches the cap of two. After that, further rebases are not posted and the PR is skipped with the reason.
- If the SHA stays `aaaa111` and the user chooses to skip, I do not post a second comment just to use up the budget.

## Files read
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/SKILL.md
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/ordering-and-checks.md
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/codex-bypass.md
