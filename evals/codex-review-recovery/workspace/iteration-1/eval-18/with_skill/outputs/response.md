# codex-review-recovery — PR #77 (simulated run)

## Step 1 — Resolve the PR

**Command:**
```
gh pr view "77" --json number,url,headRefName,headRefOid
```

**Result:**
```json
{
  "number": 77,
  "url": "https://github.com/octo-org/example-repo/pull/77",
  "headRefName": "feature-x",
  "headRefOid": "abc123"
}
```

Extracted `<owner>/<repo>` = `octo-org/example-repo` from the `url` field. This value is passed as `-R "octo-org/example-repo"` to every subsequent `gh pr`/`gh run` command in steps 2 and 4 through 8.

## Step 2 — Check the current check state

**Command:**
```
gh pr checks 77 -R "octo-org/example-repo" --json name,workflow,bucket,link
```

**Result (relevant entry):**
```json
{
  "name": "Await Codex review",
  "workflow": "Codex review status",
  "bucket": "fail",
  "link": "https://github.com/octo-org/example-repo/pull/77/checks?check_run_id=1234567"
}
```

Entry found matching both `workflow` == "Codex review status" and `name` == "Await Codex review" (exactly one match). `bucket` is `fail` — this is the only state this skill acts on. Continue to step 3.

## Step 3 — Confirm with the human

**AskUserQuestion:**
> The "Await Codex review" check failed for PR #77. Have you confirmed on Codex's own dashboard that this PR's review actually finished?
> - Yes — retry
> - No — let me check first

**User's answer:** "Yes — retry" (per the task: Codex's dashboard shows the review finished for head SHA `abc123`).

Proceeding to step 4.

## Step 4 — Re-verify the head hasn't moved

**Command:**
```
gh pr view 77 -R "octo-org/example-repo" --json headRefOid --jq '.headRefOid'
```

**Result:**
```
abc123
```

Matches step 1's `headRefOid` exactly — head has not moved. Continue to step 5.

## Step 5 — Resolve the workflow run to act on

**Command:**
```
gh run list --workflow await-codex-review.yml --repo "octo-org/example-repo" --branch "feature-x" \
  --limit 5 --json databaseId,headSha,conclusion,attempt
```

(`feature-x` contains no shell metacharacters, so it's safe to quote and pass through.)

**Result (given):**
```json
[
  { "databaseId": 400, "headSha": "abc123", "conclusion": "failure", "attempt": 1 },
  { "databaseId": 398, "headSha": "old999", "conclusion": "success", "attempt": 1 }
]
```

Filtering for entries whose `headSha` matches step 4's confirmed `headRefOid` (`abc123`): exactly **one** match — `databaseId` `400`, `conclusion` `failure`.

Per step 5's three-way conclusion check: not `success` (so nothing already resolved), and it's `failure` — one of the two legitimate "still needs recovery" outcomes. Keep `databaseId = 400` and its current `attempt = 1` as step 8's polling baseline. Nothing has been triggered yet. Continue to step 6.

## Step 6 — Post the retry comment

**Re-check the head immediately before posting (required — step 5's own lookup took real time):**
```
gh pr view 77 -R "octo-org/example-repo" --json headRefOid --jq '.headRefOid'
```

**Result:**
```
abc123
```

Still matches step 4's confirmed value. Proceed.

**Write the guard marker immediately before the guarded command:**
```
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review codex-review-recovery
```

**Result:** marker written successfully (exit 0).

**Post the comment:**
```
gh pr comment 77 -R "octo-org/example-repo" --body "@codex review"
```

**Result (given, as specified by the scenario):**
```
error: HTTP 401: Bad credentials (https://api.github.com/repos/octo-org/example-repo/issues/77/comments)
exit status 1
```

**Decision point — checking this command's exit status is mandatory per step 6:**

> "Check this command's exit status. If it fails (a transient API error, missing write permission, or an authentication failure), stop here and report the error — don't proceed to step 7 as if the comment had actually been posted; that would launch a fresh 30-minute polling window with no corresponding Codex retry ever triggered."

This is exactly an authentication failure (`HTTP 401: Bad credentials`) — one of the three explicitly named failure modes in the skill's own text. The comment was **not** posted (a 401 means the request was rejected before any write occurred). Per the skill's Boundaries section — "Never assumes a `gh pr comment` or `gh run rerun` call succeeded just because it was issued" — the flow **stops here**.

Steps 7 (re-run the failed check) and 8 (poll and report) are **not executed**. No `gh run rerun` is issued; no polling window is opened.

---

## Final response to the user

I stopped before completing the recovery — the retry comment failed to post.

**What happened:**
- PR #77 (`octo-org/example-repo`, head SHA `abc123`): the "Await Codex review" check is `fail`, and you confirmed Codex's dashboard shows the review as finished.
- I re-verified the head hadn't moved, resolved the one matching failed run (`databaseId 400`, `conclusion: failure`), re-confirmed the head again immediately before acting, wrote the guard marker, and attempted to post `@codex review`.
- That comment attempt failed: `gh pr comment 77 -R "octo-org/example-repo" --body "@codex review"` returned **HTTP 401: Bad credentials**.

**Why I stopped instead of continuing:** a 401 means the comment was never actually posted to the PR — `gh`'s credentials were rejected before the write went through. Proceeding to re-run the workflow check anyway would open a fresh 30-minute polling window with no corresponding Codex retry ever having been triggered, which would just produce a misleading timeout later. So nothing further was done: **no comment was posted, the failed check was not re-run, and no polling occurred.**

**What this likely means:** `gh`'s stored credentials (the token used by the `gh` CLI in this environment) are invalid or expired — this is a local/environment auth problem, not something about the PR or the Codex connector itself.

**Next step:** please re-authenticate the `gh` CLI (e.g. `gh auth login` or `gh auth refresh`, or check whether `GH_TOKEN`/`GITHUB_TOKEN` is set to a stale value) and let me know once that's done. I can then re-run this recovery from step 3 (a fresh human confirmation is required anyway per this skill's rules, since no prior attempt actually succeeded).
