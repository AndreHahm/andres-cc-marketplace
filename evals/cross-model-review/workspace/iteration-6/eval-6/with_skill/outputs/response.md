# Answer

**The finding is dropped.** It never reaches Codex's Phase 2 challenge payload, even though its
primary `location` field is itself eligible (an in-scope, non-excluded file). The exclusion is
triggered by the second, deleted-and-excluded file cited in its `components` array.

## The exact filtering rule

`SKILL.md`'s Phase 2 section ("Phase 2 — Cross-examine (challenger persona)") states this rule
explicitly, right before the instructions for assembling `challenger_instructions_for_codex.md`:

> "**Drop any Claude Phase 1 finding whose `location`, or any path in its `components` array, falls
> on a path Preflight step 2 excluded from `--target-paths`— before assembling this file, never pass
> it to Codex's challenger pass.**"

So the filter is not "check `location` only" — it is "check `location` **and every entry in
`components`**." A finding fails this filter (and is dropped) if *either*:

1. its `location` resolves to a path excluded from `--target-paths`, **or**
2. any path listed in its `components` array resolves to a path excluded from `--target-paths`.

In the scenario posed — eligible `location`, but a `components` entry pointing at a file the diff
deleted and that Preflight step 2 excluded from `--target-paths` — condition (2) applies. The
finding is therefore filtered out during the step that builds
`$RUN/challenger_instructions_for_codex.md`:

> "`Read` `$RUN/review.md`, `$RUN/refute.md`, and `$RUN/claude_fresh_eyes.json`; drop any finding
> with an excluded `location` or excluded `components` entry (per the paragraph above) from the last
> of these, then in what remains, replace every closing-tag-shaped substring..."

This is a concrete, mechanical step in the file-assembly pipeline (`SKILL.md`, Phase 2), not a
vague guideline — the dropped finding simply does not appear in the `<other_reviewer_findings>`
block embedded in the instruction file Codex receives, and consequently Codex's Phase 2 pass never
sees it and never produces a confirm/refute/novel classification for it.

## Where the finding ends up instead

It is not discarded from the run entirely — it survives into the final synthesized report, but as
a single-sided, Claude-only finding. Phase 3 ("Phase 3 — Synthesize and report") assigns it to the
Medium confidence tier:

> "**Medium** — ... a Claude Phase 1 finding dropped from the Codex challenge because its `location`
> was excluded from `--target-paths` (see Phase 2's Codex pass) — structurally single-sided, never
> cross-examined, not a gap to flag..."

(Phase 3's own wording here says "`location`" as shorthand for the drop reason, but it explicitly
points back to "Phase 2's Codex pass" for the operative definition — which, as quoted above,
extends to *any* `components` entry, not just `location`. The scenario in the question is exactly
the case Phase 2 defines and Phase 3 categorizes.) The finding is also explicitly noted as an
`inspection_limits` item per Phase 3's closing instructions ("any Claude finding dropped from the
Codex challenge for that same reason").

## Why checking `location` alone would not be enough

`SKILL.md` gives the precise mechanical reason, in the same Phase 2 paragraph, tied to how
`codex-review-bridge` validates a returned envelope:

> "The bridge's `semanticallyValidate` rejects the **entire returned envelope**, not just one
> finding, the moment any finding's `location` *or any of its `components` entries* resolves
> outside `--target-paths` — filtering on `location` alone still lets a finding whose primary
> location is eligible but whose `components` array cites an excluded file through, and Codex
> classifying it necessarily produces a classification entry preserving that same `components`
> relationship (per the 'every given finding must be explicitly addressed' rule below), which fails
> that check and loses every other finding in the same envelope along with it."

Breaking that down:

1. **The downstream validator checks both fields.** `codex-review-bridge`'s `semanticallyValidate`
   (referenced in Preflight step 2 and again here) rejects a whole envelope if *any* finding's
   `location` **or** any `components` entry falls outside `--target-paths`. A filter that only
   checked `location` would be blind to exactly the failure mode the validator actually enforces.

2. **Codex is contractually bound to preserve the `components` relationship.** Phase 2 requires
   that "every given finding must be explicitly addressed, none silently skipped" (challenger
   persona rule). If the excluded-`components` finding were let through to Codex, Codex's resulting
   classification entry (confirm/refute/novel) would necessarily carry forward the same
   `components` reference — Codex isn't free to drop or rewrite it, only to classify it.

3. **That reproduces the excluded path inside the *returned* envelope**, which then fails
   `semanticallyValidate` at the point Codex's response comes back — and per point 1, that failure
   rejects the **entire envelope**, not just the one offending finding. Every other, otherwise
   perfectly valid finding Codex classified in that same Phase 2 challenger response would be lost
   along with it.

So checking `location` alone is a necessary but insufficient proxy for "will this finding survive
the bridge's validation" — the actual validation surface is the union of `location` and every
`components` path, and the skill's filter is written to match that surface exactly, precisely to
avoid the catastrophic side effect of one contaminated finding taking down an entire batch of
otherwise-valid Phase 2 results.

## Section citations summary

- Phase 2, "Drop any Claude Phase 1 finding whose `location`, or any path in its `components`
  array..." paragraph — defines the filtering rule and its rationale.
- Phase 2, file-assembly step ("`Read` `$RUN/review.md`, `$RUN/refute.md`, and
  `$RUN/claude_fresh_eyes.json`; drop any finding with an excluded `location` or excluded
  `components` entry...") — where the drop is mechanically executed before Codex ever sees the
  payload.
- Phase 3, Medium confidence tier bullet — where the dropped finding lands in the final report
  (single-sided, Medium confidence, flagged in `inspection_limits`).
- Preflight step 2 — establishes `--target-paths` eligibility and why a deleted file is excluded
  from it in the first place (fails the existence check `codex-windows-guardrails` requires, or
  more generally is excluded from the eligible-files computation).
