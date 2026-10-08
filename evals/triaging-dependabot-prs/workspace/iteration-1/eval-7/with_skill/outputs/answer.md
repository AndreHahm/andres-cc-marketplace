# PR #109: rebase already posted, head SHA unchanged

## What I do

Simulated exercise: no `gh`, `git`, shell command or comment is run. This is what I would do.

1. **Live re-read (step 6.1).** I run `gh pr view 109 --json state,mergeStateStatus,headRefOid,baseRefName,files,commits`. The result is `state` OPEN, `headRefOid` `aaaa111` and `mergeStateStatus` `BEHIND`. I would also re-run the suspicious-PR check on this fresh data and validate `baseRefName` against the allowed pattern.
2. **Branch freshness (step 6.3).** `BEHIND` means the PR needs a rebase. But a `@dependabot rebase` comment was already posted for this exact head SHA (`aaaa111`) and the SHA has not changed. The skill says plainly: "do not post again: dependabot has not acted yet." So:
   - I do not run the marker script.
   - I do not run `gh pr comment`.
   - I do not post a second `@dependabot rebase`.
   - I do not push or rebase manually.
3. **Ask the user via `AskUserQuestion`:** wait (and re-check later), skip this PR for now, or stop the run. I would explain that dependabot has not acted on the earlier comment yet (the SHA is unchanged), and that a rebase re-runs CI and takes minutes.
   - If the user picks wait, I re-check later by returning to 6.1.
   - If the user picks skip, I record #109 as skipped with the reason "rebase requested, dependabot had not acted yet" and move on to the next PR.
   - If the user picks stop, I go to the wrap-up (step 7) and report.
4. I do not call `merge-pr`, because the branch is behind. I also do not offer a Codex bypass, because a rebase would void any approval anyway.

## Effect on the rebase-comment cap

- The cap is at most **two posted** `@dependabot rebase` comments per PR, counted across steps 6.3 and 6.7 together.
- **Only a posted comment counts.** The cap exists to limit comments, not checks or attempts.
- This re-check posts nothing, so it **does not consume cap**. The one comment already posted stays the only one counted: 1 of 2 used, so one remains.
- Declining to repost is the "same SHA, dependabot has not acted" rule. It is not a cap decision, and it is not a skip-for-cap-exhaustion.
- A second rebase comment could only be posted later if the head SHA changes (dependabot rebased) and the PR then falls behind or conflicts again, for example after another merge. It could also be posted if `merge-pr` later stops on the PR as behind or conflicted (6.7). That comment would also need a fresh `AskUserQuestion` approval and the marker-then-comment sequence in two sequential Bash calls. Once two have been posted, the PR is skipped with the reason.

## Files read

- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/SKILL.md
- <repo-root>/plugins/git-kit/skills/merge-pr/SKILL.md (first 325 of 430 lines)
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/ordering-and-checks.md
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/codex-bypass.md
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/test-scenarios.md
