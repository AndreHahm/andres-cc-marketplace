# Approved Changes for demo-skill

All changes below were discussed and approved, except that every DELETE
still needs Gate 4 confirmation when applied. Implementation follows
CREATE → LINK → DELETE wherever a file is removed.

## Selected Goals

- **G1: Zero reference→reference chains.** Verification: re-run the checklist's chain scan over `references/*.md` → 0 matches.
- **G2: All intake uses AskUserQuestion with options.** Verification: re-run the checklist's intake scan → 0 matches.
- **G3: Every invoked tool is declared in `allowed-tools`.** Verification: re-run the checklist's tool-scoping scan → no undeclared tools.

## Pre-Analysis Report (complete)

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: none non-standard (name, description, allowed-tools)
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO/FIXME marker handling)] [oversize ≥400 lines: none]
Workflow files: 0 [oversize ≥300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md line 5 ("Read references/b.md ...")
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): description is 22 chars, below the 80 floor (Warning tier 20-79); no when_to_use
Tool scoping (R6): undeclared: Grep (Major) / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: description size (R21); missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

## Implementation Order

1. **F1** — Consolidate `references/a.md` + `references/b.md` (resolves the ref→ref chain)
2. **F2** — Convert the free-text file intake to AskUserQuestion (F2 is independent of F1, but both edit SKILL.md's Quick Start region, so apply F1's pointer update first)
3. **F3** — Declare `Grep` in `allowed-tools`
4. **O1** — Add the four missing standard sections (auto-add, no further approval)

## F1: Reference→reference chain between a.md and b.md

**Problem:** `references/a.md` line 5 tells the reader to "Read references/b.md for the full list of marker formats", a reference→reference chain. Both files cover the same topic (TODO/FIXME markers, 5 and 4 lines). The operator approved consolidating them (saves about 2 lines) and selected goal G1.

### Files affected

| Action | Path |
|--------|------|
| CREATE | `references/todo-markers.md` (merged content of a.md and b.md, no chain directive) |
| UPDATE | `SKILL.md` — Quick Start pointer `See references/a.md for details.` → `See references/todo-markers.md for details.` |
| DELETE | `references/a.md` — pending Gate 4 |
| DELETE | `references/b.md` — pending Gate 4 |

If the operator declines the deletions at Gate 4, do not perform this consolidation (merging without deleting only duplicates content) and report it as declined.

### Exact edits

New `references/todo-markers.md`:
```markdown
# TODO Markers

Summaries list each TODO with its line number.

## Marker Formats

- `TODO:` followed by text
- `FIXME:` followed by text
```

SKILL.md before: `See references/a.md for details.`
SKILL.md after: `See references/todo-markers.md for details.`

### Verification

- `references/todo-markers.md` exists and contains every line of content from a.md and b.md
- SKILL.md points to the new file; Glob confirms the path exists
- Chain scan over `references/*.md` → 0 matches (G1)

## F2: Free-text intake in Quick Start

**Problem:** SKILL.md Quick Start says "Ask the user which file to process", collecting input without AskUserQuestion. The operator approved converting it (selected goal G2, answered Yes at the Intake question).

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — Quick Start, first sentence |

### Exact edits

Before: `Ask the user which file to process. Then grep the file for TODO markers and summarize them.`
After:
```markdown
Use AskUserQuestion to ask which file to process:

- question: "Which file should I scan for TODO markers?"
- header: "File"
- options: "Current file" (the file open in the session) / "Specify path" (the operator types a path through the automatic "Other")

Then grep the selected file for TODO markers and summarize them.
```

### Verification

- Intake scan (`ask the user`, `prompt the user`, free-form `questions:` without `options:`) → 0 matches (G2)

## F3: Grep used but not declared in allowed-tools

**Problem:** SKILL.md instructs "grep the file for TODO markers", but `allowed-tools` lists only `Read`. An undeclared tool is not pre-approved, so every use needs a permission prompt (R6, Major). Goal G3. The operator did not choose "Keep tool scoping", so this edit is in scope.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — frontmatter `allowed-tools` |

### Exact edits

Before: `allowed-tools: Read`
After: `allowed-tools: Read Grep`

### Verification

- Frontmatter `allowed-tools` includes `Grep`; tool-scoping scan → no undeclared tools (G3)
- `AskUserQuestion` (added by F2) needs no entry: it is always callable

## O1: Missing standard sections

**Problem:** Only `## Quick Start` is present. `When to Use`, `When NOT to Use`, `Testing & Validation` and `Reference Guide` are absent. These are auto-added in step 6 without further approval (the operator excluded no area that binds them).

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — append `## When to Use`, `## When NOT to Use`, `## Testing & Validation`, `## Reference Guide` |

### Exact edits

Append the four sections. `When to Use`: concrete triggers (scanning a file for TODO/FIXME markers). `When NOT to Use`: named alternatives (no specific alternative skill exists for this fixture, so say so explicitly). `Testing & Validation`: 3-5 checks plus a quality-gates checklist. `Reference Guide`: a table listing `references/todo-markers.md` (or `references/a.md` and `references/b.md` if F1 is declined).

### Verification

- All 5 standard headings present

## Post-Implementation Verification

1. `Skill(plugin-rulebook)` reports no FAIL findings
2. `skill-reviewer` reports no Critical or Major issues
3. Each selected goal's verification passes (G1, G2, G3)
4. Deferred, not planned here: R21 description size (22 chars, Warning tier) and the optional goal-verification step. They can be picked up in a later session.
