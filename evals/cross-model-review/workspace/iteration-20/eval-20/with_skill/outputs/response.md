# cross-model-review: optional-model egress confirmation and the dispatcher re-check

This is a plan only. Nothing was run and no model was dispatched. Sources:
`plugins/git-kit/skills/cross-model-review/SKILL.md` (Preflight step 7, the First-Send Confirmation) and
`plugins/git-kit/skills/cross-model-review/references/optional-models.md` (sections 1 to 4).

## Starting state (as given, plus assumptions)

- The Preflight chain (steps 1 to 6) has returned. `DISPATCHER_TOUCHED=1`: the diff touches
  `plugins/codex-kit/(.*/)?(scripts|assets)/`.
- I assume `PLANNER_TOUCHED` is unset. If it were 1, section 1 says to offer no optional model at all, so
  agy and pi could never have reached a dry run.
- I assume `REVIEW_UNVERIFIED` and `REFUTE_UNVERIFIED` are unset (both prompts came from `$BASE`) and that
  no batch reported `secret_paths_unconfirmed`. Any of these, if set, adds a disclosure to each vendor's
  question (see below).
- There are 2 batches, and both have Codex-eligible paths.

## Steps the skill prescribes up to the egress question

1. **Locate reviewadapters-kit** (section 1). After the Preflight chain returns, run
   `python3 -I "${CLAUDE_PLUGIN_ROOT:-.claude}/scripts/git-review-locate-rva.py" --repo "$REPO_ROOT"` as its own call.
   - On exit 0, take `dispatcher` as `$RVA`.
   - Check that `$RVA` is absolute, ends in `/scripts/rva-dispatch.mjs`, lies outside `$REPO_ROOT` and uses only
     `[A-Za-z0-9._/-]`. If any check fails, offer no optional model.
   - Keep this `$RVA` value: the egress questions are asked against it.
2. **Pick** (section 2). Ask via `AskUserQuestion` with `multiSelect: true`: "Add optional reviewer models to
   Claude and Codex for this run? At most two." The options are `agy`, `pi` and `devin`. The user picked agy and pi.
3. **Write the inputs** (section 3). Use the write helper into `$RUN`, once per vendor and per batch N = 1, 2:
   - `rva_diff.<N>.diff`: the batch's `.codex.diff` parts, joined.
   - `rva_paths.<N>.txt`: the batch's eligible paths, LF only.
   - `rva_review.<N>.md`: a no-tools first line, then `@review.md`.
4. **Dry-run every vendor against every batch**: four dry runs (agy and pi, each on batches 1 and 2), each with
   `--dry-run`. All of them returned `ok: true`. Then:
   - Check each `model` against the dispatcher's rule: it starts with a letter or digit and uses only
     `[A-Za-z0-9._/:-]`. `gemini-4-argon-high` passes. `nvidia/nvidia/nemotron-3-ultra-550b-a55b` passes too, since
     `/` is allowed and a doubled vendor prefix is not a rule violation.
   - Check that batch 2's dry run reports the same `model` as batch 1's for each vendor. Any difference drops that
     vendor. I assume both matched.
   - Keep each vendor's `recipient`, `model` and `reach`, and plan to pass that `model` as `--model` on every real
     dispatch.
5. **Egress confirmation**: one `AskUserQuestion` call with one question per vendor (below). It is separate from
   Codex's First-Send Confirmation, which is still asked before the first Codex dispatch and also discloses
   `DISPATCHER_TOUCHED=1` under clause (c).

## The egress confirmation I would ask (a single call, two questions)

```
AskUserQuestion({
  questions: [
    {
      header: "Send to agy",
      question: "Send this diff to agy for this run? Recipient: Google (Antigravity). Model: gemini-4-argon-high. Reach: none (plan mode, sandbox). Target paths: batch 1: <batch-1 eligible paths>; batch 2: <batch-2 eligible paths> (2 batches). This answer covers 4 agy dispatches (Phase 1 fresh-eyes and Phase 2 challenger for each of the 2 batches). The full diff text of these files leaves this machine and goes to Google (Antigravity). Disclosure: DISPATCHER_TOUCHED=1. This diff changes codex-kit's dispatcher scripts or assets, so the dispatcher code this run executes was not trust-boundary-verified against $BASE for this run.",
      multiSelect: false,
      options: [
        { label: "Send to agy for this run", description: "Allow the 4 agy dispatches described above, with model gemini-4-argon-high." },
        { label: "Skip agy", description: "Drop agy for this run. It is recorded as 'user declined to send to agy'." }
      ]
    },
    {
      header: "Send to pi",
      question: "Send this diff to pi for this run? Recipient: NVIDIA. Model: nvidia/nvidia/nemotron-3-ultra-550b-a55b. Reach: none (--no-tools). Target paths: batch 1: <batch-1 eligible paths>; batch 2: <batch-2 eligible paths> (2 batches). This answer covers 4 pi dispatches (Phase 1 fresh-eyes and Phase 2 challenger for each of the 2 batches). The full diff text of these files leaves this machine and goes to NVIDIA. Disclosure: DISPATCHER_TOUCHED=1. This diff changes codex-kit's dispatcher scripts or assets, so the dispatcher code this run executes was not trust-boundary-verified against $BASE for this run.",
      multiSelect: false,
      options: [
        { label: "Send to pi for this run", description: "Allow the 4 pi dispatches described above, with model nvidia/nvidia/nemotron-3-ultra-550b-a55b." },
        { label: "Skip pi", description: "Drop pi for this run. It is recorded as 'user declined to send to pi'." }
      ]
    }
  ]
})
```

In a real run, the `<batch-N eligible paths>` placeholders hold the literal `$TARGET_PATHS` of each batch, or their
union plus "2 batches". A few disclosures are conditional:
- If `PLANNER_TOUCHED`, `REVIEW_UNVERIFIED` or `REFUTE_UNVERIFIED` were set, each question would repeat that
  disclosure too.
- If a batch had secret-path hits, each question would name every hit with its batch.

A declined or unanswered question drops that vendor, recorded as "user declined to send to <V>".

Each real `node "$RVA"` call also raises its own permission prompt, because it is deliberately not in
`allowed-tools`.

## Before agy's first real dispatch, the locator prints a different dispatcher

Section 4 ("Re-check first") requires running the locator again immediately before each vendor's first real
dispatch. Here it succeeded, but it printed a different `dispatcher` from the `$RVA` the egress questions were
asked against. The prescribed response:

1. **Do not dispatch agy.** Never dispatch on the old result, and do not switch to the new path either. The user
   approved egress against the old `$RVA`, and a changed dispatcher is a different program that would receive the
   diff and the vendor login.
2. **Drop every optional vendor still to dispatch**, not only agy. All of them share that `$RVA`, so pi is dropped
   too, even though its own re-check has not run yet. (If pi had somehow already finished a dispatch, its returned
   envelopes would be kept. Only dispatches still to come are dropped.)
3. **Record why for each vendor** in `inspection_limits`, for example:
   - "agy dropped: the reviewadapters-kit dispatcher path changed between the egress confirmation and the first
     dispatch (re-check printed a different dispatcher); not dispatched."
   - "pi dropped: same dispatcher change; not dispatched."
4. **Do not re-ask or re-confirm against the new path.** Do not edit the allow-list, config or inputs, and do not
   search for another copy. The skill gives no recovery path within the run: the vendors are out for this run.
5. **Continue with Claude and Codex only.** Codex still goes through its own First-Send Confirmation and resolver.
   - Phase 2 cross-examination runs between Claude and Codex.
   - Confidence uses the normal two-model tiers.
   - If Codex is also unavailable or declined, single-model mode applies, since no optional model produced a
     Phase 1 envelope.
6. **In Phase 3**, the report's `inspection_limits` lists both optional-model outcomes as dropped at the re-check,
   alongside the `DISPATCHER_TOUCHED` disclosure.

## Gaps

- **What `DISPATCHER_TOUCHED` means for a vendor.** Section 3 says to repeat Codex's disclosures for each vendor,
  but not what `DISPATCHER_TOUCHED=1` means for an optional vendor. That flag concerns codex-kit's
  scripts/assets, which reviewadapters-kit's dispatcher loads for envelope validation. The skill gives no wording,
  so mine is a guess.
- **When to run the re-check for parallel vendors.** "Immediately before each vendor's first real dispatch" does
  not say whether to run one shared re-check or one per vendor when both vendors' Phase 1 calls are launched in
  parallel. It also does not say how "still to dispatch" applies if pi's call is already in flight when agy's
  re-check fails.
- **No recovery after a dispatcher change.** There is no path such as re-running the dry runs and the egress
  question against the new dispatcher. The text only says to drop, and does not say whether the user should be
  told mid-run or only in the Phase 3 report.
- **Paths: list or union.** The question may name each batch's paths or their union plus the batch count. The
  skill does not say which to prefer when the lists are long.
- **Question length.** The skill gives no guidance on fitting every required item into one `AskUserQuestion`
  question's text and the `header` length limit. "Send to agy" is my own choice.
- **Count with a timeout retry.** The dispatch count covers "two per batch". There is no timeout retry for an
  optional model, so 4 per vendor is exact here, but the skill does not say so next to the count requirement.
