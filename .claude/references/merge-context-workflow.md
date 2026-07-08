# /merge-md-context Workflow

## Phase 0 — Assessment Intake

If an `assessment_block` from `/assess-md-merge` is provided, parse it before doing any merge work.

Extract:

```text
recommendation
merge_readiness_level
recommended_strategy
recommended_invocation
must_preserve
must_resolve
must_not
context_loss_budget
human_decision_required_items
validation_checklist
source_files
known_risks
known_conflicts
```

Treat extracted items as **mandatory merge constraints**.

If the assessment says any of the following, do not perform a canonical single-file merge unless the user explicitly overrides it:

```text
MERGE NOT RECOMMENDED
DO NOT MERGE
NOT READY
BLOCKED
do-not-merge
```

If the assessment recommends `base-plus-overlay`, `variant-preserving`, `reference-pack`, `index-plus-linked-files`, or `diff-report-only`, preserve that structure by default.

If `assessment_block` is a file path (value starts with `./`, `../`, `/`, or ends with `.md`), read the file at that path and use its content as the assessment block.

If no assessment block is provided, continue with automatic relationship detection and strategy selection.

### Pipeline Resume

If `run_dir` is specified and a `manifest.md` exists in that directory, check which steps are already complete:

- If `assessment.md` is marked complete in `manifest.md`: read constraints from `<run_dir>/assessment.md` instead of re-running assessment phases.
- If `merge-report.md` is marked complete: skip merge phases and proceed from review.
- Resume from the earliest incomplete step. Report which steps are being skipped.

### Assessment Override Rule

Only allow an assessment override when the user explicitly states that they want to override the assessment recommendation.

If `assessment_override=true`, still preserve all safety, licensing, output-contract, and tool-permission conflicts in the merge report.

Never silently override an assessment.

---

## Phase 1 — Strategy Lock

If an assessment block provides a recommended strategy, use it as the default merge strategy.

Do not switch from:

- `base-plus-overlay` to `canonical-single-file`
- `variant-preserving` to `canonical-single-file`
- `reference-pack` to `canonical-single-file`
- `index-plus-linked-files` to `canonical-single-file`
- `diff-report-only` to any content-changing merge
- `do-not-merge` to any merge strategy

unless the user explicitly requests an override.

If the user-provided `merge_strategy` conflicts with the assessment strategy, stop and report the conflict unless `assessment_override=true`.

---
## Phase 1a — Dry-Run Check

If `dry_run=true`:

1. Complete Phase 0 and Phase 1 only.
2. Produce a dry-run summary:

```markdown
## Dry-Run Summary

**Planned strategy:** <selected-strategy>
**Target type:** <detected-type>
**Relationship:** <detected-relationship>
**Planned sections:** [list of merged section headings from source files]
**Conflicts to resolve:** [list from assessment or initial scan]
**Must-preserve items:** [list from assessment if provided]
**Would write to:** <run_dir>
```

3. Stop. Do not merge any files.
4. Report: "Dry run complete. Use without `dry_run=true` to perform the actual merge."

---
## Phase 2 — Identify Document Type

Inspect all files and classify each document as one of:

```text
skill
subagent
slash-command
reference
checklist
project-rule
unknown
```

Use these signals:

- YAML frontmatter with `name`, `description`, `tools`, `model`, `color`, `skills` usually indicates a subagent or skill.
- Markdown with command-like names, arguments, invocation syntax, or `allowed-tools` usually indicates a slash command.
- Checklists, criteria, policies, and examples usually indicate reference material.
- Project-wide rules, conventions, or standards usually indicate project instructions.

If multiple files describe the same entity, merge them into one target document.

If files describe different but connected entities, preserve the distinction through sections, overlays, aliases, explicit references, or a variant-preserving output.

---

## Phase 3 — Detect Entity Relationship

Before merging content, determine whether the files represent:

- `same-entity`: same name, same purpose, compatible output format
- `same-entity-style-drift`: same runtime identity, different wording, structure, or documentation depth
- `specialized-variant`: same domain, but narrower trigger conditions or persona
- `base-plus-overlay`: one document is a general capability and another is a conditional specialization
- `same-topic-reference-expansion`: same reference topic, but different granularity, lifecycle phase, usage mode, or audience
- `related-but-separate`: shared topic, but different runtime purpose

Use these signals:

- frontmatter `name`
- filename
- top-level heading
- description
- invocation rules
- argument structure
- tools and permissions
- model settings
- output format
- severity model
- referenced checklists
- command examples
- target user or target automation layer

If files represent a base entity plus a specialized variant, do not force a flat merge.

Prefer a base + overlay architecture.

---

## Phase 4 — Command Identity Normalization

For slash-command files, determine command identity from:

1. filename
2. frontmatter description
3. command examples
4. heading
5. argument structure
6. agent/tool usage
7. workflow purpose

Do not classify files as different commands only because their top-level heading differs.

If command examples reveal a concrete command path, prefer that path as canonical.

If no explicit command path exists, infer from filename and preserve alternate headings as aliases in merge notes.

For slash commands, treat these as strong identity signals:

- same command path
- same filename or near-equivalent filename
- same argument pattern
- same set of subagents or tools
- same workflow objective
- same output contract or compatible output contract

---

## Phase 5 — Select Merge Strategy

If `merge_strategy` is `auto`, select:

- `canonical-single-file` when documents are true duplicates or style variants
- `variant-preserving` when both files should remain separately usable
- `base-plus-overlay` when one file is a general capability and another is a conditional specialization
- `reference-pack` when files belong together but should remain modular references
- `index-plus-linked-files` when files are related but too large or distinct for one document
- `diff-report-only` when the user needs comparison rather than consolidation
- `do-not-merge` when relationships are unrelated, unsafe, or blocked by hard conflicts

If an assessment block is present, strategy selection must respect the Strategy Lock rule.

Never force a single-file merge when output contracts or runtime metadata conflict.

### Strategy Selection Guide

| Relationship | Recommended Strategy | Notes |
|---|---|---|
| `same-entity` | `canonical-single-file` | Merge into one clean document |
| `same-entity-style-drift` | `canonical-single-file` | Preserve all unique content, normalize style |
| `specialized-variant` | `variant-preserving` or `base-plus-overlay` | Keep variant semantics visible |
| `base-plus-overlay` | `base-plus-overlay` | Preserve base behavior and conditional overlay |
| `same-topic-reference-expansion` | `canonical-single-file` or `reference-pack` | Merge into one expanded reference only when it remains maintainable |
| `related-but-separate` | `index-plus-linked-files` or `variant-preserving` | Do not collapse into one runtime entity |
| hard conflicts or unsafe merge | `do-not-merge` | Stop unless explicitly overridden |



### Mandatory Merge Conditions Rule

When the assessment block contains `Must preserve`, `Must resolve`, `Must not`, or a validation checklist, the merged output must satisfy those items.

- `Must preserve` items must appear in the merged document, an overlay, a linked reference, or the merge report location map.
- `Must resolve` items must receive an explicit decision and rationale.
- `Must not` items must not be violated.
- Validation checklist items must be checked in the merge report.

If a condition cannot be satisfied, mark it as unresolved in the merge report.

Never silently ignore a condition.

### Context Loss Budget Rule

Use the assessment's context loss budget as a validation gate.

Allowed loss may be removed, compressed, or semantically deduplicated.

Not-allowed loss must be preserved exactly or represented explicitly in the final structure and merge report. Typical not-allowed loss includes:

- runtime metadata
- output contracts
- safety gates
- authorization gates
- external links
- reference paths
- severity semantics
- invocation rules
- tool permissions
- licensing and attribution
- examples that demonstrate unique behavior

### Human Decision Gate Rule

If the assessment block marks any item as requiring human decision, the merge workflow must either:

1. preserve both alternatives explicitly,
2. create output modes,
3. keep variants separate,
4. preserve the stricter safety rule,
5. or mark the issue as unresolved.

Do not choose silently.

Human-decision triggers include:

- incompatible output contracts
- tool permission differences involving `Write`, `Bash`, deploy, delete, network, or external side effects
- active testing, exploitation, or production-impacting workflows
- licensing conflicts
- unclear authorship or version lineage
- different runtime names
- JSON-only versus prose output
- safety gates present in only one source

---

## Phase 6 — Parse Structure

#### Large-File Two-Pass Strategy

Before reading a file in full, check its line count. If a file exceeds **500 lines**:

1. **First pass — headings-only scan:** Use `Grep` with pattern `^#+` to extract all headings from the file without reading body content. Read only the frontmatter block (first 20–30 lines) separately. This avoids a full file Read call and establishes the section tree cheaply.

   Classify each section heading as one of:
   - **Novel** — no equivalent heading in the other source → include in pass 2 read list.
   - **Redundant** — clearly duplicates a heading already in the other source → skip in pass 2.
   - **Uncertain** — heading is ambiguous or the other source may cover it differently → include in pass 2 to decide.

   Promote any section to pass 2 if it is a Must Preserve candidate from the assessment block.

2. **Second pass — targeted read:** Read only sections classified as Novel or Uncertain. Record skipped sections (Redundant) and their headings in the merge report.

For files under 500 lines, read in full (no two-pass needed).

---

For each file, extract:

```text
filename
document_type
frontmatter
main_title
section_tree
links
relative_file_references
code_blocks
examples
tables
lists
commands
rules
constraints
success_criteria
error_handling
output_format
severity_model
tool_permissions
runtime_metadata
```

Do not rewrite content yet.

Create an internal inventory of all information units.

An information unit is one distinct idea, rule, instruction, example, metadata field, command, link, output contract, severity rule, or constraint.

---

## Phase 7 — Normalize Information Units

Normalize each information unit into this internal shape:

```yaml
id: stable short identifier
source_file: filename
source_section: heading or frontmatter
type: metadata | rule | process | example | checklist | output-format | error-handling | reference | constraint | command | severity | permission | note
content: original content
normalized_meaning: concise semantic summary
links: all links found in this unit
importance: critical | high | medium | low
merge_action: keep | merge | deduplicate | conflict | relocate
```

Important:

- Keep exact links from the source.
- Keep exact command names and file paths.
- Keep exact model/tool names unless resolving metadata conflicts.
- Keep examples if they demonstrate distinct trigger scenarios or usage modes.
- Keep output contracts exactly unless introducing explicit output modes.
- Keep severity thresholds exactly unless creating an explicit mapping table.

---

## Phase 8 — Detect Duplicates and Overlap

Compare units semantically.

Treat units as duplicates only when they express the same operational meaning.

Examples of semantic duplicates:

- “Review unstaged changes from `git diff`.”
- “By default, review unstaged changes from `git diff`.”

These should be merged into one clear statement.

Do not treat the following as duplicates:

- A general process step and a detailed scenario.
- A confidence threshold and a confidence scoring rubric.
- A checklist reference and inline review criteria.
- Similar descriptions with different trigger conditions.
- Different output formats that must be reconciled.
- Different severity systems.
- A base behavior and a conditional overlay.
- Different scope discovery methods.
- Different examples that show distinct usage contexts.

---

## Phase 9 — Detect Hard Conflicts

Treat these as hard conflicts:

- different `name` values
- incompatible output contracts
- incompatible severity schemas
- different tool permissions involving `Write`, `Bash`, or elevated permissions
- different model strategy such as fixed model vs `inherit`
- different invocation semantics
- different command paths
- different runtime identity
- JSON-only output vs prose report
- required final verdict line vs schema-only output
- machine-readable output vs human-readable report

Hard conflicts must be resolved by:

1. explicit selection,
2. output modes,
3. base + overlay structure,
4. variant-preserving structure,
5. a severity/schema mapping table,
6. or a documented unresolved decision.

Do not silently combine incompatible runtime contracts.

---

## Phase 10 — Resolve Frontmatter

Merge YAML frontmatter using this strategy.

### Always preserve compatible fields

Keep fields that do not conflict, such as:

```yaml
name:
description:
argument-hint:
allowed-tools:
tools:
permissionMode:
memory:
skills:
vibe:
last-reviewed:
color:
emoji:
```

### Merge descriptions

Combine descriptions into one concise but complete description.

The merged description should include:

- primary purpose
- proactive usage
- expected input/scope
- important triggers
- mandatory constraints
- references to body sections when useful

Avoid copying multiple long descriptions verbatim.

### Resolve conflicting scalar fields

For fields like:

```yaml
name:
model:
color:
permissionMode:
memory:
```

If values conflict:

1. Choose the value that best fits the selected merge strategy.
2. Preserve the alternative in the merge report.
3. If the target format allows comments, optionally add a YAML comment.
4. If the conflict affects runtime behavior, mark it as an unresolved decision unless the strategy clearly resolves it.

Example:

```yaml
model: opus
```

Merge report:

```text
model conflict:
- file A used sonnet
- file B used opus
Decision: opus selected because the merged reviewer performs broader guideline and security analysis.
```

### Preserve unknown metadata

Do not discard unknown frontmatter keys.

Keep them if compatible.

Move them to a documented `x-merged-metadata` section only if the target runtime would reject unknown keys.

---

## Phase 11 — Tool and Permission Conflict Rule

Treat tool and permission differences as runtime-relevant conflicts.

Especially flag:

- `Write` access present in only one source
- `Bash` access present in only one source
- different permission modes
- different memory scopes
- different model settings
- different task delegation tools such as `Task`

Default to the least-privileged tool set unless the stronger permission is explicitly required by preserved behavior.

### Least-Privilege Tool Rule

When tools differ, default to the least-privileged compatible tool set.

Only preserve elevated tools like `Write` when the merged behavior explicitly requires modifying files.

If a command must dispatch agents, preserve `Task` or equivalent agent-dispatch capability.

If the merged document only reviews and reports, do not add write-capable tools unless remediation editing is part of the documented behavior.

---

## Phase 12 — Output Contract Conflict Rule

If two files define incompatible output contracts, treat this as a hard merge conflict.

Examples:

- JSON-only output vs prose report
- required final verdict line vs schema-only output
- machine-readable output vs human-readable report
- different severity systems without a mapping table

Do not silently combine incompatible output formats.

Resolve by one of:

1. selecting one canonical output contract
2. creating explicit output modes
3. preserving separate base and overlay documents
4. adding a severity/schema mapping table
5. documenting the unresolved conflict

### Output Modes

If both output styles are useful and compatible with the runtime, introduce explicit output modes:

```yaml
output_modes:
  machine:
    format: json
  human:
    format: markdown-report
```

For runtime subagents, prefer one default output contract and document alternatives clearly.

For slash commands, make the default output human-readable unless the command is explicitly automation-only.

---

## Phase 13 — Severity Mapping Rule

If severity systems differ, create an explicit mapping table.

Do not collapse severity systems unless the mapping is obvious and lossless.

Preserve threshold semantics, exception rules, and suppression rules.

Example:

| Source Severity / Anchor | Canonical Severity |
|---|---|
| Anchor 100 | CRITICAL |
| Anchor 75 | HIGH |
| Anchor 50 with critical impact | CRITICAL / P0 exception |
| Anchor 50 without critical impact | MEDIUM or suppress |
| Anchor 25 or below | suppress |

If no safe mapping exists, keep both systems as separate output modes or document the conflict.

---

## Phase 14 — Scope Fallback Policy

When merging commands that inspect code changes, preserve all scope discovery methods but order them from most specific to broadest.

Recommended order:

1. explicit user arguments
2. pull request context
3. staged changes
4. unstaged changes
5. working tree diff
6. last commit fallback
7. full project fallback, only when explicitly safe for the command

Avoid hardcoding `HEAD~1` as the only default unless all sources agree.

For PR review commands, prefer:

```bash
gh pr view
```

when a PR context exists, then use the relevant diff.

For local-only changes, prefer:

```bash
git diff --cached
git diff
git diff HEAD~1
```

as appropriate.

If no changes are found, report the searched scopes.

---

## Phase 15 — Review Selection Priority Rule

When merging review commands with multiple selection mechanisms, apply this priority:

1. explicit user-selected topics
2. safety/security escalation
3. risk-tier requirements
4. file-type applicability
5. default command behavior

Never let performance optimization suppress a required safety review.

For example:

- If the user asks for `tests`, run test review.
- If the diff touches auth or secrets, add security coverage even if the risk tier is low.
- If the PR is high-risk by size, recommend or run broader review.
- If changed files do not contain comments, skip comment-specific review unless explicitly requested.

---

## Phase 16 — Build Target Structure

Choose a clean target structure based on document type and merge strategy.

### For a Subagent or Skill

Prefer:

```markdown
---
merged frontmatter
---

# Name

Short role definition.

## When to Invoke

Concrete trigger scenarios.

## Review Scope

Default scope and user-overridden scope.

## Process

Step-by-step execution flow.

## Core Responsibilities

Main responsibility groups.

## Review Criteria

Specific criteria, thresholds, and external checklist references.

## Confidence Policy

Thresholds, scoring, and false-positive handling.

## Output Format

Required report structure and final verdict format.

## Error Handling

Missing files, no changes, unreadable references, unavailable reports.

## Success Metrics

Approval/blocking rules or acceptance criteria.

## Merge Notes

Only include if output_mode is `merged-file-with-report` or unresolved conflicts exist.
```

### For a Slash Command

Prefer:

```markdown
---
merged frontmatter
---

# /command-name or Canonical Command Title

## Purpose
## Inputs
## Preconditions
## Workflow
## Decision Rules
## Output Format
## Usage Examples
## Workflow Integration
## Error Handling
## Related Commands and Skills
## Merge Notes
```

### For a Reference Document

Prefer:

```markdown
# Title

## Purpose
## Scope
## Concepts
## Rules
## Procedures
## Examples
## References
## Merge Notes
```

### For Base + Overlay

Prefer:

```markdown
---
base frontmatter or canonical runtime metadata
---

# Canonical Name

## Base Behavior

## Conditional Overlay

## Invocation Routing

## Shared Rules

## Variant-Specific Rules

## Output Modes

## Severity Mapping

## Error Handling

## Merge Notes
```

---

## Phase 17 — Rewrite Into One Consistent Style

Rewrite the merged document in one consistent style.

Default style:

- direct
- operational
- precise
- no unnecessary prose
- no vague suggestions
- no duplicate headings
- no repeated examples unless each example adds a distinct trigger or behavior

Preserve strong wording such as:

```text
MUST
MUST NOT
Only report
Do not
Always
Never
```

when it affects behavior.

Do not convert strict runtime constraints into soft advice.

---

## Phase 18 — Preserve Links and References

Collect all links and references before rewriting.

After rewriting, verify that every original link/reference still appears exactly once unless intentionally duplicated for usability.

Preserve:

- Markdown links
- relative paths
- file references
- anchors
- code paths
- URLs
- citations
- checklist references
- command references
- slash-command references
- skill references
- agent names

If a link becomes structurally misplaced, move it to the most relevant section.

If a referenced file cannot be verified, keep the link and mention it in error handling or merge notes.

---

## Phase 19 — Generate Merge Report

If `output_mode` is `merged-file-with-report`, append a report:

```markdown
## Merge Report

### Sources

- file A
- file B

### Detected Relationship

- relationship type
- selected merge strategy
- rationale

### Preserved Unique Content

| Content | Source | Merged Section | Line Range |
|---|---|---|---|
| description | A / B | `## Section` | lines N–M |

### Key Integration Points

Record where major content from each source was integrated into the merged file, using the section heading and approximate line range in the merged output. This makes the review step verifiable without re-reading the full merged file and serves as a change log when the artifact is later edited.

| Content integrated | Source | Merged Section | Line Range |
|---|---|---|---|
| brief description | A / B | `## Section Name` | lines N–M |

### Deduplicated Content

- duplicate idea → merged location

### Conflicts

- field or section conflict
- source values
- decision
- remaining risk

### Runtime-Relevant Decisions

- model decision
- tool decision
- permission decision
- output contract decision

### Preserved Links

- link

### Severity Mappings

- source severity → canonical severity

### Assessment Compliance

Include this section when an `assessment_block` was provided.

#### Must Preserve

| Item | Status | Location |
|---|---|---|
| item | preserved / missing / partial | `## Section` lines N–M |

#### Must Resolve

| Item | Decision | Rationale |
|---|---|---|
| item | decision | reason |

#### Must Not

| Item | Status | Notes |
|---|---|---|
| item | satisfied / violated | notes |

#### Context Loss Budget

| Not-Allowed Loss Item | Status | Location or Decision |
|---|---|---|
| item | preserved / unresolved | location |

#### Validation Checklist

| Check | Status | Notes |
|---|---|---|
| check | pass / fail / unresolved | notes |

### Unresolved Assessment Items

- item requiring human decision

### Unresolved Items

- item requiring human decision
```

Do not include a merge report if the user explicitly asks for a clean final file only, unless unresolved hard conflicts remain.

---

## Phase 20 — Self-Review

Before final output, check:

```text
[ ] All source files were represented.
[ ] The entity relationship was classified.
[ ] The merge strategy was selected and justified.
[ ] No unique section was dropped.
[ ] No semantic duplicate remains.
[ ] All links and relative references were preserved.
[ ] Frontmatter is valid YAML.
[ ] Runtime-relevant metadata conflicts were handled.
[ ] Tool and permission conflicts were handled.
[ ] Output contracts are compatible or split into explicit modes.
[ ] Severity systems are mapped or documented.
[ ] Scope fallback logic is preserved where relevant.
[ ] Review-selection priority is explicit where relevant.
[ ] The final document has one consistent style.
[ ] Conflicts are either resolved or documented.
[ ] Output format is valid Markdown.
[ ] Code blocks are still fenced correctly.
[ ] The final result can be used as a standalone file.
[ ] If an assessment block was provided, it was parsed before merging.
[ ] Strategy lock was respected or explicit override was documented.
[ ] Must preserve items were preserved or marked unresolved.
[ ] Must resolve items received explicit decisions.
[ ] Must not items were not violated.
[ ] Context loss budget was respected.
[ ] Human-decision-required items were preserved, split into modes/variants, or marked unresolved.
[ ] Assessment Compliance was included in the merge report when applicable.
```

---

## Phase 21 — Write Outputs to File

Determine the run directory using the same logic as Phase 16 of `/assess-md-merge`.

If `run_dir` was provided, use it directly. If an `assessment.md` exists in that directory, confirm the artifact slug matches before writing.

### Merged Artifact — Temp-Path Write and Atomic Copy

Do not write the merged artifact directly to the final output path. Use a two-step write to protect the original file if the write fails partway through:

1. **Write to temp path:** Write the merged artifact to `<run_dir>/merged-output.md`.
2. **Structural verification:** Verify the temp file before copying:
   - File is non-empty.
   - Contains at least one `# Heading`.
   - Frontmatter block is properly closed (if present — opening `---` has a matching closing `---`).
   - All fenced code blocks are closed (equal number of opening and closing fences).
3. **Atomic copy to final path:** If verification passes, run:
   ```
   python .claude/scripts/copy_files.py <run_dir>/merged-output.md <final-output-path> --overwrite
   ```
4. **If verification fails:** Stop and report the specific failure. The original file at the output path is still intact. Do not proceed to copy.

The `merged-output.md` in the run directory serves as a recoverable intermediate — it can be inspected and manually copied if the pipeline is resumed.

**Output file:** If `output_report` is provided, write the merge report to that path. Otherwise write to `<run_dir>/merge-report.md`. When called from `/merge-pipeline`, `output_report=<run_dir>/merge-and-review-report.md` is passed; write the merge section under the heading `## Merge Report`.

If the merged artifact was written to a repository path (not the run directory), record that path in the report header.

When writing to `merge-report.md` (standalone mode), append a pre-filled suggested invocation at the end:

````markdown
## Suggested Next Step

```text
/review-merged-md
target_type=<detected-target-type>
review_mode=report-only
strictness=conservative
optimization_scope=safe-only
run_dir=<run_dir>

merged_file=<merged-artifact-path>
original_files:
- <source-a>
- <source-b>
assessment_block: <run_dir>/assessment.md
```
````

**Manifest:** If `skip_manifest=true`, skip the manifest update. Otherwise update `manifest.md` in the run directory:

- Mark `/merge-md-context` as complete with the report filename.
- Add the merged artifact path:

```markdown
## Merged Artifact

Location: `<actual path in repository>`
```

Report the run directory path and merged artifact location in the chat response.

### Diff Integration

Append a `/diff-explainer` invocation to the end of `merge-report.md` for immediate diff review:

````markdown
## Review the Changes

To explain what changed between source files and the merged result:

```text
/diff-explainer
before: <source-a>
after: <merged-artifact-path>
```
````

### Merge Ancestry

If any source file is itself a previously merged artifact (a `manifest.md` in `.claude/output/` references it as a merged artifact), record the provenance chain in `manifest.md`:

```markdown
## Merge Ancestry

| Generation | Artifact | Run Directory | Date |
|---|---|---|---|
| 1 | `<earliest-source>` | — | — |
| 2 | `<source-a>` | `.claude/output/<slug>-<date>/` | YYYY-MM-DD |
| 3 | `<merged-artifact>` | `.claude/output/<current-slug>-<date>/` | YYYY-MM-DD |
```
