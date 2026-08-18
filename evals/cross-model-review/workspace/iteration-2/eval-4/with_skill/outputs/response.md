# cross-model-review: empty-diff scenario (BASE=main, SCOPE unset)

Given: `BASE` is `main` (the default), `SCOPE` is unset, and `git diff main...HEAD` produces no
output at all. Here is exactly what the skill has me do, without actually running anything.

## Step 1 — Build the canonical diff command (Inputs section)

Before doing anything else, the skill has me build the **canonical diff command once**, as an argv
array (not a string), and reuse it everywhere rather than re-spelling the diff inline:

```bash
BASE="${BASE:-main}"        # resolves to "main" (already the default here)
DIFF=(git diff "$BASE...HEAD")
[ -n "$SCOPE" ] && DIFF+=(-- "$SCOPE")   # SCOPE is unset, so this branch is skipped — no pathspec appended
DIFF_STR=$(printf '%q ' "${DIFF[@]}")
```

So `DIFF` is just `git diff main...HEAD` — no `-- <pathspec>` suffix, since `SCOPE` is unset.

## Step 2 — Preflight step 1: run it and check for output

Preflight step 1 says: run `"${DIFF[@]}"`. If it prints nothing, report "nothing to review against
`$BASE`" (mentioning `$SCOPE` if set) and **stop**.

In this scenario `git diff main...HEAD` produces no output at all, so this condition fires
immediately. Because `SCOPE` is unset, the report does **not** mention any scope qualifier — it's
just "nothing to review against main."

## What happens as a result: the run stops here

Nothing past Preflight step 1 executes. Concretely, the skill does **not**:

- Compute the changed-file list (Preflight step 2) or check it against the Codex path-charset/
  deleted-path rules.
- Create the `$RUN` scratch dir (Preflight step 3).
- Resolve `REPO_ROOT` (Preflight step 4).
- Materialize `review.md`/`refute.md` from `$BASE` (Preflight step 5).
- Check whether the diff touches the Codex dispatcher scripts (Preflight step 6) — there's no diff
  content to check.
- Fire the Codex dispatch resolver, or the mandatory First-Send Confirmation `AskUserQuestion` —
  no Codex dispatch is attempted at all, sandboxed or fallback.
- Run Phase 1 (independent fresh-eyes review) for either Claude or Codex.
- Run Phase 2 (cross-examination/challenger passes).
- Run Phase 3 (synthesis/report/`AskUserQuestion` on which findings to fix).

This matches the skill's own documented scenario 1 under "Concrete scenarios to check": *"Empty
diff against `$BASE` → Preflight step 1 reports 'nothing to review' and stops, no dispatch of
either model."*

## Bottom line

I would report to the user: "Nothing to review against main — `git diff main...HEAD` produced no
changes." and stop there. No Codex subprocess is ever launched, no scratch directory is created, no
confirmation prompt is shown, and no findings report is produced, because the skill's very first
Preflight check (empty diff) short-circuits the entire rest of the workflow before any of the later
phases can run.
