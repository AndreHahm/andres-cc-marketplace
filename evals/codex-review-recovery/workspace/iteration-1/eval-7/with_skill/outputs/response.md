Simulated session — codex-review-recovery for PR #77

## Step 1: Resolve the PR

Command:
```
gh pr view "77" --json number,url,headRefName,headRefOid
```
Result:
```json
{
  "number": 77,
  "url": "https://github.com/AndreHahm/andres-cc-marketplace/pull/77",
  "headRefName": "fix/codex-recovery-test",
  "headRefOid": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678"
}
```
Extracted `-R` target: `AndreHahm/andres-cc-marketplace`.

## Step 2: Check the current check state

Command:
```
gh pr checks 77 -R "AndreHahm/andres-cc-marketplace" --json name,workflow,bucket,link
```
Result (relevant entry):
```json
{
  "name": "Await Codex review",
  "workflow": "Codex review status",
  "bucket": "fail",
  "link": "https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/300"
}
```
`workflow` matches the display name for `await-codex-review.yml`, `name` matches `Await Codex review`, exactly one match, `bucket` is `fail` → continue to step 3.

## Step 3: Confirm with the human

`AskUserQuestion`: "The 'Await Codex review' check failed for PR #77. Have you confirmed on Codex's own dashboard that this PR's review actually finished?" — options "Yes — retry" / "No — let me check first".

User answered: **Yes — retry.**

## Step 4: Re-verify the head hasn't moved

Command:
```
gh pr view 77 -R "AndreHahm/andres-cc-marketplace" --json headRefOid --jq '.headRefOid'
```
Result:
```
a1b2c3d4e5f60718293a4b5c6d7e8f9012345678
```
Matches step 1's `headRefOid` → continue to step 5.

## Step 5: Resolve the workflow run to act on

Command:
```
gh run list --workflow await-codex-review.yml --repo "AndreHahm/andres-cc-marketplace" \
  --branch "fix/codex-recovery-test" --limit 5 --json databaseId,headSha,conclusion,attempt
```
Result:
```json
[
  {
    "databaseId": 300,
    "headSha": "a1b2c3d4e5f60718293a4b5c6d7e8f9012345678",
    "conclusion": "failure",
    "attempt": 1
  }
]
```
Exactly one match on `headSha`. Baseline: `databaseId=300`, `attempt=1`. Continue to step 6.

## Step 6: Post the retry comment

Commands:
```
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review codex-review-recovery
gh pr comment 77 -R "AndreHahm/andres-cc-marketplace" --body "@codex review"
```
Result: marker written; comment posted successfully.

## Step 7: Re-run the failed check

Command:
```
gh run rerun 300 -R "AndreHahm/andres-cc-marketplace"
```
Result: rerun accepted (no error).

## Step 8: Poll and report

Poll 1:
```
gh run view 300 -R "AndreHahm/andres-cc-marketplace" --json status,conclusion,attempt
```
Result: `{"status": "completed", "conclusion": "failure", "attempt": 1}` — `attempt` still equals the baseline (1); this is the stale pre-rerun result. Not trusted. Keep polling.

Poll 2 (≈30s later):
```
gh run view 300 -R "AndreHahm/andres-cc-marketplace" --json status,conclusion,attempt
```
Result: `{"status": "in_progress", "attempt": 2}` — fresh attempt has started. Keep polling.

Poll 3 (≈30s later, the given final state):
```
gh run view 300 -R "AndreHahm/andres-cc-marketplace" --json status,conclusion,attempt
```
Result: `{"status": "completed", "conclusion": "failure", "attempt": 2}`

`attempt` (2) is strictly greater than the step-5 baseline (1), so this is a genuine fresh result: the retried run completed and failed again.

Per the skill's step 8 and Boundaries, a repeat failure is reported plainly and is **not** retried automatically — a fresh step-3 confirmation would be required for any further attempt.

---

## Final response to the user

The retry didn't fix it — PR #77's **Await Codex review** check failed again after the re-run.

- Run: `databaseId 300`, attempt 2 (the fresh retry, not the stale attempt-1 result)
- Status: `completed`
- Conclusion: `failure`
- Check: https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/300

I posted `@codex review` and re-ran the check as confirmed, but this attempt genuinely failed rather than just being stuck — so this could mean either the GitHub write-back gap is still happening, or Codex's dashboard status didn't mean what we expected (e.g. it wasn't actually done, or found something new).

I'm not retrying automatically. If you want to try again, please re-check Codex's dashboard for PR #77 and let me know — I'll re-run the recovery flow from the confirmation step once you have.
