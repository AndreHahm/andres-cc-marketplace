## Running codex-review-recovery for PR #77

**Step 1 — Resolve the PR**

I would run:

```
gh pr view 77 --json number,url,headRefName,headRefOid
```

(Assuming this succeeds and returns the PR's number, URL, head branch name, and head commit SHA — if it failed, I would tell the user and stop here.)

**Step 2 — Check the current check state**

```
gh pr checks 77
```

The task states this shows `Await Codex review` as `fail`. Per the skill, `fail` is the only state this skill acts on, so I continue to step 3.

**Step 3 — Confirm with the human**

This is the one gate that can't be skipped or inferred, since only the human has visibility into Codex's own dashboard. I would ask via `AskUserQuestion`:

> **Question:** The "Await Codex review" check failed for PR #77. Have you confirmed on Codex's own dashboard that this PR's review actually finished?
>
> **Options:**
> - Yes — retry
> - No — let me check first

**User's answer: "No — let me check first"**

Per the skill's instructions: *"On 'No', stop here without posting anything or re-running the job; tell the user to come back once they've checked."*

So I do not post the `@codex review` comment, and I do not re-run any failed check. I stop here.

---

### My response to the user

No problem — I won't post anything or re-run the check yet. Go ahead and check Codex's own dashboard to confirm the review for PR #77 actually finished. Once you've confirmed it, let me know and I'll pick this back up: I'll post the `@codex review` comment, re-run the matching `await-codex-review.yml` run for the PR's current head commit, and then poll the check for up to 5 minutes to report back whether it passes.
