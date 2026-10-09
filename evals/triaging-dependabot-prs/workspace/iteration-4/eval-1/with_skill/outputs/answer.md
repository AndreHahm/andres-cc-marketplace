# PR #101 (npm_and_yarn, BEHIND): posting the rebase request

Simulated; nothing was run.

## Before the two Bash calls

The user has already approved the rebase via AskUserQuestion. Per `references/dependabot-comments.md` ("Order of the final steps"), I first do the live re-read: `gh pr view 101 --json state,headRefOid` (or the step 6.1 equivalent). This re-read is not one of the two posting calls. It must come before the marker, because any Bash call between the marker and the comment consumes the marker.

- If `state` is not `OPEN`, or `headRefOid` differs from what the approval was based on, I do not post. I record the change and return to step 6.1.
- I also check that no `@dependabot rebase` was already posted for this head SHA (the 6.3 no-repost rule) and that fewer than two rebase comments have been posted for this PR (the cap).

## The two Bash calls, in order

Two sequential Bash calls, never a parallel batch, with no other Bash command in between:

1. Write the marker and wait for it to return:
   `"${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review triaging-dependabot-prs`
   In this repo's own session `CLAUDE_PLUGIN_ROOT` may be empty. The path would then expand to `/scripts/...` and fail with exit 127, so I use the `.claude` mirror path instead: `"$PWD/.claude/scripts/git-write-marker.sh" gh-pr-review triaging-dependabot-prs`.
2. As the very next Bash call:
   `gh pr comment 101 --body "@dependabot rebase"`
   The number is the validated digits-only number from step 1. The body is exactly that one string. There is no `-R`, URL or `--body-file`.

## If either call fails or is denied

- **The marker script fails (call 1):** I stop and report. I do not post the comment anyway, and I do not retry with a different command.
- **The comment is denied or fails (call 2):** typically git-kit's guard, because the marker was missing, stale or consumed. I stop and report. I do not retry with a different command or endpoint. I do not hand-write a marker, re-run the marker outside the skill, or fall back to `gh api`, a manual push or a browser action.
- **Missing mirror script:** if I used the mirror path and the file is missing, or the substituted command is still denied, I stop and report.

I record PR #101 as not yet rebased (skipped or pending, with the reason) and move on to the next PR, or ask the user whether to skip or stop.

## After a successful post

I do not assume CI finished. The rebase changes the head SHA and re-runs CI, which takes minutes. I ask via AskUserQuestion whether to re-check now, skip this PR for now, or stop. On re-check I return to step 6.1.
