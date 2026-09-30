# Preservation Rules

Critical content that MUST be preserved during skill refinement. These rules prevent accidental deletion of essential functionality.

## Table of Contents
1. [Non-Negotiable Content](#non-negotiable-content)
2. [References That Must Stay](#references-that-must-stay)
3. [Movement, Not Deletion](#movement-not-deletion)
4. [Functional Dependencies](#functional-dependencies)
5. [Error Handling Requirements](#error-handling-requirements)
6. [Testing Requirements](#testing-requirements)
7. [Decision Tree: Is This Deletable?](#decision-tree-is-this-deletable)
8. [Refinement Goals vs. Preservation](#refinement-goals-vs-preservation)
9. [Safe Refinement Patterns](#safe-refinement-patterns)
10. [The Litmus Test](#the-litmus-test)
11. [Examples: Correct Preservation](#examples-correct-preservation)
12. [Summary](#summary)

## Non-Negotiable Content

### SKILL.md Frontmatter

**NEVER delete or rename:**
- `name` field - Required for skill identification
- `description` field - Required for skill activation (Claude's discovery mechanism). It may be rewritten, but only additively: never narrow its scope or drop its trigger phrases. Moving trigger conditions out of `description` into the separate `when_to_use` field is additive across the two fields, as long as every phrase survives in one of them.

**NEVER weaken:**
- `allowed-tools` field - Principle of least privilege must be maintained or strengthened, never weakened

Example of correct vs. incorrect changes to the description:

```
WRONG: Removing description
Before: description: "Improve and validate skills. Use when refining or validating."
After: [deleted]
→ Problem: Skill won't activate anymore

CORRECT: Improving description
Before: description: "Improve skills"
After: description: "Improve and validate skills for clarity, efficiency, and production readiness. Use when refining, validating, or checking production readiness."
→ Benefit: Clearer activation triggers, better discoverability
```

Example of correct vs. incorrect changes to tool scoping:

```
WRONG: Weakening tool scoping
Before: allowed-tools: Read Edit Write Glob
After: allowed-tools: Read Edit Write Bash(*) Glob
→ Problem: Now allows ANY command (security violation)

CORRECT: Maintaining least privilege
Before: allowed-tools: Read Edit Write Glob
After: allowed-tools: Read Edit Glob
→ Benefit: Still secure, more efficient (Write removed because it is unused)
```

### Quick Start Section

**NEVER delete:** Quick Start section must remain.

**WHY:** Quick Start is what Claude uses to execute 80% of skill activations. Without it:
- Skill loses its core value proposition
- Procedures become unclear
- Activation quality degrades

Acceptable changes to Quick Start:
- Clarify wording
- Reorganize steps for better flow
- Add concrete examples
- Remove redundancy

Unacceptable changes:
- Delete entire section
- Remove steps from workflows
- Abstract procedures into theory

### Core Workflow Steps

**NEVER delete:** Core workflows must be preserved in their entirety.

Example: If a skill defines 7 validation phases, don't:
- Delete phases 4-7 "to simplify"
- Merge phases arbitrarily
- Skip phases in documentation

Acceptable changes:
- Clarify phase descriptions
- Add examples to phases
- Reorganize phases for better flow
- Split one complex phase into substeps

### Scope & Constraints

**NEVER delete:** Clear statements about scope (what's IN, what's OUT) must be preserved.

Example: If a skill says "Forbidden: Never edit cache paths", don't delete that constraint:

```
WRONG: Removing constraint to "simplify"
Before: "FORBIDDEN - Never edit (REFUSE IMMEDIATELY): ~/.claude/plugins/cache/*"
After: [deleted]
→ Problem: User might try to edit cache files; safety guardrail removed
```

```
CORRECT: Keeping constraint
Before: "FORBIDDEN - Never edit (REFUSE IMMEDIATELY): ~/.claude/plugins/cache/*"
After: "FORBIDDEN - Never edit (REFUSE IMMEDIATELY): ~/.claude/plugins/cache/* (installed plugins - read-only)"
→ Benefit: Constraint preserved with clearer reasoning
```

### Trigger Phrases

**NEVER delete:** Specific trigger phrases that enable skill activation must be preserved.

These phrases are how Claude recognizes when to invoke the skill:
- "refine"
- "improve"
- "validate"
- "production-ready"
- "simplify"

Acceptable changes:
- Add MORE trigger phrases for better activation
- Clarify existing phrases
- Explain when each phrase should trigger

Unacceptable changes:
- Delete trigger phrases
- Make description vague (defeats activation)
- Remove context about when to use skill

## References That Must Stay

**NEVER delete references that implement core functionality.** For this skill (`skill-refiner-interactive`), these files must stay:

- `refinement-workflow.md` — the preservation gates, validation phases, consolidation and extraction procedures
- `validation-checklist.md` — the Validate-mode assessment depends on it
- `preservation-rules.md` — this file protects itself
- `pre-analysis-checklist.md` — the pre-analysis checks and report template
- `interview-question-templates.md` — the interview questions and the mirror-divergence and trigger-regression asks
- `goal-derivation.md` — goal derivation, selection and measurement
- `changes-draft-format.md` — the plan-only exit writes drafts in this format

General rule: if SKILL.md points at `references/X.md`, file X is REQUIRED. Don't delete it without updating SKILL.md AND verifying functionality is preserved.

## Movement, Not Deletion

**Core principle: Move essential content, never delete it.**

If content is essential (80% rule), moving is safer than deletion:

A SKILL.md that is too long gets its supplementary lines moved to a new reference file and linked, never deleted "to simplify". The sequence (CREATE → LINK → DELETE the old source only) is specified in `movement-pattern.md`.

## Functional Dependencies

**NEVER remove content that other content depends on:**

```
Example: Both workflows depend on the "Locate the skill" procedure

Core Workflow: Refinement
  └─ Step 1: Locate the skill (then pre-analysis)

Core Workflow: Validation
  └─ Step 1: Locate the skill (same as refinement step 1)
```

If you delete the locate procedure:
- Both workflows break (can't find skills)
- The user has no way to point at the skill files
- The skill is non-functional

MUST preserve the locate procedure: multiple workflows use it.

## Error Handling Requirements

**NEVER remove error handling for critical paths:**

`skill-refiner-interactive` MUST handle:
- Missing skill files (search project, user-space, refuse cache)
- Malformed YAML (report parse errors)
- Cache path access (refuse immediately)
- Permission issues (report, don't workaround)

If any error handler is removed:
- Skill becomes fragile
- User gets cryptic failures instead of helpful errors
- Maintenance burden increases

## Testing Requirements

**NEVER remove testing verification after changes:**

Before deploying refinement:
- Phase 7 (Testing) MUST pass
- Real-world example requests MUST activate skill
- Workflows MUST execute end-to-end

If testing is skipped:
- Broken skills ship to users
- Silent failures become common
- Refinement goals are defeated

## Decision Tree: Is This Deletable?

Content in the "Non-Negotiable Content" list above is never deletable: refuse and preserve it. Anything else is eligible only after Gate 2 (would deletion impair execution, or does other content depend on it?) and Gate 4 (operator confirmation via `AskUserQuestion`). The full tree is "Is This Deletion Safe?" under Quality Decision Trees in `refinement-workflow.md`; a move or update instead follows the movement pattern.

## Refinement Goals vs. Preservation

**Remember the balance:**

| Goal | How to Achieve | Preserve |
|------|---|---|
| Reduce token usage | Move supplementary to references/ | Core content stays |
| Improve clarity | Rewrite confusing sections | All functionality preserved |
| Better organization | Consolidate related files | All content retained |
| Simplify SKILL.md | Move advanced topics to references/ | Essential procedures |
| Fix bugs | Update wrong instructions | Correct functionality |

**Key insight:** All goals are compatible with preservation. You don't need to delete to improve.

**When refinement is appropriate:**
- Simplifying overly complex language
- Moving examples/details to references (keeping originals)
- Adding missing trigger phrases
- Fixing typos or grammar
- Reorganizing for clarity
- Adding/removing tools in scope

**When refinement is NOT appropriate:**
- Shortening descriptions to "save space"
- Removing qualifiers to "make it punchier"
- Deleting sections to "reduce complexity"
- Combining unrelated ideas into fewer words
- "Updating" scope (use case removal)

**Rule:** If you're cutting content, it's not refinement. It's deletion disguised as editing.

## Safe Refinement Patterns

- **Reordering** - Rearrange sections, same content
- **Clarifying** - Reword confusing language, preserve meaning
- **Adding trigger phrases** - Make description more activation-friendly (add, don't remove)
- **Consolidating** - Merge redundant sections, don't erase

**Example of a scope-losing refinement (WRONG):**

```yaml
# BEFORE
description: >-
  Create, validate, and refine Claude Code skills. Use when: building new skills,
  validating skills against best practices, or improving skill clarity and execution.
  Handles skill structure, frontmatter, activation, references, tool scoping, and
  production readiness.
```

```yaml
# AFTER (WRONG - lost critical scope)
description: >-
  Build and refine Claude Code skills. Use when: "create skill", "validate skill",
  "improve skill". Handles frontmatter, activation triggers, references organization,
  tool scoping, production safety.
```

What was lost: "Create, validate, and" loses "validate" as an equal action; "against best practices" loses what validation means; "skill structure" is gone entirely; "production readiness" became "safety" (a different meaning).

**Enforced as a gate:** if content is removed but no corresponding content appears in its destination, the refinement is REJECTED.

## The Litmus Test

Before accepting ANY refinement, verify:

1. **Is the description still accurate?** Would someone understand all capabilities?
2. **Was anything important deleted?** Or just reorganized?
3. **Is scope preserved?** All major use cases still present?
4. **Is it still complete?** Or just shorter for brevity's sake?

If you cut something for brevity, it's not refinement—it's damage.

Skills carry no `version` field (plugin-rulebook's R5 treats it as non-standard), so there is nothing to bump after a refinement. Record what changed in the change summary and the commit message instead.

## Examples: Correct Preservation

### Example 1: Simplifying Without Losing Content

**Scenario:** User says "Make this clearer and more efficient"

```
BEFORE (620 lines):
[SKILL.md body with mixed content: procedures, examples, advanced patterns, theory]

DURING REFINEMENT:
✓ Move advanced patterns to references/edge-cases.md
✓ Consolidate related files
✓ Rewrite confusing sections for clarity
✗ DO NOT delete any procedures
✗ DO NOT remove examples
✗ DO NOT remove core constraints
```

```
AFTER (470 lines):
[SKILL.md body: procedures + essential examples only]
[references/: advanced patterns, extended examples, theory]

Result: clearer (less clutter), efficient (moved, not deleted), functional (all features preserved)
```

### Example 2: Handling Obsolete Content

**Scenario:** Old section is outdated and needs replacement

```
BEFORE:
[Old section describing deprecated workflow]

APPROACH:
✓ Create new section with updated workflow
✓ Link SKILL.md to new section
✓ DELETE old section only after links verified
✓ If old workflow is still needed: PRESERVE it (move to references/deprecated-patterns.md)

AFTER:
[New section with current workflow]
[references/deprecated-patterns.md: old workflow for users who need legacy support]
```

## Summary

**Refinement Principle:** Improve without reducing. Move without losing. Preserve what works.

**When in doubt:** Move to references instead of deleting. Moving preserves functionality while still improving efficiency.

**Operator approval:** Always use `AskUserQuestion` before deleting. Migrations and improvements don't need approval (content preserved anyway).
