## Summary
plugin-rulebook: follow-ups from the five-reviewer pass on the skill (descriptions, audit-decisions ownership, reference nits)

## Environment
- **Product/Service**: `plugins/plugin-devkit/skills/plugin-rulebook` (SKILL.md, `references/`, `scripts/`) and its neighbours `plugin-rulebook-checker`, `plugin-auditor`, `rule-reviewer`, `plugin-development`
- **Region/Version**: branch `fix/rulebook-checker-false-positives` (issues #613 and #615), reviewed 2026-10-18

## Reproduction Steps
1. While finishing the #613/#615 branch, five read-only reviewers ran on `plugins/plugin-devkit/skills/plugin-rulebook`: `skill-reviewer`, `skilldir-reviewer`, `dependency-reviewer`, `activation-reviewer`, `authority-reviewer`.
2. Findings that touch the branch's own work were fixed in commit 73e8d978: the SKILL.md run record, the R37 wrapper and summary wording, and R32 in the forward-looking lists (checklist and `plugin-rulebook-checker.md`).
3. Everything below was left out of that PR and is tracked here.

## Expected Behavior
Each item below is fixed, declined with a reason, or split to its own issue. A re-run of the same five reviewers shows no new Major finding.

## Actual Behavior
No Critical finding and no dependency cycle were found. The remaining items are wording, description-overlap and reference-file defects. The reviewers read the files statically and none ran a behavioral test, so every item is unverified beyond the reviewers' own reading.

**A. Ownership of audit decisions** (`authority-reviewer`, Major)
- `.claude/rules/plugin-rulebook-enforcement.md` ("Upstream Source Verification") says `.claude/plugin-rulebook-audit-decisions.md` is only a retained historical record and new decisions go through `pdk-verify-dev-rules`.
- `references/repo-specific-configuration.md` lines 8 and 16, `SKILL.md` line 418 and `references/skill-file-catalog.md` line 11 still call it the live decision log, and line 16 tells a reader to edit it directly.
- Fix: reword those places as historical and read-only, or amend the rule if the log is meant to stay live.

**B. Activation overlap** (`activation-reviewer`, 5 Major)
- B1. The `plugin-rulebook` skill and `plugin-rulebook-checker` agent descriptions do not name each other; only their bodies do.
- B2. `SKILL.md` line 32 ("When auditing an entire plugin for consistency") collides with `plugin-auditor` and contradicts `SKILL.md` line 45.
- B3. `plugin-rulebook` and the `rule-reviewer` agent both claim a bare "validate this rule" request. The redirect exists only in the skill body (`SKILL.md` line 39).
- B4. "creating or refining" overlaps `skill-development`, `rule-development` and `plugin-development`.
- B5. "validate" is claimed by `plugin-validator`, `plugin-development` and `plugin-rulebook`. Fixing it means editing `plugin-development`, outside this skill.
- Minor: the description has no quoted trigger phrases; "enforces" overstates a manual check; `plugin-grader` and the periodic cross-layer audit in Quick Start are not covered by the exclusions.

**C. Broken example** (`skilldir-reviewer`, Major)
- `references/formatting-rules.md` lines 69-75: the R12 example uses a markdown outer fence whose inner fences close it early.

**D. Reference nits** (`skilldir-reviewer`, Minor)
- `references/testing-run-history.md` lines 15-16: an inline code span is broken across two lines, and a pointer targets a gitignored `.claude/output` path.
- `references/skill-file-catalog.md` lines 47, 50, 51 and `references/evidence-schema.md` lines 227-229: `python scripts/x.py` run examples do not match the direct-path grants in `SKILL.md` `allowed-tools`.
- `references/adding-a-new-rule.md` line 51: stale file counts (7 and 9 against 8 listed).
- Five weak-warning code blocks (11-20 lines) in `evidence-schema.md` and `compliance-report-example.md`; the largest is 16 lines at `evidence-schema.md` 141-156.
- `references/executable-bit.md` lines 10-11: a machine-specific "reports true".
- `references/skill-file-catalog.md` line 35: the R33 row omits `domain_prefix` and snake_case.
- Point-in-time numbers stated as fact in `reference-chains.md`, `reciprocal-exclusions.md` and `testing-mandate-rules.md`.
- The antigravity-kit `bin/` and `docs/` exception in `component-file-prefix.md` may be retirable.

**E. SKILL.md housekeeping** (`skill-reviewer`, Minor)
- `Grep` is in `allowed-tools` but unused.
- The R13/R18 and R20 sweep bullets under "Classify each finding" are procedure notes, not classifications.
- `scripts/mirror-parity-check.sh` and `scripts/test_check_tool_grants.py` are committed as mode 100644 and are not granted in `allowed-tools`; verify whether that matters.

**F. Other** (`dependency-reviewer` and `authority-reviewer`, Minor)
- `plugin-lifecycle-downstream/SKILL.md` line 237 uses `Skill(git-kit:commit)`, while the repo's `route-through-git-kit-lifecycle-skills` rule says only the bare name resolves in its own sessions.
- The `Skill(starting-work)` edge in `references/branch-and-pr-preflight.md` line 23 belongs to the three lifecycle callers, not to `plugin-rulebook`.
- `plugin-rulebook-checker.md` hard-codes "all 33" enabled rules, a duplicate fact that goes stale if a rule is toggled.
- `plugin-rulebook-enforcement.md` does not define the boundary between a "component decision" and an implementation decision.

## Impact
**Low** - wording, description overlap and reference-file defects; no change to any rule, gate or script behavior.

## Additional Context
- Dedup: searched the repo for plugin-rulebook, activation, audit-decisions and reviewer-findings issues; no duplicate. Nearest but different scope: #131 (minor backlog from a 4-skill review round), #136 (`plugin-auditor` Tier 4 cleanup), #570 (follow-ups from the skill-development refactor). Related, not duplicates: #613 and #615 (the fixes the source branch ships).
- Several items touch files outside the `plugin-rulebook` skill folder (`plugin-development`, `plugin-lifecycle-downstream`, `plugin-rulebook-enforcement.md`), so a split into per-area issues may be easier to work than one fix.
