# codex-review-recovery — PR #77 (simulated run)

Simulated tool calls, in the exact order the `codex-review-recovery` skill (`plugins/git-kit/skills/codex-review-recovery/SKILL.md`) specifies, using the scenario's given results and reasonably-inferred values elsewhere.

Assumed repo: `AndreHahm/andres-cc-marketplace` (extracted from step 1's `url` field, as the skill requires). Assumed branch: `fix/pr-77-branch` (inferred; not given).

---

## Step 1 — Resolve the PR

Command:
```
gh pr view "77" --json number,url,headRefName,headRefOid
```
`$ARGUMENTS` ("77") contains no shell metacharacters, so it passes through unmodified.

Result (inferred, consistent with step 4's later confirmation):
```json
{
  "number": 77,
  "url": "https://github.com/AndreHahm/andres-cc-marketplace/pull/77",
  "headRefName": "fix/pr-77-branch",
  "headRefOid": "abc123"
}
```
`<owner>/<repo>` extracted from `url`: `AndreHahm/andres-cc-marketplace`. This is passed as `-R "AndreHahm/andres-cc-marketplace"` to every command from step 2 onward.

## Step 2 — Check the current check state

Command:
```
gh pr checks 77 -R "AndreHahm/andres-cc-marketplace" --json name,workflow,bucket,link
```

Result (inferred — must show exactly one matching entry with `bucket: fail` to make this scenario actionable):
```json
[
  {
    "name": "Await Codex review",
    "workflow": "Codex review status",
    "bucket": "fail",
    "link": "https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/999001"
  }
]
```
Exactly one entry matches both `workflow == "Codex review status"` and `name == "Await Codex review"`. `bucket` is `fail` → this is the only state the skill acts on. Continue to step 3.

## Step 3 — Confirm with the human

`AskUserQuestion`:
> The "Await Codex review" check failed for PR #77. Have you confirmed on Codex's own dashboard that this PR's review actually finished?
> - Yes — retry
> - No — let me check first

Given (per task framing — the recovery flow is underway and step 4 goes on to confirm a head SHA, so the human must have answered affirmatively): **"Yes — retry"**. Continue to step 4.

## Step 4 — Re-verify the head hasn't moved

Command:
```
gh pr view 77 -R "AndreHahm/andres-cc-marketplace" --json headRefOid --jq '.headRefOid'
```

Result (given by the task): `abc123`

This matches step 1's `headRefOid` (`abc123`) → continue to step 5.

## Step 5 — Resolve the workflow run to act on

Command:
```
gh run list --workflow await-codex-review.yml --repo "AndreHahm/andres-cc-marketplace" --branch "fix/pr-77-branch" \
  --limit 5 --json databaseId,headSha,conclusion,attempt
```
`<headRefName>` ("fix/pr-77-branch") contains none of the disallowed shell metacharacters, so it's safe to interpolate.

Result (given by the task: exactly one matching run, `databaseId 300`):
```json
[
  {
    "databaseId": 300,
    "headSha": "abc123",
    "conclusion": "failure",
    "attempt": 1
  }
]
```
Exactly one entry's `headSha` matches step 4's confirmed `headRefOid` (`abc123`) → unambiguous. Keep `databaseId = 300` and baseline `attempt = 1` for step 8's later polling. Nothing has been posted or rerun yet. Continue to step 6.

## Step 6 — Post the retry comment (re-check first)

Per the skill: "step 5's own `gh run list` call takes real (if brief) time, so immediately before posting anything, re-fetch and compare the head one more time."

Command:
```
gh pr view 77 -R "AndreHahm/andres-cc-marketplace" --json headRefOid --jq '.headRefOid'
```

Result (given by the task): `def999`

**This no longer matches step 4's confirmed value (`abc123`).** Per the skill's explicit instruction: *"If it no longer matches step 4's confirmed value, apply step 4's own stop condition here too — the PR moved again during step 5's lookup, so treat it exactly like a head that moved during step 3's wait."*

→ **STOP HERE.** Do not write the `write-git-kit-marker.sh` marker. Do not run `gh pr comment`. Do not proceed to step 7 (`gh run rerun`) or step 8 (polling). No side effect is triggered — the PR is left completely untouched, consistent with the skill's Boundaries section ("Never posts the retry comment (step 6) before step 5 has successfully resolved exactly one unambiguous run to act on" combined with "Never trusts a head or run-conclusion check from an earlier step across an intervening network call without re-verifying it immediately before the next side-effecting action").

---

## Final response to the user

PR #77's head moved again while step 5 was resolving the workflow run to act on — it's no longer at the commit you confirmed (`abc123`); it's now `def999`.

I'm stopping here without posting `@codex review` or rerunning anything. The `await-codex-review.yml` workflow's own `synchronize` trigger already starts a fresh `Await Codex review` run for the new commit `def999` independently of this recovery flow — the original failed run (databaseId 300, at `abc123`) may no longer even be relevant, since that commit has already been superseded.

Nothing was changed on the PR: no comment was posted, and no run was rerun.

Next step: check the `Await Codex review` status for the new commit (`def999`) directly — https://github.com/AndreHahm/andres-cc-marketplace/pull/77/checks — and, if it also gets stuck, come back and I'll restart this recovery flow from step 3 with a fresh confirmation for that commit.
