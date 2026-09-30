# Approved Changes for demo-skill

All changes below were discussed and approved, except that every DELETE
still needs Gate 4 confirmation when applied. Implementation follows
CREATE → LINK → DELETE wherever a file is removed.

## Selected Goals

- **G1: Zero reference→reference chains.** Verification: re-run the checklist's chain scan over `references/*.md` → 0 matches. Source finding: `references/a.md` tells the reader to read `references/b.md`.
- **G2: All intake uses `AskUserQuestion` with options.** Verification: re-run the checklist's intake scan → 0 matches. Source finding: SKILL.md Quick Start says "Ask the user which file to process".
- **G3: Every invoked tool is declared in `allowed-tools`.** Verification: re-run the checklist's tool-scoping scan → no undeclared tools. Source finding: SKILL.md instructs `grep` (Grep tool) but `allowed-tools` lists only `Read`.

## Pre-Analysis Report (complete)

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13; tiers 100/300/490/500 from plugin-rulebook settings)
Frontmatter issues: none (no non-standard fields; description is under 80 chars so R8 does not require >-)
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details)] [oversize ≥400 lines: none]
Workflow files: 0 [oversize ≥300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md line 5 → references/b.md
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): finding — description is 23 characters, below the 80-character floor
Tool scoping (R6): Grep (undeclared, Major) / none unused
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: R21 description size; reference cluster a.md + b.md (handled by the step-3 consolidation ask); missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

## Implementation Order

1. **F1** — Pre-existing finding that an earlier session approved
2. **F2** — Tool used but not declared in allowed-tools
3. **F3** — Intake without AskUserQuestion
4. **F4** — Reference→reference chain (resolved by consolidating `b.md` into `a.md`)
5. **M1** — Missing standard sections

---

## F1: Pre-existing finding (approved earlier)

**Problem:** This finding was written by an earlier session and must survive.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` |

### Verification

- Earlier verification line

---

## F2: Tool used but not declared in allowed-tools

**Problem:** SKILL.md Quick Start tells the operator to "grep the file for TODO markers", but `allowed-tools` lists only `Read`, so the `Grep` call is not pre-approved and prompts on every use (R6 tool-completeness). Serves goal G3.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — `allowed-tools` |

### Exact edits

Before: `allowed-tools: Read`
After: `allowed-tools: Read Grep`

If F3 adds an `AskUserQuestion` call, do not list it: it is always callable, so listing it is an advisory no-op.

### Verification

- The frontmatter `allowed-tools` line includes `Grep`
- The checklist's tool-scoping scan reports no undeclared tools

---

## F3: Intake without AskUserQuestion

**Problem:** SKILL.md Quick Start says "Ask the user which file to process" as free-form intake. Pre-analysis flags this as an intake violation, and the operator approved converting it. Serves goal G2.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — Quick Start |

### Exact edits

Before: `Ask the user which file to process.`
After: an `AskUserQuestion` block (question "Which file should I process?", a short header, 2-4 options derived from the files found by `Glob`, with the automatic "Other" for a typed path).

### Verification

- The Quick Start contains an `AskUserQuestion` block with `options`
- The checklist's intake scan reports 0 matches

---

## F4: Reference→reference chain between a.md and b.md

**Problem:** `references/a.md` line 5 says "Read references/b.md for the full list of marker formats", a reference→reference chain. Both files cover the same topic (TODO marker details), so the operator approved consolidating them at the step-3 ask (saves about 3 lines: 9 lines across two files become about 6 in one). Serves goal G1.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `references/a.md` — append the "Marker Formats" section from `b.md`, drop the "Read references/b.md" directive |
| DELETE | `references/b.md` — pending Gate 4 (also the source file of a consolidation; if the operator declines the deletion, do not perform this consolidation) |

### Exact edits

Before (`a.md` line 5): `Read references/b.md for the full list of marker formats.`
After: the two `b.md` bullets (`TODO:` and `FIXME:` followed by text) under a `## Marker Formats` heading in `a.md`.

Order: CREATE/UPDATE the merged content in `a.md` first, confirm the SKILL.md pointer to `references/a.md` still resolves, then delete `b.md`.

### Verification

- `references/a.md` contains both marker bullets and no directive to read another `references/` file
- `references/b.md` no longer exists and nothing links to it
- The checklist's chain scan reports 0 matches

---

## M1: Missing standard sections

**Problem:** SKILL.md has a Quick Start but lacks `## When to Use`, `## When NOT to Use`, `## Testing & Validation` and `## Reference Guide`. These are auto-added when the plan is applied; BATCH 1 Question 4 excluded nothing relevant (the operator kept only the validation gates).

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — add the four missing sections |

### Exact edits

Add `## When to Use` (concrete trigger bullets), `## When NOT to Use` (named alternatives), `## Testing & Validation` (3-5 checks plus a quality-gates checklist) and `## Reference Guide` (a table listing `references/a.md` with its purpose).

### Verification

- All 5 standard sections are present in SKILL.md

---

## Post-Implementation Verification

1. `Skill(plugin-rulebook)` reports no FAIL findings
2. `skill-reviewer` reports no Critical or Major issues
3. Each selected goal's verification passes (G1, G2, G3)
