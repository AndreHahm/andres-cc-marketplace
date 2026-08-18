# What happens when the user picks "Stay Claude-native for this run"

## Short answer

Picking **"Stay Claude-native for this run"** at the First-Send Confirmation routes the run into
**single-model mode immediately, before any Codex dispatch is attempted** — the same terminal path
that resolver step 3 uses for a genuine Codex-unavailable failure. Phase 1's Codex pass is skipped,
Phase 2 is skipped entirely, and Phase 3 synthesizes from Claude's Phase 1 findings alone. The skill
is explicit that neither of the two bad outcomes in the question — "Phase 1 still attempts the
declined dispatch" or "Phase 2 waits on a Codex envelope that was never created" — is allowed to
happen. `inspection_limits` records the reason as **"user declined to send to Codex"**, explicitly
distinguished in the text from "Codex unavailable."

## Where this is stated

**The controlling instruction** is the paragraph immediately after the First-Send Confirmation block
(right below the "Send to Codex for this run" / "Stay Claude-native for this run" option list):

> "**On 'Stay Claude-native for this run': enter single-model mode immediately, before any dispatch is
> attempted** — the same skip-Phase-1's-Codex-pass-and-all-of-Phase-2 path resolver step 3 uses, not
> just the zero-Codex-unavailable case. Record the `inspection_limits` reason as 'user declined to send
> to Codex' rather than 'Codex unavailable' — this is a deliberate opt-out, not a failure, and the
> report should say so accurately. Without this, nothing else in this document transitions the workflow
> out of the two-model path on this answer, leaving Phase 1 free to still attempt the declined dispatch
> or Phase 2 to wait on a Codex envelope that will never exist."

This paragraph is doing three things relevant to the question:

1. It names the exact control-flow target: the same "skip-Phase-1's-Codex-pass-and-all-of-Phase-2
   path" that the **Codex dispatch resolver's step 3** (lines 211-219 of the resolver section) already
   defines for the case where every dispatch attempt has failed and the user is asked whether to
   proceed single-model or stop. The opt-out answer reuses that exact same path rather than inventing a
   new one.
2. It states the transition must happen "immediately, before any dispatch is attempted" — i.e. Phase 1
   never even tries to call the resolver for Codex once this answer is given.
3. It explicitly calls out the two failure modes the question asks about — Phase 1 still attempting the
   declined dispatch, and Phase 2 waiting on a Codex envelope that will never exist — as exactly the bugs
   this instruction exists to prevent ("Without this, nothing else in this document transitions the
   workflow...").

## Why Phase 1 does not attempt Codex dispatch

Phase 1's own text gates the Codex sub-step on single-model mode: "**Codex's pass**, via the resolver
above (**skip entirely in single-model mode — see resolver step 3**)." Since the First-Send-Confirmation
opt-out routes into that same single-model-mode state (per the paragraph above), Phase 1's Codex pass is
skipped along with it — Claude's native pass still runs as normal (it doesn't depend on Codex at all),
but no dispatch to `bridge-invoke.mjs`/`guarded-dispatch.mjs` is ever made.

## Why Phase 2 does not run at all (so nothing "waits" on a missing envelope)

Phase 2 opens with its own explicit single-model-mode gate: "**Single-model mode (Codex unavailable,
user chose to proceed — see resolver step 3): skip this phase entirely and go straight to Phase 3.**
There is no second reviewer's findings to cross-examine, and Claude cross-examining its own Phase 1
output would reintroduce the self-ratification failure mode this skill exists to avoid." Because the
opt-out enters that same single-model-mode state, Phase 2 is bypassed wholesale — there is no step in
Phase 2 that blocks or polls waiting for `$RUN/codex_fresh_eyes.json`; the phase is never entered.

## Where Phase 3 picks it up, and what it records

Phase 3 opens with the matching synthesis rule: "**Single-model mode (Phase 2 was skipped — resolver
step 3):** synthesize from Claude's Phase 1 findings alone (`$RUN/claude_fresh_eyes.json`). Every
finding is capped at Medium confidence (see the Medium tier below) since nothing cross-examined it.
Record `single_model_mode: true` and the reason (Codex unavailable) in `inspection_limits`, then skip
straight to 'Rank by `severity × confidence`' below — there is no second envelope to merge."

Taken together with the First-Send-Confirmation paragraph's override ("Record the `inspection_limits`
reason as 'user declined to send to Codex' rather than 'Codex unavailable'"), the concrete recorded
reason for this specific scenario is:

- `single_model_mode: true`
- `inspection_limits` reason string: **"user declined to send to Codex"**

not the generic "Codex unavailable" wording Phase 3's own single-model note uses as its default label —
the skill deliberately carves out this distinction so the final report accurately reflects that Codex
was never attempted because of a deliberate opt-out, not because a dispatch failed.

## Corroborating sections (Testing & Validation)

The skill's own test scenarios and quality gates independently restate this exact behavior, confirming
it isn't just one paragraph's claim but a documented, checkable requirement:

- **Scenario 10**: "The First-Send Confirmation is answered 'Stay Claude-native for this run' →
  single-model mode is entered immediately, with `inspection_limits` recording 'user declined to send to
  Codex,' never a dispatch attempt on the declined path."
- **Quality gate** (last bullet in the Quality gates checklist): "'Stay Claude-native for this run' at
  the First-Send Confirmation always enters single-model mode immediately — never leaves Phase 1/2 to
  still attempt or wait on a declined Codex dispatch."

## Summary of the control-flow path

```
First-Send Confirmation → "Stay Claude-native for this run"
        │
        ▼
Enter single-model mode immediately (same terminal state as resolver step 3's
"proceed single-model" branch), BEFORE any dispatch attempt
        │
        ▼
Phase 1: Claude's native pass runs normally; Codex's pass is skipped entirely
(per Phase 1's own "skip entirely in single-model mode" clause)
        │
        ▼
Phase 2: skipped entirely (per Phase 2's own single-model-mode opening clause) —
no cross-examination, no waiting on any Codex envelope, because Phase 2 is never entered
        │
        ▼
Phase 3: synthesizes from Claude's Phase 1 findings alone; every finding capped at
Medium confidence; single_model_mode: true; inspection_limits reason =
"user declined to send to Codex" (not "Codex unavailable")
```

So, to directly answer the two either/or questions posed:

- **Does Phase 1 still attempt to dispatch Codex?** No — the skill explicitly names this as the failure
  mode it is preventing, and Phase 1's Codex sub-step is conditioned on single-model mode, which this
  answer enters immediately.
- **Does Phase 2 end up waiting on a Codex envelope that was never created?** No — Phase 2 is skipped
  entirely as a whole phase; it never reaches the point where it would read or wait for
  `$RUN/codex_fresh_eyes.json` or `$RUN/codex_challenger.json`.
- **What reason is recorded in `inspection_limits`?** "user declined to send to Codex" — deliberately
  worded differently from the generic "Codex unavailable" reason used by the true-failure single-model
  path, per the First-Send Confirmation paragraph's explicit override of Phase 3's default wording.
