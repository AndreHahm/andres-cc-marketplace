Step 8 ("Poll briefly and report") for PR #77, with databaseId 300 (baseline attempt 1 from step 5, reran in step 7):

**Mechanism**

- **Command**: `gh run view <databaseId> -R "<owner>/<repo>" --json status,conclusion,attempt` — for this case, `gh run view 300 -R "<owner>/<repo>" --json status,conclusion,attempt`.
- **Target**: the exact workflow run resolved in step 5 (databaseId 300) — explicitly *not* the PR-level check summary (`gh pr checks`).
- **Fields polled**: `status`, `conclusion`, `attempt`.

**Why polling alone isn't enough**: `gh run rerun` gives no guarantee the rerun has actually started or finished by the time step 8's calls run. The run can still report its pre-rerun `completed` result for a moment before GitHub propagates the new attempt, and a fast-finishing rerun can complete before any poll happens to catch an intermediate `queued`/`in_progress` state. So status-watching alone can't reliably distinguish the old (stale) result from a genuinely fast new one — the skill instead compares against step 5's baseline `attempt` number.

**Trustworthy vs. stale**:
- Never trust a `completed` result unless its `attempt` is strictly greater than step 5's baseline `attempt` (baseline = 1 in this scenario). A `completed` result still at `attempt` 1 is always the stale pre-rerun state — keep polling, don't report it.
- Once `attempt` has incremented (i.e., > 1), that entry's `conclusion` (`success`/`failure`) reflects this retry's real outcome as soon as `status` is `completed` — there's no need to have separately observed `queued`/`in_progress` first.

**How it stops**: the `gh run view` call is repeated up to 10 times, spaced roughly 30 seconds apart (~5 minutes total) — a much shorter window than the check's own 30-minute timeout, since this is actively watching for the fresh signal from steps 6-7 rather than waiting cold. Every call stays inside the skill's own declared `Bash(gh run view:*)` grant; no background-shell or `until`-loop primitive is used. It reports whichever of three outcomes occurs first:
1. **Genuine success** — `attempt` > baseline (1) and `conclusion` is `success`: report success, done.
2. **Still not resolved after 10 calls** — report that it's still in flight and point at the check's own URL, since the 30-minute window from the fresh re-run may still legitimately be running.
3. **Genuine failure again** — `attempt` > baseline (1) and `conclusion` is `failure`: report plainly (this may mean the write-back gap is still happening, or Codex's dashboard status didn't mean what was expected); don't retry automatically — let the human decide whether to repeat from step 3.
