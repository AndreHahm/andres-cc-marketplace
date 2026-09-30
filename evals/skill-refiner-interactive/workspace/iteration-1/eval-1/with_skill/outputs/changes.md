# Approved Changes for demo-skill

All changes below were discussed and approved. Implementation follows
CREATE → LINK → DELETE wherever a file is removed.

Target skill directory: `OUTDIR/target/` (SKILL.md, references/a.md, references/b.md).

## Selected Goals

- **G1 — Zero reference→reference chains.** Verification: re-run the pre-analysis chain scan over `references/*.md` (imperative directives to read another `references/` file) → 0 matches. Source: F1.
- **G2 — All user intake uses AskUserQuestion with options.** Verification: re-run the pre-analysis intake scan (`ask the user`, `prompt the user`, free-form `questions:` blocks) → 0 matches. Source: F2.
- **G3 — Every invoked tool is declared in `allowed-tools`.** Verification: re-run the pre-analysis tool-scoping scan → no undeclared tools. Source: F3.

## Pre-Analysis Report (complete)

```
Pre-Analysis: demo-skill
Lines: 8 body (13 total) - OK (R13)
Frontmatter issues: description is single-line (not >-); no when_to_use
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker formats)] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md:5 -> references/b.md
Spawn anti-patterns: none
Intake pattern violations: Quick Start (line 11) - asks the user for a file with no AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): Grep (used line 11, not declared) / none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: reference cluster a.md+b.md (addressed by O1 via Step 3 approval); missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

## Implementation Order

1. **F1** — Remove the reference→reference directive by inlining b.md's marker list into a.md
2. **F2** — Convert the free-form file intake in Quick Start to AskUserQuestion
3. **F3** — Declare `Grep` in `allowed-tools`
4. **O1** — Delete the now-orphaned `references/b.md` (depends on F1)

Note for the applying session: step 6's standard-section auto-add (When to Use, When NOT to Use, Testing & Validation, Reference Guide) and the approved production check (Security scan) are not part of this plan's findings; run them per the normal workflow.

---

## F1: Reference→reference chain (a.md → b.md)

**Problem:** `references/a.md` line 5 says "Read references/b.md for the full list of marker formats." A reference file must not direct the reader to another reference file; SKILL.md loads a.md, and b.md would only be reached through that chain. Goal G1.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `references/a.md` |

### Exact edits

    # Before (a.md, line 5):
    Read references/b.md for the full list of marker formats.
    # After:
    Marker formats:

    - `TODO:` followed by text
    - `FIXME:` followed by text

### Verification

- `Grep` for `references/` in `references/*.md` → no directive to read another reference file
- a.md contains both marker bullets (Gate 3 migration check, before O1 deletes b.md)

---

## F2: Intake without AskUserQuestion in Quick Start

**Problem:** `SKILL.md` line 11 says "Ask the user which file to process." with no AskUserQuestion block, so the intake is free-form. Goal G2.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — Quick Start, line 11 |

### Exact edits

    # Before:
    Ask the user which file to process. Then grep the file for TODO markers and summarize them.
    # After:
    Use AskUserQuestion to ask which file to process (options: the open/recently
    changed files found with Glob, plus "Other" for a typed path). Then grep the
    file for TODO markers and summarize them.

(Exact option list is for the applying session to derive from observed inputs; the requirement is a structured `AskUserQuestion` with options.)

### Verification

- Intake scan over SKILL.md → no free-form "ask the user" intake remains
- Quick Start names AskUserQuestion with options

---

## F3: `Grep` used but not declared in allowed-tools

**Problem:** `SKILL.md` line 11 instructs the operator to grep the file, and F2's new text also uses `Glob`; frontmatter line 4 declares only `Read`, so the call is blocked at runtime (R6). Goal G3.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — frontmatter `allowed-tools` |

### Exact edits

    # Before:
    allowed-tools: Read
    # After:
    allowed-tools: Read Grep Glob

(Include `Glob` only if F2's edit keeps the Glob-based option list; otherwise `Read Grep`.)

### Verification

- Re-run the tool-scoping scan → no undeclared tools, no unused declared tools

---

## O1: Delete orphaned references/b.md (Gate 4 approved)

**Problem:** After F1, b.md's content lives in a.md and nothing links to b.md (SKILL.md links only a.md). Keeping it leaves a dead duplicate. Operator approved consolidation and the deletion.

### Files affected

| Action | Path |
|--------|------|
| DELETE | `references/b.md` (only after F1 lands and a.md verified to hold both bullets) |

### Exact edits

CREATE (F1: inline into a.md) → LINK (no other links exist to update) → DELETE `references/b.md`.

### Verification

- `Glob references/*.md` → only a.md
- `Grep` for `b.md` across the skill → 0 matches

---

## Post-Implementation Verification

1. `Skill(plugin-rulebook)` reports no FAIL findings
2. `skill-reviewer` reports no Critical or Major issues
3. Each selected goal's verification passes (G1, G2, G3)
