# merge-pr 910 --bypass-codex-review: steps 4(c) and 4(d)

This is a simulated run. No `gh` or `git` command was run and no repository file was edited. The commands below are the ones the skill would run.

Where things stand: step 1 validated `910` as the PR reference, so `<pr-ref>` is `910` in every call below. Step 2 entered the bypass path because the only non-passing required context is `Publish Codex policy result`, and it is **missing**. Step 3 returned `MERGE ALLOWED`. Step 4(a) screened the reason "Docs-only change, reviewed by the maintainer" and it passed: it has no bot-trigger mention and no sensitive content. Step 4(b) resolved the head SHA, checked it against the `headRefOid` that step 2 classified, wrote the `gh-pr-review` marker and posted the attestation comment.

## Step 4(c), part 1: wait for in-flight runs

**What the wait is for:** a run that started earlier (for example from a body edit) could still be in flight. If it finished after the baseline was recorded, its stale `Publish Codex policy result` would land later and look like the bypass failing. The wait makes sure no such run is still going on this head.

**How it works:** poll `gh pr view 910 --json headRefOid,statusCheckRollup` every 15 seconds, for at most 40 attempts. Stop polling once no required context is pending or missing. A `CheckRun` that is not `COMPLETED`, or a `StatusContext` with `state: PENDING`, keeps its context pending.

**The one exception:** `Publish Codex policy result` is allowed to stay **missing**. On the bypass path, the label applied below is what creates that check, so waiting for it here would never end. If an entry for it showed up that was not `COMPLETED`, that entry would keep the wait going.

**Head check:** each poll compares `headRefOid` with the head attested in 4(b). If it differs, the run stops and reports both SHAs.

**Does the wait end? Yes, on the first poll.**
- `Hygiene` is `COMPLETED` / `SUCCESS`, so it is passing.
- `Python quality` is `COMPLETED` / `SUCCESS`, so it is passing.
- `Publish Codex policy result` is missing, which is the allowed exception.

Nothing is pending and nothing else is missing, so the wait ends as long as the head is unchanged. If the 40 attempts had run out, the run would stop and name the contexts that were still pending.

## Step 4(c), part 2: record the baseline before touching the label

1. Run `gh pr view 910 --json statusCheckRollup`. The skill reads `statusCheckRollup` here, not `gh pr checks --json`, which older `gh` releases reject.
2. There is no `Publish Codex policy result` entry, so there is no `startedAt` of its own to record. The skill says to record **the latest `startedAt` of any entry in the whole rollup** instead.
3. The two entries are `Hygiene` (10:02:00Z) and `Python quality` (10:05:00Z). **The baseline is `10:05:00Z`**, taken from the `Python quality` CheckRun.
   - It is not `Hygiene`'s 10:02:00Z, which is earlier.
   - It is not a "no baseline" value, because then any policy result would be accepted.
   - The rule is "any entry", so if the rollup held a later non-required entry, that later time would become the baseline.

This baseline is what stops an older run's policy result, if it lands late, from being taken as the replacement.

## Step 4(c), part 3: apply the label

1. Check that the label exists: `gh api "repos/{owner}/{repo}/labels/s%3A%20codex%20review%20bypassed"`, with `{owner}/{repo}` taken from step 1's `url`. If it does not exist, stop and report that the bypass failed. The skill never creates the label.
2. Check whether the PR already has it: `gh pr view 910 --json labels`.
   - **Already present:** remove it with `gh pr edit 910 --remove-label "s: codex review bypassed"`, then add it again. Adding a label that is already there does nothing, so no new `labeled` event would fire.
   - **Not present:** add it with `gh pr edit 910 --add-label "s: codex review bypassed"`.

## Step 4(d): which `Publish Codex policy result` entry is accepted

The `labeled` event starts `marketplace-ci.yml` again, and its `publish` job re-evaluates the check against the attestation that was just posted.

**Polling:** `gh pr view 910 --json statusCheckRollup`, every 15 seconds, at most 20 attempts.

**The accepted entry** is a `Publish Codex policy result` **CheckRun** that meets both conditions:
- its `startedAt` is **strictly later than 10:05:00Z**, the rollup-wide baseline used because the check was missing at baseline time;
- its `status` is `COMPLETED`.

If more than one such entry exists, the one with the latest `startedAt` counts. Its `conclusion` is then classified by step 2's rules:
- `SUCCESS`, `NEUTRAL` or `SKIPPED` means passing.
- `FAILURE`, `CANCELLED` and the other failure values mean failing.

**Rejected entries:**
- Any entry that started at or before 10:05:00Z. For example, a stale run from an earlier body edit that lands late is never the replacement.
- An entry that is not `COMPLETED` yet. The poll keeps waiting.

**If the 20 attempts run out** with no accepted entry, stop and report that the replacement policy check never completed.

Even a correct local attestation can still fail on the server: a malformed marker, an actor or SHA mismatch, or a failed permission check. After this, step 4(e) re-runs the whole of step 2 **without** the bypass exception, and every required context, `Publish Codex policy result` included, has to really pass before step 5 asks for confirmation.
