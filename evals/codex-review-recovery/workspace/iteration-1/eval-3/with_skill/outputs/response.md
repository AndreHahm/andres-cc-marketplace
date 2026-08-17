# codex-review-recovery run for PR #77

## Step 1 — Resolve the PR

Command run:
```
gh pr view 77 --json number,url,headRefName,headRefOid
```

Result:
- number: 77
- headRefName: feature-x
- headRefOid: abc123

This succeeded, so we continue.

## Step 2 — Check the current check state

Command run:
```
gh pr checks 77
```

Result: the `Await Codex review` line shows `fail`.

Per the skill, `fail` is the only state this skill acts on (a `pass` would mean nothing to recover, and a
`pending` would mean nothing to recover yet). Since it's `fail`, we continue to step 3.

## Step 3 — Confirm with the human

This is the one gate that can't be skipped or inferred. I ask via `AskUserQuestion`:

> The 'Await Codex review' check failed for PR #77. Have you confirmed on Codex's own dashboard that this
> PR's review actually finished?
>
> Options: "Yes — retry" / "No — let me check first"

Per the task setup, the user already confirmed in an earlier turn that Codex's dashboard shows the review
finished, so the answer here is treated as **"Yes — retry"**. Since the answer is not "No", we proceed to
step 4 (posting nothing yet would have happened if the answer had been "No" — it wasn't).

## Step 4 — Post the retry comment

Command run:
```
gh pr comment 77 --body "@codex review"
```

This is what prompts Codex to act again.

## Step 5 — Re-run the failed check

Posting the comment above does not itself re-trigger `await-codex-review.yml` (its `on:` trigger list has
no `issue_comment` entry), so the failed run must be explicitly re-run. First, resolve the specific run
tied to the PR's *current* head SHA:

```
gh run list --workflow await-codex-review.yml --branch feature-x --limit 5 \
  --json databaseId,headSha,conclusion
```

Result (two entries):
- databaseId 111, headSha def456, conclusion failure
- databaseId 222, headSha abc123, conclusion failure

Step 1 gave `headRefOid = abc123`, which is the PR's actual current head SHA. Matching that against the
run list: databaseId 111 has headSha `def456` (does **not** match — this is a stale run for an old
commit), and databaseId 222 has headSha `abc123` (matches the current head exactly).

**Chosen run: databaseId 222**, because its `headSha` (`abc123`) matches the PR's current `headRefOid`
from step 1. databaseId 111 is explicitly not chosen — despite being listed first/most recent — because
re-running it would re-poll for a commit (`def456`) that is no longer the PR's head, which the skill
explicitly warns against ("don't re-run a stale run for an old commit").

Command run:
```
gh run rerun 222
```

## Step 6 — Poll briefly and report

Per the skill, I now check `gh pr checks 77` for the `Await Codex review` line every ~30 seconds for up to
5 minutes (a bounded background poll), and report whichever of these actually happens:
- `pass` — report success, done.
- still not resolved after 5 minutes — report that it's still in flight (and note this 5-minute polling
  window is this skill's own bound, not equivalent to the check's real 30-minute timeout).
- `fail` again — report plainly, and do not retry automatically; let the human decide whether to repeat
  from step 3.

No further check-state data was provided for this scenario beyond the initial `fail`, so this step is
narrated as the action that would be taken next; the actual outcome would be reported based on what
`gh pr checks 77` returns during that polling window.

## Final response to the user

"I confirmed PR #77's `Await Codex review` check was in a `fail` state, and you'd already confirmed
Codex's dashboard shows the review finished, so I posted `@codex review` as a retry comment on the PR.
I then re-ran the check run tied to the PR's current head commit (`abc123`) — that's run `222`, not run
`111`, since `111`'s head SHA (`def456`) belongs to an older commit and re-running it would poll for the
wrong commit. I'm now polling `Await Codex review` every ~30 seconds for up to 5 minutes and will report
back with whichever of pass / still-in-flight / fail actually happens — if it fails again, I won't retry
automatically; that would need a fresh confirmation from you first."
