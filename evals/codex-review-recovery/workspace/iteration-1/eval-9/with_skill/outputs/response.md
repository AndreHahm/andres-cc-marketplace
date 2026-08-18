# codex-review-recovery — PR #77 simulation

## Step 1 — Resolve the PR

Command:
```
gh pr view "77" --json number,url,headRefName,headRefOid
```

Result (inferred):
```json
{
  "number": 77,
  "url": "https://github.com/octo-org/example-repo/pull/77",
  "headRefName": "feature-x",
  "headRefOid": "abc123"
}
```

Extracted `<owner>/<repo>` = `octo-org/example-repo` from the `url` field. This will be passed as
`-R "octo-org/example-repo"` to every subsequent `gh pr`/`gh run` command.

## Step 2 — Check the current check state

Command:
```
gh pr checks 77 -R "octo-org/example-repo" --json name,workflow,bucket,link
```

Result (inferred): entry with `name = "Await Codex review"` and `workflow = "Codex review status"`
(the display name for `await-codex-review.yml`), `bucket = "fail"`. Exactly one entry matches both
fields.

Since `bucket` is `fail`, this is the only state the skill acts on — continue to step 3.

## Step 3 — Confirm with the human

`AskUserQuestion`:
> The "Await Codex review" check failed for PR #77. Have you confirmed on Codex's own dashboard that
> this PR's review actually finished?
> - Yes — retry
> - No — let me check first

User answer (given by task): **Yes — retry.**

## Step 4 — Re-verify the head hasn't moved

Command:
```
gh pr view 77 -R "octo-org/example-repo" --json headRefOid --jq '.headRefOid'
```

Result (given by task): `abc123`

This matches step 1's `headRefOid` (`abc123`) — no new commit was pushed while waiting for
confirmation. Continue to step 5.

## Step 5 — Post the retry comment

Command:
```
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review codex-review-recovery
```
Result (inferred): marker file written successfully (fresh, <60s old).

Command:
```
gh pr comment 77 -R "octo-org/example-repo" --body "@codex review"
```
Result (inferred): comment posted successfully (e.g. returns the comment URL).

## Step 6 — Re-run the failed check

Command:
```
gh run list --workflow await-codex-review.yml --repo "octo-org/example-repo" --branch "feature-x" \
  --limit 5 --json databaseId,headSha,conclusion
```

Result (given by task):
```json
[
  { "databaseId": 300, "headSha": "abc123", "conclusion": "failure" },
  { "databaseId": 301, "headSha": "abc123", "conclusion": "success" },
  { "databaseId": 302, "headSha": "old111", "conclusion": null }
]
```

Checking entries against step 4's confirmed head SHA (`abc123`): **two** entries match —
`databaseId 300` (conclusion `failure`) and `databaseId 301` (conclusion `success`). Entry 302
(`headSha old111`) does not match and is excluded.

Per the skill's explicit instruction: "If **more than one** entry's `headSha` matches, also stop and
tell the user rather than guessing — a PR reopened or marked ready more than once without a new commit
can produce multiple runs sharing the same head SHA ... and picking the wrong one could rerun an
already-passing or superseded run instead of the failed one confirmed in step 2."

This is exactly that case — the PR was apparently marked ready for review twice (or reopened) without
a new commit in between, producing two runs (300 and 301) sharing head SHA `abc123`, one of which
(301) already succeeded. **Stop here. Do not run `gh run rerun` on either databaseId. Do not proceed
to step 7.**

## Final response to the user

I confirmed PR #77's "Await Codex review" check had failed, you confirmed on Codex's dashboard that
the review actually finished, and the PR's head SHA hadn't moved since (still `abc123`). I posted
`@codex review` on the PR to prompt Codex again.

However, I can't safely pick which workflow run to re-run: `gh run list` for
`await-codex-review.yml` on branch `feature-x` shows **two** runs sharing head SHA `abc123`:

- **databaseId 300** — conclusion `failure` (this looks like the stuck/failed run you're asking me to
  recover)
- **databaseId 301** — conclusion `success` (a separate run for the same commit that already passed)

This usually happens when a PR gets marked ready for review (or reopened) more than once without a
new commit landing in between — each of those events starts its own `Await Codex review` run, and
both runs end up tagged with the same head SHA.

Per this skill's own guidance, I'm stopping rather than guessing which one to re-run — re-running 301
would be pointless (it already passed), and re-running the wrong one risks confusing the signal
further. Since the `@codex review` comment is already posted, could you tell me:

1. Which run you want re-run — 300 (the failed one) or something else — or
2. Whether it's fine to just wait, since run 301 already shows `success` for this exact commit and the
   PR may already be unblocked by that passing run.

I haven't re-run anything or polled further; let me know how you'd like to proceed.
