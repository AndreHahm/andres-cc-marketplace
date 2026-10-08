# Posting the rebase request for dependabot PR #101 (simulated, nothing executed)

Basis: SKILL.md step 6.3 (branch freshness) and the "Posting a comment" section.

## Preconditions (already true or checked before the two calls)

- `mergeStateStatus` is `BEHIND`, so step 6.3 applies. The user approved this exact action (`@dependabot rebase` on PR #101) via `AskUserQuestion`.
- The PR number is digits-only (`101`), so it is validated.
- Step 6.1's live re-read (`gh pr view 101 --json state,mergeStateStatus,headRefOid,baseRefName,files,commits`) was done just before asking. If the PR is no longer `OPEN` or the head SHA changed, I do not post, and I record or re-ask instead.
- No `@dependabot rebase` has been posted for this head SHA yet, and fewer than two rebase comments have been posted for this PR, so the cap does not block it. This is the first posted comment, so it counts as 1 of 2.

## The exact Bash calls, in order

They are two separate, sequential Bash calls. They are never run in a parallel batch, and no other Bash command goes between them.

1. Call 1, and wait for it to return:

   ```
   "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review triaging-dependabot-prs
   ```

2. Call 2, as the very next Bash call:

   ```
   gh pr comment 101 --body "@dependabot rebase"
   ```

Call 2 has no `-R`, no URL, no `--body-file`, and no other body text. The marker is valid for about a minute and is deleted by the next Bash or PowerShell call of any kind. So nothing else, including a `gh pr view`, may run between the two calls.

## If either call fails or is denied

- **Call 1 fails** (the marker script errors): I stop and report. I do not post the comment anyway, and I do not try another command or endpoint (test scenario 24).
- **Call 2 is denied or fails** (for example the guard rejects it because the marker is stale or another Bash call intervened): I stop and report. I do not retry with a different command or endpoint, and I do not write the marker again and loop. I do not fall back to a manual push, `gh api`, `--body-file`, or any other route (SKILL.md "Posting a comment", test scenario 23).
- In both cases I record PR #101 as not rebased by this run, say that no comment was posted (or that the post could not be confirmed), and ask the user via `AskUserQuestion` how to proceed. Whether it counts toward the cap depends on whether a comment was actually posted, because only a posted comment counts.

## After a successful post

Dependabot acts asynchronously, the head SHA will change, and CI re-runs, which takes minutes. I do not assume CI is finished. I ask via `AskUserQuestion` whether to re-check now, skip this PR for now, or stop. A re-check returns to step 6.1. If the head SHA is unchanged after a posted rebase, I do not post again. I offer wait / skip / stop.

## Files read

- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/SKILL.md
- <repo-root>/plugins/git-kit/skills/merge-pr/SKILL.md (first 325 of 430 lines)
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/ordering-and-checks.md
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/codex-bypass.md
- <repo-root>/plugins/git-kit/skills/triaging-dependabot-prs/references/test-scenarios.md
