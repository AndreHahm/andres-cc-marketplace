# cross-model-review: First-Send Confirmation declined for Codex, pi returns a valid Phase 1 envelope

Scenario: locator succeeded, user picked `pi`, pi's dry run passed, user answered "Send to pi for this run", and at the First-Send Confirmation for Codex the user picked the decline option. pi then returned a valid Phase 1 envelope.

## 1. First-Send Confirmation options

The question is an `AskUserQuestion` asked once per invocation, before the first real Codex dispatch and before the Codex backend resolves (SKILL.md, "First-Send Confirmation"). It must:

- name the reviewer persona and the target paths of every batch (or their union plus the batch count);
- state the number of Codex dispatches it covers (two per batch with Codex-eligible paths, plus a possible timeout retry per batch) and that one answer covers all of them;
- disclose (a) that the dispatched process can read anything the account can read; (b) if Preflight step 2's fallback is reached, `danger-full-access` with network access and no sandbox; (c) `DISPATCHER_TOUCHED` or `PLANNER_TOUCHED` if set; (d) `REVIEW_UNVERIFIED` or `REFUTE_UNVERIFIED` if set.

Options are exactly two: **"Send to Codex for this run"** and **"Skip Codex for this run"**. The pi egress question is separate; it was already answered and does not count toward this one (optional-models.md section 3).

## 2. What happens to Codex

On "Skip Codex for this run" the skill says to skip every Codex dispatch before any is attempted. In this run that means:

- Codex's resolver (Step 1 `bridge-invoke.mjs`, and the Step 2 `guarded-dispatch.mjs` fallback) is never run.
- No `$RUN/codex_fresh_eyes.<N>.json` and no `$RUN/codex_challenger.<N>.json` are produced.
- No Codex-side fallback question (resolver step 3) is asked. That question only follows a failure, and a declined dispatch is not a failure.
- `inspection_limits` records the reason as **"user declined to send to Codex"**, not "Codex unavailable", because the skill calls it a deliberate opt-out.

Because pi returned a valid Phase 1 envelope, this is not single-model mode. The run stays on the two-model path: Claude plus pi.

## 3. Phase 1

- Claude's native fresh-eyes pass runs as usual, writing `$RUN/claude_fresh_eyes.json`.
- pi's Phase 1 runs per batch with eligible paths. It uses the confirmed `--model`, the batch's three files, and `--secret-paths-confirmed` only for batches whose hits were confirmed. Output goes to `$RUN/pi_fresh_eyes.<N>.json`.
- Codex contributes nothing to Phase 1.

## 4. Phase 2

Phase 2 runs, because the rule is "per vendor and batch with a valid Phase 1 envelope from at least one other model" (optional-models.md section 4). Claude counts as the other model.

- **pi's challenger:** build `$RUN/rva_challenger.pi.<N>.md` from Claude's Phase 1 findings for the batch (filtered to `$TARGET_PATHS` and neutralized), with the no-tools first line and no diff block. Dispatch with `--reviewer-type challenger-reviewer`, same `--model`, and the same diff and paths files. Output goes to `$RUN/pi_challenger.<N>.json`.
- **Claude's challenger:** follow `refute.md` over the confirmed optional model's envelopes, `$RUN/pi_fresh_eyes.<N>.json`. The skill's text names Codex's envelopes as well, but those do not exist here, so Claude cross-examines pi's findings only. Write the result to `$RUN/claude_challenger.json`.
- Each finding must be explicitly classed as confirmed, refuted or novel relative to a prior finding id. None may be silently skipped.
- A typed failure for pi's Phase 2 drops only that vendor-batch, and its category is recorded in `inspection_limits`.

Phase 2 is skipped only if pi also had no valid Phase 1 envelope. Here it did, so it runs.

## 5. Phase 3 and the report

- Confidence follows optional-models.md section 5, where the "models" are Claude and pi:
  - **Low / contested:** a Phase 2 pass refuted the finding, even if both raised it in Phase 1. Show both sides.
  - **High:** both models raised it independently in Phase 1, or one raised it and the other's Phase 2 confirmed it.
  - **Medium:** everything else, including findings only one side raised with no cross-examination.
  - A `critical` finding is never dropped, even at Low/contested.
- Rank by severity times confidence. The table columns are `severity | confidence | location | claim | found-by / confirmed-or-refuted-by`, and the last column names each model (Claude, pi).
- `inspection_limits` must include: the declined-Codex reason; each pi outcome (not located, not picked, dropped at dry run, declined, or failed per batch, if any); the Preflight step 2 charset or deleted-path exclusion if it applied; any Claude finding dropped from a challenge for an excluded location; the unverified-instructions fallback if Preflight step 5 set it; the dispatcher or planner disclosure if Preflight step 6 set it; and `$INDEX_COPY_FAILED` and `$INTENT_ADD_REFUSED` if set.
- The scope plan is reported as scoped-review.md section 6 requires: planner limits, dropped slices, excluded folders, unfinished batches, `PLANNER_TOUCHED`, and the manifest path with completed slice names.
- The report ends by asking which findings to fix, through `AskUserQuestion`. No code is edited until the user picks.
- Caveat to state plainly: `$RUN` persists after the run, and this skill has no scoped delete.

## Gaps

1. **Ordering of the two confirmations.** The skill says the pi egress question happens "independent of" Codex's First-Send Confirmation, but never says which comes first. The text only says the Codex question comes "before the backend resolves" and the pi question comes "before that vendor's first real dispatch". I assumed the pi question is asked before the Codex one, since Preflight step 7 orders the optional-model steps first.
2. **Where the declined-Codex reason is recorded in mixed mode.** Phase 3 gives an explicit reason-recording rule for single-model mode, and the resolver gives the "user declined to send to Codex" wording. The skill never says where or how that reason appears when another model still produced envelopes. I recorded it in `inspection_limits`.
3. **Whether Codex-only disclosures still apply.** Preflight step 6 and the Codex confirmation's disclosures (c) and (d) are written for a Codex dispatch. The skill still lists the dispatcher-not-verified and `REVIEW_UNVERIFIED` notes in `inspection_limits` even when Codex is declined. I assumed they still apply to Claude and pi, since both use `review.md` and the diff, but the skill does not say this.
4. **Claude's challenger input.** Phase 2 says Claude's challenger covers "the other side's findings", which reads as Codex plus every optional model. With Codex declined it covers only pi. The skill does not state this case, so I inferred it.
5. **What counts as a "valid" envelope.** The skill relies on codex-kit's validated envelope and a typed failure for pi, but does not define "valid" for pi's output beyond the dispatcher's own check. The run-time rule for a pi envelope that is structurally valid but has an empty or off-topic `findings` list is not stated.
6. **Phase 1 batch-level rule versus the single decline.** The resolver's "no batch has a valid Codex envelope" rule can ask a question once, but a decline is not an attempt and so is never counted. The skill does not say explicitly that a decline suppresses that question. I assumed it does, since the decline section says to skip before any attempt.
7. **Scenario record.** I read SKILL.md and optional-models.md only. I did not read `references/testing-scenarios.md`, `references/resolver-failure-handling.md` or `references/scoped-review.md`, so any detail that lives only in those files is not covered here.
