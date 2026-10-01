# Skills fall short of the new R35, R34 and R9 rules in bulk: triage and decide

## Summary
The `plugin-rulebook` R34-R37 work added forward-looking rules that currently fail on a large share of existing skills. None of it was fixed, and nothing fails today because the rules only apply to newly created or modified components.

## Environment
- **Product/Service**: `plugin-devkit` rulebook rules R35 (standard sections), R34 (reference integrity) and R9 (local identifiers) against `plugins/*/skills/*/SKILL.md`
- **Region/Version**: repository state on 2026-10-02; counts below come from an ad hoc script, not the rulebook's own checker

## Reproduction Steps
1. List `plugins/*/skills/*/SKILL.md` (141 skills) and check each for `## Quick Start`, `## When to Use`, `## When NOT to Use`, and `## Reference Guide` when the skill has a `references/` directory.
2. For each skill, scan `SKILL.md` and its `references/*.md` (fenced blocks excluded) for backticked `references/<file>.md` pointers and check each exists in that skill's own `references/`.
3. Search tracked fixtures under `evals/` and `plugins/analysis-kit/tests/` for home-directory style paths.

## Expected Behavior
Either the gaps are fixed or each is consciously accepted, so a future change to one of these skills does not start failing a rule on unrelated lines.

## Actual Behavior
1. **R35:** 71 of 141 skills lack at least one required section: 52 have no Quick Start, 17 no When to Use, 17 no When NOT to Use, and 19 have `references/` but no Reference Guide (a skill can miss several).
2. **R34:** 54 bare backticked `references/<file>.md` pointers do not exist in the citing skill's own `references/`. Many are likely pointers meant for another skill and need a qualified `<skill>/references/<file>.md` form; some may be legitimate.
3. **R9:** 22 tracked files under `evals/` and `plugins/analysis-kit/tests/` contain a home-directory style path. Some are probably placeholders or redaction examples, so each needs triage; none are listed here.

## Impact
**Low** - Nothing is broken and the rules are forward-looking, but the first edit to any of these skills will surface the failures, and R35 in particular hits about half the repo.

## Additional Context
- These figures replace the rougher numbers in an earlier handoff (72 skills, about 30 pointers); the method here is stated above and can be rerun.
- Suggest splitting into three follow-ups (R35, R34, R9) if the work is taken on, and deciding per rule whether it stays forward-looking.
- Related: #446 (the shared-folder mirroring work that R34's path rules interact with).
