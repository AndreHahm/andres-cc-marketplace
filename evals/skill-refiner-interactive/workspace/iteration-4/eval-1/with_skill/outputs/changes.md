# Approved Changes for demo-skill

All changes below were discussed and approved. Implementation follows
CREATE → LINK → DELETE wherever a file is removed.

## Selected Goals

1. **G1 — Zero reference→reference chains.** Verification: re-run the pre-analysis chain scan over `references/*.md` (imperative directives to read another `references/` file) → 0 matches. Source: reference chain finding (`references/a.md:5`).
2. **G2 — All intake uses `AskUserQuestion` with options.** Verification: re-run the pre-analysis intake scan over SKILL.md (`ask the user`, `prompt the user`, free-form `questions:` blocks) → 0 matches. Source: intake violation (`SKILL.md:11`).
3. **G3 — Every invoked tool is declared in `allowed-tools`.** Verification: re-run the pre-analysis tool-scoping scan → no undeclared tools. Source: `Grep` used at `SKILL.md:11` but not declared.

## Pre-Analysis Report (complete)

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: description 22 chars, below R21 min 80 (no what+when)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker handling)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md:5 -> references/b.md
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): Grep (used at SKILL.md:11, not declared) / none unused
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — flag as Missing
Deferred goal candidates: frontmatter (R21 description min), missing goal verification, reference cluster (handled by F1), missing standard sections (handled by M1)
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

Not in this plan (deferred, not approved this session): rewrite `description` to meet R21's 80-character minimum with a what+when formula; add a goal-measurement step to demo-skill itself.

## Implementation Order

1. **F1** — Merge `references/b.md` into `references/a.md` and delete `b.md` (removes the ref→ref chain; serves G1)
2. **F2** — Convert the Quick Start file-intake to `AskUserQuestion` (serves G2)
3. **F3** — Declare `Grep` in `allowed-tools` (serves G3)
4. **M1** — Add the four missing standard sections (depends on F1: the Reference Guide table must list the post-merge reference files only)

## F1: Reference chain `a.md` → `b.md`, resolved by consolidating

**Problem:** `references/a.md` line 5 tells the reader to "Read references/b.md for the full list of marker formats", a reference→reference chain (references must be one level deep from SKILL.md). `b.md` is reachable only through `a.md`. Both files cover the same topic (TODO/FIXME marker handling), so the operator approved consolidating them at the step-3 ask. Merging saves 1 line (9 → 8) and, more importantly, removes the chain.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `references/a.md` (append b.md's content, drop the chain line) |
| DELETE | `references/b.md` (only after the merged content is verified; Gate 4 operator confirmation required at apply time) |

### Exact edits

`references/a.md` — Before (lines 3-5):

```
Summaries list each TODO with its line number.

Read references/b.md for the full list of marker formats.
```

After (full file, 8 lines):

```
# Details

Summaries list each TODO with its line number.

## Marker Formats

- `TODO:` followed by text
- `FIXME:` followed by text
```

Then delete `references/b.md`. SKILL.md's existing pointer to `references/a.md` (line 13) stays valid, so no LINK change is needed. Order: CREATE/UPDATE a.md → confirm the two marker lines are present → Gate 3 (destination complete) → Gate 4 (ask the operator to approve deleting `b.md`; if declined, do not perform the consolidation, report it as declined) → DELETE `b.md`.

### Verification

- `Grep` for `references/` inside `references/*.md` → 0 directive matches (G1)
- `references/b.md` no longer exists; `a.md` contains both `TODO:` and `FIXME:` lines
- `Glob` confirms every `references/` path linked from SKILL.md exists

## F2: Plain-text file intake in Quick Start

**Problem:** `SKILL.md` line 11 says "Ask the user which file to process." That collects input without `AskUserQuestion`, which the pre-analysis flags as an intake violation. The operator approved converting it. Note that a file path is open-ended input; the automatic "Other" choice is how the operator types a path, so the options cover only the common cases.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — Quick Start, line 11 |

### Exact edits

Before:

```
Ask the user which file to process. Then grep the file for TODO markers and summarize them.
```

After:

```
Use AskUserQuestion — question: "Which file should I process?", options: "File already in context" / "A file I will name" (the operator types a path through the automatic "Other"). Then use Grep on that file for TODO markers and summarize them.
```

(The "use Grep" wording also makes the tool use explicit for F3.)

### Verification

- Intake scan over SKILL.md for `ask the user` / `prompt the user` → 0 matches (G2)
- The Quick Start names `AskUserQuestion` with explicit options

## F3: `Grep` used but not declared in `allowed-tools`

**Problem:** SKILL.md line 11 instructs the reader to grep the file for TODO markers (a `Grep` invocation), but frontmatter line 4 declares only `Read`. An undeclared tool is not pre-approved, so every use prompts (R6 tool completeness, Major). `AskUserQuestion` (added by F2) needs no grant; it is always callable, and listing it is an R5 ADVISORY no-op.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — `allowed-tools` (frontmatter line 4) |

### Exact edits

Before: `allowed-tools: Read`
After: `allowed-tools: Read Grep`

### Verification

- Frontmatter `allowed-tools` includes `Grep`; tool-scoping scan shows no undeclared tools (G3)
- No declared tool is unused (`Read` is still used)

## M1: Missing standard sections

**Problem:** SKILL.md has only `## Quick Start`. `## When to Use`, `## When NOT to Use`, `## Testing & Validation` and `## Reference Guide` are all absent. Per the refinement workflow these are auto-added without operator approval.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` (append four sections after Quick Start) |

### Exact edits

Add, in order (content sketch, derived only from what the skill already does):

- `## When to Use` — bullets: summarising TODO/FIXME markers in a named file.
- `## When NOT to Use` — explicit redirections with named alternatives. No sibling skills can be identified from demo-skill's own content, so the applying session must name real alternatives (or ask the operator) rather than invent any.
- `## Testing & Validation` — 3-5 checks plus a quality-gates checklist, e.g. "asked for a file via AskUserQuestion", "every TODO listed with its line number", "FIXME markers handled per references/a.md".
- `## Reference Guide` — table with one row: `references/a.md` | TODO/FIXME summary rules and marker formats. (Lists only `a.md`, since F1 removes `b.md`.)

### Verification

- All 5 standard headings present in SKILL.md
- Reference Guide lists exactly the files present in `references/` after F1

## Post-Implementation Verification

1. `Skill(plugin-rulebook)` reports no FAIL findings
2. `skill-reviewer` reports no Critical or Major issues
3. Each selected goal's verification passes (G1, G2, G3)
