## Summary
A mandatory quality-gate instruction told users to invoke a skill-local script via a bare relative path (`python scripts/smoke_test.py`, no `${CLAUDE_SKILL_DIR}` anchor), which resolves against the caller's own working directory, not the skill's — potentially failing outright or silently executing an unrelated same-named script in the caller's own project.

## Environment
- **Product/Service**: `plugin-devkit` plugin — `rule-development`'s Quality-gates checklist / Reference Guide instructions
- **Region/Version**: this repo, found during PR #164 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Read the mandatory quality-gate instruction: `python scripts/smoke_test.py`.
2. Run this skill from a project working directory that has its own, unrelated `scripts/smoke_test.py` (or none at all).
3. The bare relative path resolves against that project's cwd, not the skill's own installed directory — even this repo has no root-level `scripts/smoke_test.py`, so the mandatory gate as literally written cannot succeed from the repo root either.

## Expected Behavior
An instruction invoking a skill-local script should anchor the path to `${CLAUDE_SKILL_DIR}` (or the plugin-relative equivalent), never a bare relative path.

## Actual Behavior
Following the instruction as written either fails (no such file at the resolved location) or, worse, silently executes a different, unrelated script that happens to share the same relative path in the caller's own project.

## Impact
[Severity: Medium] A "mandatory" quality gate that can silently run the wrong script (or none at all) undermines the whole point of making it mandatory. Fixed in `plugin-devkit`'s PR #164 (commit `0661014`): both the Quality-gates checklist line and the Reference Guide row's run instruction now use `python ${CLAUDE_SKILL_DIR}/scripts/smoke_test.py`, matching this repo's own `skill-development` precedent for the same field.

## Additional Context
Mined from PR #164's own review history (`chatgpt-codex-connector[bot]`; 11 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #164` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. This extends the repo-wide `CLAUDE_PLUGIN_ROOT`-vs-skill-directory theme already tracked in this document (PR #143's `CLAUDE_PLUGIN_ROOT` finding) to a sibling variable (`${CLAUDE_SKILL_DIR}`) and a distinct failure mode (bare relative path vs. a missing path segment).

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/164#discussion_r3880682590
