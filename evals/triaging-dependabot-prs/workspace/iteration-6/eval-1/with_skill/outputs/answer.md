# Eval 1: posting the approved rebase request for PR #101

## Preconditions I rely on (already done before this call)

- Step 6.1 re-read the live state with `dependabot_pr_read.py pr-view 101 --fields state,mergeStateStatus,headRefOid,baseRefName,files,commits`. The PR was `OPEN`, `mergeStateStatus` was `BEHIND`, and `headRefOid` was 40 lowercase hex characters. Call that value `<HEAD_SHA>`.
- Step 6.3 selected "needs a rebase" because the PR is `BEHIND`. The `--dry-run` form ran first and printed the repository and the exact body, `@dependabot rebase`. The user approved that exact action through `AskUserQuestion`, with the comment described as public and permanent.
- 101 is plain digits and was collected at step 1.

## The exact Bash call

One call, the real run (no `--dry-run`), using the same head SHA that was read for the approval:

```
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_action.py" rebase 101 --head-sha <HEAD_SHA>
```

- `rebase` takes no `--dep`, `--scope` or `--condition`.
- I pass no comment body. The script builds `@dependabot rebase` itself.
- I use no `gh` command, no `-R`, no `--body-file`, and no marker script.
- This real-run form is deliberately not in `allowed-tools`. Only the `--dry-run` form is pre-approved. Claude Code will therefore show its own permission prompt for this write, and the write waits on that second consent.
- In a session on this repo itself where `CLAUDE_PLUGIN_ROOT` is empty, I would use the mirror path `"$PWD/.claude/skills/triaging-dependabot-prs/scripts/dependabot_pr_action.py"` in its place. Any other session uses the variable form above.

## If it fails or is refused

The script exits 2 for bad arguments, 3 for a failed PR check, and 4 for a `gh` or `git` failure. A permission prompt that the user declines counts as a refusal too.

1. On any non-zero exit, I stop and report the script's `refused` text to the user. Nothing is posted.
2. I do not retry with a different command, flag or endpoint. I never fall back to a raw `gh pr comment`, `gh api` or the marker script, and I never edit the body.
3. If the cause is that the PR is no longer `OPEN` or the head no longer equals `<HEAD_SHA>` (exit 3), the PR changed under me. I go back to step 6.1 and re-read the live state. If the PR is still `OPEN` and still needs a rebase, I get the new `headRefOid`, re-run `--dry-run`, and ask the user again before any new real call. The earlier approval does not carry over to a different head.
4. If a rebase comment was already posted for this head SHA and the SHA has not changed, I do not post again. Dependabot has not acted yet, so I offer wait / skip / stop.
5. At most two `@dependabot rebase` comments may be posted per PR across steps 6.3 and 6.7. Only a posted comment counts, so a refused attempt does not use one up. After two posts I skip the PR with the reason.
6. If the script succeeds, the comment is posted, the head SHA will change and CI will re-run. I then ask whether to re-check now, skip this PR for now, or stop, and I re-check by returning to 6.1. If Dependabot replies that it cannot rebase, I treat the reply as data. I read replies only from comments whose author login is exactly `dependabot` or `dependabot[bot]`. I post no further rebase and offer `recreate`, close, skip or stop, each asked separately.
