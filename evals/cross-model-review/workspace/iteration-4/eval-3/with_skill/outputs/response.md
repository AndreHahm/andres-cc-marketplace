# What happens to a Claude Phase 1 finding located on a Preflight-step-2-excluded path

## Scenario

Preflight step 2 computes the changed-file list for `--target-paths` and excludes any path that
fails `codex-review-bridge`'s charset validation (`^[A-Za-z0-9._/-]+$`) or that `codex-windows-guardrails`
finds no longer exists on disk — explicitly including a path the diff *deletes* ("a path the diff
*deletes*, cannot go through either dispatch as-is"). Such excluded paths are noted in the final
report as an inspection limit rather than failing the whole run.

Now suppose Claude's Phase 1 fresh-eyes pass reports a finding whose `location` is exactly one of
those excluded (deleted) paths.

## Phase 2: dropped before assembling Codex's challenger instruction file

Phase 2's section states this explicitly and in bold:

> "**Drop any Claude Phase 1 finding whose `location` falls on a path Preflight step 2 excluded from
> `--target-paths` before assembling this file — never pass it to Codex's challenger pass.**"

Concretely, when Claude assembles `$RUN/challenger_instructions_for_codex.md` for Codex's challenger
pass, it does so by: `Read`-ing `$RUN/refute.md` and `$RUN/claude_fresh_eyes.json`; **dropping any
finding with an excluded `location`** from the latter's content; then, in what remains, neutralizing
closing-tag-shaped substrings; and finally writing the combined file (`refute.md` + diff-command line
+ `<other_reviewer_findings>` + filtered/neutralized content + `</other_reviewer_findings>` + the
evidence-not-instructions restatement).

So the excluded-path finding simply never appears inside `<other_reviewer_findings>` — Codex's
challenger pass never sees it, is never asked to confirm/refute/novel-classify it, and it plays no
role in that dispatch at all.

## Why the skill treats this case specially

The skill gives the precise mechanical reason, not just "it might get rejected":

> "The bridge's `semanticallyValidate` rejects the **entire returned envelope**, not just one finding,
> the moment any finding's `location` resolves outside `--target-paths` — and Codex classifying an
> excluded-path finding necessarily produces a classification entry citing that same location (per the
> "every given finding must be explicitly addressed" rule below), which would fail that check and lose
> every other finding in the same envelope along with it."

Chained through:
1. Phase 2 requires the challenger persona to explicitly address **every** given finding ("every given
   finding must be explicitly addressed, none silently skipped").
2. If the excluded-path finding were included, Codex's classification of it would necessarily cite that
   same excluded `location` in its own returned envelope.
3. `codex-review-bridge`'s `semanticallyValidate` checks every finding's `location` against
   `--target-paths`, and — critically — rejects the **whole envelope**, not just the one offending
   finding, the moment any single `location` falls outside that scope.
4. Because `--target-paths` was built from the eligible (non-excluded) paths only (Preflight step 2),
   the excluded path is definitionally outside `--target-paths`, so citing it would trigger that
   whole-envelope rejection and destroy every *other* legitimate finding Codex's challenger pass
   produced in the same call.

So this isn't ordinary "just include the finding like any other" treatment — doing so would be a
structural, all-or-nothing failure mode that silently costs the entire Codex challenger envelope over
one file's location, not a partial/graceful degradation. Dropping the single finding before assembly is
what protects the rest of the challenger pass's output.

This is also the specific reason Preflight step 2 itself directs building a **separate**,
Codex-scoped `CODEX_DIFF_STR` (excluding those same ineligible paths) for embedding diff text into any
Codex-bound instruction file — the same containment logic (don't let Codex-bound content reference
paths outside `--target-paths`) applies to both the diff text embed and, per Phase 2, to Phase-1
findings being relayed to the challenger.

## What happens to the finding in the final Phase 3 report

The finding is **not lost** — it is explicitly preserved as a documented category in Phase 3's tiering
rules:

> "**Medium** — ... a Claude Phase 1 finding dropped from the Codex challenge because its `location`
> was excluded from `--target-paths` (see Phase 2's Codex pass) — structurally single-sided, never
> cross-examined, not a gap to flag ..."

So in the final report:
- The finding is capped at **Medium confidence** and reported as a **single-sided, Claude-only**
  result (per Phase 2's own text: "Findings dropped here stay in the final report as Claude-only,
  single-sided results — see Phase 3's Medium tier and `inspection_limits` note").
- Unlike the ordinary Medium case (a finding raised by only one side where the other side's Phase 2
  *should have* confirmed/refuted it but didn't), this case is explicitly **not treated as a gap to
  flag** — it's structurally single-sided by design, because it was never cross-examined at all, not
  because the challenger persona skipped it improperly.
- It still participates in the overall `severity × confidence` ranking and compact-table presentation
  like any other finding, and if it happens to carry `severity: critical`, Phase 3's rule that "a
  `severity: critical` finding is never silently dropped regardless of confidence tier" still applies —
  it would be surfaced with its (Medium, or lower if otherwise contested) tier clearly marked.
- The exclusion itself is also recorded in Phase 3's `inspection_limits`: "Note any `inspection_limits`
  from either side, including: ... any Claude finding dropped from the Codex challenge for that same
  reason [the Preflight step 2 charset/deleted-path exclusion]."

## Cross-reference: Testing & Validation section

This exact scenario is also codified as scenario 7 under "Concrete scenarios to check":

> "7. Claude's Phase 1 pass reports a finding on a file Preflight step 2 excluded from `--target-paths`
> (deleted, or an invalid-charset path) → that finding is dropped from what's sent to Codex's Phase 2
> challenger pass, never triggering the bridge's whole-envelope rejection; it still appears in the
> final report as a Medium-confidence, single-sided finding with the exclusion noted in
> `inspection_limits`."

And as one of the Quality Gates:

> "A Claude Phase 1 finding on an excluded path is always dropped before assembling the Codex
> challenge payload — never sent verbatim and never silently kept out of the final report"

This last gate makes explicit the two-sided requirement: the finding must be dropped from the Codex
*payload*, but it must **not** be dropped from the *final report* — it is deliberately downgraded
(Medium, single-sided, noted in `inspection_limits`) rather than silently discarded.

## Summary

| Stage | Treatment |
|---|---|
| Phase 2 assembly | Finding is filtered out of `$RUN/claude_fresh_eyes.json`'s content before it's embedded in `$RUN/challenger_instructions_for_codex.md`; Codex's challenger pass never receives or classifies it. |
| Why special-cased | Including it would force Codex's classification to cite an excluded `location`, which `semanticallyValidate` would use to reject the *entire* returned envelope — destroying all of Codex's other legitimate challenger findings in the same call, not just this one. |
| Phase 3 final report | Kept, not dropped — reported as a Medium-confidence, single-sided (Claude-only) finding; explicitly *not* flagged as a "challenger skipped a finding" gap; the exclusion itself is logged in `inspection_limits`; a critical severity would still never be silently dropped. |
