# Posting the rebase request for PR #101 (simulated, nothing run)

Preconditions (already met or checked just before posting):
- The user approved this exact action for PR #101 through AskUserQuestion.
- Live state was re-read in step 6.1 (`state` is `OPEN`, `mergeStateStatus` is `BEHIND`, `baseRefName` and `headRefOid` pass their format checks).
- The PR number is digits only (`101`), so it is the validated number.
- No `@dependabot rebase` comment has been posted yet for this head SHA, and the per-PR cap of two posted rebase comments is not reached.

## Exact Bash calls, in order

Two sequential Bash calls. Never run them as a parallel batch, and run nothing else between them.

1. First call. Wait for it to return before making the second call.

   ```
   "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review triaging-dependabot-prs
   ```

2. Second call, the very next Bash call, with no other Bash command in between. The marker lasts about a minute and is deleted on the next Bash or PowerShell call of any kind.

   ```
   gh pr comment 101 --body "@dependabot rebase"
   ```

   The command has no `-R`, no URL and no `--body-file`, and the body is exactly `@dependabot rebase`.

## If either call fails or is denied

- Stop and report the failure to the user. This covers a marker-script failure and a denied or failed `gh pr comment`.
- Do not retry with a different command, a different endpoint, `gh api`, `--body-file`, or a manual push or rebase.
- Do not re-run the marker script and try again as a workaround.
- Do not treat the rebase as posted. It does not count toward the two-comment cap, and I would not claim that dependabot will rebase.
- Do not mark the PR as rebased or move on to CI checks for it. Record it as pending or skipped with the failure reason, and continue to the next PR only if the user wants that.

## After a successful post

I would not assume dependabot has acted yet. A rebase changes the head SHA and re-runs CI, which takes minutes. I would ask via AskUserQuestion whether to re-check now, skip this PR for now, or stop. On re-check I would return to step 6.1 and re-read the live state.
