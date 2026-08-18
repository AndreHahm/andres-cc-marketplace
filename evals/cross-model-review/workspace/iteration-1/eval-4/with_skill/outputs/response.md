# What cross-model-review does when `git diff main...HEAD` is empty

Given: `BASE=main`, `SCOPE` unset, and `git diff main...HEAD` produces no output at all.

## Inputs step

Since `SCOPE` is unset, `BASE` defaults are moot (it's already `main`). Per the Inputs section, the
skill builds the canonical diff command once, as an argv array:

```bash
BASE="${BASE:-main}"          # BASE="main"
DIFF=(git diff "$BASE...HEAD")   # DIFF=(git diff main...HEAD)
[ -n "$SCOPE" ] && DIFF+=(-- "$SCOPE")   # SCOPE unset, so this branch is skipped — DIFF unchanged
DIFF_STR=$(printf '%q ' "${DIFF[@]}")   # shell-quoted text form, for embedding in prompts later
```

So `DIFF` stays exactly `(git diff main...HEAD)` with no `-- <pathspec>` appended, since `SCOPE` is
empty.

## Preflight step 1 — the actual stopping point

Preflight step 1 says: run `"${DIFF[@]}"`. If it prints nothing, report "nothing to review against
$BASE" (mention `$SCOPE` if set) and stop.

The user has stated as a given that `git diff main...HEAD` produces no output. That satisfies this
condition exactly. So the skill:

1. Runs (conceptually) `git diff main...HEAD`.
2. Observes empty output.
3. Reports to the user: **"nothing to review against main"** — and, per the "(mention `$SCOPE` if
   set)" clause, since `SCOPE` is unset in this scenario, `$SCOPE` is *not* mentioned in the report.
4. **Stops.** No further preflight steps run — not step 2 (changed-file list for `--target-paths`),
   not step 3 (`RUN=$(mktemp -d)` scratch dir), not step 4 (resolving `REPO_ROOT`), and not step 5
   (materializing `review.md`/`refute.md` from `$BASE`).
5. Phase 1 (independent review), Phase 2 (cross-examine), and Phase 3 (synthesize and report) never
   start. No Codex dispatch resolver call is made, so the First-Send Confirmation
   (`AskUserQuestion`) never fires either, since that confirmation only applies "before the *first*
   real Codex dispatch attempted" — and no dispatch is ever attempted here.
6. No scratch directory is created, so there is nothing under `$RUN` to note as un-deleted per
   Phase 3's closing remark (that remark never gets reached in this scenario).

## Net effect

The skill's behavior on an empty diff is a clean, immediate no-op after a single check: it tells the
user there is nothing to review relative to `main`, and does not proceed to invoke Claude's own
review pass, dispatch Codex, or produce any findings table. No files are written, no repository
state is touched, and no `AskUserQuestion` prompt is shown, because the whole flow terminates before
any point in the skill that would need one.
