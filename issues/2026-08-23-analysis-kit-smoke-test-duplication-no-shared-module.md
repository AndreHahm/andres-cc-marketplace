## Summary
All 11 `analysis-kit` skills carry a byte-identical `scripts/smoke_test.py` (5 structural checks: frontmatter, Bash-grant usage, referenced-script existence, Reference-Guide-file existence, Phase-header sequencing). A regex bug found during a `plugin-lifecycle-downstream` audit (2026-08-23) had to be fixed identically in all 11 files at once, confirming the duplication is a real maintenance cost, not just a style nit. Consolidating into a shared module is the obvious fix, but breaks on this plugin's `.claude/skills/` mirror.

## Environment
- **Product/Service**: `analysis-kit` plugin, all 11 skills' `scripts/smoke_test.py`
- **Region/Version**: this repo, found during `plugin-lifecycle-downstream`'s Phase 5 Audit (consistency-reviewer finding con-M5) on a run scoped to `fix/analysis-kit-downstream-qa`

## Reproduction Steps
1. Compare any two of `plugins/analysis-kit/skills/*/scripts/smoke_test.py` — the five `check_*` functions are identical except for the skill name in the module docstring.
2. Note each skill also has a mirrored copy at `.claude/skills/<skill>/scripts/smoke_test.py` (this repo's R19 in-development-mirror convention — both copies must stay byte-identical).
3. Try the obvious consolidation: move the five checks into a single `plugins/analysis-kit/scripts/skill_structure_checks.py`, and have each per-skill `smoke_test.py` become a thin entry point that imports it.
4. Observe: `plugins/analysis-kit/skills/<skill>/scripts/smoke_test.py` can resolve the shared module via a relative `sys.path.insert` (e.g. `Path(__file__).resolve().parents[3] / "scripts"`), but `.claude/skills/<skill>/scripts/smoke_test.py` cannot — there is no `.claude/scripts/` directory, since only skill directories are mirrored into `.claude/`, not plugin-level `references/`/`scripts/` directories (confirmed empirically: `find .claude -iname "report-discovery-convention.md"` and similarly for other plugin-level analysis-kit reference files returns nothing).

## Expected Behavior
A consolidation approach that keeps both mirror copies runnable and byte-identical (or otherwise resolves cleanly under this plugin's R19 mirroring convention) without duplicating the shared module's actual logic a second time.

## Actual Behavior
No consolidation approach was applied — the duplication was left in place (accepted risk, recorded in the `plugin-lifecycle-downstream` run's Phase 6 Wave 3 disposition) specifically because every option considered either breaks the `.claude/` mirror copy or reintroduces the same duplication one level up (a second copy of the shared module under `.claude/`).

## Impact
**Low-to-Medium** — the 11 files are small (~120 lines each) and the actual defect class (a shared bug across all 11) has already been demonstrated once. The cost is maintenance friction (any future fix to the shared logic needs the same edit applied 11 times, verified consistent), not a live correctness bug today.

## Additional Context
- This is the same shape of problem `.claude/rules/plugin-rulebook-enforcement.md`'s R19 exception already names for skill-level content ("that duplication is structurally expected... as long as both copies stay identical") — but R19's exception is about two *plugin-level* copies staying identical, not about a *third*, shared-module copy that only one of the two mirror trees can structurally host.
- Possible directions to evaluate (not decided here):
  - Accept the 11-way duplication permanently as a deliberate, disclosed tradeoff (matches this plugin's existing R19 exception in spirit) — document it explicitly rather than leaving it implicit.
  - Give the shared module its own home under `.claude/` too (e.g. `.claude/scripts/analysis-kit-smoke-common.py`) and have *both* mirror copies of each skill's `smoke_test.py` import from their respective local-tree copy of the shared module — trades one duplication (11 identical smoke_test.py files) for a smaller one (2 identical shared-module copies).
  - Revisit whether plugin-level `scripts/`/`references/` directories should be mirrored into `.claude/` at all, as part of a broader look at the mirror convention's own scope.
