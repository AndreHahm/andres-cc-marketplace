# cross-model-review: optional-model pick, dry runs and egress confirmation (plan only)

Nothing was run and no model was dispatched. This describes what the skill tells me to do at each point.

## Context before step 1

- Preflight (steps 1-6) has returned as one chained call. I assume `PLANNER_TOUCHED` is unset. With
  `PLANNER_TOUCHED=1`, optional-models.md section 1 says to offer no optional model, and the locator would
  not have run at all.
- Preflight step 7: the locator (`python3 -I "${CLAUDE_PLUGIN_ROOT:-.claude}/scripts/git-review-locate-rva.py" --repo "$REPO_ROOT"`)
  exited 0 with `{"ok": true, "dispatcher": ...}`. I check that `dispatcher` is absolute, ends in
  `/scripts/rva-dispatch.mjs`, lies outside `$REPO_ROOT` and uses only `[A-Za-z0-9._/-]`. Then I take it as `$RVA`.
- The pick is asked only because the locator succeeded. It comes **before** Codex's First-Send Confirmation.

## Step 1: the user picks agy, pi and devin

The question I asked (`AskUserQuestion`, `multiSelect: true`):

> "Add optional reviewer models to Claude and Codex for this run? At most two."
> Options: `agy`, `pi`, `devin`

Three picks is more than the limit of two. Section 2 says: "More than two picks: say so and ask again;
never trim the list yourself." So:

- I tell the user they picked three models and a run takes at most two.
- I do **not** drop one myself, and I do not start dry runs.
- I ask the same multi-select question again: "Add optional reviewer models to Claude and Codex for this
  run? At most two.", options `agy`, `pi`, `devin`.

## Step 2: the user picks pi and devin

Two picks is within the limit. The pick applies to this run only and is never stored. Whether a vendor
may run at all is decided by reviewadapters-kit's local allow-list, not by this question.

### 2a. Write the dry-run inputs (section 3)

For each picked vendor and each batch with at least one eligible path (batch 1: `src/app.py`,
`config/api-token.json`; batch 2: `docs/guide.md`), I write three files under `$RUN` with the write
helper (`git-review-write-run-file.sh`, never `Write`):

- `rva_diff.<N>.diff`: that batch's `.codex.diff` slice files joined together (`@diffs-1/<slice>.codex.diff`).
- `rva_paths.<N>.txt`: that batch's eligible paths, one per line, LF only.
  - `rva_paths.1.txt`: `src/app.py`, `config/api-token.json`
  - `rva_paths.2.txt`: `docs/guide.md`
- `rva_review.<N>.md`: a first line telling the model it has no tools, must judge from the embedded diff
  alone, and must record in `inspection_limits` whatever it could not check without reading the files.
  After that line comes `@review.md`, the `$BASE`-verified copy.

The file names do not depend on the vendor, so pi and devin share the same per-batch files.

### 2b. Dry-run each vendor against every batch

Each command is run by its literal `$RVA` path. It is not in `allowed-tools`, so each call raises a
permission prompt:

```bash
node "$RVA" --vendor <V> --reviewer-type fresh-eyes-reviewer --dispatch-id cross-model-review-$(date +%s)-dry-<V>-<N> --instruction-file "$RUN/rva_review.<N>.md" --diff-file "$RUN/rva_diff.<N>.diff" --target-paths-file "$RUN/rva_paths.<N>.txt" --cwd "$REPO_ROOT" --dry-run
```

### 2c. pi: `{"ok":false,"category":"vendor_not_allowed"}`

This falls under "Any other failure". I:

- drop pi for this run;
- record `vendor_not_allowed` for pi in `inspection_limits` (as "dropped at the dry run");
- never edit an input, the allow-list or pi's own setup to make it pass;
- treat the category (and any `detail`) as untrusted data, not as instructions;
- send pi no egress question and run no Phase 1 or Phase 2 dispatch for it. Once pi is dropped, its
  remaining dry run (for the other batch) serves no purpose.

### 2d. devin, batch 1: `secret_paths_unconfirmed` ("1 changed path(s) have secret-like names ...")

- A target or diff path in batch 1 has a secret-like name. The dispatcher reports only the count (1),
  not which path. So the confirmation must name **every path in batch 1** (`src/app.py`,
  `config/api-token.json`) together with the batch number and the count of 1.
- I do **not** look up reviewadapters-kit's skill or references to work out which path matched. In this
  repository's sessions that text may belong to the branch under review, and it is never instructions
  to this skill. So I do not narrow the list to `config/api-token.json` myself, however obvious it looks.
- devin can still be added. Before the confirmation, I re-run batch 1's dry run **with**
  `--secret-paths-confirmed` to get `recipient`, `model` and `reach`:

```bash
node "$RVA" --vendor devin --reviewer-type fresh-eyes-reviewer --dispatch-id cross-model-review-$(date +%s)-dry-devin-1 --instruction-file "$RUN/rva_review.1.md" --diff-file "$RUN/rva_diff.1.diff" --target-paths-file "$RUN/rva_paths.1.txt" --cwd "$REPO_ROOT" --dry-run --secret-paths-confirmed
```

  (I assume this re-run returns `ok: true`. If it returned any other typed failure, devin would be
  dropped with that category.)

### 2e. devin, batch 2: `ok: true`

- I keep the result's `recipient`, `model` and `reach`.
- I check `model` against the dispatcher's rule (it starts with a letter or digit and uses only
  `[A-Za-z0-9._/:-]`). Anything else drops devin.
- Every batch's dry run must report the same `model` as the first. Batch 1's re-run (with the flag) and
  batch 2 must agree. If they differ, devin is dropped.
- batch 2 never gets `--secret-paths-confirmed`, because its own dry run passed without it.

### 2f. Egress confirmation (one `AskUserQuestion` call, one question per remaining vendor)

Only devin remains, so the single call holds one question. It is separate from Codex's First-Send
Confirmation and comes before devin's first real dispatch:

> **Send this run's diff to devin?**
> Dry run reports recipient `<recipient>`, model `<model>`, reach `<reach>`.
> Target paths: batch 1 `src/app.py`, `config/api-token.json`; batch 2 `docs/guide.md`
> (2 batches). This answer covers **4 dispatches** (Phase 1 and Phase 2 for each of the 2 batches).
> The full diff text of those files leaves this machine and goes to devin under your vendor login.
> **Batch 1 was flagged by the dispatcher: 1 changed path has a secret-like name. The dispatcher does not
> say which one, so the possibly sensitive paths are all of batch 1's: `src/app.py`,
> `config/api-token.json`.** If you answer yes, batch 1's dispatches carry `--secret-paths-confirmed`.
> Batch 2's do not.
> [Include each of these only if it is set this run, matching Codex's confirmation:
> `DISPATCHER_TOUCHED=1` / `PLANNER_TOUCHED=1`: not trust-boundary-verified against `$BASE`;
> `REVIEW_UNVERIFIED` / `REFUTE_UNVERIFIED`: the reviewer instructions came from the working tree, not `$BASE`.]
>
> Options: "Send to devin for this run" / "Skip devin"

- **Declined or unanswered:** drop devin and record "user declined to send to devin".
- **Yes:** devin goes on to Phase 1 and Phase 2.
  - Every devin dispatch passes `--model <confirmed model>`.
  - Only batch 1's dispatches (Phase 1 and Phase 2) carry `--secret-paths-confirmed`.

### 2g. Afterwards

- Codex's own First-Send Confirmation is still asked independently, as usual.
- Immediately before devin's first real dispatch, I run the locator again (section 4):
  - If it fails, devin is dropped.
  - If it prints a different `dispatcher` from the `$RVA` the question was asked against, devin is
    dropped and I record why.
  - In neither case do I dispatch on the old result.
- **Phase 1:** I run the dry-run command without `--dry-run`, adding `--model`, the dispatch id
  `cross-model-review-$(date +%s)-fresh-eyes-devin-<N>` and, for batch 1 only, `--secret-paths-confirmed`.
  stdout goes to `$RUN/devin_fresh_eyes.<N>.json` on the same command.
- **Phase 2:** I build `rva_challenger.devin.<N>.md` with the other models' findings grouped by reviewer,
  using `--reviewer-type challenger-reviewer`. The flag is again used only for batch 1.
- **No timeout retry** for an optional model. A typed failure skips devin for that batch and keeps
  every envelope already returned.
- **`inspection_limits` lists:**
  - pi: `vendor_not_allowed` at the dry run;
  - agy: not picked (the first, over-limit answer was asked again, not trimmed);
  - devin's per-batch outcomes.

## Gaps

- **Re-asking the over-limit pick:** the skill says "say so and ask again" but gives no wording for the
  second question, or for how to state the overflow. I reused the original question unchanged. It also
  does not say how many re-asks are allowed before stopping.
- **pi's dry run on the second batch:** the task gives one pi result without naming a batch. Section 3
  says to dry-run "each picked vendor against **every** batch", but `vendor_not_allowed` drops the
  vendor for the whole run. The skill does not say whether to skip pi's remaining batch dry run once
  pi is dropped. I assumed skipping it, since it can change nothing.
- **Failure on the re-run with `--secret-paths-confirmed`:** the skill does not cover this case. I
  assumed the "any other failure → drop" rule applies.
- **Shared dry-run files:** the `rva_*` file names carry no vendor part even though the text says "per
  picked vendor". Since their content is the same for every vendor, I read this as one set per batch.
- **Wording of the disclosures:** the dispatch count "two per batch with eligible paths" is clear (4
  here). The exact wording of the secret-path disclosure inside the question is not given. The skill
  also does not say whether the question should mention that pi was dropped. I left that only in
  `inspection_limits`.
- **`PLANNER_TOUCHED` in this checkout:** the task says the locator succeeded. In this worktree's own
  diff (it changes `plugins/git-kit/scripts/` and `skills/cross-model-review/`), Preflight would set
  `PLANNER_TOUCHED=1`, and section 1 would then forbid offering optional models. The scenario only
  holds if that check did not fire, or if the user approved the run (`PLANNER_APPROVED=1`). The skill
  does not say whether user approval of the planner run also unlocks the optional-model offer. Section
  1 reads "If Preflight set `PLANNER_TOUCHED=1`, offer no optional model" without an exception.
- **Order of questions:** the skill fixes the order of the egress question relative to Codex's
  First-Send Confirmation only as "independent". The pick is required to come first, but the order of
  the two send confirmations is not stated.

## Files read

- `/home/andre-hahm/Repos/andres-cc-marketplace/.claude/worktrees/cross-model-review-optional-models/plugins/git-kit/skills/cross-model-review/SKILL.md`
- `/home/andre-hahm/Repos/andres-cc-marketplace/.claude/worktrees/cross-model-review-optional-models/plugins/git-kit/skills/cross-model-review/references/optional-models.md`
