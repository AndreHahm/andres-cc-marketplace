# Recommendations Plan

**Requested scope:** The source report at `evals/generating-analysis-recommendations/workspace/iteration-1/eval-1/source-report.md` (Findings A-D) named as input for expansion into a WHAT/WHY/HOW plan.
**Inspected scope:** Same as requested — the source report was read in full; no additional evidence-gathering was performed beyond it (this skill expands existing findings rather than independently re-verifying their underlying evidence).
**Unavailable evidence:** none
**Limitations:** All four recommendations below carry `Evidence origin: inherited` — this run did not independently re-verify the underlying evidence (the `Glob`/`Grep` counts, incident-log references, etc.) behind any finding, only expanded what the source report already asserted. The source report predates `report-evidence-convention.md` and carries no per-finding `Evidence origin`/`Coverage`/`Confidence`/`Evidence source` metadata of its own (only the report-level Coverage Preamble at its top) — per that convention's Backward Compatibility section, the absence of finding-level metadata in the source is itself treated as `Coverage: partial` / `Confidence: low` for whatever is inherited from it, rather than assumed `complete`/`high`.

**Derivation note (deviation, disclosed per this skill's own instructions):** The supplied report path (`evals/.../eval-1/source-report.md`) does not follow analysis-kit's normal `.claude/output/<skill-name>/<scope-slug>-<timestamp>.md` layout — it is an eval fixture with no skill-name parent directory and no `<scope-slug>-<timestamp>` filename shape. Two derivations in this skill's instructions assume that normal layout and needed a judgment call here:
- **`<id-prefix>`** (Phase 3): the literal instruction is "the report's own filename with `.md` stripped, prefixed with the source skill's own directory name." Since this path has no skill-name directory to prefix with (its immediate parent is `eval-1`, not a skill), `<id-prefix>` is the filename stem alone: `source-report`.
- **`<scope-slug>`** (Persist step): the literal instruction is "derive from the source report's own scope-slug." Since the filename carries no scope-slug, this run derived one from the report's own stated `Requested scope` line ("billing-kit repository, full component sweep") → `billing-kit-full-sweep`.

---

## Strategic Investment

### `source-report-rec-01`

**WHAT:** Add input validation to `parse_amount_field()` in `scripts/parse_invoice.py`, define an explicit error-recovery strategy (skip / abort / quarantine the malformed line) for invalid input, and update all 6 call sites (12 call sites total) to handle the new validation-failure return value consistently.

**WHY:** `parse_amount_field()` is called from 12 different call sites across 6 files with no input validation before its value is passed to `float()`. A malformed invoice line (a stray currency symbol or thousands separator) raises an unhandled `ValueError` that crashes the entire batch job partway through, discarding already-processed invoices in that batch — this has caused 3 separate production incidents in the last quarter per the incident log (Finding B).

**HOW:** Finding B's own evidence states there is no existing input-validation pattern elsewhere in this codebase to follow, so the approach needs to be designed from scratch: (1) decide the error-recovery strategy (skip/abort/quarantine) first, since it fixes the new return-value contract every one of the 6 call sites must then handle; (2) implement the validation inside `parse_amount_field()`, guarding against the malformed-input shapes already observed before the `float()` call; (3) update each of the 6 call sites to handle the new failure path consistently, rather than only the site where an incident happened to occur.

Complexity: **High** — touches 6 files at 12 call sites, and no existing validation pattern exists in this codebase to follow (rubric: "requires new architecture... or has no existing pattern to follow").
Risk: **High** — `parse_amount_field()` is a widely-used shared component; changing its failure behavior affects every caller (rubric: "changes behavior in a widely-used shared component").
Benefit: **High** — resolves a finding with 3 documented production incidents and a batch-job-crashing failure mode (rubric: "prevents a category of failure... outsized downstream effect").

<!-- finding:start -->
Priority bucket: Strategic Investment — High complexity/risk, High benefit; plan for it deliberately (decide the error-recovery strategy before touching any call site) rather than folding it into an unrelated pass.

Evidence origin: inherited
Coverage: partial
Confidence: low
Evidence source: evals/generating-analysis-recommendations/workspace/iteration-1/eval-1/source-report.md (Finding B)
<!-- finding:end -->

---

## Nice-to-Have

### `source-report-rec-02`

**WHAT:** Update the skill count in README.md's opening summary from "12 skills" to "15 skills."

**WHY:** README.md states "12 skills" in its opening summary, but the plugin currently ships 15 skills, verified via `Glob('skills/*/SKILL.md')` (15 matches) — no other content in README.md references the old count (Finding A).

**HOW:** Single-line text edit to the count in the opening paragraph; no other file changes needed, per Finding A's own note that nothing else in README.md references the old count.

Complexity: **Low** — a single-file text edit (rubric: "a single-file text/config edit").
Risk: **Low** — additive/reversible, no behavior change (rubric: "no behavior change to existing functionality").
Benefit: **Low** — polish; doesn't change session outcomes (rubric: "polish; doesn't change session outcomes").

<!-- finding:start -->
Priority bucket: Nice-to-Have — Low complexity/risk, Low benefit; fine to defer.

Evidence origin: inherited
Coverage: partial
Confidence: low
Evidence source: evals/generating-analysis-recommendations/workspace/iteration-1/eval-1/source-report.md (Finding A)
<!-- finding:end -->

### `source-report-rec-03`

**WHAT:** Normalize log-message capitalization in `scripts/parse_invoice.py` to one consistent style across its log statements.

**WHY:** Log messages in `scripts/parse_invoice.py` mix "Processing invoice..." (capitalized) with "skipping malformed line" (lowercase) inconsistently across different log statements in the same file — purely cosmetic, doesn't affect log parseability or any downstream tooling that consumes these logs (Finding C).

**HOW:** Pick whichever capitalization convention is already dominant in the file, then edit the minority-style log statements to match it. **Dependency:** land this after `source-report-rec-01` (Finding B) — that change adds new log statements for the skip/quarantine failure path in this same file, and normalizing capitalization now would otherwise need a second pass once those new statements land.

Complexity: **Low** — a small, self-contained text change to existing log statements, no new abstraction.
Risk: **Low** — cosmetic only; Finding C itself states it doesn't affect log parseability or downstream tooling.
Benefit: **Low** — purely cosmetic (rubric: "polish; doesn't change session outcomes").

<!-- finding:start -->
Priority bucket: Nice-to-Have — Low complexity/risk, Low benefit; fine to defer.

Evidence origin: inherited
Coverage: partial
Confidence: low
Evidence source: evals/generating-analysis-recommendations/workspace/iteration-1/eval-1/source-report.md (Finding C)
<!-- finding:end -->

---

## Reconsider

### `source-report-rec-04`

**WHAT:** Reconsider — do **not** undertake a full rewrite of the persistence layer. The evidence supports only a narrow fix: change the flat-file JSON store's write path to write to a temp file, then atomically rename it over the target file.

**WHY:** Finding D's own evidence shows a single edge case — the flat-file JSON store loses a write if the process is killed mid-write — discovered from one specific incident (a forced VM restart during a write corrupting one record), fully explained by this one narrow race condition, with no other correctness issue found in the flat-file store during that analysis. A full rewrite would be high complexity (new architecture, or a pattern that would need inventing) and high risk (the persistence layer is a widely-used shared component) for a benefit the evidence caps at moderate — one already-fully-understood gap, already closable by a five-line fix. The risk/complexity of a full rewrite doesn't clearly justify itself against that narrow a benefit.

**HOW:** If any change is made at all, use the write-then-atomic-rename pattern Finding D itself points to as already established in this codebase (`scripts/persist_report.py`'s own write-then-rename logic) — described in the source finding as a five-line fix that closes the identified gap completely, without the architectural risk a full rewrite would introduce. **No dependency** on the other three entries — different file (persistence layer, not `scripts/parse_invoice.py` or README.md).

Complexity (of the full-rewrite framing being reconsidered): **High** — rewriting the persistence layer is new/large-scope work with no narrower existing pattern needed for that scope.
Risk (of the full-rewrite framing): **High** — the persistence layer is a widely-used shared component; a rewrite changes its behavior broadly.
Benefit: **Medium** — Finding D's own evidence caps this at "degrades quality/reliability if left unfixed, fix improves a specific dimension" (data durability on crash) — not "prevents a category of failure" broadly, since the finding states no other correctness issue was found and the gap is fully explained by one narrow race condition.

<!-- finding:start -->
Priority bucket: Reconsider — High risk/complexity (of a full rewrite) with benefit that doesn't clearly justify it, per Finding D's own evidence. Named explicitly rather than silently omitted, per the rubric's own guidance that a "don't do this" verdict is itself useful information. The narrow atomic-write fix above is the justified alternative, if any change is made at all.

Evidence origin: inherited
Coverage: partial
Confidence: low
Evidence source: evals/generating-analysis-recommendations/workspace/iteration-1/eval-1/source-report.md (Finding D)
<!-- finding:end -->

---

## Suggested Order of Operations

1. **`source-report-rec-02`** (Finding A, README count) — independent, trivial, no dependency on anything else.
2. **`source-report-rec-04`** (Finding D, persistence layer) — independent (different file: the persistence layer, not `scripts/parse_invoice.py` or README.md); if the narrow atomic-write fix is approved, it can land any time.
3. **`source-report-rec-01`** (Finding B, invoice-parsing validation) — plan deliberately: decide the error-recovery strategy first, since it's a precondition for touching any of the 6 call sites in `scripts/parse_invoice.py`.
4. **`source-report-rec-03`** (Finding C, log capitalization) — land **after** `source-report-rec-01`, since both touch `scripts/parse_invoice.py`; normalizing capitalization before Finding B's new skip/quarantine log statements exist would mean re-normalizing again once those statements land.
