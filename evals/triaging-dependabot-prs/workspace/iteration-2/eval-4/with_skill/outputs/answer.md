# PR #105: merge-pr stopped as behind base (simulated; nothing was run or posted)

## Decision
I ignore merge-pr's `/git-sync-branch` advice and return to step 6.3 (Branch freshness). SKILL.md 6.7 says to do exactly this when merge-pr stops because the branch is behind or conflicted. 6.3 also says a PR whose merge-pr run stopped as behind needs a rebase "whatever `mergeStateStatus` says, because `BLOCKED` can hide a stale branch". So the `BLOCKED` reading does not change the outcome.

I never sync the branch myself: no `git-sync-branch`, no checkout of the dependabot branch, no manual push, no hand-resolved lockfile conflict. Only `@dependabot rebase` is allowed.

## Steps
1. **Re-read live state (6.1).** I would run `gh pr view 105 --json state,mergeStateStatus,headRefOid,baseRefName,files,commits`. I stop here if `state` is not `OPEN`. I also re-run the suspicious-PR check and validate `baseRefName` against `^[A-Za-z0-9._/@+=-]+$`.
2. **Compare the head SHA with the earlier comment.** Exactly one `@dependabot rebase` comment was posted earlier in the run.
   - **Head SHA unchanged since that comment:** dependabot has not acted yet. I do **not** post again. I offer wait / skip / stop through `AskUserQuestion`.
   - **Head SHA changed** (dependabot rebased, then the base moved again so the branch is 2 behind): this is a new situation. One posted comment is below the cap of two posted `@dependabot rebase` comments per PR, so a second comment is allowed. It is the last one. Any further need to rebase means I skip PR #105 and report why.
3. **Ask before posting.** I ask `AskUserQuestion` for this exact action: post `@dependabot rebase` on PR #105. This is a separate approval from the plan approval.
4. **Post using the marker-then-comment sequence, as two sequential Bash calls:**
   - First call: `"${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review triaging-dependabot-prs`. I wait for it to return.
   - Very next call, with nothing in between: `gh pr comment 105 --body "@dependabot rebase"`. The number is validated, with no `-R`, URL or `--body-file`.
   - If the marker script fails or the comment is denied, I stop and report. I do not retry with another command.
5. **After posting, ask via `AskUserQuestion`:** re-check now / skip this PR for now / stop. A rebase changes the head SHA and re-runs CI, which takes minutes. If the user picks re-check, I return to 6.1.
6. **Later on the new head.** When 6.1 shows the new SHA and the PR is no longer behind, I continue with 6.4 (required CI), 6.5 (Codex policy check), 6.6 (`Skill(merge-pr)` again) and 6.7 (confirm `MERGED`). Any bypass approval must come after the final rebase, because a rebase voids it.

## Not done
- No second rebase comment on an unchanged head SHA.
- No `/git-sync-branch`, no manual push or conflict resolution.
- No other `@dependabot` command.
- No merge question of my own; merge-pr asks for the merge itself.

## Files read
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/SKILL.md
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/ordering-and-checks.md
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/codex-bypass.md
