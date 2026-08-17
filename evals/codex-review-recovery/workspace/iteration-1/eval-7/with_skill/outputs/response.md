# codex-review-recovery — PR #77 (simulated session)

## Step 1 — Resolve the PR

**Command:**
```
gh pr view "77" --json number,url,headRefName,headRefOid
```

**Result (simulated):**
```json
{
  "number": 77,
  "url": "https://github.com/AndreHahm/andres-cc-marketplace/pull/77",
  "headRefName": "fix/webhook-retry-backoff",
  "headRefOid": "a1b2c3d4e5f6789012345678901234567890abcd"
}
```

## Step 2 — Check current check state

**Command:**
```
gh pr checks 77
```

**Result (simulated):**
```
NAME                    WORKFLOW               STATE     STARTED       DURATION  URL
Await Codex review      await-codex-review.yml fail      30m ago       30m0s     https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/19203344551
lint                    ci.yml                 pass      31m ago       1m12s     https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/19203344552
tests                   ci.yml                 pass      31m ago       4m03s     https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/19203344553
```

Exactly one line resolves to `await-codex-review.yml`, and its state is `fail` — actionable. Continuing to step 3.

## Step 3 — Confirm with the human

**AskUserQuestion:**
> The "Await Codex review" check failed for PR #77. Have you confirmed on Codex's own dashboard that this PR's review actually finished?
> - Yes — retry
> - No — let me check first

**Given (per task setup):** the user already confirmed Codex's dashboard once this session → answer: **"Yes — retry"**.

## Step 4 — Post the retry comment

**Command:**
```
gh pr comment 77 --body "@codex review"
```

**Result (simulated):**
```
https://github.com/AndreHahm/andres-cc-marketplace/pull/77#issuecomment-2531000771
```

## Step 5 — Re-run the failed check

**Command:**
```
gh run list --workflow await-codex-review.yml --branch "fix/webhook-retry-backoff" --limit 5 \
  --json databaseId,headSha,conclusion
```

**Result (simulated):**
```json
[
  { "databaseId": 19203344551, "headSha": "a1b2c3d4e5f6789012345678901234567890abcd", "conclusion": "failure" },
  { "databaseId": 19198877210, "headSha": "9f8e7d6c5b4a3210987654321098765432109fed", "conclusion": "failure" }
]
```

`headSha` of the first entry (`a1b2c3d4...`) matches step 1's `headRefOid` — this is the run to re-run.

**Command:**
```
gh run rerun 19203344551
```

**Result (simulated):**
```
✓ Requested rerun of run 19203344551
```

## Step 6 — Poll briefly and report

**Commands (simulated, ~30s apart, up to 10 calls):**
```
gh pr checks 77   # call 1 → Await Codex review  pending
gh pr checks 77   # call 2 → Await Codex review  pending
gh pr checks 77   # call 3 → Await Codex review  pending
...
gh pr checks 77   # call 10 → Await Codex review  fail
```

**Given (per task setup):** the poll resolves to `fail` again before the 10-call window is exhausted.

Per the skill's own step 6 branch for this outcome: report plainly, do **not** retry automatically — a repeat failure needs its own fresh step-3 confirmation if the user wants to try again, per the skill's Boundaries section ("Never loops step 3-6 automatically on a repeat failure").

---

## Final response to the user

The "Await Codex review" check on PR #77 failed again after the retry.

What I did:
1. Confirmed the check was `fail` on `await-codex-review.yml`.
2. You confirmed Codex's own dashboard showed the review as finished, so I posted `@codex review` on the PR and re-ran the matching workflow run (run `19203344551`, matching the PR's current head SHA `a1b2c3d4...`).
3. Polled `gh pr checks 77` for about 5 minutes — it settled back to `fail`.

I'm not retrying automatically. A second failure right after a fresh retry is more likely to mean something genuinely wrong — either the GitHub write-back gap is still happening, or Codex's dashboard status didn't mean what we expected — than a repeat of the same transient signal gap.

A few ways to proceed, your call:
- Double-check Codex's dashboard again for PR #77 specifically (not a cached view) — if it still shows the review as done, we can repeat the confirm → retry → re-run cycle from scratch.
- Open the failed run directly to see if it's actually still polling vs. hard-failed: https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/19203344551
- If Codex's dashboard actually shows the review still in progress or errored on Codex's side, this isn't a GitHub write-back gap at all, and this skill isn't the right recovery path for that.

Let me know if you want me to go again from the confirmation step.
