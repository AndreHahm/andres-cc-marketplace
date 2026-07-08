---
description: Assess whether multiple Markdown files should be merged before running `/merge-md-context`.
---

# /assess-md-merge

## Purpose

Assess whether multiple Markdown files should be merged before running `/merge-md-context`.

This command does **not** perform the merge.

It analyzes the planned merge, evaluates risks, identifies document relationships, checks whether context could be lost, and produces a clear recommendation:

- merge is recommended
- merge is conditionally recommended
- merge is not recommended
- a different structure is better

The user decides whether to proceed with `/merge-md-context`.

## Inputs

The user provides two or more Markdown files.

Optional parameters:

```text
target_type: skill | subagent | slash-command | reference | auto
intended_output: single-file | base-plus-overlay | variant-set | reference-pack | auto
merge_goal: consolidate | deduplicate | standardize | migrate | compare | archive | auto
risk_tolerance: low | medium | high
strictness: conservative | balanced | aggressive
run_dir: <auto | .claude/output/<artifact-slug>-<YYYY-MM-DD>>
```

Defaults:

```text
target_type: auto
intended_output: auto
merge_goal: auto
risk_tolerance: low
strictness: conservative
run_dir: auto
```

## Core Rule

Do not merge automatically.

This workflow only produces an assessment and recommendation.

The final response must clearly state whether running `/merge-md-context` is recommended.

## Workflow

See [references/assess-merge-workflow.md]({REPO_ROOT}/.claude/references/assess-merge-workflow.md)

Run the referenced workflow step-by-step in the defined order beginning with `Phase 1 — Identify Inputs` and ending with `Phase 16 — Write Assessment to File`.

## Recommendation Language

Use clear wording.

Examples:

```text
MERGE RECOMMENDED
The files describe the same skill with compatible metadata and output expectations. The merge would reduce duplication and improve maintainability.
```

```text
MERGE CONDITIONALLY RECOMMENDED
The files describe the same topic, but the output contracts and severity models differ. A merge is reasonable only if explicit output modes and severity mapping are preserved.
```

```text
MERGE NOT RECOMMENDED
The files are related but serve different runtime purposes. A single merged file would hide important differences. Use a base-plus-overlay structure instead.
```

```text
DO NOT MERGE
The files have incompatible safety rules and execution behavior. Merging them would create an ambiguous or unsafe workflow.
```

## Readiness and Decision Output Requirements

Every final assessment must include:

```markdown
## Merge Readiness

Level: READY | READY WITH CONDITIONS | NEEDS HUMAN DECISION | NOT READY | BLOCKED

Reason: <short reason>
```

If `human_decision_required: true`, include:

```markdown
## Human Decision Required

Decision needed: <specific decision>
Recommended default: <safe default>
Why it matters: <risk or runtime consequence>
```

Every final assessment must include a `Context Loss Budget`, `Decision Options`, and either a `Recommended Invocation` or an alternative-structure plan.

## User Decision Gate

End every assessment with a user decision gate.

Use this format:

```markdown
## User Decision

Recommended next step:

- Run `/merge-md-context` with strategy: `<strategy>`
- Or use the proposed alternative structure instead

The merge should only be performed after explicit user confirmation.
```

## Output Files

When this workflow completes, write the full assessment to a run directory.

### Run Directory

```text
.claude/output/<artifact-slug>-<YYYY-MM-DD>/
```

The `artifact_slug` is derived from the primary merged artifact filename (lowercase kebab-case, no `.md` extension). If the merged filename is not yet known at assessment time, derive it from the first source file by stripping trailing version suffixes (`-1`, `-2`, `(1)`, etc.) and lowercasing.

If `run_dir` is specified explicitly, use that path instead. If the computed directory already exists from a different session, append `-2`, `-3`, etc.

### Files Written

| File | Contents |
|---|---|
| `assessment.md` | Full assessment output from this workflow |
| `manifest.md` | Pipeline index — created or updated with step status |

The `assessment.md` file ends with a pre-filled `/merge-md-context` invocation referencing `run_dir`.

## Self-Review Checklist

Before finalizing the assessment, verify:

```text
[ ] All files were classified.
[ ] Frontmatter fields validated against platform schema (Phase 1.5) — non-standard fields excluded from Must preserve.
[ ] Relationship classification is justified.
[ ] Merge drivers were identified.
[ ] Hard conflicts were checked.
[ ] Information loss risk was assessed.
[ ] Maintainability impact was assessed.
[ ] Executability impact was assessed.
[ ] Safety impact was assessed.
[ ] Merge Readiness Level is assigned and justified.
[ ] Human Decision Required triggers were checked.
[ ] Context Loss Budget is present.
[ ] Decision Options matrix is present.
[ ] Recommended Invocation or alternative-structure plan is present.
[ ] Recommendation follows from the evidence.
[ ] A better alternative is proposed when merge is not ideal.
[ ] Conditions Before Merge are actionable.
[ ] Merge Instruction Block is present when merge is recommended.
[ ] Merge Instruction Block has Must preserve, Must resolve, Must not, and Validation checklist sections.
[ ] Must preserve does not include non-standard frontmatter fields.
[ ] Final output does not perform the merge.
[ ] User decision remains explicit.
[ ] Output files were written to run directory.
```

## Example Invocation

```text
/assess-md-merge target_type=auto merge_goal=consolidate risk_tolerance=low

Files:
- SKILL.md
- SKILL(1).md
```

```text
/assess-md-merge
run_dir=.claude/output/my-skill-2026-06-18

Files:
- SKILL.md
- SKILL(1).md
```

## Example Output Summary

```markdown
# Markdown Merge Assessment

## Recommendation

MERGE CONDITIONALLY RECOMMENDED

## Short Rationale

Both files describe the same `code-reviewer` skill and share the same domain, role, and output goal. A merge would reduce duplication and preserve useful unique sections. However, the files use different reference path conventions and slightly different severity labels. The merge is safe only if references are preserved and severity labels are normalized explicitly.

## Relationship Classification

`same-entity-style-drift`

## Merge Suitability Score

32 / 40 — merge conditionally recommended.

## Recommended Strategy

`canonical-single-file`

## Conditions Before Merge

- Preserve both reference path families.
- Compose output formats instead of replacing one.
- Preserve stricter evidence and file:line requirements.
- Ensure `Bash` remains in `allowed-tools` if verification commands are preserved.

## Merge Instruction Block

Copy this block into `/merge-md-context` if you decide to proceed.

```text
target_type=skill
merge_strategy=canonical-single-file
preferred_style=operational
strictness=conservative
output_mode=merged-file-with-report

Files:
- SKILL.md
- SKILL(1).md

Must preserve:
- Both reference path families.
- Stricter evidence and file:line requirements.
- Verification commands and Bash executability.
- Positive feedback requirement.

Must resolve:
- Severity label drift.
- Output template composition.
- Nested metadata union.

Must not:
- Drop external references.
- Remove error handling.
- Remove actionable review requirements.

Validation checklist:
- [ ] Both reference path families are present or explicitly resolved.
- [ ] Final output includes file:line evidence requirements.
- [ ] Bash is present in `allowed-tools` if shell commands remain.
- [ ] Merge Report documents severity and output decisions.
```

## User Decision

Recommended next step:

- Run `/merge-md-context` with strategy: `canonical-single-file`

The merge should only be performed after explicit user confirmation.
```
