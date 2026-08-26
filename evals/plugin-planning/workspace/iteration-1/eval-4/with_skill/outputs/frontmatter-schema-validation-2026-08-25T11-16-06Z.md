# Plugin Plan: Frontmatter Schema Validation

**Generated:** 2026-08-25T11:16:06Z
**Concept source:** direct description (ideation skipped)

## Component Inventory

| Name | Type | Purpose | Trigger phrases (rough) |
|---|---|---|---|
| `frontmatter-schema-validation` | Skill | Validates YAML frontmatter blocks in markdown files against a schema, reporting field-level errors | "validate frontmatter", "check YAML frontmatter against schema", "does this file's frontmatter match the schema" |

## Content Depth Allocation (Skills Only)

| Skill | Tier | Reason |
|---|---|---|
| `frontmatter-schema-validation` | Rich | Core validation logic (YAML parsing + schema matching) is a deterministic executable utility, not prose guidance alone — needs a `scripts/` validator plus `references/` for schema-format conventions |

## Functional Groups

### Frontmatter Validation
- `frontmatter-schema-validation`

## Code-Smell Check
No code smells flagged — a single skill is well under the >4-agent / multi-skill-summary threshold.

## Next Step
Design this skill with `skill-development`, or hand off to `plugin-lifecycle-upstream` to run Design + Build for the whole plan.

---

**Note on scope:** the user asked to plan a single, already-well-understood component directly, with no
Concept Card and no prior `plugin-ideation` run. Per this skill's own "When NOT to Use" guidance, a single
obvious skill would normally skip straight to `skill-development` (Design) without a planning pass —
this plan was produced anyway because the user explicitly asked for the Step 5 output for this workflow.
