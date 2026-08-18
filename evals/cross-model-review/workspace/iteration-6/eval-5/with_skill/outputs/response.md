# Does Phase 3 discard Codex's Phase 1 findings when Phase 2's Codex dispatch times out?

**No. Phase 3 preserves everything that already completed — including Codex's Phase 1
findings — and does *not* fall back to full Claude-only single-model synthesis.** This is
an explicitly named case in the skill, distinct from the "full single-model" path, with its
own handling.

## Where the skill says this

The governing text is the second sub-bullet under **Codex dispatch resolver**, step 3
("On any other typed failure from either path..."), lines 235-243:

> **If this failure happens on Phase 2's Codex call** (Phase 1's Codex dispatch already
> succeeded — `$RUN/codex_fresh_eyes.json` exists, and Claude's own native Phase 2 pass may
> have too), this is a **partial failure, not full single-model mode — do not discard the
> already-completed envelopes.** "Single-model" here only means Codex's Phase 2 challenge
> didn't happen; Phase 3 still merges Codex's Phase 1 findings and Claude's completed Phase 2
> pass (if it finished) as usual, and records in `inspection_limits` that Codex's own Phase 2
> challenge of Claude's findings didn't complete — any Claude Phase 1 finding left
> unaddressed by that missing pass falls to the existing Medium tier (same as the "challenger
> prompt's rule was violated" case), never silently dropped and never treated as if Codex had
> never run at all.

This is the resolver's own contrast to the *other* sub-bullet immediately above it (lines
232-234), which is the actual full-single-model trigger:

> **If this failure happens on Phase 1's Codex call** (nothing from Codex has succeeded yet),
> "single-model" means the full single-model path: skip every remaining Codex dispatch —
> Phase 1's Codex pass (already failed) and Phase 2 entirely — and follow the single-model
> paths called out in Phase 2 and Phase 3 below.

Since the scenario in the question has Phase 1's Codex dispatch *succeed* (`$RUN/codex_fresh_eyes.json` is written) and only Phase 2's Codex call fails, it matches the "Phase 2's Codex call" sub-bullet, not the "Phase 1's Codex call" one — so the full single-model path is explicitly not what applies here.

## What concretely still happens

Working through what "already-completed envelopes" means for this scenario, per Phase 1 and
Phase 2's own text:

- **Claude's native Phase 1 pass** (`$RUN/claude_fresh_eyes.json`) — unaffected, already ran
  (Phase 1, lines 279-283).
- **Codex's Phase 1 pass** (`$RUN/codex_fresh_eyes.json`) — succeeded per the question's
  premise, and per the resolver text above is explicitly *not* discarded.
- **Claude's native Phase 2 pass** (`$RUN/claude_challenger.json`) — this is Claude following
  `refute.md` against Codex's Phase 1 findings (Phase 2, lines 316-317: "Claude's native
  pass: follow `$RUN/refute.md`, given `$RUN/codex_fresh_eyes.json` as the findings to
  cross-examine"). Nothing in Phase 2 makes this pass depend on Codex's *own* Phase 2 call —
  it's an independent dispatch/execution. The resolver text explicitly allows for it having
  "may have too" completed, and Phase 3 uses it "if it finished."
- **Codex's Phase 2 pass** (`$RUN/codex_challenger.json`) — this is the one that timed out
  and is genuinely missing. This pass would have cross-examined *Claude's* Phase 1 findings
  (Phase 2, lines 319 onward: Codex's challenger pass reviews the other model's — i.e.
  Claude's — Phase 1 findings). Its absence is what's actually lost.

So Phase 3 is not entering the "Single-model mode (Phase 2 was skipped)" branch at all
(lines 372-379) — that branch is reserved for when Phase 2 is skipped *entirely* (Codex
unavailable at Phase 1, zero eligible paths, or user declined at First-Send Confirmation —
see line 299's cross-reference). Here Phase 2 ran, just not both halves of it. `single_model_mode: true` is not set for this run, since that flag is scoped to the full-Phase-2-skipped case only.

## Effect on confidence tiers (Phase 3 synthesis)

Because Phase 2 wasn't skipped, Phase 3 goes through its normal merge/dedupe/tier logic
(lines 380-408), not the single-model shortcut ("skip straight to 'Rank by `severity ×
confidence`'" — line 379, which only applies in the fully-skipped case):

- **Codex's Phase 1 findings that Claude's Phase 2 pass did cross-examine** (since Claude's
  native Phase 2 pass ran against `codex_fresh_eyes.json`) get normal treatment: confirmed →
  High (line 396-398, "one raised it in Phase 1 and the other's Phase 2 pass explicitly
  confirms it"); explicitly refuted → Low/contested (lines 393-395, "an explicit Phase 2
  refutation always wins"); or, if independently raised by both models' Phase 1 passes with
  no refutation, High regardless (line 396-397, first clause) — that clause doesn't require
  a Phase 2 pass on either side.
- **Claude's Phase 1 findings**, which needed Codex's *own* Phase 2 pass (the one that timed
  out) to be confirmed/refuted/marked novel, are left with nothing to cross-examine them from
  the Codex side. Per the resolver's own text, these fall to **Medium** — explicitly "the
  same as the 'challenger prompt's rule was violated' case," i.e. the Medium-tier bullet at
  lines 399-402: "raised in Phase 1 by one side only, and the other's Phase 2 pass neither
  confirms nor refutes it... flag this as a gap, don't just drop the finding."
- A `severity: critical` finding among these is still never silently dropped regardless of
  tier (line 407-408).

## Reporting

Per Phase 3's closing instructions (lines 412-416), the report's `inspection_limits` records
the specific reason given in the resolver text — "Codex's own Phase 2 challenge of Claude's
findings didn't complete" — rather than a generic "Codex unavailable" or an implication that
Codex never participated. The final ranked table (line 410) and High-confidence expansion
(line 411) proceed as normal, just with the affected Claude Phase 1 findings capped at
Medium and that gap flagged, not with Codex's Phase 1 contribution erased from the report.

## Summary

Phase 3 treats this as a **partial failure**, not a trigger for Claude-only single-model
synthesis. Codex's Phase 1 findings (`$RUN/codex_fresh_eyes.json`) are preserved and merged
normally, Claude's completed native Phase 2 pass (if it finished) still cross-examines them
normally, and only the specific cross-examination that never happened — Codex's Phase 2
challenge of Claude's Phase 1 findings — is missing, which caps the *affected* (Claude-only)
findings at Medium confidence and is disclosed in `inspection_limits`. Nothing is silently
dropped, and the run is not reported as if Codex never participated.
