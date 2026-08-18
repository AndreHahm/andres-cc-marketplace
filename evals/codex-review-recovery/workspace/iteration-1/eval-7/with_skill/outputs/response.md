# codex-review-recovery — simulated run for PR #77

## Step 1 — Resolve the PR

```
$ gh pr view "77" --json number,url,headRefName,headRefOid
```
Result:
```json
{
  "number": 77,
  "url": "https://github.com/AndreHahm/andres-cc-marketplace/pull/77",
  "headRefName": "fix/parse-days-threshold",
  "headRefOid": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0"
}
```
Extracted `-R "AndreHahm/andres-cc-marketplace"` for all subsequent commands.

## Step 2 — Check current check state

```
$ gh pr checks 77 -R "AndreHahm/andres-cc-marketplace" --json name,workflow,bucket,link
```
Result (relevant entry):
```json
{"name": "Await Codex review", "workflow": "Codex review status", "bucket": "fail", "link": "https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/300"}
```
Exactly one entry matches both `workflow == "Codex review status"` and `name == "Await Codex review"`. `bucket` is `fail` → continue to step 3.

## Step 3 — Confirm with the human

`AskUserQuestion`: "The 'Await Codex review' check failed for PR #77. Have you confirmed on Codex's own dashboard that this PR's review actually finished?"
Options: "Yes — retry" / "No — let me check first"

User answer: **"Yes — retry"** (already confirmed per the session's prior turn).

## Step 4 — Re-verify the head hasn't moved

```
$ gh pr view 77 -R "AndreHahm/andres-cc-marketplace" --json headRefOid --jq '.headRefOid'
```
Result: `a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0`

Matches step 1's `headRefOid`. Continue to step 5.

## Step 5 — Post the retry comment

```
$ "${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review codex-review-recovery
```
Result: marker file written (`gh-pr-review` guard-type, current timestamp).

```
$ gh pr comment 77 -R "AndreHahm/andres-cc-marketplace" --body "@codex review"
```
Result: comment posted successfully (`https://github.com/AndreHahm/andres-cc-marketplace/pull/77#issuecomment-...`).

## Step 6 — Re-run the failed check

```
$ gh run list --workflow await-codex-review.yml --repo "AndreHahm/andres-cc-marketplace" --branch "fix/parse-days-threshold" --limit 5 --json databaseId,headSha,conclusion
```
Result:
```json
[
  {"databaseId": 300, "headSha": "a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0", "conclusion": "failure"}
]
```
Exactly one entry, and its `headSha` matches step 4's confirmed `headRefOid`.

```
$ gh run rerun 300 -R "AndreHahm/andres-cc-marketplace"
```
Result: rerun triggered. `databaseId` to poll in step 7: **300**.

## Step 7 — Poll and report

```
$ gh run view 300 -R "AndreHahm/andres-cc-marketplace" --json status,conclusion
```
Poll 1 result: `{"status": "completed", "conclusion": "failure"}`
→ No `queued`/`in_progress` observed yet — this is still the stale pre-rerun result. Not trusted. Keep polling.

```
$ gh run view 300 -R "AndreHahm/andres-cc-marketplace" --json status,conclusion
```
Poll 2 result: `{"status": "in_progress", "conclusion": null}`
→ Fresh attempt confirmed started.

```
$ gh run view 300 -R "AndreHahm/andres-cc-marketplace" --json status,conclusion
```
Poll 3 result: `{"status": "completed", "conclusion": "failure"}`
→ `in_progress` was already observed on the prior poll, so this `completed` result is genuine: the retry itself failed.

Per the skill's Boundaries: a repeat failure is reported plainly and never auto-retried — the flow stops here and returns control to the human for a fresh step-3 confirmation if they want to try again.

---

## Final response to the user

The retry didn't fix it. Here's where things stand on PR #77:

- Posted `@codex review` and re-ran the `Await Codex review` job (run `300`) for head `a1b2c3d4e5f`.
- The re-run genuinely completed (confirmed via an observed `in_progress` status before the completion) with **conclusion: failure** — this isn't a stale pre-rerun read, it's the real outcome of this retry.

This means either the write-back gap is still happening on this second attempt, or Codex's dashboard status didn't correspond to what was expected for this head SHA. I'm not retrying automatically — per this skill's own rule, a repeat failure needs a fresh human confirmation before trying again, not an automatic second attempt.

If you want to retry again: re-check Codex's dashboard for PR #77 at this head commit, and if it still shows the review as finished, let me know and I'll re-run the recovery flow from the confirmation step. You can also check the run directly: https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/300
