## Summary
Consolidated tracking issue for the minor/advisory findings still open after `plugin-lifecycle-downstream`'s full QA pass on `analysis-kit` (2026-08-23/24, branch `fix/analysis-kit-downstream-qa`). All Critical and Major findings from that run's Phase 5 audit were fixed and independently re-verified (4 fix waves, commits `731363b`..`ae97a3a`); this issue tracks the remaining Minor/Informational items instead of leaving them scattered across per-agent report output with no durable record. The "~54" figure used during the run's own Phase 11 Grading summary was a rough rollup estimate, not a literal enumerated count — this issue lists the concrete items actually traceable back to a specific reviewer finding; some of Phase 5's ~54 aggregate informational notices (R13 size/R5 no-op advisories in particular) are large in count but trivial in substance, and are grouped rather than listed one-by-one below.

## Environment
- **Product/Service**: `analysis-kit` plugin, all 11 skills
- **Region/Version**: this repo, `plugin-lifecycle-downstream` run scoped to `fix/analysis-kit-downstream-qa`, evidence gathered across Phase 3 (Validate), Phase 5 (Audit), and Phase 6's re-verification rounds (Waves 1-4)

## Reproduction Steps
N/A — this is a documentation/consistency backlog, not a reproducible bug. Each item below names the file, the specific gap, and its origin.

## Remaining Items

**Rulebook advisories (grouped, non-blocking, R13/R5 only — ADVISORY tier, no REQUIRED violations anywhere in the plugin):**
- R13 (SUGGESTED, file-size tier): 9 of 11 skills' `SKILL.md` sit in the Weak Warning informational tier (>100 lines); `running-a-full-retrospective` alone is now in the Soft Warning tier (454 lines, still well under the 490 Warning threshold) after this run's fix waves added content to it. No action required at current tiers — watch `running-a-full-retrospective` if it keeps growing; extract further Phase 5 detail to `references/phase-5-fix-execution.md` if it approaches 490 lines.
- R5 (SUGGESTED, harmless no-op): all 11 skills' `allowed-tools` list `AskUserQuestion`, a documented harmless no-op per `plugin-rulebook`'s own settings.json exception. Optional cleanliness removal, not required.

**Security/data-boundary wording gaps (`security-reviewer`, Phase 5 + Wave 1 re-verification, all Minor):**
1. `generating-analysis-recommendations/SKILL.md:43` — the "treat the source report as data" boundary should extend to "the source report, or any findings pasted directly," since the skill also accepts pasted findings as a co-equal input the current sentence doesn't name.
2. `analyzing-plugin-components/SKILL.md` Phase 2 — `component_inventory.py`'s full JSON payload (100KB+) is persisted to the scratchpad wholesale; the skill states only a prose suggestion to filter it, not the specific fields actually needed (`category`, `path`, `mtime`).
3. `analyzing-tool-and-framework-use/SKILL.md:93` and `comparing-session-to-specification/SKILL.md:56` — both state their data-only boundary in Phase 3, after Phases 1-2 have already read the data in question; move or restate the boundary at first read instead.
4. `running-a-full-retrospective/SKILL.md:255-257,260,395-397` — three condensed restatements of the resolution-order logic still describe a step-4-only match as merely "empty" or "not found," without sec-M1's fix's qualifier that a step-4-only match must be treated the same as no match. The authoritative text (`references/phase-5-fix-execution.md`) is correct; only the condensed SKILL.md restatements lag it.
5. `analyzing-plugin-components`, `analyzing-actor-behavior`, `analyzing-governance-and-conflicts`, `mining-recurring-patterns` — the sec-M4 provenance-scoping sentence added this run uses an ASCII `--` instead of the em dash (`—`) used throughout the surrounding prose in these 4 files (`analyzing-tool-and-framework-use`'s copy already uses `—` correctly). Cosmetic only.
6. `running-a-full-retrospective/SKILL.md:186-191` — Phase 4's addendum path (direct `redact_secrets.py` call) carries no personal-data caveat of its own, unlike Phase 3's persist step. Low impact since the addendum folds into a report that already carries the caveat elsewhere.
7. `references/phase-5-fix-execution.md`'s containment check (`Step 3b` and the pipeline-hand-off equivalent) — the symlink-escape clause is textually present but cannot be runtime-verified without executing the pipeline; a disclosed limitation, not a wording gap.

**Documentation-precision typos (`completeness-reviewer`, Phase 5, Minor):**
8. `starting-an-analysis/SKILL.md`'s Gotchas section says "the two" Tier-1 branches that have a Tier 2, but Phase 1 confirms three of four Tier-1 branches actually have one — should read "the three."
9. `references/report-discovery-convention.md`'s `comparing-sessions` row labels four restatement sites as "three sites" — all four sites are real and correctly described, just miscounted.

**Oversized reference blocks (`skilldir-reviewer`, Phase 5, Minor, R18 SUGGESTED):**
10. `analyzing-tool-and-framework-use/references/tool-classification-taxonomy.md` — the "Categories" fenced block (17 content lines) and the "Tool Usage Record" YAML example block (12 content lines) both cross R18's 10-line weak-warning threshold. Consider converting to a table or trimming.

**Activation-boundary gaps (`activation-reviewer`, Phase 5, Minor — informational tier, distinct from the 2 Major gaps already fixed this run):**
11. `generating-analysis-recommendations/SKILL.md`'s "When NOT to Use" doesn't name `running-a-full-retrospective`, even though that skill already redirects to it. Add the reciprocal exclusion if/when a real collision is observed (none has surfaced yet — this is asymmetry, not a confirmed live defect).
12. `mining-recurring-patterns` and `analyzing-actor-behavior` both use "subagent" as a shared specific noun (token/time usage vs. dispatch-quality assessment) with no cross-reference either direction. Add reciprocal exclusion bullets naming the distinguishing criterion (quantity/usage vs. quality/performance).

## Expected Behavior
Each item above is small and independently actionable — most are one-sentence or one-bullet edits. A future session can work through this list (or a subset) as a lightweight follow-up pass, without needing to re-run the full audit that originally surfaced them.

## Actual Behavior
None of the above were fixed in the originating `plugin-lifecycle-downstream` run — they were deliberately left open (Minor/Informational tier, non-blocking for that run's Grading gate) and are recorded here instead of being lost once that run's own per-agent report output ages out of context.

## Impact
**Low** — every item above is Minor or Informational tier; none blocks the plugin's current Grading score (9.6/10, no gates triggered) or represents a live correctness/security defect. This issue exists for traceability, not urgency.

## Additional Context
- Related: issue #105 (con-M5, shared smoke-test module duplication) and issue #106 (sec-M6, unanchored Bash-grant wildcard) are tracked separately since both need a design decision, not a mechanical fix — this issue is deliberately scoped to items that don't need one.
- Full evidence trail: `.claude/output/plugin-lifecycle-downstream/analysis-kit-2026-08-23/` (gitignored locally; phase reports referenced by name in this run's own conversation history).
