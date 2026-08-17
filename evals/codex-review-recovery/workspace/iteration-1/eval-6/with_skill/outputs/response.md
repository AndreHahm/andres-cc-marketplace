Step 6 of codex-review-recovery ("Poll briefly and report") works as follows, per the SKILL.md:

- **Tool/command called**: `gh pr checks <number>`, called again (the same command already used in step 2), checking the `Await Codex review` line's state each time.
- **How many times**: Repeat this same call up to 10 times, spaced roughly 30 seconds apart. This gives a total polling window of roughly ~5 minutes.
- **How it decides to stop**: Stop as soon as the state changes from `pending`/still-fresh to `pass` or `fail`. If neither happens within the 10 calls, stop after the 10th call (still "in flight").
- **Scope constraint**: Every call must stay inside the skill's own declared `Bash(gh pr checks:*)` allowed-tools grant — the skill explicitly says not to reach for a background-shell or `until`-loop primitive outside that scope. Each poll is an individual, bounded `gh pr checks` invocation, not a looping shell construct.
- **What it reports**, depending on outcome:
  - `pass` — report success, done.
  - Still not resolved after 10 calls — report that it's still in flight and point at the check's own URL, noting the 30-minute window from the fresh re-run (steps 4-5) may still legitimately be running.
  - `fail` again — report plainly; note this may mean the write-back gap is still happening, or that Codex's dashboard status didn't mean what was expected. The skill explicitly says not to retry automatically — let the human decide whether to repeat from step 3.

Additional framing from elsewhere in the document that bears directly on step 6: this 5-minute polling window is deliberately much shorter than the check's own real 30-minute timeout (since step 6 is actively watching for the fresh signal produced by steps 4-5, not waiting cold), and the Boundaries section reiterates that this skill's own polling timeout must never be treated as equivalent to the check's real 30-minute timeout — a "still not resolved" report after step 6 is described explicitly as incomplete-wait, not failure. The Boundaries section also reiterates that a repeat `fail` after step 6 must never trigger an automatic second attempt through steps 3-6 — each retry needs its own fresh step-3 human confirmation.
