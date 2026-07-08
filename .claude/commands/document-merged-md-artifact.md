---
description: Create a Markdown documentation file for a merged Markdown artifact produced by `/merge-md-context` and optionally reviewed by `/review-merged-md`.
---

# /document-merged-md-artifact

## Purpose

Create a Markdown documentation file for a merged Markdown artifact produced by `/merge-md-context` and optionally reviewed by `/review-merged-md`.

The documentation explains how the merged skill, subagent, slash-command, reference, checklist, or project rule should be used, what changed during the merge, what decisions were made, which issues remain open, and what next steps are recommended.

The goal is to make the merged artifact understandable and maintainable for future users and agents.

## Position in the Workflow Chain

Use this workflow after the merge and, ideally, after the merged artifact review:

```text
/assess-md-merge
/merge-md-context
/review-merged-md
/document-merged-md-artifact
```

Responsibilities:

| Workflow | Main Question |
|---|---|
| `/assess-md-merge` | Should these files be merged? |
| `/merge-md-context` | How should the files be merged? |
| `/review-merged-md` | Was the merge successful and safely improvable? |
| `/document-merged-md-artifact` | How should users understand, apply, maintain, and improve the merged artifact? |

## Inputs

Required:

```text
merged_file: <merged-artifact.md>
```

Recommended:

```text
assessment_file: <assessment-output.md>
merge_report: <merge-report.md>
review_report: <review-merged-md-output.md>
original_files:
  - <original-a.md>
  - <original-b.md>
```

Optional:

```text
target_type: skill | subagent | slash-command | reference | checklist | project-rule | auto
documentation_audience: user | maintainer | agent | mixed
documentation_depth: concise | standard | detailed
include_original_sources: yes | no
include_open_points: yes | no
include_next_steps: yes | no
output_filename: <name>.md
run_dir: <auto | .claude/output/<artifact-slug>-<YYYY-MM-DD>>
```

Defaults:

```text
target_type: auto
documentation_audience: mixed
documentation_depth: standard
include_original_sources: yes
include_open_points: yes
include_next_steps: yes
output_filename: <merged-artifact-name>-documentation.md
run_dir: auto
```

## Core Rules

1. The documentation must describe the merged artifact, not re-merge it.
2. Preserve important links and references from the merged artifact.
3. Do not invent decisions that are not supported by the merge report, assessment, or review report.
4. Clearly separate facts, decisions, open points, and recommendations.
5. If information is missing, say so explicitly.
6. Keep usage instructions practical and actionable.
7. Include enough context that a future user can understand how and when to use the merged artifact.
8. Do not hide unresolved conflicts.
9. Do not remove cautionary notes, safety gates, output contracts, or runtime constraints.
10. Make the document useful both for humans and future agents.

## Workflow

See [references/document-merged-workflow.md]({REPO_ROOT}/.claude/references/document-merged-workflow.md)

Run the referenced workflow step-by-step in the defined order beginning with `Phase 1 — Load Inputs` and ending with `Phase 11 — Write Documentation to File`.

## Documentation Outcomes

The generated documentation should help answer:

- What is this merged artifact?
- What should it be used for?
- When should it not be used?
- How is it invoked or applied?
- Which original files contributed important behavior?
- What did the merge change?
- What assumptions or decisions were made?
- Are there open issues?
- Are there safe future improvements?
- What should the user do next?

## Documentation Quality Criteria

The documentation is acceptable only if:

```text
[ ] It explains how to use the merged artifact.
[ ] It identifies the artifact type.
[ ] It documents merge context and source files.
[ ] It includes merge-report information.
[ ] It lists open points if any exist.
[ ] It lists next steps if useful.
[ ] It preserves important references.
[ ] It explains output contracts.
[ ] It explains runtime/tooling constraints.
[ ] It does not hide unresolved conflicts.
[ ] It is useful without reopening the original chat.
```

## Optional Documentation Modes

### Concise Mode

Use for simple merges.

Sections:

```text
Overview
How to Use
Merge Summary
Open Points
Next Steps
```

### Standard Mode

Use by default.

Sections:

```text
Overview
Artifact Summary
How to Use
Runtime Notes
Output Contract
References
Merge Summary
Merge Report
Open Points
Next Steps
Maintenance Notes
```

### Detailed Mode

Use for important skills, security-related agents, slash-commands, or repository standards.

Adds:

```text
Assessment Summary
Review Summary
Source Coverage
Decision Log
Risk Notes
Validation Checklist
Change Log
```

## Safety Rules for Documentation

For security, deployment, automation, write-access, or active-testing artifacts:

- Document authorization gates.
- Document human approval gates.
- Document destructive-action restrictions.
- Document credential handling rules.
- Document production restrictions.
- Document escalation paths.
- Do not simplify away warnings.

## Self-Review Checklist for This Workflow

Before finalizing the documentation, verify:

```text
[ ] The documentation describes the merged artifact accurately.
[ ] The usage section is practical.
[ ] Merge decisions are traceable to assessment or merge report.
[ ] Open points are not hidden.
[ ] References are preserved.
[ ] Runtime and tooling constraints are documented.
[ ] Output contracts are documented.
[ ] Safety rules are documented where relevant.
[ ] Next steps are realistic.
[ ] The documentation can stand alone.
```

## Example Invocation

```text
/document-merged-md-artifact

target_type=slash-command
documentation_audience=mixed
documentation_depth=standard
include_open_points=yes
include_next_steps=yes

merged_file=review-pr-merged.md
assessment_file=assess-review-pr.md
merge_report=merge-review-pr-report.md
review_report=review-merged-review-pr.md
original_files:
- review-pr-1.md
- review-pr-2.md
```

```text
/document-merged-md-artifact
run_dir=.claude/output/review-pr-2026-06-18

merged_file=.claude/commands/review-pr.md
original_files:
- .claude/commands/review-pr-1.md
- .claude/commands/review-pr-2.md
```

## Example Output Filename

```text
review-pr-merged-documentation.md
```
