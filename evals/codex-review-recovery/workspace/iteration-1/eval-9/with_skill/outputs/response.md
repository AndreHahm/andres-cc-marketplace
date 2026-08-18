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

Extracted `<owner>/<repo>` = `octo-org/example-repo` from the `url` field. This value is passed as `-R "octo-org/example-repo"` to every subsequent `gh pr`/`gh run` command.

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

Entry found matching both `workflow` == "Codex review status" and `name` == "Await Codex review" (exactly one match). `bucket` is `fail` → this is the only state the skill acts on → continue to step 3.

## Step 3 — Confirm with the human

**AskUserQuestion:**
> The "Await Codex review" check failed for PR #77. Have you confirmed on Codex's own dashboard that this PR's review actually finished?
> - Yes — retry
> - No — let me check first

**User's answer:** "Yes — retry" (per the task: the user has already confirmed Codex's dashboard shows the review finished, with head SHA `abc123`).

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

This matches step 1's `headRefOid` (`abc123`) exactly — the head has not moved since step 1. Continue to step 5.

## Step 5 — Resolve the workflow run to act on

**Command:**
```
gh run list --workflow await-codex-review.yml --repo "octo-org/example-repo" --branch "feature-x" \
  --limit 5 --json databaseId,headSha,conclusion,attempt
```

(`feature-x` contains no shell metacharacters, so it is safe to quote and pass through.)

**Result (given):**
```json
[
  { "databaseId": 300, "headSha": "abc123", "conclusion": "failure", "attempt": 1 },
  { "databaseId": 301, "headSha": "abc123", "conclusion": "success", "attempt": 1 },
  { "databaseId": 302, "headSha": "old111", "conclusion": "failure", "attempt": 1 }
]
```

Filtering for entries whose `headSha` matches step 4's confirmed `headRefOid` (`abc123`): **two** entries match — databaseId `300` (conclusion `failure`) and databaseId `301` (conclusion `success`).

Per the skill's Step 5 instructions: *"If more than one entry's `headSha` matches, also stop and tell the user rather than guessing — a PR reopened or marked ready more than once without a new commit can produce multiple runs sharing the same head SHA ... and picking the wrong one could rerun an already-passing or superseded run instead of the failed one confirmed in step 2."*

**This is exactly that case.** The flow stops here. Nothing has been posted or rerun — steps 6 (post `@codex review` / write marker), 7 (`gh run rerun`), and 8 (polling) are **not executed**.

---

## Final response to the user

I stopped before taking any action. Here's why:

For PR #77 (head SHA `abc123`), the "Await Codex review" check is currently `fail`, and I confirmed with you that Codex's own dashboard shows the review finished for that same head SHA. However, when I looked up the actual workflow runs for this branch, **two runs both match the confirmed head SHA `abc123`**:

| databaseId | headSha | conclusion |
|---|---|---|
| 300 | abc123 | failure |
| 301 | abc123 | success |

This happens when a PR is marked ready for review (or reopened) more than once without a new commit in between — each event can spin up its own `Await Codex review` run against the same commit.

Per this skill's own rule, I won't guess which one to act on: re-running the wrong one could rerun an already-*passing* run (301) instead of the *failed* one (300), or vice versa produce a misleading result. **No comment was posted to the PR and no run was rerun.**

To move forward, could you tell me which of these two runs corresponds to the check that's currently showing as failed in the PR's checks list (`300`, the `failure` one, is the most likely candidate since it matches the `fail` bucket seen in step 2) — or would you like me to just re-run `300` specifically? Once you confirm which `databaseId` to act on, I can post `@codex review` and rerun that exact run.
