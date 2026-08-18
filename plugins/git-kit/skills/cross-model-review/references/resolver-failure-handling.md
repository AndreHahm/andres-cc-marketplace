# Resolver step 3: full single-model mode vs. partial Phase 2 failure

Extracted from the "Codex dispatch resolver" section's step 3 per plugin-rulebook's R13 (SKILL.md
grew past the 500-line Critical threshold). SKILL.md keeps the two-case split inline; this file holds
the fuller reasoning for each.

- **On Phase 1's Codex call failing** (nothing from Codex has succeeded yet): "single-model" means
  the full single-model path — skip every remaining Codex dispatch (Phase 1's Codex pass, already
  failed, and all of Phase 2 entirely) and follow the single-model paths called out in Phase 2 and
  Phase 3.
- **On Phase 2's Codex call failing** (Phase 1's Codex dispatch already succeeded —
  `$RUN/codex_fresh_eyes.json` exists, and Claude's own native Phase 2 pass may have too): this is a
  **partial failure, not full single-model mode — do not discard the already-completed envelopes.**
  "Single-model" here only means Codex's Phase 2 challenge didn't happen; Phase 3 still merges
  Codex's Phase 1 findings and Claude's completed Phase 2 pass (if it finished) as usual, and records
  in `inspection_limits` that Codex's own Phase 2 challenge of Claude's findings didn't complete —
  any Claude Phase 1 finding left unaddressed by that missing pass falls to the existing Medium tier
  (same as the "challenger prompt's rule was violated" case), never silently dropped and never
  treated as if Codex had never run at all.

The distinction matters because the two cases have completely different amounts of real work to
preserve: treating a Phase 2-only failure as if it were a Phase 1 failure would silently discard a
successful Codex Phase 1 dispatch and Claude's own completed Phase 2 pass, understating the review's
actual coverage in the final report.
