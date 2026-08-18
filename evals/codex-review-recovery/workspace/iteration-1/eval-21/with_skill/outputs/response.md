# Simulated run: codex-review-recovery — PR #77

**Scenario setup:** step 6 already posted `@codex review` successfully at head `abc123`. At step 7,
the conclusion re-check (`gh run view <databaseId> --json conclusion`) returns `{"conclusion": "success"}`
— someone else already resolved this exact run since step 5's check. The head has not moved, but per
the skill's own stated check order (conclusion first, head last), the conclusion re-check runs first and
is evaluated before any head re-check happens.

Invented-but-plausible values used throughout: repo `acme/widgets-app`, `headRefName`
`feature/retry-logic`, `headRefOid` `abc123`, resolved run `databaseId` `4821093344` with baseline
`attempt` `1`.

---

## Step 1 — Resolve the PR

`$ARGUMENTS` = `"77"`. Validated against the allowlist: matches `^[0-9]+$` — accepted.

Command:
```
gh pr view 77 --json number,url,headRefName,headRefOid
```
Simulated result:
```json
{"number":77,"url":"https://github.com/acme/widgets-app/pull/77","headRefName":"feature/retry-logic","headRefOid":"abc123"}
```
Command succeeded. Extracted `<owner>/<repo>` = `acme/widgets-app` from the `url` field — this is used
as `-R "acme/widgets-app"` on every subsequent `gh pr`/`gh run` call rather than trusting the current
checkout's own remote.

## Step 2 — Check the current check state

```
gh pr checks 77 -R "acme/widgets-app" --json name,workflow,bucket,link
```
Simulated result (relevant entry):
```json
{"name":"Await Codex review","workflow":"Codex review status","bucket":"fail","link":"https://github.com/acme/widgets-app/pull/77/checks?check_run_id=998877"}
```
Exactly one entry matches both `workflow == "Codex review status"` and `name == "Await Codex review"`.
`bucket` is `fail` — this is the only state this skill acts on. Continue to step 3.

## Step 3 — Confirm with the human

`AskUserQuestion`:

> The "Await Codex review" check failed for PR #77. Have you confirmed on Codex's own dashboard that
> this PR's review actually finished?
> - Yes — retry
> - No — let me check first

Simulated answer: **"Yes — retry"** (the scenario states step 6 went on to post successfully, which
only happens after this gate clears). Continue to step 4.

## Step 4 — Re-verify the head hasn't moved

```
gh pr view 77 -R "acme/widgets-app" --json headRefOid --jq '.headRefOid'
```
Simulated result: `abc123`

Matches step 1's `headRefOid` (`abc123`). Continue to step 5.

## Step 5 — Resolve the workflow run to act on

`headRefName` = `feature/retry-logic`, validated against `^[A-Za-z0-9._/-]+$` — matches, accepted.

```
gh run list --workflow await-codex-review.yml --repo "acme/widgets-app" --branch "feature/retry-logic" \
  --limit 5 --json databaseId,headSha,conclusion,attempt
```
Simulated result:
```json
[{"databaseId":4821093344,"headSha":"abc123","conclusion":"failure","attempt":1}]
```
Exactly one entry, and its `headSha` (`abc123`) matches step 4's confirmed `headRefOid`. Not zero
matches, not multiple — no ambiguity to stop on. Check its `conclusion` (free, already returned):
`"failure"` — one of the two legitimate "still needs recovery" outcomes, so proceed. Keep
`databaseId = 4821093344` and baseline `attempt = 1` for step 8's later comparison. Nothing has been
triggered yet. Continue to step 6.

## Step 6 — Post the retry comment

Immediately before posting, re-fetch and compare the head one more time:
```
gh pr view 77 -R "acme/widgets-app" --json headRefOid --jq '.headRefOid'
```
Simulated result: `abc123` — still matches step 4's confirmed value. Continue.

```
"${CLAUDE_PLUGIN_ROOT}/scripts/write-git-kit-marker.sh" gh-pr-review codex-review-recovery
```
Marker written (fresh, <60s old, satisfies `guard-raw-pr-review.sh`).

```
gh pr comment 77 -R "acme/widgets-app" --body "@codex review"
```
Per the scenario: **posted successfully** (exit 0) at head `abc123`. This is what actually prompts
Codex to act again. Exit status checked — success, so continue to step 7.

## Step 7 — Re-run the failed check

Two things may have changed during step 6's network round-trip, so both are re-checked immediately
before rerunning — **in this order: conclusion first, head last**, so the head check is the very last
thing before the rerun call itself.

**Conclusion re-check (first):**
```
gh run view 4821093344 -R "acme/widgets-app" --json conclusion
```
Given result:
```json
{"conclusion": "success"}
```

Apply the same three-way check used in step 5:
- `success` → stop and report the check already resolved on its own — don't rerun an already-passing run.
- `failure`/`timed_out` → proceed.
- anything else → stop, report the unexpected value.

`conclusion` is `"success"`. **This triggers the stop condition.** Someone else already resolved this
exact run (`databaseId 4821093344`) since step 5's check found it `failure`. The skill's instructions
are explicit that this three-way check is applied here as its own complete gate — a `success` result
stops the flow immediately.

**Consequence for the head re-check:** the scenario notes the head has in fact not moved, but per the
skill's own stated ordering, the head re-check is the *second* of the two checks and only runs after
the conclusion check has already passed. Since the conclusion check itself stopped the flow, the head
re-check is never reached — there is no scenario in the skill's instructions where a later check in the
same ordered sequence executes after an earlier one has already triggered a stop. No `gh pr view`
call for the head is made in this branch, and no `gh run rerun` is issued.

Flow ends here. Step 8 (polling) is never entered — polling only applies once a rerun has actually been
triggered.

---

## Final response to the user

The "Await Codex review" check for PR #77 has already resolved on its own — no rerun was needed or issued.

- Your confirmation and the `@codex review` comment I posted (at head `abc123`) went through fine.
- Before re-running the check, I re-checked the run's current status first, per the flow's ordering (conclusion before head), and found it had already flipped to `conclusion: success` — someone (or something) else resolved this exact workflow run (`databaseId 4821093344`) in the time between when I first found it failing and this final check.
- Since it's already `success`, I did not re-run it — re-running an already-passing run isn't something this flow does.
- No further action needed on your end unless you want to double check the check status on the PR yourself: `https://github.com/acme/widgets-app/pull/77/checks?check_run_id=998877`.
