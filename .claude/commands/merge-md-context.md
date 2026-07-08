---
description: Intelligently merge multiple Markdown files that describe the same or closely related topic into one coherent Markdown file.
---

# /merge-md-context

## Purpose

Intelligently merge multiple Markdown files that describe the same or closely related topic into one coherent Markdown file.

The merge must preserve all relevant information, remove overlap, avoid duplication, keep external links and references intact, and produce a single clean target document with a consistent structure and writing style.

This command is designed for Markdown-based:

- agent skills
- subagents
- slash commands
- reference documents
- checklists
- project rules
- implementation guides
- prompt libraries

---

## Slash Command

```text
/merge-md-context
```

---

## Inputs

The user provides two or more Markdown files.

This workflow can also consume the output of `/assess-md-merge` as a binding preflight contract.

Optional user parameters:

```text
target_type: skill | subagent | slash-command | reference | checklist | project-rule | auto
preferred_style: concise | detailed | operational | documentation | preserve-primary
primary_file: <filename or auto>
strictness: conservative | balanced | aggressive
merge_strategy: auto | canonical-single-file | variant-preserving | base-plus-overlay | reference-pack | index-plus-linked-files | diff-report-only | do-not-merge
assessment_block: optional Merge Instruction Block from `/assess-md-merge`
assessment_override: false | true
output_mode: merged-file | merged-file-with-report
run_dir: <auto | .claude/output/<artifact-slug>-<YYYY-MM-DD>>
dry_run: false | true
```

Defaults:

```text
target_type: auto
preferred_style: operational
primary_file: auto
strictness: conservative
merge_strategy: auto
assessment_block: none
assessment_override: false
output_mode: merged-file-with-report
run_dir: auto
dry_run: false
```

---

## Core Rules

1. Do not lose context.
2. Do not silently discard information.
3. Do not duplicate equivalent content.
4. Preserve all external links, file references, relative paths, anchors, citations, examples, commands, and code blocks.
5. Preserve important metadata from frontmatter.
6. If metadata conflicts, resolve only when safe. Otherwise, record the conflict in a merge report.
7. Prefer semantic deduplication over literal deduplication.
8. Keep operational instructions executable and unambiguous.
9. Keep examples when they add different usage context.
10. If unsure whether something is redundant, keep it once in the most appropriate section.
11. Do not weaken mandatory instructions such as `MUST`, `MUST NOT`, `Always`, `Never`, or `Only`.
12. Do not merge incompatible runtime contracts without an explicit mode, mapping, or documented conflict.
13. If an `assessment_block` is provided, treat its constraints as mandatory unless the user explicitly overrides them.
14. Do not ignore `Must preserve`, `Must resolve`, `Must not`, or context-loss rules from an assessment.
15. Do not turn a preflight recommendation of `do-not-merge`, `BLOCKED`, or `NOT READY` into a normal single-file merge unless `assessment_override=true` is explicitly provided.

---

# Workflow

See [references/merge-context-workflow.md]({REPO_ROOT}/.claude/references/merge-context-workflow.md)

Run the referenced workflow step-by-step in the defined order beginning with `Phase 0 — Assessment Intake` and ending with `Phase 21 — Write Outputs to File`.


---

# Output

Return:

1. The merged Markdown file written to its proper repository location.
2. `merge-report.md` written to the run directory.
3. Optional unresolved decisions.
4. Assessment Compliance section when an assessment block was provided.

If the user asks for a downloadable file, create a single `.md` file with the merged result. For `base-plus-overlay`, `variant-preserving`, `reference-pack`, or `index-plus-linked-files`, create all required files or clearly state which files should remain separate.

### Run Directory

All process artifacts are written to:

```text
.claude/output/<artifact-slug>-<YYYY-MM-DD>/
```

| File | Contents |
|---|---|
| `merge-report.md` | Full merge report and assessment compliance |
| `manifest.md` | Pipeline index — updated with step status and merged artifact path |

The `merge-report.md` file ends with a pre-filled `/review-merged-md` invocation referencing `run_dir`. The merged artifact itself is written to its repository location, not the run directory.

---

# Important Behavior

When merging operational agent, skill, or command files:

- Do not weaken mandatory instructions.
- Do not remove trigger conditions.
- Do not remove confidence thresholds.
- Do not remove severity mappings.
- Do not remove output contracts.
- Do not remove error handling.
- Do not remove references to external checklists or project rules.
- Do not remove runtime-critical metadata.
- Do not add elevated permissions without a documented reason.
- Prefer one clear canonical instruction over multiple similar phrasings.
- Preserve runtime-critical metadata.
- Flag runtime metadata conflicts instead of hiding them.

---

# Example Invocation

```text
/merge-md-context target_type=subagent preferred_style=operational strictness=conservative merge_strategy=auto output_mode=merged-file-with-report

Files:
- code-reviewer-1.md
- code-reviewer-2.md
```

```text
/merge-md-context target_type=slash-command preferred_style=operational merge_strategy=auto output_mode=merged-file-with-report

Files:
- review-pr-1.md
- review-pr-2.md
```

```text
/merge-md-context
run_dir=.claude/output/review-pr-2026-06-18
assessment_block=.claude/output/review-pr-2026-06-18/assessment.md

Files:
- .claude/commands/review-pr-1.md
- .claude/commands/review-pr-2.md
```

---

# Test Case Decision Patterns

## Pattern 1 — Same Subagent with Style Drift

Use `canonical-single-file` when:

- names match
- purpose matches
- output contracts are compatible
- differences are mostly wording, structure, or missing sections

Typical result:

- one merged subagent file
- merged frontmatter
- unified process
- deduplicated confidence policy
- preserved checklist links
- merge report for scalar metadata conflicts

## Pattern 2 — Security Base + Conditional Persona

Use `base-plus-overlay` when:

- one file is a general security reviewer
- another file is a conditional exploitability persona
- names differ
- output contracts differ
- model strategy differs
- permissions differ

Typical result:

- base security reviewer
- conditional overlay section
- invocation routing
- output modes
- severity mapping
- explicit permission decision

## Pattern 3 — Slash Command with Documentation Drift

Use `canonical-single-file` when:

- files describe the same command objective
- headings differ but command purpose matches
- one source has stronger operational logic
- another source has better examples and documentation

Typical result:

- one canonical slash-command file
- merged frontmatter
- normalized command identity
- risk-gated workflow
- scope fallback policy
- review selection priority
- examples and workflow integration preserved

---

# Recommended Merge Report Template

```markdown
## Merge Report

### Sources

- `<source-a>`
- `<source-b>`

### Detected Relationship

`same-entity | same-entity-style-drift | specialized-variant | base-plus-overlay | related-but-separate`

### Selected Merge Strategy

`canonical-single-file | variant-preserving | base-plus-overlay`

### Rationale

Explain why this strategy was selected.

### Preserved Unique Content

- `<source-a>`: preserved item
- `<source-b>`: preserved item

### Deduplicated Content

- Duplicate concept: merged into `<section>`

### Conflicts and Decisions

| Area | Source A | Source B | Decision |
|---|---|---|---|
| model | value | value | decision |
| tools | value | value | decision |
| output format | value | value | decision |

### Preserved Links and References

- link or reference

### Unresolved Items

- item
```

---

## Skill File Merge Extension

Use this extension when merging Markdown files that represent reusable skills, especially `SKILL.md` files with frontmatter, reference tables, allowed tools, examples, constraints, and output contracts.

Load the extension from: [references/skill-file-merge-extension.md]({REPO_ROOT}/.claude/references/skill-file-merge-extension.md)
