# Eval 4: merge-pr stopped on PR #105 as behind its base

## Decision

I ignore merge-pr's `/git-sync-branch` advice. I do not run it, check out the dependabot branch, or push anything by hand. Per step 6.7, a "behind or conflicted" stop from `merge-pr` sends the PR back to step 6.3 (branch freshness). A `BLOCKED` `mergeStateStatus` does not rule out a stale branch, so 6.3 treats merge-pr's report as a rebase trigger.

## What I do, in order

1. **Re-read live state (6.1).** I would run `gh pr view 105 --json state,mergeStateStatus,headRefOid,baseRefName,files,commits`. The earlier read may be stale. If `state` is not `OPEN`, I record the PR as merged or closed by someone else and move on. I re-run the suspicious-PR check. I validate `baseRefName` and `headRefOid` (40 lowercase hex) before using them anywhere.

2. **Check the rebase cap and the head SHA (6.3).** One `@dependabot rebase` has been posted, and the cap is two posted comments per PR across 6.3 and 6.7. Only posted comments count. So a second comment is allowed, but only if the head has moved on:
   - **Head SHA unchanged since the earlier rebase comment.** Dependabot has not acted yet. I do not post again. I ask via `AskUserQuestion` whether to wait, skip this PR for now, or stop.
   - **Head SHA changed (the earlier rebase landed) and the branch is behind again.** This is the likely case if the base advanced after that rebase. I ask via `AskUserQuestion` for approval to post the second `@dependabot rebase`. The approval covers that exact action for PR #105. This is the last allowed comment, because the cap is then reached.

3. **Post the comment only if approved (Posting a comment).** I would use two sequential Bash calls, never in parallel:
   1. `"${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review triaging-dependabot-prs`
   2. Immediately after, with no other Bash command in between: `gh pr comment 105 --body "@dependabot rebase"`

   The PR number is the validated digits-only number, with no `-R`, URL or `--body-file`. If the marker script fails or the comment is denied, I stop and report. I do not retry with another command.

4. **After posting, ask what next.** A rebase changes the head SHA and re-runs CI, which takes minutes. I ask via `AskUserQuestion` whether to re-check now, skip PR #105 for now, or stop. On re-check I return to 6.1. Then I run required CI (6.4), the Codex policy check (6.5) and `Skill(merge-pr)` again (6.6). After a rebase, any Codex bypass approval is void and must be re-approved against the new head.

5. **Cap exhausted.** If PR #105 ends up behind or conflicted again after the second posted rebase, I skip it and record the reason as "rebase cap (2 posted comments) reached". I do not post a third comment.

6. **Continue the loop.** Whichever branch applies, I continue with the next PR. The remaining PRs are likely behind too, because the base advanced.

## What I do not do

- Run `/git-sync-branch`, `git rebase`, or any manual push or conflict resolution.
- Post `@dependabot rebase` without a fresh approval and a fresh live read.
- Post a second rebase comment while the head SHA is unchanged from the one already commented on.
