# merge-pr 910 --bypass-codex-review "Docs-only change, reviewed by the maintainer" — step 4(c) and 4(d)

Simulated exercise: no `gh`/`git` command was run and no repository file was edited. The commands below
are the ones the skill would run.

## Starting state (given)

- Step 2: the only non-passing required context is `Publish Codex policy result`, classified **missing**
  (no entry at all in `statusCheckRollup`). With `--bypass-codex-review` and a non-empty reason, the
  bypass exception applied on this first pass of step 2, and the PR is on the bypass path.
- Step 3: `MERGE ALLOWED`.
- Step 4(a)-(b): the reason was screened, the head SHA was resolved and matched step 2's `headRefOid`,
  the `gh-pr-review` marker was written in its own `Bash` call, and the attestation comment was posted
  as the very next call.
- Rollup: two required contexts, both `CheckRun` entries from workflow `Marketplace CI`:
  - `Hygiene`: `COMPLETED` / `SUCCESS`, `startedAt` 10:02:00Z
  - `Python quality`: `COMPLETED` / `SUCCESS`, `startedAt` 10:05:00Z
  - `Publish Codex policy result`: no entry (missing)

## Step 4(c), part 1: the in-flight wait

What it waits for: the skill says "first wait until no run is in flight on this head", by polling
`gh pr view 910 --json headRefOid,statusCheckRollup` 15 seconds apart, up to 40 attempts,
"until no required context is pending or missing". Any non-`COMPLETED` entry keeps a context pending.
A different `headRefOid` on any poll stops the run and reports both SHAs.

Evaluated against the given rollup:

- `Hygiene` and `Python quality` are `COMPLETED`, so neither is pending. Nothing is in flight.
- `Publish Codex policy result` is a required context and is **missing**.

The skill's own end condition is "no required context is pending **or missing**". The context that is
missing is the one this bypass exists to replace. Nothing re-creates it before the label write later in
4(c). No run is in flight to report it. So the condition can never hold on this head before the label
is applied.

**Does the wait end?** Following this version of the skill literally, it does not end successfully. It
polls 40 times (about ten minutes) and the bound runs out. The skill then says "an exhausted bound stops
and reports the contexts still pending". The run stops and reports `Publish Codex policy result` as
still missing. The baseline is not captured, the label is not applied, and 4(d) and 4(e) never run.
The attestation comment from 4(b) stays posted with no label, so the bypass is not completed. A fresh
bypass needs a new invocation.

This is a defect in this version of 4(c), and I flag it rather than work around it. The wait was added
for issue #850, to keep an earlier run's stale `Publish Codex policy result` from landing after the
baseline. It has the same "pending or missing" condition as step 2's issue-#850 wait. But in this
scenario a missing `Publish Codex policy result` is the expected state on the bypass path: nothing is in
flight, and only the label will ever produce the context. The text does not exempt that context, and it
does not limit the wait to contexts that have an earlier entry on this head, so the wait deadlocks. I
would not skip the wait on my own judgement. I report the stop and name this as the cause.

## Step 4(c), part 2: the baseline you would record (only if the wait had ended)

The skill records one value, before it touches the label at all. It runs
`gh pr view 910 --json statusCheckRollup` and records the `startedAt` of the current
`Publish Codex policy result` `CheckRun` entry. If several entries have that name, it uses the latest
`startedAt`. If there is no entry yet, it notes that.

Here the recorded baseline is **"no `Publish Codex policy result` entry exists yet"**, with no
timestamp. The `startedAt` values of `Hygiene` (10:02:00Z) and `Python quality` (10:05:00Z) are not the
baseline. 4(c) records only the `Publish Codex policy result` entry, not the latest `startedAt` across
the rollup. That rollup-wide baseline belongs to step 2's issue-#850 wait for the skill's own
push or body edit, and neither happened in this run.

The skill would then:

1. Check the label exists: `gh api "repos/{owner}/{repo}/labels/s%3A%20codex%20review%20bypassed"`.
   If it is missing, stop and report the bypass as failed. The skill never creates the label.
2. Run `gh pr view 910 --json labels`. If `s: codex review bypassed` is already present, remove it and
   add it again. A plain `--add-label` on a present label is a no-op and does not fire the `labeled`
   event. Otherwise run `gh pr edit 910 --add-label "s: codex review bypassed"`.

## Step 4(d): which `Publish Codex policy result` entry is accepted (only if 4(c) had completed)

The label write re-triggers `marketplace-ci.yml` (its `pull_request` trigger includes `labeled`). That
re-runs the `publish` job, which evaluates the posted attestation. The skill polls
`gh pr view 910 --json statusCheckRollup` 15 seconds apart, up to 20 attempts.

It accepts a `Publish Codex policy result` **`CheckRun`** entry that meets both of these:

- **Newer than the baseline.** Its `startedAt` is strictly later than the 4(c) baseline, or the check
  was missing at the baseline. Here it was missing, so the first such entry to appear qualifies on
  this test. There is no earlier entry it could be confused with. If more than one entry has the name,
  the one with the latest `startedAt` is used.
- **Finished.** Its `status` is `COMPLETED`. A `QUEUED`/`IN_PROGRESS` entry keeps the poll going.

Its `conclusion` is then classified by step 2's four-state rules:

- `SUCCESS`/`NEUTRAL`/`SKIPPED`: passing.
- `FAILURE`/`CANCELLED`/`TIMED_OUT`/`ACTION_REQUIRED`/`STARTUP_FAILURE`/`STALE`: failing. A malformed
  attestation, an actor or SHA mismatch, or a server-side permission failure can still produce this.

If 20 polls pass with no such entry, the run stops and reports that the replacement policy check never
completed.

After that, 4(e) re-runs the full step-2 readiness check **without** the bypass exception. That covers
every required context, including `Hygiene`, `Python quality` and `Publish Codex policy result`, all of
which must now pass for real. Then step 5 asks for confirmation, and step 7(b) runs its final recheck,
with the merge bound to the head SHA attested in 4(b) through `--match-head-commit`.

## Outcome under this version of the skill

The run stops in 4(c) when the in-flight wait's 40-attempt bound runs out. It reports
`Publish Codex policy result` as still missing. The baseline ("no entry yet"), the label write and the
4(d) acceptance rule above are what the skill would do next, but this version never gets that far in
this scenario.
