# Answer: All-Deletions Diff and the Empty Eligible-Files List

## Does the skill still attempt a Codex dispatch?

**No.** The skill explicitly does **not** attempt a Codex dispatch in this case.

Per **Preflight step 2**:

> "**If the eligible-files list is empty after exclusions (every changed file was deleted or had an
> invalid character), skip Codex entirely and enter single-model mode now — before attempting any
> dispatch.**"

The skill reasons that `bridge-invoke.mjs` (the codex-review-bridge dispatch script) "rejects a
falsy/empty `--target-paths` outright as a missing required argument, so a dispatch attempt here is
guaranteed to fail; forcing it anyway wastes a round-trip and produces a misleading 'Codex unavailable'
framing when Codex simply had nothing eligible to review." So rather than calling the Codex dispatch
resolver and letting it fail, the skill proactively short-circuits before any dispatch is even attempted.

This is corroborated by the **Testing & Validation** section's scenario 9:

> "Every changed file is a deletion or an invalid-charset path (Preflight step 2's eligible list is
> empty) → single-model mode is entered proactively, before any dispatch attempt, with
> `inspection_limits` recording 'zero Codex-eligible paths' rather than 'Codex unavailable.'"

and by the corresponding **Quality gates** checklist item:

> "A dispatch is never attempted when Preflight step 2's eligible-files list is empty — single-model
> mode is entered proactively instead"

## What happens instead?

The skill enters **single-model mode** immediately, at Preflight step 2 — before Phase 1 even begins,
not partway through it after a failed attempt. Per Preflight step 2:

> "Skip Phase 1's Codex pass and all of Phase 2, same as resolver step 3's single-model path..."

That means:

- **Phase 1**: Claude still runs its own native pass (following `$RUN/review.md` against `"${DIFF[@]}"`,
  writing `$RUN/claude_fresh_eyes.json`) — Codex's pass in Phase 1 is skipped entirely.
- **Phase 2**: Skipped wholesale. Phase 2's own opening line makes this explicit: "**Single-model mode
  (Codex unavailable, user chose to proceed — see resolver step 3): skip this phase entirely and go
  straight to Phase 3.**" (The zero-eligible-paths case is treated as the same single-model path,
  per Preflight step 2's "same as resolver step 3's single-model path" language.)
- **Phase 3**: Synthesizes from Claude's Phase 1 findings alone (`$RUN/claude_fresh_eyes.json`). Per
  Phase 3's own single-model-mode note: "synthesize from Claude's Phase 1 findings alone... Every
  finding is capped at Medium confidence... since nothing cross-examined it. Record `single_model_mode:
  true` and the reason... in `inspection_limits`, then skip straight to 'Rank by `severity × confidence`'
  below — there is no second envelope to merge."

So the end-to-end effect is a Claude-only review: findings are capped at Medium confidence (per Phase 3's
tier rules — "every finding in single-model mode... Phase 2 never ran, so nothing could confirm or
refute it"), and the report notes the single-model-mode reason in `inspection_limits`.

## What `inspection_limits` reason is recorded, and how does it differ from "Codex unavailable"?

The recorded reason is:

> **"zero Codex-eligible paths in this diff"**

as stated explicitly in Preflight step 2: "...record the `inspection_limits` reason as 'zero
Codex-eligible paths in this diff' rather than 'Codex unavailable' — the distinction matters for anyone
reading the report." This is reiterated in Testing & Validation scenario 9, which uses the near-identical
phrase "zero Codex-eligible paths."

This differs from the **"Codex unavailable"** framing used elsewhere in the skill in two ways:

1. **Different trigger/cause.** "Codex unavailable" is reserved for the Codex dispatch resolver's step 3
   case — an actual failed or degraded dispatch attempt: a typed failure from either dispatch script
   (`guardrails_disabled`, the `codex` CLI missing, `codex-kit` not installed at all producing a raw
   `cli_unavailable`-equivalent OS-level `node` failure, etc.), after which the skill asks via
   `AskUserQuestion` whether to proceed single-model or stop (Codex dispatch resolver, step 3; also
   Testing & Validation scenario 2). "Zero Codex-eligible paths" is instead a Preflight-time structural
   fact about the diff itself (every changed path was deleted or had an invalid character) — Codex was
   never actually reachable-or-not; there was simply nothing legally dispatchable to send it.
2. **No dispatch attempt occurs, and no user prompt is needed.** The "Codex unavailable" path involves an
   actual attempted (and failed) dispatch, is discovered live during Phase 1/2, and triggers a mandatory
   `AskUserQuestion` decision point (proceed single-model or stop) per resolver step 3. The
   "zero Codex-eligible paths" path is resolved at **Preflight step 2**, purely from the diff's own
   file list, with no dispatch attempt and (per the skill's wording) no indication that an
   `AskUserQuestion` gate is required here — the skill just "enters single-model mode now." The skill's
   own stated rationale for keeping these reasons distinct is that conflating them "produces a misleading
   'Codex unavailable' framing when Codex simply had nothing eligible to review" — i.e., "Codex
   unavailable" would wrongly imply Codex itself (the tool/backend) was down or inaccessible, when in
   fact the diff simply gave it nothing in-scope to review.

## Section/step citations summary

- **Preflight step 2** (lines ~117–124): the empty-eligible-list rule itself, the rationale (`bridge-
  invoke.mjs` rejects empty `--target-paths`), the instruction to skip Phase 1's Codex pass and all of
  Phase 2, and the exact `inspection_limits` wording ("zero Codex-eligible paths in this diff" vs. "Codex
  unavailable").
- **Codex dispatch resolver, step 3**: defines the actual "Codex unavailable" case (typed dispatch
  failures / `codex-kit` or `codex` CLI missing) and its `AskUserQuestion` single-model-or-stop gate —
  the case this scenario is explicitly distinguished from.
- **Phase 2** opening line: confirms Phase 2 is skipped entirely in single-model mode.
- **Phase 3**, "Single-model mode" note: confirms synthesis from Claude's Phase 1 findings alone, the
  Medium-confidence cap, and recording `single_model_mode: true` plus the reason in `inspection_limits`.
- **Testing & Validation, scenario 9**: the concrete worked example matching this exact question ("Every
  changed file is a deletion or an invalid-charset path... single-model mode is entered proactively,
  before any dispatch attempt, with `inspection_limits` recording 'zero Codex-eligible paths' rather than
  'Codex unavailable'").
- **Quality gates** checklist: "A dispatch is never attempted when Preflight step 2's eligible-files list
  is empty — single-model mode is entered proactively instead."
