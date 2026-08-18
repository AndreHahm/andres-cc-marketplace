# codex-review-recovery — PR #77 simulated run

Following `codex-review-recovery`'s Instructions in exact step order.

## Step 1 — Resolve the PR

`$ARGUMENTS` = `77` — checked against the shell-metacharacter blocklist (`;`, `` ` ``, `$(`, `&`, `|`, `(`, `)`); none present, so it passes through.

```
gh pr view "77" --json number,url,headRefName,headRefOid
```

Result:
```json
{
  "number": 77,
  "url": "https://github.com/example-org/example-repo/pull/77",
  "headRefName": "feature-x",
  "headRefOid": "abc123"
}
```

Extracted `<owner>/<repo>` = `example-org/example-repo` from the `url` field. This will be passed as `-R "example-org/example-repo"` to every `gh pr`/`gh run` command from here on.

## Step 2 — Check the current check state

```
gh pr checks 77 -R "example-org/example-repo" --json name,workflow,bucket,link
```

Result (relevant entry):
```json
[
  {
    "name": "Await Codex review",
    "workflow": "Codex review status",
    "bucket": "fail",
    "link": "https://github.com/example-org/example-repo/pull/77/checks?check_run_id=900"
  }
]
```

Exactly one entry matches both `workflow == "Codex review status"` and `name == "Await Codex review"`. `bucket` is `fail` → this is the only state the skill acts on. Continue to step 3.

## Step 3 — Confirm with the human

`AskUserQuestion`:

> The "Await Codex review" check failed for PR #77. Have you confirmed on Codex's own dashboard that this PR's review actually finished?
> - Yes — retry
> - No — let me check first

User response: **Yes — retry** (the user has confirmed Codex's dashboard shows the review finished).

## Step 4 — Re-verify the head hasn't moved

```
gh pr view 77 -R "example-org/example-repo" --json headRefOid --jq '.headRefOid'
```

Result: `abc123`

This matches step 1's `headRefOid` (`abc123`) — confirmed head SHA for this run is `abc123`. Continue to step 5.

## Step 5 — Resolve the workflow run to act on

`<headRefName>` = `feature-x` — checked against the shell-metacharacter blocklist; none present, so it's safe to interpolate.

```
gh run list --workflow await-codex-review.yml --repo "example-org/example-repo" --branch "feature-x" \
  --limit 5 --json databaseId,headSha,conclusion,attempt
```

Result:
```json
[
  {
    "databaseId": 300,
    "headSha": "abc123",
    "conclusion": "timed_out",
    "attempt": 1
  }
]
```

Exactly one entry, and its `headSha` (`abc123`) matches step 4's confirmed `headRefOid`. Its `conclusion` is `timed_out` — not `success` (so not already resolved by someone else), and it is one of the two legitimate "still needs recovery" outcomes (`failure` or `timed_out`), matching the skill's stated scope of a check that "failed or timed out." Proceed.

Baseline captured for step 8: `<databaseId> = 300`, baseline `attempt = 1`. Nothing has been triggered yet. Continue to step 6.

## Step 6 — Post the retry comment

Re-fetch and compare the head immediately before posting, since step 5's `gh run list` call took real (if brief) time:

```
gh pr view 77 -R "example-org/example-repo" --json headRefOid --jq '.headRefOid'
```

Result: `abc123` — still matches step 4's confirmed value. Proceed.

Write the marker required by git-kit's `guard-raw-pr-review.sh` hook, immediately before the guarded command:

```
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review codex-review-recovery
```

Result: marker file written successfully (exit 0).

Post the retry comment:

```
gh pr comment 77 -R "example-org/example-repo" --body "@codex review"
```

Result: comment posted —
`https://github.com/example-org/example-repo/pull/77#issuecomment-1000001`

## Step 7 — Re-run the failed check

Re-check the target run's conclusion immediately before rerunning it, since step 6's own network round-trip elapsed since step 5 captured it:

```
gh run view 300 -R "example-org/example-repo" --json conclusion
```

Result:
```json
{ "conclusion": "timed_out" }
```

Still `timed_out` (not `success`, not an unexpected value) — proceed.

```
gh run rerun 300 -R "example-org/example-repo"
```

Result: rerun triggered successfully (no output).

## Step 8 — Poll briefly and report

Polling the exact run (`databaseId 300`), comparing `attempt` against step 5's baseline of `1`, waiting `sleep 30` between calls:

**Poll 1:**
```
gh run view 300 -R "example-org/example-repo" --json status,conclusion,attempt
```
Result: `{"status":"completed","conclusion":"timed_out","attempt":1}`
`attempt` (1) is not strictly greater than baseline (1) → this is the stale pre-rerun result. Don't trust it; keep polling.

```
sleep 30
```

**Poll 2:**
```
gh run view 300 -R "example-org/example-repo" --json status,conclusion,attempt
```
Result: `{"status":"in_progress","conclusion":null,"attempt":2}`
`attempt` has incremented to 2 (> baseline), but `status` is not yet `completed`. Keep polling.

```
sleep 30
```

**Poll 3:**
```
gh run view 300 -R "example-org/example-repo" --json status,conclusion,attempt
```
Result: `{"status":"completed","conclusion":"success","attempt":2}`
`attempt` (2) is strictly greater than baseline (1), and `status` is `completed` — this is a genuine fresh result. `conclusion` is `success`.

Report: success.

---

## Final response to the user

The `Await Codex review` check for PR #77 has been recovered successfully:

- The check was confirmed `fail` (step 2), and you confirmed Codex's own dashboard showed the review already finished.
- The PR's head (`abc123`) was verified unchanged both before asking and again immediately before posting.
- Exactly one matching workflow run was found (run `300`, `timed_out`, attempt 1) and re-verified `timed_out` immediately before rerunning it.
- Posted `@codex review` on PR #77, then reran run `300`.
- Polled the fresh rerun (attempt `2`) directly rather than the PR-level check summary: it completed with **`success`** after 2 polls (~1 minute).

The `Await Codex review` check for PR #77 now shows **success**. No further action needed.
