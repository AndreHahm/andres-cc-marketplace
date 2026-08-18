codex-review-recovery — PR #77, Step 7 (Poll briefly and report)

Context: Step 6 already resolved the single run matching the confirmed head SHA and re-ran it via
`gh run rerun <databaseId> -R "<owner>/<repo>"`, keeping databaseId 300 specifically for step 7 to poll
(per the skill: "run `gh run rerun <databaseId> -R "<owner>/<repo>"` and keep this exact `<databaseId>`
for step 7 — poll that specific run, not a fresh lookup").

What step 7 does, per the skill document:

1. Tool/command called: `gh run view <databaseId> -R "<owner>/<repo>" --json status,conclusion` — for
   this task that's `gh run view 300 -R "<owner>/<repo>" --json status,conclusion`.

2. Target polled: the exact run rerun in step 6 (databaseId 300) — explicitly NOT the PR-level check
   summary (`gh pr checks`). The skill states this is "so there's no ambiguity between the old and new
   attempt."

3. Why polling is needed at all: `gh run rerun` gives no guarantee the rerun has actually started by the
   time the first poll call runs — the run can still report its pre-rerun `completed`/`failure` result for
   a moment before GitHub propagates the new attempt.

4. How it decides a result is trustworthy vs. stale:
   - Never trust a `completed` result until a `queued` or `in_progress` status has been observed on at
     least one earlier poll first — that observation is the confirmation the fresh attempt actually
     started.
   - A `completed` result seen before `queued`/`in_progress` has been observed is treated as the stale
     pre-rerun state; the skill says to keep polling and not report it.
   - Once `queued`/`in_progress` has been seen on some earlier poll, the next `completed` result is
     treated as genuine, and its `conclusion` field (`success`/`failure`) is taken as this retry's real
     outcome.

5. How it stops / reports: the `gh run view` call is repeated up to 10 times, spaced roughly 30 seconds
   apart. Every call stays inside the skill's own declared `Bash(gh run view:*)` grant — the skill
   explicitly says not to reach for a background-shell or `until`-loop primitive outside that scope. This
   gives a much shorter window (~5 minutes total) than the check's own 30-minute timeout, since step 7 is
   actively watching for the fresh signal from steps 5-6 rather than waiting cold. Step 7 ends by reporting
   whichever of three outcomes occurs:
   - A genuine `success` (observed only after `queued`/`in_progress` was seen) — report success, done.
   - Still not resolved after 10 calls — report that it's still in flight and point at the check's own
     URL, noting the fresh re-run's 30-minute window may still legitimately be running.
   - A genuine `failure` again — report plainly; the skill notes this may mean the write-back gap is still
     happening, or that Codex's dashboard status didn't mean what was expected. The skill is explicit that
     step 7 must NOT retry automatically — it lets the human decide whether to repeat from step 3.
