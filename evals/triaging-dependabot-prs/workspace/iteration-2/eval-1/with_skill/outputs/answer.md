# Posting the `@dependabot rebase` request for PR #101 (simulated)

Context: PR #101 is an `npm_and_yarn` bump with `mergeStateStatus` `BEHIND`. The user has approved the rebase request through AskUserQuestion. Per SKILL.md step 6.3 and "Posting a comment", the post takes exactly two sequential Bash calls. They are never run in parallel, and no other Bash call goes between them.

Preconditions I would already have satisfied (no extra Bash call is needed between the two calls below):
- Step 6.1 live re-read of the PR state, with the state still `OPEN` and still `BEHIND`.
- No rebase comment already posted for this head SHA, and fewer than two posted rebase comments for this PR (the cap).
- PR number validated as digits only (101).

## Call 1: write the marker

```
"${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review triaging-dependabot-prs
```

I wait for it to return before doing anything else.

## Call 2: post the comment

This is the very next Bash call, with no other Bash command in between. The guard accepts the marker for about a minute. It deletes the marker on the next Bash call of any kind, so an intervening call would make the comment get denied.

```
gh pr comment 101 --body "@dependabot rebase"
```

There is no `-R`, no URL and no `--body-file`.

## If either call fails or is denied

- If the marker script fails, or the comment is still denied (including because the marker expired or was consumed), I stop and report the failure to the user.
- I do not retry with a different command or endpoint.
- I do not try to work around it: no `gh api` comment POST, no manual `git push` or rebase, no `--body-file` or `-R` variants, and no hand-writing the marker file by another route.
- I do not count it as a posted comment, because only a posted comment counts toward the two-rebase cap.
- I leave PR #101 unrebased and record it as pending or skipped, with the reason being the marker or comment failure.

## After a successful post

I ask the user whether to re-check now, skip PR #101 for now, or stop. A rebase changes the head SHA and re-runs CI, which takes minutes. On a re-check I return to step 6.1.
