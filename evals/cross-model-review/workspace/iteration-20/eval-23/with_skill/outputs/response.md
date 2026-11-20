# Eval 23: pi picked, two batches, the dry runs report different models

**Short answer:** I drop pi for this run, so pi gets no real dispatch and no `--model` is used. The two
dry runs report different models (`nvidia/nemotron-3-ultra` for batch 1, `nvidia/nemotron-3-super` for
batch 2). `references/optional-models.md` section 3 says: "Every batch's dry run must report the same
`model` as the first; a different one drops the vendor." Because pi is dropped, I ask no egress question
for it. The run goes on with Claude and Codex only.

## Step by step

1. **Preflight steps 1-6** run as one chained call (SKILL.md, "Preflight"). The planner gives 2 batches.
   I assume `PLANNER_TOUCHED` is unset; otherwise no optional model would be offered at all (section 1).
2. **Preflight step 7, locate:** the locator (`git-review-locate-rva.py --repo "$REPO_ROOT"`) exits 0. I
   check that `dispatcher` is absolute, ends in `/scripts/rva-dispatch.mjs`, lies outside `$REPO_ROOT`
   and uses only `[A-Za-z0-9._/-]`, then take it as `$RVA`.
3. **Pick:** this question comes before the First-Send Confirmation. I ask one `AskUserQuestion` with
   `multiSelect: true`:
   - Question: "Add optional reviewer models to Claude and Codex for this run? At most two."
   - Options: `agy`, `pi`, `devin`.

   The user picks `pi` only. One pick is within the limit of two. The pick holds for this run only and
   is not stored.
4. **Inputs:** for pi, I write three files per batch through the write helper into `$RUN`, six files in
   total. For each batch N (1 and 2):
   - `rva_diff.<N>.diff`: the batch's joined `.codex.diff` parts.
   - `rva_paths.<N>.txt`: the eligible paths, one per line, LF line endings.
   - `rva_review.<N>.md`: a first line saying the model has no tools, then `@review.md`.
5. **Dry run each batch:** I dry-run pi against both batches with `node "$RVA" --vendor pi
   --reviewer-type fresh-eyes-reviewer --dispatch-id cross-model-review-<ts>-dry-pi-<N> ...
   --dry-run`. A dry run sends nothing.
   - Batch 1 returns `ok: true`, recipient NVIDIA, model `nvidia/nemotron-3-ultra`, reach `none
     (--no-tools)`. The model passes the format check (it starts with a letter and uses only
     `[A-Za-z0-9._/:-]`). This is the "first" model, the one every later batch must match.
   - Batch 2 returns `ok: true`, model `nvidia/nemotron-3-super`. This model also passes the format
     check, but it differs from batch 1's model. **pi is dropped for this run.**
   - I do not edit an input, the allow-list or pi's setup to make the two match. I do not choose one
     model and use it for both batches. I do not keep pi for batch 1 only. The rule drops the vendor,
     not one batch.
6. **Egress confirmation:** the skill asks "a single `AskUserQuestion` call with one question per
   remaining vendor". No vendor remains, so I ask no egress question. I would not have asked "Send to pi
   for this run" / "Skip pi". Asking it would show the user a recipient and model that the real
   dispatch might not use, which is exactly what the same-model rule exists to prevent.
7. **No locator re-check and no pi dispatch:** section 4's locator re-check runs only "immediately
   before each vendor's first real dispatch", and pi has none. Phase 1 and Phase 2 send nothing to pi.
   No `$RUN/pi_fresh_eyes.<N>.json` or `pi_challenger.<N>.json` file exists, and no `--model` value is
   ever passed.
8. **The rest of the run:** Codex's First-Send Confirmation still comes before the first Codex dispatch.
   It is a separate question and pi's outcome does not affect it:
   - Question: name the persona and every batch's target paths, say there are 4 Codex dispatches (two
     per batch, plus a possible timeout retry per batch), and include disclosures (a)-(d).
   - Options: "Send to Codex for this run" / "Stay Claude-native for this run".

   Phases 1-3 then run between Claude and Codex as usual. Confidence uses the two-model tiers, because
   pi is not "a confirmed optional vendor with a valid envelope" (section 5).
9. **Phase 3 report:** `inspection_limits` lists the outcome as "pi: dropped at the dry run: batch 1
   reported `nvidia/nemotron-3-ultra`, batch 2 reported `nvidia/nemotron-3-super`; the dry runs did not
   agree on one model". Section 5 requires every optional-model outcome to be listed, "dropped at the dry
   run" included. I also tell the user in one line that pi was not used and why.

## Which `--model` do the real dispatches use?

None. pi has no real dispatch. If both dry runs had reported the same model, every pi dispatch (both
batches, Phase 1 and Phase 2) would have passed that one confirmed value as `--model`.

## Gaps

- **What "the first" dry run means:** the skill does not define it. If the dry runs run in parallel,
  "first" could mean batch 1 or whichever finished first. The outcome here is the same either way,
  because any mismatch drops pi. I read "first" as batch 1.
- **The `inspection_limits` wording:** the skill gives no category name for a model mismatch. The typed
  failures name categories (`vendor_not_allowed` and others), but this drop is not a typed failure, so I
  made up a description.
- **Whether to tell the user right away:** the skill does not say whether to tell the user about the
  drop at the moment it happens or only in the Phase 3 report. It also does not say whether the user may
  re-pick a different vendor afterwards. A pick question is asked only once, so I did not offer a re-pick.
- **Skipping the egress question:** the skill does not explicitly say that the egress question is
  skipped when no vendor remains. I inferred it from "one question per remaining vendor".
- **Why the models can differ:** the skill does not explain how one vendor's dry runs could report
  different models, for example a per-batch or size-based model choice in reviewadapters-kit's
  settings. It also does not say whether a different-model result should be flagged as suspicious, as
  opposed to a configuration quirk.
