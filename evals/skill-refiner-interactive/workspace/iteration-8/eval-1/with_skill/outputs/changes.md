# Approved Changes for demo-skill

All changes below were discussed and approved, except that every DELETE
still needs Gate 4 confirmation when applied. Implementation follows
CREATE → LINK → DELETE wherever a file is removed.

## Selected Goals

1. **G1 — Zero reference→reference chains.** Verification: re-run the pre-analysis chain scan over `references/*.md` → 0 matches. Source: ref→ref finding.
2. **G2 — All intake uses `AskUserQuestion` with options.** Verification: re-run the pre-analysis intake scan → 0 matches. Source: intake violation finding.
3. **G3 — Every invoked tool is declared in `allowed-tools`.** Verification: re-run the pre-analysis tool-scoping scan → no undeclared tools. Source: undeclared-tool finding.

Scope limits chosen: keep validation gates (no `## Testing & Validation` section is auto-added). Tool scoping is not excluded. Production check chosen: security scan (read-only scan found nothing).

## Pre-Analysis Report (complete)

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: single-line `description` (needs `>-`); no non-standard fields; allowed-tools `Read`
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO/FIXME marker handling)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md:5 "Read references/b.md for the full list of marker formats"
Spawn anti-patterns: none
Intake pattern violations: Quick Start (SKILL.md:11) "Ask the user which file to process" — free-form intake
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): 22 chars, below the 80-char floor (combined also below 80)
Tool scoping (R6): undeclared: Grep (SKILL.md:11) / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: single-line description (frontmatter), R21 description size, reference cluster (covered by F1), missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

## Implementation Order

1. **F1** — Merge `references/b.md` into `references/a.md` (removes the ref→ref chain; G1)
2. **F2** — Convert Quick Start intake to `AskUserQuestion` (G2)
3. **F3** — Declare `Grep` in `allowed-tools` (G3)
4. **F4** — Fix frontmatter `description`: multi-line `>-` form and R21 minimum length (deferred-goal finding, not a measured goal)
5. **O1** — Auto-add standard sections `When to Use`, `When NOT to Use`, `Reference Guide` (Testing & Validation excluded by operator scope limit)

F1 before F2/O1 because the Reference Guide table (O1) must list the post-merge file set. F3 is independent.

## F1: Reference→reference chain between a.md and b.md

**Problem:** `references/a.md` line 5 tells the reader to "Read references/b.md for the full list of marker formats", a reference→reference chain. The two files (5 and 4 lines) cover the same topic, TODO/FIXME marker handling, so the operator approved consolidating them, which also removes the chain.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `references/a.md` — append b.md's content, drop the "Read references/b.md" line |
| UPDATE | `SKILL.md` — pointer stays `references/a.md` (no link change needed) |
| DELETE | `references/b.md` — pending Gate 4 (runs after a.md is updated and the link is verified: CREATE → LINK → DELETE) |

### Exact edits

Before (`references/a.md`):
```
Read references/b.md for the full list of marker formats.
```
After (`references/a.md`):
```
## Marker Formats

- `TODO:` followed by text
- `FIXME:` followed by text
```

### Verification

- `references/a.md` contains both marker bullets and no directive to read another reference
- Chain scan over `references/*.md` → 0 matches (G1)
- No file anywhere links to `references/b.md`

## F2: Free-form intake in Quick Start

**Problem:** `SKILL.md` line 11 says "Ask the user which file to process" without `AskUserQuestion`. The file to process is open-ended, so the question carries no fixed option list beyond what the skill can observe; an `AskUserQuestion` block with derived options (e.g. files in the working directory containing TODO markers, plus automatic "Other" for a path) follows the intake pattern.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — Quick Start, line 11 |

### Exact edits

Before: `Ask the user which file to process. Then grep the file for TODO markers and summarize them.`
After (shape; final wording set at apply time):
```
Use AskUserQuestion to ask which file to process — options: files found by Glob that
contain TODO markers (up to 4); the operator types another path via "Other".
Then Grep the file for TODO markers and summarize them.
```

### Verification

- Intake scan over SKILL.md → 0 matches (G2)
- The question block has an `options` list of 2-4 entries

## F3: `Grep` used but not declared (R6)

**Problem:** `SKILL.md` line 11 instructs a grep of the target file, but frontmatter `allowed-tools: Read` does not include `Grep`, so each use prompts. Undeclared use is Major under R6.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — frontmatter `allowed-tools` (add `Glob` too if F2's option discovery uses it) |

### Exact edits

Before: `allowed-tools: Read`
After: `allowed-tools: Read Grep` (or `Read Glob Grep` if F2 uses Glob)

### Verification

- Tool-scoping scan → no undeclared tools, no unused declared tools (G3)

## F4: Frontmatter `description` is single-line and below the R21 floor

**Problem:** `description: Helps with demo tasks.` is one line (needs the `>-` block form) and 22 characters, under the R21 minimum of 80. It also gives no trigger conditions, so activation is weak. Not a selected goal (deferred candidate), but `Skill(plugin-rulebook)` R21 would fail it at apply time.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — frontmatter `description` |

### Exact edits

Before: `description: Helps with demo tasks.`
After (shape; wording set by the operator at apply time):
```
description: >-
  Scans a file for TODO and FIXME markers and summarizes each with its line number. Use when
  asked to list, find, or summarize TODO markers in a file.
```
(at least 80 characters, within R21 limits)

### Verification

- `Skill(plugin-rulebook)` R21 and R8 → OK

## O1: Auto-add missing standard sections

**Problem:** SKILL.md lacks `## When to Use`, `## When NOT to Use`, and `## Reference Guide`. These are auto-added in step 6 (no further approval), except `## Testing & Validation`, which the operator excluded via "Keep validation gates".

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — add three sections |

### Exact edits

Add `## When to Use` (concrete triggers: listing/summarizing TODO markers), `## When NOT to Use` (name a real alternative at apply time; none exists in this fixture), and `## Reference Guide`:

```
| Resource | Purpose |
|---|---|
| `references/a.md` | Summary format and TODO/FIXME marker formats |
```

### Verification

- The three headings are present; no `## Testing & Validation` added
- Every file in `references/` appears in the Reference Guide table

## Post-Implementation Verification

1. `Skill(plugin-rulebook)` reports no FAIL findings
2. `skill-reviewer` reports no Critical or Major issues
3. Each selected goal's verification passes (G1, G2, G3)
