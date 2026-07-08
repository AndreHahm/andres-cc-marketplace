# /review-merged-md

## Workflow

### Phase 1 — Load and Classify Inputs

Read:

- all original files
- merged file
- assessment block or assessment file, if provided
- merge report, if provided

#### Merge-Report-Anchored Mode

If a merge-report is provided and contains a completed Assessment Compliance section (Must Preserve / Must Resolve / Must Not tables), switch to merge-report-anchored mode:

- Read: merged output + merge-report only. Do not load the full original source files.
- Derive the Must Preserve checklist from the merge-report's Must Preserve table.
- Derive the Must Not checklist from the merge-report's Must Not table.
- For Source Coverage (Phase 3): use the merge-report's "Preserved Unique Content" and "Key Integration Points" tables rather than re-scanning the originals. Mark coverage status for each item listed.

Fall back to reading original files when:
- No merge-report is provided.
- The merge-report's Assessment Compliance section is absent or incomplete (fewer items than the assessment).
- A Must Preserve item cannot be located in the merged output and cannot be confirmed from the merge-report's tables alone.

#### Mode Selection

Determine review mode before loading any content:

- If `review_mode=verify-only` is set explicitly: use verify-only mode (Phase 12).
- If `review_mode` is not set AND a merge-report with complete Assessment Compliance is present AND the assessment score is ≥ 28/40: automatically use verify-only mode and report this at the start.
- Otherwise: use full review mode (all phases).

Classify the target document type:

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

Extract from the merged file:

```text
frontmatter
title
section tree
links
relative references
external references
code blocks
examples
runtime metadata
tools and permissions
output contracts
severity schemas
safety rules
human-decision gates
error handling
success metrics
merge notes
assessment compliance section
```

### Phase 2 — Validate Against Assessment

If an assessment block or file is provided, validate the merged file against it.

Check:

```text
recommendation
merge readiness level
recommended strategy
must preserve
must resolve
must not
context loss budget
human decision required triggers
recommended invocation
validation checklist
```

For each assessment item, assign:

```text
satisfied
partially satisfied
not satisfied
not applicable
unclear
```

If the merged file violates a `Must not` item, classify the issue as at least `High`.

If the merged file fails a `Must preserve` item, classify the issue as at least `High`.

If the merged file ignores a `Human Decision Required` trigger, classify the issue as `Critical`.

### Phase 3 — Validate Against Original Files

Build an inventory of unique information units from the original files.

For each original file, extract:

```text
frontmatter fields
unique metadata
unique sections
unique constraints
unique process steps
unique examples
unique links and references
unique output format requirements
unique safety gates
unique error handling
unique success metrics
unique anti-patterns
unique false-positive rules
unique command invocations
unique code/config examples
```

Then check whether each unit is present in the merged file.

Use these statuses:

```text
preserved exactly
preserved semantically
merged into another section
missing
weakened
changed
conflicted
not applicable
```

A unit counts as preserved if its operational meaning is retained, even if wording changed.

A unit counts as lost if its meaning, trigger, constraint, link, or runtime effect disappeared.

### Phase 4 — Link and Reference Integrity Review

Verify that all original links and references are preserved unless intentionally marked as removed in the merge report.

Check:

- Markdown links
- URLs
- relative paths
- anchor links
- reference file paths
- documentation links
- command references
- code paths
- citations
- support files

Classify each reference:

```text
preserved
renamed with rationale
missing
duplicated unnecessarily
broken-looking
ambiguous
```

Do not auto-fix reference paths unless the target repository convention is explicit.

If both `reference/` and `references/` path families existed in the originals, ensure path drift was either preserved or explicitly resolved.

### Phase 5 — Frontmatter and Runtime Metadata Review

For skills, subagents, and slash-commands, validate frontmatter and runtime metadata.

Check:

- YAML validity
- `name`
- `description`
- `allowed-tools` or `tools`
- `model`
- `permissionMode`
- `memory`
- `skills`
- `agent`
- `context`
- `license`
- `metadata`
- `version`
- `last-reviewed`
- `color`
- `emoji`
- unknown fields

Rules:

- Compatible metadata should be merged.
- Conflicting metadata should be explained.
- Runtime-affecting metadata must not be silently changed.
- Tool permissions must obey least privilege.
- If the body contains executable commands, required tools must be allowed.
- If `Write`, deploy, delete, network, or active testing tools appear, verify that safety gates exist.

### Phase 6 — Output Contract Review

Check all output format requirements from the originals and assessment.

Validate:

- required final lines
- JSON-only constraints
- severity sections
- verdict labels
- reporting schema
- tables
- checklist status blocks
- machine-readable summaries
- human-readable reports
- output modes

Rules:

- Compatible formats may be composed.
- Incompatible formats require output modes or separate variants.
- JSON-only output must not be mixed with prose unless explicitly converted to a separate mode.
- Required final verdict lines must remain present exactly if specified.

### Phase 7 — Safety and Authorization Review

For security, automation, agents, deployment, testing, or external-effect workflows, check:

- safety gates
- authorization gates
- active testing gates
- human escalation rules
- credential handling rules
- destructive action confirmation
- production environment restrictions
- no-exploitation-beyond-PoC rules
- no data loss or disruption rules

If an original file had a stricter safety rule than the merged file, flag this as context weakening.

If active testing, reconnaissance, exploitation, write access, deletion, deployment, or external API actions exist without a gate, classify as `Critical`.

### Phase 8 — Functional Coherence Review

Assess whether the merged document works as a standalone artifact.

Check:

- clear purpose
- clear invocation rules
- clear process
- consistent terminology
- no duplicate contradictory sections
- no unresolved conflicts hidden in the body
- no broken heading hierarchy
- no bloated repeated content
- examples still match the final behavior
- instructions are executable
- output format matches the workflow

For slash-commands:

- arguments are clear
- tool usage is allowed
- workflow order is executable
- selection rules do not conflict
- user decision gates are explicit

For skills:

- when-to-use is clear
- reference loading is clear
- constraints are visible
- output contract is clear
- skill remains teachable and reusable

For subagents:

- runtime identity is clear
- model and tool decisions are justified
- invocation conditions are clear
- output format is unambiguous
- orchestration boundaries are preserved

For references:

- sections are logically grouped
- checklists remain actionable
- severity labels are preserved
- implementation and review guidance are not mixed confusingly
- examples remain correct

### Phase 9 — Self-Review of the Merged Version

Run this checklist internally before writing the report. Do not produce a `## Self-Review` section in the output — if the checklist reveals issues, surface them under `## Required Fixes` or `## Optional Improvements` in Phase 12.

```text
[ ] Does the merged file have one clear purpose?
[ ] Is the document type obvious?
[ ] Is the structure easy to navigate?
[ ] Are all mandatory rules visible?
[ ] Are all references preserved?
[ ] Are all output contracts clear?
[ ] Are examples still accurate?
[ ] Are safety gates strong enough?
[ ] Are runtime permissions justified?
[ ] Are conflicts documented?
[ ] Is duplicate content removed safely?
[ ] Does the file remain maintainable?
[ ] Could a future agent execute this reliably?
```

If any item fails, add a Required Fix or Optional Improvement entry with the specific concern. The checklist is a guard against missed issues, not a report section.

### Phase 10 — Identify Safe Optimizations

Suggest optimizations only if they do not reduce context, content, functionality, or references.

Safe optimizations may include:

- heading normalization
- section reordering
- duplicate sentence removal
- clearer table labels
- consistent severity naming
- moving merge notes to the end
- adding a missing table of contents
- adding an explicit output mode label
- adding cross-links between related sections
- improving wording without changing meaning
- replacing repeated text with one canonical statement

Unsafe optimizations include:

- deleting examples with unique context
- removing output formats
- removing references
- changing severity semantics
- simplifying away safety gates
- collapsing variants
- dropping metadata
- normalizing paths without repository convention
- changing tool permissions
- changing invocation rules
- removing human approval gates

Classify each suggested optimization:

```text
safe
safe with validation
needs human decision
unsafe
```

### Phase 11 — Optional Optimized Version

Only produce an optimized version when:

```text
review_mode: optimized-version
```

or when the user explicitly requests it.

If producing an optimized version:

1. Apply only safe optimizations.
2. Preserve all required content.
3. Keep all links and references.
4. Keep all metadata.
5. Keep all output contracts.
6. Add an optimization report.
7. Re-run the self-review checklist against the optimized version.

If an optimization needs a human decision, do not apply it automatically.

### Phase 12 — Final Review Report

#### Verify-Only Mode

Use when `review_mode=verify-only` is active (set explicitly or auto-selected in Phase 1).

Produce a compact report covering only the checklist-verifiable items. Skip runtime/metadata review, safety review, output contract review, and optimization opportunities.

```markdown
# Merged Markdown Review (verify-only)

## Outcome

MERGE ACCEPTED / MERGE NEEDS REVISION / MERGE BLOCKED

## Assessment Compliance

**Summary:** N Must Preserve ✅ / N ✗ — N Must Resolve ✅ / N ✗ — N Must Not ✅ / N violated

List only items that are **not satisfied** or **partially satisfied**:

| Item | Type | Status | Notes |
|---|---|---|---|
| (only failures or gaps) | Must Preserve / Must Resolve / Must Not | not satisfied / partial | … |

If all items pass: `All assessment constraints satisfied.`

## Source Coverage

| Source | Coverage | Missing Items |
|---|---|---|

## Required Fixes

List fixes required before accepting the merge. Omit section if none.

## Final Recommendation

ACCEPT / ACCEPT AFTER FIXES / REVISE MERGE / DO NOT USE MERGED VERSION
```

#### Full Review Mode

Use for `review_mode=report-only`, `report-with-patch`, or `optimized-version`, or when the assessment score is below 28/40.

```markdown
# Merged Markdown Review

## Outcome

MERGE ACCEPTED / MERGE ACCEPTED WITH MINOR OPTIMIZATIONS / MERGE NEEDS REVISION / MERGE HAS CONTEXT LOSS / MERGE BLOCKED

## Short Rationale

Brief explanation.

## Assessment Compliance

See `<run_dir>/assessment.md` for the full constraint list (Must Preserve / Must Resolve / Must Not / Validation Checklist).

**Summary:** N Must Preserve ✅ / N partially satisfied / N ✗ — N Must Resolve ✅ / N ✗ — N Must Not ✅ / N violated

List only items that are **not satisfied** or **partially satisfied**:

| Item | Type | Status | Notes |
|---|---|---|---|
| (only failures or gaps) | Must Preserve / Must Resolve / Must Not | not satisfied / partial | … |

If all items pass, replace the table with: `All assessment constraints satisfied.`

## Original File Coverage

| Source File | Coverage | Missing / Changed Items | Notes |
|---|---|---|---|

## Link and Reference Integrity

| Reference | Status | Location | Notes |
|---|---|---|---|

## Runtime and Metadata Review

Summary of metadata, tools, permissions, and runtime-sensitive decisions.

## Output Contract Review

Summary of output formats and verdict/reporting requirements.

## Safety Review

Summary of safety gates, authorization gates, and escalation rules.

## Optimization Opportunities

| Optimization | Classification | Benefit | Risk |
|---|---|---|---|

## Required Fixes

List fixes required before accepting the merge.

## Optional Improvements

List safe improvements.

## Final Recommendation

ACCEPT / ACCEPT AFTER FIXES / REVISE MERGE / DO NOT USE MERGED VERSION
```

---

### Phase 13 — Write Review Report to File

Determine the run directory using the same logic as Phase 16 of `/assess-md-merge`.

If `run_dir` was provided, use it directly.

**Output file and append mode:**

- If `output_file` is provided and `append=true`: append the review section to that file under the heading `## Review`. Do not write a separate `review-report.md`. Use the compact format — Outcome, Assessment Compliance summary (reference `assessment.md` by path; do not reproduce the full constraint table), Source Coverage, Required Fixes, Final Recommendation.
- Otherwise: write `review-report.md` to the run directory with the full review report from Phase 12.

When writing standalone `review-report.md`, append a pre-filled suggested invocation at the end:

````markdown
## Suggested Next Step

```text
/document-merged-md-artifact
target_type=<detected-target-type>
documentation_audience=mixed
documentation_depth=standard
include_open_points=yes
include_next_steps=yes
run_dir=<run_dir>

merged_file=<merged-artifact-path>
original_files:
- <source-a>
- <source-b>
```
````

**Manifest:** If `skip_manifest=true`, skip the manifest update. Otherwise update `manifest.md` in the run directory:

- Mark `/review-merged-md` as complete with the output filename.

Report the run directory path in the chat response.
