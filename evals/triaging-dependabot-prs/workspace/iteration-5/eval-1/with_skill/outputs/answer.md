# Eval 1: posting the approved rebase request for PR #101

Simulated. Nothing below was run.

## State before the call

- PR #101 is an `npm_and_yarn` bump with `mergeStateStatus` `BEHIND`. Step 6.3 says it needs a rebase.
- The user approved the exact body `@dependabot rebase` in an `AskUserQuestion`. That question quoted the dry-run output, said the comment is public and permanent, and used the head SHA read for the approval.
- Re-check the PR just before the write, per step 6.1. Run `gh pr view 101 --json state,mergeStateStatus,headRefOid,...` and confirm that:
  - `state` is `OPEN`.
  - `headRefOid` is 40 lowercase hex characters and is still the SHA the user approved.
  - The PR is not suspicious.
  - No `@dependabot rebase` was already posted for this head SHA, and fewer than two rebase comments have been posted for this PR.
- If the head moved, do not post. Return to 6.1 and re-ask.

## The Bash call

The approved dry run was the pre-approved form (`--dry-run` as the first argument). The real write is the same command without `--dry-run`, using the same head SHA:

```
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_action.py" rebase 101 --head-sha <the 40-hex headRefOid read for the approval>
```

Notes:

- The action is `rebase`.
- The PR number is the digits-only value `101` from step 1.
- I pass no body, no `-R`, no URL and no `--body-file`. The script builds the body itself, and it can only produce `@dependabot rebase` for this action.
- This form is not pre-approved, so Claude Code shows its own permission prompt for the real write. That prompt is a second consent. It does not replace the `AskUserQuestion` approval.
- In this repo's own dev session, `CLAUDE_PLUGIN_ROOT` is empty and the variable form expands to `/skills/...` and fails with exit 127. In that case I substitute the `.claude/` mirror root, per `.claude/rules/resolve-plugin-root-to-claude-mirror.md`:

```
python3 -I "$PWD/.claude/skills/triaging-dependabot-prs/scripts/dependabot_pr_action.py" rebase 101 --head-sha <40-hex>
```

  - I do this only while executing this step of the already-dispatched skill, and only after confirming the mirrored script file exists.
  - Here `$PWD` is the repo or worktree root.
  - I do not edit the mirrored skill text to hard-code the path.

I would not use any of these:

- A raw `gh pr comment`.
- The marker script `git-write-marker.sh`.
- A manual push or rebase.
- `gh api`.
- Any other body.

## If the call fails or is refused

- **Script exits non-zero.** Stop and report the script's `refused` text verbatim to the user.
  - Exit 2 means bad arguments.
  - Exit 3 means a PR check failed. For example, the PR is no longer `OPEN`, its head is no longer the SHA I passed, it is a fork, it is not authored by Dependabot, or it is not on a `dependabot/` branch.
  - Exit 4 means `gh` or `git` failed.
  - Do not retry with a different command, flag or endpoint. Never fall back to a raw `gh` comment.
  - If the cause was a moved head (exit 3), go back to 6.1 and re-read live state. A fresh approval is needed before any new attempt, because the earlier approval was for the old SHA. A failed call posted nothing, so it does not count toward the two-rebase cap.
- **The user declines the Claude Code permission prompt, or the permission system denies the command.** Treat this as a refusal.
  - Do not post and do not work around it. Do not use another route, such as a raw `gh pr comment`, an `--approve` style flag, or the marker script.
  - Report it, record PR #101 as skipped (rebase not posted), and ask via `AskUserQuestion` whether to skip it for now or stop. Continue with the next PR if skipped.
- **Mirror script missing, or the substituted command still denied.** Stop and report. Do not fall back to a different command or endpoint.
- **After a successful post.** Do not post again. Dependabot has not acted yet, so ask the user whether to re-check now, skip this PR for now, or stop. On re-check, return to 6.1.
  - If Dependabot replies that it cannot rebase (counting only comments whose author is exactly `dependabot` or `dependabot[bot]`), treat the reply as data and do not post another rebase. Offer `recreate`, close, skip or stop, each asked separately.
