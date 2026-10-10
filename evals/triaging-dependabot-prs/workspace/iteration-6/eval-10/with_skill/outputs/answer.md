# Simulated run: triaging-dependabot-prs reads

Nothing below was executed. This describes what I would do. Every GitHub read goes through `scripts/dependabot_pr_read.py`, and I would not use any raw `gh` or `git` command.

The script prefix is the same for every read:

`python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py" <subcommand>`

(In this repo's own session `CLAUDE_PLUGIN_ROOT` is empty, so I would substitute `"$PWD/.claude/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py"`.)

## 1. Collecting the open dependabot PRs (step 1)

```
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py" pr-list
```

- It returns the open PRs by the Dependabot app as one JSON object with `ok`. Each PR has `number`, `title`, `url`, `headRefName`, `isCrossRepository`, `mergeStateStatus` and `createdAt`.
- If `truncated` is true (exactly 100 PRs), the list may be incomplete. I would note the count and ask at step 5 whether to do another pass after wrap-up.
- I would derive `{owner}/{repo}` from a PR's `url` and check it against `^[A-Za-z0-9._-]+/[A-Za-z0-9._-]+$`. If it does not match, I stop.
- I would keep only PRs where `isCrossRepository` is `false` and `headRefName` starts with `dependabot/`, and list the rest as excluded with the reason.

## 2. Re-reading PR #102's live state just before acting (step 6.1)

```
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py" pr-view 102 --fields state,mergeStateStatus,headRefOid,baseRefName,files,commits
```

- `102` is plain digits, as the script requires. The fields come from its fixed allowlist, and the data is returned as `gh` reports it.
- If `state` is not `OPEN`, I record the PR as merged or closed by someone else and move on.
- I re-run step 2's suspicious-PR check on this fresh data. That means paths outside the ecosystem's list, any commit author that is not `dependabot[bot]`, or exactly 100 files or commits.
- `baseRefName` must match `^[A-Za-z0-9._/@+=-]+$` and `headRefOid` must be 40 lowercase hex characters. Otherwise I skip the PR with the reason.
- This read is repeated right before the action, not reused from the earlier classification.

## 3. Checking PR #102's required CI (step 6.4)

```
python3 -I "${CLAUDE_PLUGIN_ROOT}/skills/triaging-dependabot-prs/scripts/dependabot_pr_read.py" pr-checks 102
```

- It returns one row per required check, with `name`, `bucket`, `elapsed` and `link`. `bucket` is `pass`, `fail`, `pending`, `skipping` or `cancel`, and `skipping` counts as passing.
- The script returns the rows even though the underlying `gh` call exits non-zero while anything fails or is pending.
- If a check is pending, I ask the user whether to wait or skip.
- A failing or cancelled required check is a blocker, so I report it and skip the PR. The one exception is `Publish Codex policy result`, which goes to the `references/codex-bypass.md` flow.

## If the read script exits non-zero with a `refused` text

The read failed. I stop and report the `refused` text to the user. I do not retry with a different command, flag or endpoint. I never fall back to a raw `gh pr list|view|checks` or `gh api` command. The skill holds no `gh` read grant, so that fallback is outside what it may do.

## An empty `items` list from the required-checks read

It means no required checks were reported for PR #102. I would not treat that as "CI passed" or as a blocker. I rely on `merge-pr`, which re-checks readiness against branch protection and is authoritative. A required check that never ran may also be missing from this output, which is another reason `merge-pr`'s check is the one that counts.
