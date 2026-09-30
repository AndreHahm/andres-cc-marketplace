# Common Scenarios

## "Simplify this skill"

Focus on clarity: restructure sections, improve examples, simplify language.
Identify redundancy in references, suggest consolidation.
Verify 80% rule for SKILL.md body content.

## "Reduce token usage"

Apply the **80% rule**: identify supplementary content used in <20% of cases that can move to `references/`.
Keep core content (80%+ usage) in SKILL.md.
Consolidate related reference files.
Verify activation doesn't suffer from moved content.

## "Improve user interaction UX"

Audit all AskUserQuestion calls (2-4 options per question, at most 4 questions per call, progressive disclosure).
Convert free-form instructions to predefined AskUserQuestion options where applicable.
Ensure questions follow wizard pattern (ask → wait → ask, not forms).
Verify descriptions are clear and help users make good choices.
Check for >4 options violations — split into multiple AskUserQuestion batches.

## "Improve reference quality"

Audit every reference link: does it provide context about what agents will find?
Pattern check: `[Core knowledge]. Edge cases and depth: references/file.md.`
Flag orphaned links (bare links with no context) — agents don't know what's in them.
Add context snippets so agents load references intentionally, not out of uncertainty.

## "Check if this skill is production-ready"

Run Core Workflow: Validation — delegates to `skill-reviewer` (full mode) and `Skill(plugin-rulebook)`, does not reimplement their checks.
Check: error handling, tool scoping, clear trigger phrases, comprehensive testing.
Flag missing production patterns.
Present `skill-reviewer`'s verdict plus any `plugin-rulebook` FAIL findings.

## "Fix my skill" / "Run improvement loop"

Automated fix-review loops with no operator checkpoints belong to `skill-improver-loop`, which owns issue categorization, the completion marker and the stop-hook contract. This skill is for interactive refinement: its own step 10 runs `skill-reviewer` and `Skill(plugin-rulebook)` once goals are measured, and emits `<skill-improvement-complete>` only after both are clean and every selected goal passed or was accepted with a reason.

## "Just tell me what to change, don't edit anything"

Plan-only run: pre-analysis, goal selection and the interview happen as usual, then the plan-only exit (step 5) writes the approved findings and selected goals to a `changes.md` draft and stops. No edits, no goal measurement.

## "Make this skill pass a measurable bar"

Goal-driven run: pre-analysis findings become up to 3 goals, each with a verification. Step 8 measures them after validation; a failed goal either returns to step 6 or is accepted with a recorded reason.

## "This SKILL.md section is too large"

Extract it by the Content Extraction procedure in `refinement-workflow.md` (when to extract, CREATE → LINK → DELETE, extraction report). Gate 2 confirms the section is supplementary first; validation phases 5 and 7 then confirm the pointer resolves and no orphan appeared.
