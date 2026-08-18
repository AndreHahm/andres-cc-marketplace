# Simulated run — codex-review-recovery — PR #77

**Scenario setup (invented, consistent with skill conventions):**
- Repo: `octo-org/example-repo`
- PR #77, branch `fix/login-timeout`
- `headRefOid`: `abc123` (abbreviated for readability)
- Workflow file: `.github/workflows/await-codex-review.yml`, display name `Codex review status`, job name `Await Codex review`
- Resolved failed run: `databaseId` 300, baseline `attempt` 1

---

## Step 1 — Resolve the PR

Command:
```
gh pr view "77" --json number,url,headRefName,headRefOid
```

Simulated result:
```json
{
  "number": 77,
  "url": "https://github.com/octo-org/example-repo/pull/77",
  "headRefName": "fix/login-timeout",
  "headRefOid": "abc123"
}
```

Reasoning: `$ARGUMENTS` is `77` — a plain PR number, no shell metacharacters, so it passes through unmodified. Extract `<owner>/<repo>` = `octo-org/example-repo` from the `url` field. This will be passed as `-R "octo-org/example-repo"` to every subsequent `gh pr`/`gh run` call. Baseline `headRefOid` for later comparisons: `abc123`.

Continue to step 2.

---

## Step 2 — Check the current check state

Command:
```
gh pr checks 77 -R "octo-org/example-repo" --json name,workflow,bucket,link
```

Simulated result (relevant entry):
```json
{
  "name": "Await Codex review",
  "workflow": "Codex review status",
  "bucket": "fail",
  "link": "https://github.com/octo-org/example-repo/actions/runs/900123"
}
```

Reasoning: Exactly one entry matches both `workflow == "Codex review status"` and `name == "Await Codex review"` — no ambiguity. `bucket` is `fail`, which is the only state this skill acts on. Continue to step 3.

---

## Step 3 — Confirm with the human

`AskUserQuestion`:

> The "Await Codex review" check failed for PR #77. Have you confirmed on Codex's own dashboard that this PR's review actually finished?
> - Yes — retry
> - No — let me check first

Simulated answer: **"Yes — retry"** (scenario states the recovery flow proceeds through step 7, so the human confirmed).

Continue to step 4.

---

## Step 4 — Re-verify the head hasn't moved

Command:
```
gh pr view 77 -R "octo-org/example-repo" --json headRefOid --jq '.headRefOid'
```

Simulated result: `abc123`

Reasoning: Matches step 1's `headRefOid` (`abc123`). No stop condition triggered. Continue to step 5.

---

## Step 5 — Resolve the workflow run to act on

Command:
```
gh run list --workflow await-codex-review.yml --repo "octo-org/example-repo" --branch "fix/login-timeout" \
  --limit 5 --json databaseId,headSha,conclusion,attempt
```

Simulated result:
```json
[
  {"databaseId": 300, "headSha": "abc123", "conclusion": "failure", "attempt": 1},
  {"databaseId": 288, "headSha": "old999", "conclusion": "success", "attempt": 1}
]
```

Reasoning: `headRefName` (`fix/login-timeout`) contains no shell metacharacters — safe to quote and pass. Exactly one entry's `headSha` matches step 4's confirmed `abc123`: `databaseId` 300. Its `conclusion` is `failure` — not `success` (would stop), not an unexpected value (would stop) — `failure` is one of the two legitimate "still needs recovery" outcomes. Keep `databaseId=300` and baseline `attempt=1` for step 8's later comparison. Nothing has been posted or triggered yet. Continue to step 6.

---

## Step 6 — Post the retry comment

Re-check immediately before posting:
```
gh pr view 77 -R "octo-org/example-repo" --json headRefOid --jq '.headRefOid'
```
Simulated result: `abc123` — still matches. No stop condition.

Marker write (required immediately before the guarded command):
```
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review codex-review-recovery
```
Simulated result: marker written successfully.

Post the comment:
```
gh pr comment 77 -R "octo-org/example-repo" --body "@codex review"
```
Simulated result: exit status 0 (success), comment posted.

Reasoning: Exit status checked — succeeded, so it's safe to proceed. Continue to step 7.

---

## Step 7 — Re-run the failed check

Two re-checks required immediately before rerunning, per the scenario's own stipulation that **both pass**:

**Head re-check:**
```
gh pr view 77 -R "octo-org/example-repo" --json headRefOid --jq '.headRefOid'
```
Given result: `abc123` — still matches step 6's confirmed value. No stop condition.

**Conclusion re-check:**
```
gh run view 300 -R "octo-org/example-repo" --json conclusion
```
Given result: `{"conclusion": "failure"}` — still `failure` (not `success`, not an unexpected value). Baseline `attempt` for databaseId 300 remains 1, as resolved in step 5. Proceed.

Both re-checks pass, so the rerun command is issued:
```
gh run rerun 300 -R "octo-org/example-repo"
```

**Given result:** non-zero exit status.
```
error: You do not have permission to rerun this workflow (HTTP 403)
```

**Decision point:** Per step 7's explicit instruction — *"Check this command's exit status too. If it fails (a transient API error, missing Actions permission, or an authentication failure), stop here and report the error rather than proceeding to step 8 — polling a run that was never actually rerun would just watch the stale baseline `attempt` for all 10 calls and falsely report 'still in flight' after ~5 minutes, when nothing is actually happening."*

This is exactly the "missing Actions permission" case the instructions name explicitly (HTTP 403, permission denied). The command failed. **Stop here. Do not proceed to step 8's polling.**

---

## Final response to the user

> I confirmed Codex's dashboard status with you and posted `@codex review` on PR #77 — that part succeeded. But re-running the failed check (run `300`, `octo-org/example-repo`) failed:
>
> ```
> error: You do not have permission to rerun this workflow (HTTP 403)
> ```
>
> This looks like a missing Actions permission on the account/token running this session, not a transient API blip — the `@codex review` comment is already posted, but the stuck `Await Codex review` check (run `300`) has **not** been re-run, so no fresh polling window has started. I'm not going to poll for a result, since nothing was actually triggered and doing so would just watch a stale `attempt` and falsely report "still in flight."
>
> To finish recovery, someone with Actions write/rerun permission on `octo-org/example-repo` needs to either:
> - Re-run that job themselves (via the Actions tab or `gh run rerun 300 -R octo-org/example-repo` with sufficient permissions), or
> - Grant the current credential rerun rights on this workflow.
>
> Once that's done, this can be re-checked from step 5's run resolution (or just have the run rerun manually) — there's no need to repeat the step-3 dashboard confirmation, since that hasn't changed.
