# Required `dispatch.reviewer` value for Codex's Phase 2 (challenger) dispatch

## The required value

Codex's returned envelope must set `dispatch.reviewer` to exactly **`challenger-reviewer`** — the
same string passed as the `--reviewer-type` flag when Codex is dispatched for Phase 2.

**Evidence from SKILL.md (Phase 2 — Cross-examine):**

The actual dispatch command for Codex's Phase 2 pass is:

> "Dispatch the same way as Phase 1 with `--reviewer-type challenger-reviewer --instruction-file
> "$RUN/challenger_instructions_for_codex.md" --dispatch-id
> "cross-model-review-$(date +%s)-challenger-codex"`. Save to `$RUN/codex_challenger.json`."
> (SKILL.md, Phase 2, lines 366–368)

So the `--reviewer-type` argument sent to the dispatcher (`bridge-invoke.mjs` in the sandboxed path,
or `guarded-dispatch.mjs` in the Windows fallback path — see the "Codex dispatch resolver" section,
lines 193–213) is literally the string `challenger-reviewer`.

SKILL.md states the matching requirement explicitly in the same Phase 2 section, distinguishing
Claude's own (looser) convention from Codex's (strict) one:

> "This is still just a findings envelope (same shape as Phase 1; Claude's own native write may use a
> descriptive `dispatch.reviewer` like `"claude-challenger"`, but Codex's `dispatch.reviewer` must
> exactly match the `--reviewer-type` it was dispatched with — see `refute.md`'s Output section)"
> (SKILL.md, Phase 2, lines 310–312)

## Why it must be exactly that string — the `refute.md` side of the contract

`refute.md`'s Output section is the authoritative statement of this requirement, since it's the prompt
Codex actually receives and follows when acting as the challenger persona:

> "Same envelope shape and field semantics as `prompts/review.md`'s Output section
> (`plugins/codex-kit/skills/codex-review-bridge/references/envelope-schema.md` is the authoritative
> contract). **`dispatch.reviewer` must be exactly the reviewer-type value this dispatch was invoked
> with — the same string shown in this prompt's own `<dispatch reviewer="...">` tag — never a
> substituted or invented name.**"
> (refute.md, "Output" section, lines 63–66)

This confirms both the value (whatever `--reviewer-type` the dispatch actually used — here,
`challenger-reviewer`) and the mechanism by which Codex is expected to know it: the dispatcher embeds
that same value into the instruction content Codex receives, in a `<dispatch reviewer="...">` tag, so
Codex is meant to echo it back verbatim rather than choose or invent its own label.

## What happens if Codex uses a different value, e.g. `codex-challenger`

`refute.md` states the consequence directly, in the very next sentence after the requirement:

> "`codex-review-bridge`'s own semantic validation rejects the entire envelope on any mismatch between
> the dispatched `--reviewer-type` and the returned `dispatch.reviewer`, so echoing anything else (e.g.
> a hand-picked `codex-challenger` label) fails every Codex-side Phase 2 dispatch outright."
> (refute.md, "Output" section, lines 67–70)

So if Codex returned `dispatch.reviewer: "codex-challenger"` instead of `"challenger-reviewer"`:

1. **The dispatcher's semantic validation rejects the whole envelope**, not just the mismatched field —
   this is the same `semanticallyValidate` mechanism SKILL.md references elsewhere for a different
   check (dropping findings whose `location`/`components` fall outside `--target-paths` — Phase 2,
   lines 333–343), confirming this is a real, enforced validation step in the dispatch scripts
   (`bridge-invoke.mjs` / `guarded-dispatch.mjs`), not just a documentation convention.
2. **This is a typed failure from the dispatch**, which routes into the "Codex dispatch resolver"
   section's step 3 handling: "On any other typed failure from either path... tell the user Codex is
   unavailable for this run and ask via `AskUserQuestion` whether to proceed single-model... or stop."
   (SKILL.md, lines 225–231)
3. **Because this failure happens on Phase 2's Codex call** (not Phase 1's), the resolver explicitly
   calls out that this is a **partial failure, not full single-model mode**:

   > "If this failure happens on Phase 2's Codex call (Phase 1's Codex dispatch already succeeded —
   > `$RUN/codex_fresh_eyes.json` exists, and Claude's own native Phase 2 pass may have too), this is a
   > partial failure, not full single-model mode — do not discard the already-completed envelopes.
   > 'Single-model' here only means Codex's Phase 2 challenge didn't happen; Phase 3 still merges
   > Codex's Phase 1 findings and Claude's completed Phase 2 pass (if it finished) as usual, and
   > records in `inspection_limits` that Codex's own Phase 2 challenge of Claude's findings didn't
   > complete — any Claude Phase 1 finding left unaddressed by that missing pass falls to the existing
   > Medium tier (same as the 'challenger prompt's rule was violated' case), never silently dropped and
   > never treated as if Codex had never run at all."
   > (SKILL.md, Codex dispatch resolver, step 3, lines 235–243)

   This cross-references Phase 3's Medium confidence tier definition: "raised in Phase 1 by one side
   only, and the other's Phase 2 pass neither confirms nor refutes it (only possible if the challenger
   prompt's 'address every given finding' rule was violated — flag this as a gap, don't just drop the
   finding)" (SKILL.md, Phase 3, lines 399–402).

## Summary

- **Required value:** `challenger-reviewer` — must exactly match the `--reviewer-type` flag the Codex
  Phase 2 dispatch actually used (SKILL.md lines 366–368; refute.md lines 64–66).
- **A different value (e.g. `codex-challenger`)** causes `codex-review-bridge`'s semantic validation to
  reject the entire returned envelope outright (refute.md lines 67–70). That rejection is treated as a
  typed dispatch failure under the Codex dispatch resolver's step 3 (SKILL.md lines 225–231), and
  because it occurs at Phase 2 rather than Phase 1, it is handled as a **partial failure**: Codex's
  already-succeeded Phase 1 findings and Claude's own completed Phase 2 pass are preserved and still
  merged in Phase 3, the missing Codex Phase 2 challenge is recorded in `inspection_limits`, and any
  Claude Phase 1 finding left unaddressed by the missing challenge is capped at Medium confidence
  rather than silently dropped (SKILL.md lines 232–243, 399–402).
