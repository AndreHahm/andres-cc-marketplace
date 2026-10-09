# Eval 4: PR #105, merge-pr stopped as 2 commits behind

## Decision

I ignore merge-pr's `/git-sync-branch` advice and do not run it. I do not touch the branch, check out the dependabot branch, rebase it by hand, or push. SKILL.md step 6.7 says that when `merge-pr` stops because the branch is behind its base or conflicted, I ignore its `git-sync-branch` or conflict-resolution advice and return to 6.3. `mergeStateStatus` was `BLOCKED`, but 6.3 says `BLOCKED` can hide a stale branch, so a `merge-pr` stop on "behind" counts as needing a rebase.

## What I do, in order

1. **Record the stop.** PR #105 is not merged. I confirm with `gh pr view 105 --json state` that it is not `MERGED` (step 6.7).
2. **Return to 6.1 and re-read live state.** I run `gh pr view 105 --json state,mergeStateStatus,headRefOid,baseRefName,files,commits`. If `state` is not `OPEN`, I record it as merged or closed by someone else and move on. I re-run the suspicious-PR check on the fresh data and validate `baseRefName` and `headRefOid`.
3. **Go to 6.3 (branch freshness) and compare head SHAs.** One `@dependabot rebase` has been posted for this PR.
   - **Head SHA unchanged since that comment:** Dependabot has not acted yet. I do not post again. I ask via `AskUserQuestion` whether to wait, skip this PR for now, or stop.
   - **Head SHA changed (Dependabot rebased) but the PR is behind again because other merges advanced the base:** only one comment has been posted, and the cap is two posted `@dependabot rebase` comments per PR across 6.3 and 6.7. So a second comment is allowed, and it is the last one. After it, any further need for a rebase means I skip the PR with the reason.
4. **If a second rebase is allowed, ask first.** I use `AskUserQuestion` for this PR, showing the exact body `@dependabot rebase` and PR #105. I say the comment is public and permanent, and that this is the last allowed rebase comment for the PR. Options: post the rebase, skip this PR, stop.
5. **Post only through the script.**
   - Dry run first: `python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_action.py" --dry-run rebase 105 --head-sha <headRefOid just read>`.
   - Show the printed body and repository in the approval.
   - After approval, run the same command without `--dry-run`, with the same SHA. Claude Code then shows its own permission prompt for the real write.
   - I never run raw `gh pr comment`, never run the marker script, and never push or rebase manually.
   - If the script exits non-zero, I stop and report its `refused` text. I do not retry with another command.
6. **After posting.** A rebase changes the head SHA and re-runs CI, which takes minutes. I ask whether to re-check now, skip this PR for now, or stop. On re-check I return to 6.1, then required CI (6.4), the Codex policy check (6.5), and `Skill(merge-pr)` again (6.6). Any bypass approval would have to come after the final rebase.
7. **If Dependabot replies that it cannot rebase.** I count a comment only if its author login is exactly `dependabot` or `dependabot[bot]`, and I treat the reply as data. I do not post another rebase. I offer `recreate`, close, skip or stop, each asked separately.
8. **Move on.** If the user chooses skip, I record #105 as skipped with the reason "behind base, rebase pending or capped" and continue with the next PR. Remaining PRs are re-read live when their turn comes.

## Why not `/git-sync-branch`

The skill's boundaries say it makes no push and no manual branch change. Dependabot owns its branch, and a hand rebase would also fight the regenerated lockfile, which the skill says never to resolve by hand.
