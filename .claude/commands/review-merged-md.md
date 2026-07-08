---
description: Review a merged Markdown document after `/merge-md-context` has produced a result.
---

# /review-merged-md

## Purpose

Review a merged Markdown document after `/merge-md-context` has produced a result.

This workflow verifies that the merged version:

1. satisfies the prior `/assess-md-merge` assessment,
2. preserves all relevant content from the original files,
3. remains functionally correct for its target type,
4. keeps links, references, metadata, output contracts, safety rules, and examples intact,
5. can be improved without reducing context, content, or functionality.

This command does **not** blindly rewrite the merged document.

It performs a structured review and recommends safe optimizations. If requested, it may produce an optimized version, but only after validating that the optimized version still preserves the required context.

## Position in the Workflow Chain

Use this workflow after:

```text
/assess-md-merge
/merge-md-context
/review-merged-md
```

Responsibilities:

| Workflow | Main Question |
|---|---|
| `/assess-md-merge` | Should these files be merged? |
| `/merge-md-context` | How should the files be merged? |
| `/review-merged-md` | Was the merge successful, complete, and safely improvable? |

## Inputs

Required inputs:

```text
original_files:
  - <original-file-a.md>
  - <original-file-b.md>
merged_file:
  - <merged-result.md>
```

Optional inputs:

```text
assessment_file: <assessment-output.md>
assessment_block: <assessment-output-or-merge-instruction-block>
merge_report: <merge-report-from-merge-md-context>
target_type: skill | subagent | slash-command | reference | checklist | project-rule | auto
review_mode: verify-only | report-only | report-with-patch | optimized-version
strictness: conservative | balanced | aggressive
optimization_scope: none | safe-only | structure | style | deduplication | full-safe
run_dir: <auto | .claude/output/<artifact-slug>-<YYYY-MM-DD>>
```

Defaults:

```text
target_type: auto
review_mode: report-only
strictness: conservative
optimization_scope: safe-only
run_dir: auto
```

## Core Rules

1. Do not remove unique context.
2. Do not weaken mandatory rules.
3. Do not change runtime behavior silently.
4. Do not normalize links or paths unless the target convention is explicit.
5. Do not collapse separate output modes unless explicitly safe.
6. Do not remove safety gates, authorization gates, escalation rules, or human-decision gates.
7. Do not remove examples unless they are exact duplicates.
8. Do not change metadata values unless the merge report already justified the decision.
9. Prefer small, explainable optimizations over broad rewrites.
10. If an optimization could affect behavior, classify it as unsafe unless explicitly approved.

## Review Outcome Types

The workflow must classify the merged document as one of:

```text
MERGE ACCEPTED
MERGE ACCEPTED WITH MINOR OPTIMIZATIONS
MERGE NEEDS REVISION
MERGE HAS CONTEXT LOSS
MERGE BLOCKED
```

Definitions:

| Outcome | Meaning |
|---|---|
| `MERGE ACCEPTED` | The merge satisfies the assessment and originals; no meaningful changes needed |
| `MERGE ACCEPTED WITH MINOR OPTIMIZATIONS` | Merge is valid; small improvements are safe |
| `MERGE NEEDS REVISION` | Merge is mostly valid but misses or mishandles some important items |
| `MERGE HAS CONTEXT LOSS` | Unique source content, references, constraints, or output contracts were lost |
| `MERGE BLOCKED` | The merged file is unsafe, misleading, non-executable, or contradicts assessment conditions |

## Workflow

See [references/review-merged-workflow.md]({REPO_ROOT}/.claude/references/review-merged-workflow.md)

Run the referenced workflow step-by-step in the defined order beginning with `Phase 1 — Load and Classify Inputs` and ending with `Phase 13 — Write Review Report to File`.

## Output File

When this workflow completes, write the review report to the run directory.

```text
.claude/output/<artifact-slug>-<YYYY-MM-DD>/review-report.md
```

If `run_dir` is provided, use that path directly. The `review-report.md` file ends with a pre-filled `/document-merged-md-artifact` invocation referencing `run_dir`.

The `manifest.md` in the run directory is updated to mark this step complete.

## Severity Model for Review Findings

Use this severity model:

| Severity | Meaning |
|---|---|
| Critical | Context loss, unsafe behavior, broken output contract, missing human gate |
| High | Missing mandatory condition, missing important reference, weakened constraint |
| Medium | Ambiguous wording, duplicated section, incomplete merge note |
| Low | Minor wording, formatting, or ordering improvement |

## Review Decision Rules

Use these rules:

### Accept

Use when:

- all assessment conditions are satisfied
- all original files are covered
- no critical or high issues exist
- only minor optional optimizations remain

### Accept After Fixes

Use when:

- the merge is fundamentally correct
- only low or medium issues exist
- fixes are straightforward and safe

### Revise Merge

Use when:

- high issues exist
- important source content is missing
- output contracts are partially broken
- reference preservation is incomplete
- metadata decisions are unclear

### Do Not Use Merged Version

Use when:

- critical context is lost
- safety gates are missing
- output contract is broken
- runtime identity is wrong
- assessment strategy was violated
- merge recommendation was ignored without override

## Merge Review Instruction Block

If the review finds required fixes, produce a block that can be copied back into `/merge-md-context` or a revision workflow.

```text
Required merge revision instructions:

Must fix:
- ...

Must preserve:
- ...

Must not change:
- ...

Validation after revision:
- ...
```

## Self-Review Checklist for This Workflow

Before finalizing the review, verify:

```text
[ ] Assessment was considered if provided.
[ ] All original files were checked.
[ ] Merged file was checked as standalone artifact.
[ ] Links and references were reviewed.
[ ] Metadata and runtime fields were reviewed.
[ ] Output contracts were reviewed.
[ ] Safety gates were reviewed.
[ ] Missing content was distinguished from safely merged content.
[ ] Optimization suggestions do not reduce context or functionality.
[ ] Final recommendation is clear.
[ ] No optimized version was produced unless requested.
```

## Example Invocation

```text
/review-merged-md

target_type=slash-command
review_mode=report-only
strictness=conservative
optimization_scope=safe-only

assessment_file=assess-review-pr.md
merge_report=merge-review-pr-report.md
merged_file=review-pr-merged.md

original_files:
- review-pr-1.md
- review-pr-2.md
```

```text
/review-merged-md
run_dir=.claude/output/review-pr-2026-06-18

merged_file=.claude/commands/review-pr.md
original_files:
- .claude/commands/review-pr-1.md
- .claude/commands/review-pr-2.md
```

## Example Final Recommendation

```markdown
## Final Recommendation

ACCEPT AFTER FIXES

The merged slash-command preserves the required roles, risk-gating logic, output format, and examples. However, the `/pr-risk` reference from the original file is missing and the assessment condition requiring optional parallel mode was only partially satisfied.

Fix those two issues before using the merged version.
```
