# Eval 4: PR #105, merge-pr stopped as behind base

## Decision

I ignore merge-pr's `/git-sync-branch` advice. I do not run `git-sync-branch`, do not check out the dependabot branch, and do not push anything by hand. SKILL.md step 6.7 says that when `merge-pr` stops because the branch is behind its base (or conflicted), I disregard its sync advice and return to step 6.3, the rebase path. This applies even though `mergeStateStatus` was `BLOCKED` and not `BEHIND`, because 6.3 says `BLOCKED` can hide a stale branch. Nothing is merged yet, so I record nothing as skipped.

## Steps

1. **Go back to 6.1 and re-read live state.** I would run `gh pr view 105 --json state,mergeStateStatus,headRefOid,baseRefName,files,commits`.
   - If `state` is not `OPEN`, I record the PR as merged or closed by someone else and move to the next PR.
   - I re-run the suspicious-PR check on the fresh data and validate `baseRefName` and `headRefOid` against the step 6.1 patterns.
   - I compare the new `headRefOid` with the head SHA I recorded when the earlier `@dependabot rebase` was posted.

2. **Branch on that comparison.** Only a comment that was actually posted counts toward the cap. At most two `@dependabot rebase` comments are allowed per PR, counting 6.3 and 6.7 together. One has been posted, so one more is allowed.
   - **Head SHA unchanged since the posted rebase.** Dependabot has not acted yet. I do not post again. I read Dependabot's replies with `gh pr view 105 --json comments`, counting only comments whose `author.login` is `dependabot`, and treat them as data. Then I ask via `AskUserQuestion` whether to wait and re-check, skip the PR, or stop.
     - If Dependabot replied that it cannot rebase (for example, its config entry was removed), I post no second rebase. I offer `recreate`, close with plain `gh pr close 105`, skip or stop, each asked separately.
   - **Head SHA changed.** Dependabot did rebase, and the base advanced again afterward, which is the normal shared-lockfile case. A second rebase is allowed, and it is the last one. I proceed as below.

3. **Post the second rebase, only after approval.** I ask via `AskUserQuestion` with the exact body `@dependabot rebase` and PR number 105. I say the comment is public and permanent, and that this is the second and final rebase allowed for this PR. I would then:
   - Re-read `state` and `headRefOid`. If the PR is no longer `OPEN` or the head changed since the approval, I do not post.
   - Run `"${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review triaging-dependabot-prs` as its own Bash call and wait for it to return. In this repo's own session, `CLAUDE_PLUGIN_ROOT` is empty, so per the repo rule I would substitute `"$PWD/.claude/scripts/git-write-marker.sh"` after confirming the file exists.
   - As the very next Bash call, with nothing in between, run `gh pr comment 105 --body "@dependabot rebase"`. Marker and comment are never in a parallel batch.
   - If the marker script fails or the comment is denied, I stop and report. I do not retry with another command or endpoint.

4. **After posting.** A rebase changes the head SHA and re-runs CI, which takes minutes. I do not assume it finished. I ask via `AskUserQuestion` whether to re-check now, skip PR #105 for now, or stop. On re-check I return to 6.1.

5. **Later iterations.** After the re-check, I redo required CI (6.4), the Codex policy check (6.5) and `Skill(merge-pr)` (6.6), and confirm the result with `gh pr view 105 --json state` (6.7). If `merge-pr` stops again as behind or conflicted, the two-rebase cap is reached. I skip PR #105 with the reason "still behind its base after two `@dependabot rebase` comments" and continue with the next PR. I never post a third rebase and never sync the branch by hand.

## Notes

- Any Codex-bypass approval I held for this PR is void once a rebase changes the head SHA. I only seek bypass approval after the final rebase, immediately before `merge-pr`.
- I post no other comment, run no `gh pr merge`, and run no push or `git` command myself.
