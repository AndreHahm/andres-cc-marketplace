# Approved Changes for demo-skill

All changes below were discussed and approved, except that every DELETE
still needs Gate 4 confirmation when applied. Implementation follows
CREATE → LINK → DELETE wherever a file is removed.

## Selected Goals

1. **G1: Zero reference→reference chains** (source: ref→ref chain finding)
   - Verification: re-run the checklist's chain scan over `references/*.md` → 0 matches
2. **G2: Every invoked tool is declared in `allowed-tools`** (source: undeclared-tool finding)
   - Verification: re-run the checklist's tool-scoping scan → no undeclared tools
3. **G3: `description` and `when_to_use` within the R21 tiers** (source: description-size finding)
   - Verification: `Skill(plugin-rulebook)` R21 → OK

## Pre-Analysis Report (complete)

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: none for R5 (no non-standard fields); R8 not triggered (description is 22 characters, under the 80-character block-scalar threshold)
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md (both cover TODO marker summaries)] [oversize ≥400 lines: none]
Workflow files: 0 [oversize ≥300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md line 5 ("Read references/b.md for the full list of marker formats.")
Spawn anti-patterns: none
Intake pattern violations: none flagged — SKILL.md Quick Start "Ask the user which file to process" takes a file path, which is unbounded input with no predictable options, so plain text is correct
Argument consistency (R22): none (no $ARGUMENTS / $N / named-argument use in the body; no argument-hint or arguments declared)
when_to_use split candidate: no (description has no embedded trigger clause and is well under 400 characters)
Description size (R21): description 22 chars, below the 80-char floor (past the warning line, above the 20-char critical line); no when_to_use; combined 22 chars, below the 80-char combined floor
Tool scoping (R6): undeclared: Grep (Quick Start says "grep the file for TODO markers") / unused declared: none (Read is used)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (only Quick Start present)
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: reference cluster (a.md + b.md) — addressed by F1 through the step-3 consolidation anyway; missing goal verification section (optional, not a defect)
R13/R18 threshold source: plugin-rulebook/assets/settings.json (plugins/plugin-devkit copy)
```

Notes on judgment calls: "grep the file" is lowercase prose but it is an instruction to search, so it is treated as a `Grep` invocation (Major, R6). R21's floor is 80 (warning) and 20 (critical), so a 22-character description is a warning-tier finding. `references/a.md` and `b.md` are also non-descriptive file names (R10, REQUIRED, not part of the pre-analysis checklist); F1's new file name addresses it.

## Scope Decisions Recorded

- Step-3 consolidation ask: "Consolidate" (merge `a.md` and `b.md` into one file; 9 lines total).
- BATCH 1 Question 4: "Keep validation gates" — the `Testing & Validation` section is NOT added by this plan (O1 below skips it).
- BATCH 2 production checks: "Security scan" — no credentials, keys, tokens or `${VAR}` substitutions found in SKILL.md or references/.
- Plan-only run: no edits were made to the target skill; no goal measurement was run.

## Implementation Order

1. **F1** — Consolidate `references/a.md` + `references/b.md` into `references/todo-markers.md`, removing the ref→ref chain (G1)
2. **F2** — Declare `Grep` in `allowed-tools` (G2)
3. **F3** — Rewrite `description` to meet the R21 floor (G3; F3 and F2 both edit the frontmatter, so apply together)
4. **O1** — Add the missing standard sections (F1 must land first so the Reference Guide lists the new file)

## F1: Reference→reference chain between a.md and b.md

**Problem:** `references/a.md` line 5 tells the reader to "Read references/b.md for the full list of marker formats", a reference→reference chain (references must be one level deep from SKILL.md). The two files are also one topic (TODO markers) and total 9 lines, and their names (`a`, `b`) are non-descriptive (R10). The operator approved consolidation at step 3.

### Files affected

| Action | Path |
|--------|------|
| CREATE | `references/todo-markers.md` |
| UPDATE | `SKILL.md` — Quick Start pointer (line 11) |
| DELETE | `references/a.md` — pending Gate 4 |
| DELETE | `references/b.md` — pending Gate 4 |

### Exact edits

New `references/todo-markers.md` (merged content of both files, chain directive dropped):

```markdown
# TODO Markers

Summaries list each TODO with its line number.

## Marker Formats

- `TODO:` followed by text
- `FIXME:` followed by text
```

`SKILL.md` line 11:

Before: `See references/a.md for details.`
After: `See references/todo-markers.md for details.`

Order: CREATE `todo-markers.md` → Gate 3 (destination complete: all 4 content lines of `a.md` and `b.md` present) → LINK the SKILL.md pointer → Gate 4 confirmation → DELETE `a.md` and `b.md`. If the operator declines deleting the source files, do not perform this consolidation and report it as declined (G1 then stays unmet unless the `a.md` line 5 directive is removed instead).

### Verification

- `Glob references/*.md` lists only `todo-markers.md`
- `Grep` for `references/` in `references/*.md` returns 0 matches
- SKILL.md points at `references/todo-markers.md`, which exists

## F2: Tool used but not declared in allowed-tools

**Problem:** The Quick Start tells the operator to "grep the file for TODO markers" (SKILL.md line 9), but `allowed-tools` lists only `Read`, so `Grep` is not pre-approved and prompts on every use (R6 tool-completeness, Major).

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — `allowed-tools` (line 4) |

### Exact edits

Before: `allowed-tools: Read`
After: `allowed-tools: Read Grep`

### Verification

- The frontmatter `allowed-tools` line includes `Grep`
- Re-run of the tool-scoping scan reports no undeclared tools and no unused declared tools

## F3: Description below the R21 floor

**Problem:** `description` is "Helps with demo tasks." (22 characters) against an 80-character floor (R21). It names no concrete action and no trigger condition, so activation is unreliable. Both are fixed by a fuller What+When description.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — `description` (line 3) |

### Exact edits

Before: `description: Helps with demo tasks.`

After (147 characters; over 80 so R8 requires the `>-` block scalar):

```yaml
description: >-
  Finds TODO and FIXME markers in a single file and summarizes each with its line number.
  Use when asked to list or summarize TODO markers in a file.
```

Because `description` text changes, the apply session must run step 9 (trigger-regression ask) before finalizing.

### Verification

- `Skill(plugin-rulebook)` R21 and R8 report OK
- Description is between 80 and 1018 characters

## O1: Missing standard sections

**Problem:** Only `## Quick Start` exists. The standard-section policy adds `## When to Use`, `## When NOT to Use` and `## Reference Guide` when absent. `## Testing & Validation` is deliberately NOT added, because the operator chose "Keep validation gates" at BATCH 1 Question 4 (that exclusion binds the auto-added standard sections). If a later `plugin-rulebook` or `skill-reviewer` pass raises a finding that needs that section, the apply session must ask "Expand scope for this fix" / "Keep the exclusion" first.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — append three sections after Quick Start |

### Exact edits

Append after the Quick Start section (wording to be confirmed at apply time; the "named alternatives" for When NOT to Use cannot be inferred from the skill's own content, so the applier asks the operator for them):

```markdown
## When to Use

- Summarizing the TODO and FIXME markers in one file
- Listing each marker with its line number

## When NOT to Use

- Searching for markers across many files or a whole repository (name the preferred alternative here)
- Tracking or resolving the TODOs themselves (name the preferred alternative here)

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/todo-markers.md` | How summaries are formatted and the recognized marker formats |
```

### Verification

- `Grep` for `^## ` in SKILL.md shows Quick Start, When to Use, When NOT to Use and Reference Guide; no `Testing & Validation` heading was added
- The Reference Guide lists exactly the files present in `references/`

## Post-Implementation Verification

1. `Skill(plugin-rulebook)` reports no FAIL findings
2. `skill-reviewer` reports no Critical or Major issues
3. Each selected goal's verification passes (G1, G2, G3)
