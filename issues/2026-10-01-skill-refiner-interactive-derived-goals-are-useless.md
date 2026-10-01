# skill-refiner-interactive: derived goals are vacuous, unmeetable or conflict with other rules

## Summary
`skill-refiner-interactive` derives its per-session goals mechanically from pre-analysis findings. On a real run all three proposed goals were either already satisfied before any edit, a convention rather than a defect, or in tension with another rule, so the operator rejected every one and no refinement happened.

## Environment
- **Product/Service**: `plugin-devkit` plugin, `skill-refiner-interactive` skill (`SKILL.md` Core Workflow steps 1 and 8, `references/goal-derivation.md`, `references/pre-analysis-checklist.md`)
- **Region/Version**: repository state on 2026-10-01; target skill was `plugin-rulebook` (486-line `SKILL.md`, 34 reference files)

## Reproduction Steps
1. Run `skill-refiner-interactive` on `plugin-rulebook`, choose "Refine" and the "Define explicitly" interview.
2. Let pre-analysis finish. It finds a Soft Warning size tier, a 699-character `description` with an embedded "Use when" clause, and no goal-verification section.
3. Read the three goals offered at goal selection (cap is 3, per `goal-derivation.md`).

## Expected Behavior
The goals offered describe an outcome the operator would want from the session, can fail before the work and pass after it, and agree with the other rules the skill later enforces in step 10.

## Actual Behavior
1. **"SKILL.md within the tier the operator chose"** (from 486 lines, an R13 Soft Warning; the Warning tier starts above 490). The table gives no target number, so one has to be invented (450). The finding is informational, not a defect. Reaching it means moving rule text out, which pushes against the skill's own 80% rule: the 362-line "Active Rules" section is core content.
2. **"Frontmatter R21-compliant with `description` and `when_to_use`"** (from the `when_to_use` split candidate). The verification, `Skill(plugin-rulebook)` R21 returning OK, already passes before any edit, so the goal is satisfied by doing nothing. The checklist also flags a split at roughly 400 characters while R21's own split hint is 900, so the checklist fires where the rulebook does not.
3. **"Add a goal-measurement step"** (from "goal verification absent"). `pre-analysis-checklist.md` calls it "an optional, low-priority candidate rather than a defect" and `goal-derivation.md` calls it a convention. It still takes one of the three slots, and for a rules-reference skill it has no meaning.

Two findings were correctly not turned into goals, but show the same conflicts:
- **Cross-skill references:** the checklist recommends rewriting a bare `<skill>/references/X.md` path to `${CLAUDE_PLUGIN_ROOT}/skills/<skill>/references/X.md`. `plugin-rulebook` R34 makes a path that lands in a sibling skill's folder a Critical finding, so a goal of "0 bare paths" would create R34 Critical findings.
- **Reference-to-reference chains:** the scan matches index files and plain "see" pointers, so a goal of "zero chains, 0 matches" cannot literally pass.

The operator's verdict on the offered goals: "useless".

## Impact
**Low** - Nothing breaks and the skill still refines. The goal step adds a question that cannot help, and in this run it ended the session without refining anything.

## Additional Context
- Cause: goals come from pre-analysis findings, not from what the operator wants. They therefore restate checks that step 10 (`plugin-rulebook` and `skill-reviewer`) already enforces, so step 8 duplicates step 10, and nothing checks that a goal can fail before the work starts.
- Suggested direction, to settle during implementation:
  1. Source goals from the operator's stated intent (ask what outcome they want), with pre-analysis findings only as optional suggestions.
  2. Run each goal's verification once before any edit and reject or reword a goal that already passes.
  3. Leave conventions that are not defects out of goal derivation.
  4. Give the size-tier goal an explicit target and a check that it does not violate the 80% rule.
  5. Reconcile `pre-analysis-checklist.md` with R21's split hint and R34's cross-skill rule so one source decides.
- `evals/skill-refiner-interactive/evals.json` has 21 dry-run scenarios, 16 of which involve goals. A keyword scan found none that checks an offered goal can fail before any edit (eval 5 only checks that a failing goal passes before completion), which would explain how a vacuous goal went unnoticed.
- Related: #457 asked for measurable per-session goals in four skills, including this one. This issue is about the quality of the goals the implemented mechanism produces. Refs #457.
