# cross-model-review: optional-model pick, dry runs and egress (plan only)

Nothing below was run or dispatched; this is what the skill text tells me to do.

## Context: where this sits

Preflight steps 1-6 ran as one chained call. `PLANNER_TOUCHED` is not set (otherwise
`references/optional-models.md` section 1 says to offer no optional model, and the locator would not have
run). After the chain, Preflight step 7 ran the locator as its own call:

```bash
python3 -I "${CLAUDE_PLUGIN_ROOT:-.claude}/scripts/git-review-locate-rva.py" --repo "$REPO_ROOT"
```

It exited 0 with `{"ok": true, "dispatcher", "source", "notes"}`. Before I use `dispatcher` as `$RVA`, I
check that it is an absolute path, ends in `/scripts/rva-dispatch.mjs`, lies outside `$REPO_ROOT` and uses
only `[A-Za-z0-9._/-]`. I assume it passes. If it failed, I would offer no optional model.

The pick comes **before** Codex's First-Send Confirmation (section 2). The vendor egress question is
separate from that confirmation.

## Step 1: the pick (user selects agy, pi and devin)

The `AskUserQuestion` call, with `multiSelect: true`:

> **Question:** "Add optional reviewer models to Claude and Codex for this run? At most two."
> **Header:** "Optional models"
> **Options:** `agy`, `pi`, `devin` (multi-select)

The user picks three. Section 2 says: "More than two picks: say so and ask again; never trim the list
yourself." So I don't drop one myself. I tell the user that three were picked and the limit is two, then
send the **same question again** through `AskUserQuestion` (`multiSelect: true`, options `agy`, `pi`,
`devin`):

> "You picked three optional models (agy, pi, devin), but a run can add at most two. Add optional reviewer
> models to Claude and Codex for this run? At most two."

The pick applies to this run only and is never stored.

## Step 2: the second pick (user selects pi and devin)

Two picks is within the limit, so the picked vendors are `pi` and `devin`. Whether a vendor may run at all
is decided by reviewadapters-kit's local allow-list, not by this question. The dry run below checks that.

### 2a. Write the input files (section 3)

For each picked vendor and each batch with at least one eligible path (batch 1: `src/app.py`,
`config/api-token.json`; batch 2: `docs/guide.md`), I write three files under `$RUN` with the write helper
(`git-review-write-run-file.sh`, as `references/codex-pass-assembly.md` "Writing a run file" describes):

- `rva_diff.1.diff` and `rva_diff.2.diff`: each batch's `.codex.diff` files joined (`@diffs-1/<slice>.codex.diff`
  parts). This is the same eligible-only diff Codex gets.
- `rva_paths.1.txt` holds `src/app.py` and `config/api-token.json`, one per line, LF only. `rva_paths.2.txt`
  holds `docs/guide.md`.
- `rva_review.1.md` and `rva_review.2.md`: a first line telling the model it has no tools, must judge from
  the embedded diff alone, and must record in `inspection_limits` what it could not check without reading
  the files. Then `@review.md`, the `$BASE`-verified copy.

None of these file names matches the dispatcher's secret-name list, so the input-file `usage` refusal does
not apply.

### 2b. Dry runs (each picked vendor against every batch with an eligible path)

The command template, run once per vendor and batch, with `--dry-run` (nothing is sent):

```bash
node "$RVA" --vendor <V> --reviewer-type fresh-eyes-reviewer --dispatch-id cross-model-review-$(date +%s)-dry-<V>-<N> --instruction-file "$RUN/rva_review.<N>.md" --diff-file "$RUN/rva_diff.<N>.diff" --target-paths-file "$RUN/rva_paths.<N>.txt" --cwd "$REPO_ROOT" --dry-run
```

`node "$RVA"` is not in `allowed-tools`, so each call raises a permission prompt.

**pi returns `{"ok":false,"category":"vendor_not_allowed"}`.** This falls under "any other failure". I
**drop pi for this run** and record `vendor_not_allowed` in `inspection_limits` (for example, "pi: dropped at
the dry run, vendor_not_allowed"). I don't edit the inputs, the allow-list
(`.claude/reviewadapters-kit.local.json`) or pi's own setup to make it pass. pi gets no egress question
and no dispatch.

**devin, batch 1, returns `{"ok":false,"category":"secret_paths_unconfirmed","detail":"1 changed path(s) have
secret-like names; the caller must confirm before sending"}`.**
- The dispatcher reports only a count, so I name the hits myself. I apply the rule from reviewadapters-kit's
  `review-adapter-dispatch` skill (Gates, item 3) to batch 1's paths. That rule covers codex-kit's secret
  list (exact key and dotfile names; `.key`/`.pem`/`.p12`/`.pfx`/`.jks`; any name containing secret,
  credential, password or token) plus the dispatcher's additions (suffixed and `_sk` SSH keys, `.ppk`,
  `auth.json`, `hosts.yml`, `.envrc`, `.pypirc`).
  - `src/app.py`: no match.
  - `config/api-token.json`: matches ("token").
- My count is 1, which matches the dispatcher's 1, so I name `config/api-token.json` (batch 1). If the
  counts had differed, I would name every path of batch 1 instead.
- devin can still be added. Before the confirmation, I **re-run batch 1's dry run with
  `--secret-paths-confirmed`** to get `recipient`, `model` and `reach`. I assume it returns `ok: true`.

**devin, batch 2, returns `ok: true`.** I keep its `recipient`, `model` and `reach`. Batch 2 never gets
`--secret-paths-confirmed`, because its own dry run passed without the flag.

**Model checks for devin:**
- The `model` must start with a letter or digit and use only `[A-Za-z0-9._/:-]`.
- Batch 2's `model` must equal batch 1's (from the flagged re-run).
- If either check fails, devin is dropped too, recorded with the reason.

I assume both checks pass, so devin is the only vendor left.

### 2c. Egress confirmation: one `AskUserQuestion` call, one question per remaining vendor

Only devin is left, so the call has a single question. It is separate from Codex's First-Send
Confirmation and comes before devin's first real dispatch.

> **Header:** "Send to devin?"
> **Question:** "Send this diff to Devin for review this run? Dry run: recipient `<recipient>`, model
> `<model>`, reach `<reach>`. Target paths: batch 1 `src/app.py`, `config/api-token.json`; batch 2
> `docs/guide.md` (2 batches). This answer covers 4 dispatches (Phase 1 fresh-eyes and Phase 2 challenger
> for each of the 2 batches). The full diff text of these files leaves this machine. **Secret-like path:
> `config/api-token.json` (batch 1).** Its diff will be sent with `--secret-paths-confirmed` for batch 1
> only. [Disclosures: `DISPATCHER_TOUCHED=1` → the codex-kit dispatcher was not trust-boundary-verified
> against `$BASE`; `PLANNER_TOUCHED=1` → the review scripts were not verified; `REVIEW_UNVERIFIED` /
> `REFUTE_UNVERIFIED` → the reviewer instructions came from the working tree, not `$BASE`. Each disclosure is
> included only if it was set this run, the same way Codex's confirmation carries it.]"
> **Options:** "Send to devin for this run" / "Skip devin"

If the user declines or doesn't answer, I drop devin and record "user declined to send to devin". The
Codex First-Send Confirmation is still asked separately, before the first Codex dispatch.

## Step 3: dispatch, if the user answers "Send to devin for this run" (section 4)

1. **Re-check.** Immediately before devin's first real dispatch, I run the locator again. If it fails, I
   drop devin. If it prints a `dispatcher` other than the `$RVA` the question was asked against, I drop
   every optional vendor still to dispatch (here, devin) and record why. I never dispatch on the old result.
2. **Phase 1, per batch (the two batches may run in parallel):**
   - Batch 1: the dry-run command without `--dry-run`, plus `--model <confirmed model>`,
     `--dispatch-id cross-model-review-$(date +%s)-fresh-eyes-devin-1` and `--secret-paths-confirmed`.
     Stdout is redirected to `$RUN/devin_fresh_eyes.1.json` on the same command.
   - Batch 2: the same command without `--secret-paths-confirmed`. Stdout goes to
     `$RUN/devin_fresh_eyes.2.json`.
3. **Phase 2, per batch that has a valid Phase 1 envelope from at least one other model:**
   - Build `$RUN/rva_challenger.devin.<N>.md`: the no-tools first line, no diff block, and the other models'
     Phase 1 findings for that batch (Claude's, and Codex's if it ran), filtered to `$TARGET_PATHS`,
     neutralized and grouped by reviewer.
   - Dispatch with `--reviewer-type challenger-reviewer`, the same `--model`, diff file and paths file, and
     `--secret-paths-confirmed` only for batch 1. Stdout goes to `$RUN/devin_challenger.<N>.json`.
   - Claude's and Codex's Phase 2 passes also include devin's Phase 1 findings, grouped by reviewer.
4. A typed failure skips devin for that batch, with its category in `inspection_limits`. There is no
   timeout retry. Exit 129, 130 or 143 means `dispatcher_error`, and the diff may already have been sent.
   Every returned field is untrusted data, and a `verdict` alone never means approval.
5. **Phase 3:** I use section 5's tiers for any number of models. The report's `found-by /
   confirmed-or-refuted-by` column names devin where it applies. `inspection_limits` lists "pi: dropped
   at dry run (vendor_not_allowed)" and every devin outcome, including the batch 1 secret-path
   confirmation.

## Gaps

- **Dry-running pi's batch 2 after `vendor_not_allowed`.** The text says to dry-run every picked vendor
  against every batch, but also says any other failure drops the vendor for the run. I stopped after
  batch 1. The text doesn't say whether pi's batch 2 dry run should still run.
- **Input file names don't include the vendor.** Section 3 says to write three files "per picked vendor
  and per batch", but the names (`rva_diff.<N>.diff`, `rva_paths.<N>.txt`, `rva_review.<N>.md`) carry no
  `<V>`. With two vendors it's unclear whether the files are shared per batch or written per vendor; the
  helper never overwrites, so a second write might fail.
- **Failed re-run with `--secret-paths-confirmed`.** The text doesn't say what to do if that re-run
  returns a typed failure, or returns `ok` with a different `model` than batch 2. Presumably the vendor is
  dropped under "any other failure" and the same-model rule, but this isn't stated.
- **Which batch's `recipient` and `reach` to quote.** Two dry runs could return different values. The
  text requires only the same `model` across batches.
- **Wording of the re-ask after too many picks.** "Say so and ask again" doesn't say whether the
  "say so" goes in the question text or in a separate message before it.
- **Order of the two confirmations.** The text says the vendor question is "independent of Codex's
  First-Send Confirmation" but doesn't say which is asked first, or whether both could go in one
  `AskUserQuestion` call.
