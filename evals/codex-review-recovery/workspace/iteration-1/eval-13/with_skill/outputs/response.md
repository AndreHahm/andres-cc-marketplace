# codex-review-recovery — PR #77 simulated run

## Simulated commands, in skill order

**Step 1 — Resolve the PR**
```
gh pr view "77" --json number,url,headRefName,headRefOid
```
Result:
```json
{
  "number": 77,
  "url": "https://github.com/AndreHahm/andres-cc-marketplace/pull/77",
  "headRefName": "fix/retry-logging",
  "headRefOid": "abc123"
}
```
`<owner>/<repo>` extracted from `url`: `AndreHahm/andres-cc-marketplace`. This is passed as `-R "AndreHahm/andres-cc-marketplace"` to every command from step 2 onward.

**Step 2 — Check the current check state**
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
Exactly one entry matches `workflow == "Codex review status"` and `name == "Await Codex review"`, and its `bucket` is `fail` → continue to step 3.

**Step 3 — Confirm with the human**
`AskUserQuestion`:
> "The 'Await Codex review' check failed for PR #77. Have you confirmed on Codex's own dashboard that this PR's review actually finished?"
> Options: "Yes — retry" / "No — let me check first"

Human response: **"Yes — retry"** → continue to step 4.

**Step 4 — Re-verify the head hasn't moved**
```
gh pr view 77 -R "AndreHahm/andres-cc-marketplace" --json headRefOid --jq '.headRefOid'
```
Result: `abc123` — matches step 1's `headRefOid` (`abc123`) → continue to step 5.

**Step 5 — Resolve the workflow run to act on**
```
gh run list --workflow await-codex-review.yml --repo "AndreHahm/andres-cc-marketplace" --branch "fix/retry-logging" \
  --limit 5 --json databaseId,headSha,conclusion,attempt
```
Result:
```json
[
  {"databaseId": 300, "headSha": "abc123", "conclusion": "failure", "attempt": 1}
]
```
Exactly one entry's `headSha` matches step 4's confirmed `headRefOid` (`abc123`). Resolved run: `databaseId 300`, baseline `attempt 1` → continue to step 6. Nothing posted or rerun yet.

**Step 6 — Post the retry comment**
Re-check head immediately before posting:
```
gh pr view 77 -R "AndreHahm/andres-cc-marketplace" --json headRefOid --jq '.headRefOid'
```
Result: `abc123` — still matches step 4's confirmed value → proceed.

Write the guard marker immediately before the comment call:
```
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review codex-review-recovery
```
Result: marker written successfully (exit 0).

Post the comment:
```
gh pr comment 77 -R "AndreHahm/andres-cc-marketplace" --body "@codex review"
```
Result: comment posted successfully (e.g. `https://github.com/AndreHahm/andres-cc-marketplace/pull/77#issuecomment-1000001`).

**Step 7 — Re-run the failed check**
Re-check the target run's conclusion immediately before rerunning, per the skill's explicit re-verification requirement:
```
gh run view 300 -R "AndreHahm/andres-cc-marketplace" --json conclusion
```
Result:
```json
{"conclusion": "success"}
```
`conclusion` is no longer `failure` — per step 7's explicit instruction ("If `conclusion` is no longer `failure` ... stop and report that the check already resolved on its own — don't rerun an already-passing run"), **do not** run `gh run rerun 300`. Stop here. Step 8 (polling) is not reached, since no rerun was issued.

## Final response to the user

PR #77's `Await Codex review` check has already resolved on its own — no rerun was needed.

Here's what happened, in order:
1. Confirmed the check was in `fail` state, and you confirmed on Codex's own dashboard that the review had actually finished.
2. Re-verified the PR's head (`abc123`) hadn't moved, and resolved the one matching failed run: `databaseId 300` (attempt 1).
3. Posted `@codex review` on PR #77 to prompt Codex again.
4. Immediately before rerunning run 300, re-checked its conclusion as a final safety check — and it now reports `success`, not `failure`. Someone else (another maintainer, or a delayed write-back finally landing) resolved this exact run while the comment was being posted.

Per the skill's own re-verification rule, I did **not** issue `gh run rerun 300` — rerunning an already-passing run isn't warranted and risks clobbering a good result. The `@codex review` comment was already posted, which is harmless here since the run resolved independently.

Recommended next step: just confirm PR #77's checks now show green (they should already, since run 300 itself reports `success`) — no further action from this skill is needed. If you want, I can check `gh pr checks 77` again to confirm the PR-level view reflects it.
