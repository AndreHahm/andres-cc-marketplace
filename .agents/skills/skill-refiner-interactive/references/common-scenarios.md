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
See `references/80-percent-rule.md` for decision examples.

## "Improve user interaction UX"

Audit all AskUserQuestion calls (max 4 options, progressive disclosure).
Convert free-form instructions to predefined AskUserQuestion options where applicable.
Ensure questions follow wizard pattern (ask → wait → ask, not forms).
Verify descriptions are clear and help users make good choices.
Check for >4 options violations — split into multiple AskUserQuestion batches.
See `references/ask-user-question-patterns.md` for patterns and decision trees.

## "Improve reference quality"

Audit every reference link: does it provide context about what agents will find?
Pattern check: `[Core knowledge]. See references/file.md for [edge cases/depth].`
Flag orphaned links (bare links with no context) — agents don't know what's in them.
Add context snippets so agents load references intentionally, not out of uncertainty.

## "Check if this skill is production-ready"

Run Core Workflow: Validation — delegates to `skill-reviewer` (full mode) and `Skill(plugin-rulebook)`, does not reimplement their checks.
Check: error handling, tool scoping, clear trigger phrases, comprehensive testing.
Flag missing production patterns. See `references/production-patterns.md`.
Present `skill-reviewer`'s verdict plus any `plugin-rulebook` FAIL findings.

## "Fix my skill" / "Run improvement loop"

Requires `plugin-devkit` plugin for the `skill-reviewer` agent.
Call `skill-reviewer` → categorize issues → fix Critical/Major → evaluate Minor → repeat.
Output `<skill-improvement-complete>` marker when no Critical/Major issues remain.

## "This SKILL.md section is too large"

When a section is ≥80 lines and used in <20% of activations, extract it to a reference file.

1. **Pre-analysis:** Identify section name, line count, and estimated activation frequency
2. **Gate 2:** Confirm extraction won't impair execution (section must be supplementary)
3. **CREATE** `references/<topic>.md` with the full section content
4. **LINK:** Replace the inline section with a pointer (8 lines or fewer):
   ```markdown
   ## Section Name
   See `references/<topic>.md` for [what's there].
   ```
5. **DELETE** the inline body (the pointer replaces it)
6. **Validate:** Phase 5 (references exist, no orphans) + Phase 7 (pointer resolves correctly)

See `references/refinement-workflow.md#content-extraction` for detailed procedure and examples.
