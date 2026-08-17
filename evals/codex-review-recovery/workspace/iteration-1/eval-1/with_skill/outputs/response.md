**Step 1 — Resolve the PR**

I would run:

```
gh pr view 77 --json number,url,headRefName,headRefOid
```

This resolves PR #77's number, URL, head branch name, and head commit SHA — needed later (step 5) to make
sure any re-run targets the run tied to the PR's current head commit, not a stale one. (This step succeeded
per the task context, since check output for PR #77 is already available.)

**Step 2 — Check the current check state**

I would run:

```
gh pr checks 77
```

...and look at the `Await Codex review` line specifically. Per the task, this shows the check as `pending`,
4 minutes into its run.

Per the skill's Instructions (step 2) and its "When NOT to Use" section: a `pending` check means there is
nothing to recover yet — the check is still within its normal polling window (it can run for up to 30
minutes before failing), and 4 minutes in is well within that. The skill is explicit that "it's been a
while" is not sufficient reason to intervene, and a still-running check must not be treated as if it were
stuck.

**Stopping here — no further action taken**

Per the skill, when the check is `pending` I stop at this point. I do **not**:
- ask the AskUserQuestion confirmation in step 3 (that only applies once the check is in the `fail` state),
- post an `@codex review` comment (step 4),
- look up or re-run any workflow run (step 5),
- start the post-action polling loop (step 6).

None of those actions apply — this skill's step 2 explicitly routes a `pending` state straight to "tell the
user and stop," bypassing steps 3–6 entirely.

**Final response to the user:**

> PR #77's `Await Codex review` check is still `pending` — it's about 4 minutes into its run, which is well
> within its normal 30-minute polling window. There's nothing to recover yet, so I haven't taken any action
> (no comment posted, no re-run triggered). This skill only kicks in once the check has actually failed or
> timed out. If it's still pending or fails after the full 30 minutes, let me know and — if you've also
> confirmed on Codex's own dashboard that the review actually finished — I can run the recovery steps then.
