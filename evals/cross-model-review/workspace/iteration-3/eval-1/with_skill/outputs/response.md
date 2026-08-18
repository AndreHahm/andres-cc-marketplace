# Cross-Model Review: Single-Model Fallback Walkthrough (Codex Unavailable, `codex-kit` Not Installed)

## Setup: how we got to the `AskUserQuestion` in the first place

Before Phase 1 even starts, the **Codex dispatch resolver** section governs every Codex call. Because
`codex-kit` "is not installed at all," attempting Step 1 (`codex-review-bridge`'s `bridge-invoke.mjs`)
fails at the OS level — `node` can't find the script — before either dispatch script ever produces its
own typed-failure JSON. The skill explicitly calls this out as "the same `cli_unavailable` fallback case
`codex-backend.md` names explicitly," and routes it straight to **resolver step 3** (it is *not*
`isolation_profile_unavailable`, so Step 2/`codex-windows-guardrails` is never attempted):

> "On any other typed failure from either path — including `guardrails_disabled`, the `codex` CLI itself
> missing, and **`codex-kit` not being installed at all**... tell the user Codex is unavailable for this
> run and ask via `AskUserQuestion` whether to proceed single-model (Claude only — loses the cross-vendor
> benefit, findings default to Medium confidence since nothing cross-examines them) or stop. On
> single-model: skip every remaining Codex dispatch for the rest of this run — Phase 1's Codex pass, and
> Phase 2 entirely — and follow the single-model paths called out in Phase 2 and Phase 3 below."
> (Codex dispatch resolver, step 3)

The user picking "proceed single-model" at that prompt is exactly the scenario this answer walks
forward from. Two consequences are already locked in at this point, per that same paragraph: (a) Phase
1's Codex pass and all of Phase 2 are skipped outright, and (b) every surviving finding is pre-committed
to a **Medium** confidence ceiling, because nothing will cross-examine it.

(Side note on ordering: the **First-Send Confirmation** — "mandatory, once per session, before the
*first* real Codex dispatch attempted" — gates the act of *attempting* a Codex dispatch, not the
fallback question itself. In this scenario the Step 1 attempt is the first real dispatch attempt, so
that confirmation would have fired immediately before the resolver's Step 1 attempt, disclosing what
would happen if Codex were reachable; it does not re-fire again since no further Codex dispatch is
ever attempted in single-model mode.)

## Phase 1 — Independent review (fresh-eyes persona)

**What still runs:** Claude's native pass runs exactly as normal. Per the skill: "**Claude's native
pass:** review as yourself, following `$RUN/review.md`... Hold the findings in that envelope shape;
write to `$RUN/claude_fresh_eyes.json` (`dispatch.reviewer: "claude-fresh-eyes"`, `dispatch.backend:
"claude"`)." Nothing about single-model mode changes this — Claude still uses `Grep`/`Glob` to trace
call sites, still reasons over `"${DIFF[@]}"` from Preflight, and still emits the same envelope shape
documented in `codex-review-bridge`'s `envelope-schema.md`.

**What gets skipped:** Codex's pass. The Phase 1 heading for Codex's pass says explicitly: "**Codex's
pass**, via the resolver above (**skip entirely in single-model mode — see resolver step 3**)." So the
steps that would normally follow — reading `$RUN/review.md`, appending `Review the diff:
$CODEX_DIFF_STR`, writing `$RUN/review_for_codex.md`, and dispatching with
`--reviewer-type fresh-eyes-reviewer` — never execute. `$RUN/codex_fresh_eyes.json` is simply never
created.

**End state of Phase 1:** only `$RUN/claude_fresh_eyes.json` exists; no Codex envelope of any kind.

## Phase 2 — Cross-examine (challenger persona)

**What gets skipped:** the entire phase. The skill states this as the very first line of Phase 2:

> "**Single-model mode (Codex unavailable, user chose to proceed — see resolver step 3): skip this
> phase entirely and go straight to Phase 3.** There is no second reviewer's findings to cross-examine,
> and Claude cross-examining its own Phase 1 output would reintroduce the self-ratification failure mode
> this skill exists to avoid."

So none of the Phase 2 machinery runs: no `refute.md` pass for Claude (`$RUN/claude_challenger.json` is
never produced), and none of the Codex-challenger assembly work — the "outside `--target-paths`"
instruction-file assembly, the closing-tag neutralization of the other model's findings
(`neutralizeClosingTags`-equivalent step), or the `challenger_instructions_for_codex.md` dispatch —
happens at all. This is a deliberate design choice stated directly in the phase text, not an accidental
gap: having Claude "confirm/refute" its own Phase 1 findings would be exactly the self-ratification
failure mode the skill's own opening section says cross-model review exists to prevent ("This kills the
two failure modes of solo LLM review: self-ratification (a model won't critique its own work) and
confident false positives").

**What still runs:** nothing — the whole phase is bypassed, and the flow moves straight to Phase 3.

## Phase 3 — Synthesize and report (no auto-fix)

Phase 3 opens with its own explicit single-model branch:

> "**Single-model mode (Phase 2 was skipped — resolver step 3):** synthesize from Claude's Phase 1
> findings alone (`$RUN/claude_fresh_eyes.json`). Every finding is capped at Medium confidence (see the
> Medium tier below) since nothing cross-examined it. Record `single_model_mode: true` and the reason
> (Codex unavailable) in `inspection_limits`, then skip straight to 'Rank by `severity × confidence`'
> below — there is no second envelope to merge."

Concretely:

- **Source of findings:** `$RUN/claude_fresh_eyes.json` only — no merge/dedupe step runs, because
  there's no second envelope to merge against (the normal "Merge, dedupe... assign confidence" step
  that follows, with its High/Medium/Low tiers based on Phase-1/Phase-2 agreement, is explicitly
  skipped over per the sentence above).
- **Confidence level:** every single finding is capped at **Medium**, regardless of how strong the
  finding looks to Claude on its own. This is not the normal Medium tier definition (which is about
  partial Phase-2 corroboration) — it's a blanket ceiling applied because "nothing cross-examined it."
  Nothing can reach High in single-model mode, since High requires either two independent Phase-1
  hits or an explicit Phase-2 confirmation, and neither is possible here.
- **Disclosure:** `inspection_limits` must record `single_model_mode: true` and the reason (Codex
  unavailable), per the instruction above. This sits alongside any other `inspection_limits` entries
  that may have accumulated in Preflight (e.g. excluded target paths, unverified `review.md`/
  `refute.md`, or an unverified Codex dispatcher) — the skill's closing synthesis paragraph groups
  these together: "Note any `inspection_limits` from either side, including... Preflight step 5's
  unverified-instructions fallback... and Preflight step 6's dispatcher-not-verified disclosure."
- **Reporting mechanics that still apply unchanged:** the skill still ranks by `severity × confidence`
  and presents the compact table (`severity | confidence | location | claim | found-by /
  confirmed-or-refuted-by`), expanding High-confidence items with `evidence`/`fix` — though in
  single-model mode no item can actually be High, so in practice every row tops out at Medium. The
  "never silently drop a `severity: critical` finding regardless of confidence tier" rule still holds
  even here — a critical finding found only by Claude, capped at Medium confidence, is still surfaced,
  not dropped. The report still ends by asking the user which findings, if any, to fix, and the skill
  still does not edit any code until that pick is made — this final gate is unaffected by single-model
  mode.
- **`$RUN` cleanup:** unchanged — the skill still does not delete `$RUN` afterward, so
  `claude_fresh_eyes.json` (the sole envelope produced this run) persists under the OS temp directory
  until manually cleaned up, same as the multi-model case.

This exact flow is also independently codified in the skill's own "Testing & Validation" section as
scenario 2 ("`codex-kit` is not installed at all, or the `codex` CLI itself is missing"): "On 'proceed
single-model': Phase 1's Codex pass and all of Phase 2 are skipped, Phase 3 synthesizes from Claude's
Phase 1 findings alone, and every finding is capped at Medium confidence in the final report" — and as
a Quality Gate: "Single-model mode always skips Phase 1's Codex pass and all of Phase 2 — never
dispatches Codex after the user chose to proceed single-model."

## Summary table

| Phase | Claude native | Codex | Confidence outcome |
|---|---|---|---|
| Phase 1 | Runs normally → `$RUN/claude_fresh_eyes.json` | Skipped entirely (resolver step 3 fallback) | n/a |
| Phase 2 | Skipped entirely (avoids self-ratification) | Skipped entirely | n/a |
| Phase 3 | Synthesizes from Claude's Phase 1 findings alone | No envelope to merge | Every finding capped at **Medium**; `single_model_mode: true` + reason recorded in `inspection_limits`; critical findings still never dropped; still ends on the user pick before any edit |

## Key citations

- Resolver step 3 (Codex dispatch resolver section) — triggers the fallback question and states what
  gets skipped and the Medium-confidence default.
- Phase 1, "Codex's pass" line — "skip entirely in single-model mode — see resolver step 3."
- Phase 2 opening line — "skip this phase entirely and go straight to Phase 3," with the
  self-ratification rationale.
- Phase 3 opening line — synthesize from Claude's Phase 1 findings alone, Medium confidence cap,
  `single_model_mode: true` in `inspection_limits`, skip straight to ranking.
- Testing & Validation, scenario 2 and the matching Quality Gate bullet — restates the same behavior as
  an explicit test case.
