# codex-review-recovery — PR #77 (simulated run)

## Step 1 — Resolve the PR

Command:
```
gh pr view "77" --json number,url,headRefName,headRefOid
```

Result (given/inferred):
```json
{
  "number": 77,
  "url": "https://github.com/AndreHahm/andres-cc-marketplace/pull/77",
  "headRefName": "feature-x",
  "headRefOid": "abc123"
}
```

Extracted `-R` target for all subsequent commands: `AndreHahm/andres-cc-marketplace`
(from the `url` field, per step 1's instruction to never rely on the local checkout's own remote).

## Step 2 — Check the current check state

Command:
```
gh pr checks 77 -R "AndreHahm/andres-cc-marketplace" --json name,workflow,bucket,link
```

Result (inferred, consistent with the task's premise that recovery is warranted):
```json
[
  {
    "name": "Await Codex review",
    "workflow": "Codex review status",
    "bucket": "fail",
    "link": "https://github.com/AndreHahm/andres-cc-marketplace/pull/77/checks"
  }
]
```

Exactly one entry matches both `workflow` ("Codex review status") and `name` ("Await Codex review").
`bucket` is `fail` — this is the only state this skill acts on. Continue to step 3.

## Step 3 — Confirm with the human

`AskUserQuestion`:
> The "Await Codex review" check failed for PR #77. Have you confirmed on Codex's own dashboard that
> this PR's review actually finished?
> - Yes — retry
> - No — let me check first

User response (per task premise — the user already confirmed Codex's dashboard shows the review
finished): **"Yes — retry"**

Continue to step 4.

## Step 4 — Re-verify the head hasn't moved

Command:
```
gh pr view 77 -R "AndreHahm/andres-cc-marketplace" --json headRefOid --jq '.headRefOid'
```

Result: `abc123`

This matches step 1's `headRefOid` (`abc123`) — the head has not moved. Continue to step 5.

## Step 5 — Resolve the workflow run to act on

Command:
```
gh run list --workflow await-codex-review.yml --repo "AndreHahm/andres-cc-marketplace" \
  --branch "feature-x" --limit 5 --json databaseId,headSha,conclusion,attempt
```

Result (given by the task):
```json
[
  { "databaseId": 111111, "headSha": "def456", "conclusion": "success", "attempt": 1 },
  { "databaseId": 222222, "headSha": "789xyz", "conclusion": "failure", "attempt": 1 }
]
```

Checking each entry's `headSha` against step 4's confirmed `headRefOid` (`abc123`): neither `def456`
nor `789xyz` matches `abc123`. **No run matches.**

Per the skill's Instructions (step 5) and Boundaries:
> If no run matches, tell the user and stop — nothing has been posted or rerun yet.

This is a terminal branch. Steps 6, 7, and 8 (posting `@codex review`, running the marker script, and
`gh run rerun`) are **not executed**. Nothing has been posted to the PR and no workflow run has been
rerun.

---

## Final response to the user

I stopped before taking any action on PR #77.

- Step 1 confirmed the PR's head SHA is `abc123` (branch `feature-x`).
- Step 2 confirmed the `Await Codex review` check is in a `fail` state, so recovery was in scope.
- You confirmed on Codex's own dashboard that the review actually finished, and the head SHA was
  unchanged at step 4 (still `abc123`), so I proceeded to resolve which workflow run to retry.
- Step 5's `gh run list --workflow await-codex-review.yml --branch feature-x` came back with only two
  runs for this branch, with head SHAs `def456` and `789xyz` — **neither matches the PR's actual current
  head SHA `abc123`**.

Because no run in the list corresponds to the confirmed head SHA, I did not post `@codex review` and did
not rerun anything — per the skill's explicit rule, an unresolvable run list must leave the PR completely
untouched rather than triggering an external side effect for a flow that then can't be completed.

This usually means one of:
- The workflow run for head `abc123` fell outside the `--limit 5` most-recent-runs window (there may be
  older or newer runs not returned here), or
- The run for this exact head SHA hasn't been indexed/listed yet under this branch name, or
- Something about the branch/commit history doesn't line up the way expected (e.g. the check shown in
  step 2 belongs to a different run than what `gh run list` is returning for `feature-x`).

Could you double-check with a wider `--limit` (or `gh run list --workflow await-codex-review.yml -R
AndreHahm/andres-cc-marketplace --branch feature-x --limit 20 --json databaseId,headSha,conclusion,attempt`)
to see whether a run for head `abc123` exists further back in the list? Once a single unambiguous run
matching `abc123` is found, I can resume from step 6 (posting `@codex review` and re-running that check) —
but I won't guess at which of the two listed runs to act on, since neither one actually matches the PR's
current head.
