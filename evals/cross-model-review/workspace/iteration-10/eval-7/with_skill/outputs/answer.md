# cross-model-review: 5 files / 40 KB, Claude + Codex available, no exclusions

Sources: `plugins/git-kit/skills/cross-model-review/SKILL.md` (Preflight step 1, Phase 1, Phase 2, Codex dispatch resolver) and `references/scoped-review.md` (sections 1-3), `references/codex-pass-assembly.md`.

## Preflight step 1 (SKILL.md, Preflight; scoped-review.md section 1)

It runs inside the single chained Bash call that also exports the throwaway `GIT_INDEX_FILE`. It does two things:

```bash
python3 plugins/git-kit/scripts/git-review-scope.py --merge-base "$MERGE_BASE" --base-ref "$BASE" ${SCOPE:+--scope "$SCOPE"} --output "$RUN/manifest-1.json" || PLAN_FAILED=1
"${DIFF[@]}" > "$RUN/full.diff"; DIFF_STATUS=$?
```

- The planner is the review scope planner. `--scope` is omitted because no `SCOPE` was given. The manifest goes to `$RUN/manifest-1.json`. A planner failure sets `PLAN_FAILED=1` and does not break the `&&` chain.
- The diff is written to `$RUN/full.diff`, so its text stays out of context. A non-zero `DIFF_STATUS` is a Preflight failure: report the Git error and ask for a valid `$BASE`. Exit 0 with an empty file means "nothing to review" and the run stops.

## Dispatches and the folder question

- **Batching (scoped-review.md section 3):** consecutive slices are packed into batches up to the manifest's `max_slice_bytes`. "A diff within budget is one batch, so the run is a single dispatch pair as before."
- **Caveat:** I did not find the numeric `max_slice_bytes` in these files. It comes from the planner. I assume 40 KB of files is within budget. The doc only cites a 112 KB retry as still timing out.
- **Phase 1:** 1 Codex dispatch (`fresh-eyes-reviewer`, saved to `$RUN/codex_fresh_eyes.1.json`), plus Claude's native pass.
- **Phase 2:** 1 Codex dispatch (`challenger-reviewer`, saved to `$RUN/codex_challenger.1.json`), plus Claude's native challenger pass.
- **Total:** 2 Codex dispatches, assuming the following hold:
  - at least one path is Codex-eligible (charset and symlink checks pass);
  - the user answers "Send to Codex for this run" at the First-Send Confirmation;
  - the bridge does not fail or time out.
- **Folder question: no (scoped-review.md section 2).** The user is asked about folders only when `dropped_slices` is non-empty, or the request itself named folders to leave out. Here nothing is dropped and there are no exclusions, so nothing is asked, and "a normal run behaves as before."
- **What the user is asked:** the mandatory First-Send Confirmation (SKILL.md, resolver). It is about sending to Codex, not about folders. It discloses the read access and the `danger-full-access` fallback, plus any `DISPATCHER_TOUCHED`/`PLANNER_TOUCHED`/unverified-instruction notices.

## If the planner exits 2 (scoped-review.md section 1; SKILL.md Preflight step 1)

- Exit 2 means bad input, a git failure, or an `--output` that already exists. The `|| PLAN_FAILED=1` fallback sets the flag. The diff is still written to `$RUN/full.diff`.
- "A planner failure (`PLAN_FAILED=1`) is never a pass." The skill must not treat scope as planned.
- The skill asks via `AskUserQuestion` with two choices:
  1. Review the whole diff unscoped: one dispatch group of every eligible file, no manifest, no round-two carry-over.
  2. Stop.
- If unscoped is chosen, "review scope planner unavailable" is recorded in `inspection_limits`. The Phase 3 report includes the planner-unavailable fallback (scoped-review.md section 6).
- Each phase would then use a single dispatch group for the whole eligible file set, so the Codex count stays 1 + 1 under the same assumptions.
