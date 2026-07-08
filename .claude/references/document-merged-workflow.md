# /document-merged-md-artifact

## Workflow

### Phase 1 — Load Inputs

Read the available inputs:

- merged artifact
- assessment output or assessment block
- merge report
- merged artifact review report
- original source files, if available

Classify each input:

```text
merged artifact
assessment
merge report
review report
source file
unknown
```

If optional inputs are missing, proceed with the available information and mark missing context in the documentation.

### Phase 2 — Identify Artifact Type and Runtime Role

Classify the merged artifact as:

```text
skill
subagent
slash-command
reference
checklist
project-rule
prompt
unknown
```

Extract:

```text
name
title
description
purpose
target audience
when to use
when not to use
inputs or arguments
tools or permissions
model/runtime settings
references
output contract
safety rules
error handling
success metrics
examples
```

### Phase 3 — Extract Usage Guidance

Create practical handling guidance based on the artifact type.

#### For Skills

Document:

- when the skill should be used
- what context it expects
- which reference files it loads
- what output it produces
- what constraints must be respected
- how to verify successful use
- specific anti-patterns that would lead someone to incorrectly trigger this skill — derived from what the source files were actually handling (domain confusions, related-but-different tasks, out-of-scope triggers). These are the most valuable "When Not to Use" bullets; do not substitute generic ones.

#### For Subagents

Document:

- when to invoke the subagent
- expected input scope
- tool and permission implications
- model/runtime assumptions
- output format
- orchestration boundaries
- safety or escalation rules

#### For Slash-Commands

Document:

- command name or inferred invocation
- arguments
- default behavior
- execution flow
- topic filters or modes
- output format
- related commands
- failure behavior

#### For References or Checklists

Document:

- intended use
- review or implementation lifecycle phase
- severity model
- checklist sections
- how to apply the reference
- related skills/commands
- maintenance expectations

### Phase 4 — Summarize Merge Context

Use the assessment and merge report to document:

```text
source files
relationship classification
recommended merge strategy
actual merge strategy
merge readiness level
merge suitability score
why the merge was performed
what changed
what was preserved
what was deduplicated
what was resolved
what was intentionally kept separate
```

If the actual merge strategy differs from the assessment recommendation, state this clearly.

### Phase 5 — Capture Merge Report

Create a dedicated Merge Report section.

Include:

- source files
- preserved unique content
- deduplicated content
- resolved conflicts (reference only — see below)
- unresolved conflicts
- metadata decisions
- output contract decisions
- reference preservation
- safety gate decisions
- assessment compliance summary

**Do not reproduce the Conflicts and Decisions table from merge-report.md.** Instead, reference it by path: "See `<run_dir>/merge-report.md` → Conflicts and Decisions for the full decision log." Focus this section on what documentation.md uniquely provides: source file contributions, preserved unique content summary, and assessment compliance. For merges with more than 3 conflict rows, copying the table adds length without adding value.

Keep this section factual.

Do not rewrite it into marketing language.

### Phase 6 — Capture Review Findings

If a `/review-merged-md` report is available, summarize:

```text
review outcome
assessment compliance status
original file coverage
missing or changed items
link/reference integrity
runtime metadata review
output contract review
safety review
self-review rating
required fixes
optional improvements
final recommendation
```

If no review report is available, add a note recommending one.

### Phase 7 — Identify Open Points

Document unresolved or uncertain items.

Open points may include:

- unresolved metadata conflicts
- unclear reference path conventions
- missing source files
- missing review report
- unresolved tool permission decisions
- unclear model/runtime decisions
- output modes needing validation
- missing tests or examples
- safety gates needing human confirmation
- follow-up documentation needed
- repository-specific conventions not known

For each open point, include:

```text
status
impact
recommended owner
suggested resolution
priority
```

Priority scale:

```text
High
Medium
Low
Optional
```

### Phase 8 — Define Next Steps

If useful, propose next steps.

Examples:

- run `/review-merged-md`
- validate references in the target repository
- test slash-command invocation
- verify allowed tools match body instructions
- add missing reference files
- normalize reference paths
- run lint/format checks
- add examples
- add CI validation
- update registry or index
- commit merged artifact and documentation together
- schedule future review

Do not add next steps if no meaningful follow-up exists.

### Phase 9 — Create Maintenance Notes

Add guidance for future maintainers:

- when to update the artifact
- how to add new variants
- when to split the artifact again
- how to preserve output contracts
- how to handle future source drift
- which sections are runtime-sensitive
- which sections are safe to edit

### Phase 10 — Produce Documentation

Generate one Markdown document using the output template below.

#### Output Template

```markdown
# Documentation: <Merged Artifact Name>

## Overview

Short explanation of what this merged artifact is and why it exists.

## Artifact Summary

| Field | Value |
|---|---|
| Name | |
| Type | |
| Purpose | |
| Primary Users | |
| Invocation / Usage | |
| Output | |
| Status | |

## How to Use

Practical usage instructions.

## When to Use

- ...

## When Not to Use

Derive 3–5 specific anti-patterns from what the source files were actually handling — domain confusions, related-but-different tasks, or out-of-scope triggers that someone might realistically reach for. Generic bullets ("don't use for comprehensive X" or "don't use for Y development") are not useful here.

- ...

## Inputs, Arguments, and Scope

Explain expected inputs, command arguments, files, review scope, or context.

## Runtime and Tooling Notes

Document tools, permissions, model/runtime settings, and execution assumptions.

## Output Contract

Explain required output format, verdicts, JSON schemas, report sections, final lines, or checklist status.

## References and Linked Files

List all important references and linked files.

| Reference | Purpose | Notes |
|---|---|---|

## Merge Summary

Explain why the merge was performed and which strategy was used.

## Source Files

| Source | Role in Merge | Key Contributions |
|---|---|---|

## Merge Report

### Preserved Content

- ...

### Deduplicated Content

- ...

### Resolved Conflicts

See `<run_dir>/merge-report.md` → Conflicts and Decisions for the full decision log.

Summary of key decisions (brief, not a reproduced table):

- ...

### Unresolved Conflicts

| Conflict | Impact | Recommendation |
|---|---|---|

## Review Summary

Only include if review report is available.

| Area | Status | Notes |
|---|---|---|

## Open Points

| Priority | Open Point | Impact | Suggested Resolution |
|---|---|---|---|

## Next Steps

- ...

## Maintenance Notes

- ...

## Change Log

| Date | Change | Notes |
|---|---|---|
| YYYY-MM-DD | Initial documentation for merged artifact | Created after merge |
```

---

### Phase 11 — Write Documentation to File

Determine the run directory using the same logic as Phase 16 of `/assess-md-merge`.

If `run_dir` was provided, use it directly.

Determine the output filename:

- If `output_filename` was specified, write to `<run_dir>/<output_filename>`.
- Otherwise write to `<run_dir>/documentation.md`.

Write the documentation produced in Phase 10 to that file.

**CHANGELOG entry:** After writing documentation.md, determine the merged artifact's parent directory. Write or append a one-line entry to `<artifact-directory>/CHANGELOG.md`:

- If `CHANGELOG.md` does not exist, create it with a Markdown table header.
- Append one row recording the merge date, source basenames, and a one-sentence summary of key changes.

```markdown
| Date | Event | Summary |
|---|---|---|
| YYYY-MM-DD | Merged from <source-a-basename>, <source-b-basename> | <one-sentence summary of what changed> |
```

This makes the merge history discoverable from the skill directory itself, not only from `.claude/output/`. If `run_dir` is inside the skill directory or the artifact path cannot be determined, skip this step and note it in the report.

**Manifest:** If `skip_manifest=true`, skip the manifest update — the calling pipeline writes the manifest itself. Otherwise update `manifest.md` in the run directory:

- Mark `/document-merged-md-artifact` as complete.
- Append a pipeline completion summary:

```markdown
## Pipeline Complete

| File | Purpose |
|---|---|
| `assessment.md` | Pre-merge assessment and recommendation |
| `merge-and-review-report.md` | Merge decisions and post-merge verification |
| `documentation.md` | Usage guide and maintenance notes |

Merged artifact: `<actual path in repository>`
```

Report the run directory path and confirm all pipeline files are written.
```
