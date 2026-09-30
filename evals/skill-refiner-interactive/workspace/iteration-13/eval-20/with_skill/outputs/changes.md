# Approved Changes for demo-mirror

All changes below were discussed and approved, except that every DELETE
still needs Gate 4 confirmation when applied. Implementation follows
CREATE → LINK → DELETE wherever a file is removed. (This plan has no DELETE.)

Authoritative copy for this session (Mirror question answer): `skills/demo-mirror/` (OUTDIR/target/skills/demo-mirror). The mirror `.claude/skills/demo-mirror/` (OUTDIR/target/claude-mirror/skills/demo-mirror) is brought in line with it as the first edit of step 6, and every later edit applies to BOTH copies. Nothing was overwritten while planning.

## Selected Goals

- **G1: Description within R21 tiers.** Verification: `Skill(plugin-rulebook)` R21 → OK. Source finding: description is 36 characters, under the 80-character minimum.

Deferred candidate (not selected): add a goal-measurement step (`## Goal Verification` heading or equivalent). Optional, low priority.

## Pre-Analysis Report (complete)

```
Pre-Analysis: demo-mirror
Lines: 11 - OK (R13)
Frontmatter issues: none (R5/R8 fine)
Large sections (>=50 lines): none
Reference files: 0 [clusters: none] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): none
Spawn anti-patterns: none
Intake pattern violations: none
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): FINDING - description 36 chars, below the 80-char minimum (above the 20-char critical floor)
Tool scoping (R6): none / none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: none (the 2 candidates fit under the cap of 3)
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

Also found: the two copies differ on one line (Quick Start sentence). Production security scan (operator-selected): no credentials, keys, tokens or `${VAR}` substitutions in either copy.

Scope limits from BATCH 1 Question 4: "Keep validation gates", so no `## Testing & Validation` section is added.

## Implementation Order

1. **F1** — Bring the mirror copy in line with the authoritative copy
2. **F2** — Expand the description to meet R21 (goal G1). F2 depends on F1, so the copies are identical before the edit lands in both
3. **M1** — Add the missing standard sections (When to Use, When NOT to Use, Reference Guide)

## F1: Mirror copy diverges from the authoritative copy

**Problem:** `skills/demo-mirror/SKILL.md` and `.claude/skills/demo-mirror/SKILL.md` are an R19 in-development mirror pair but differ on line 11 (Quick Start). The operator chose the `skills/demo-mirror` copy as authoritative. The mirror's extra clause "grouped by marker type" would be discarded when the mirror is overwritten. This is a rewrite in place (an edit, not a deletion), and the discarded clause is disclosed here.

### Files affected

| Action | Path |
|--------|------|
| MIRROR | `claude-mirror/skills/demo-mirror/SKILL.md` (`.claude/skills/demo-mirror/SKILL.md`) — overwritten with the authoritative copy as the first edit of step 6, after the Rollback note |

### Exact edits

Before (mirror, line 11): `Read the file, find TODO markers with Grep, and list each with its line number, grouped by marker type.`
After (line 11): `Read the file, find TODO markers with Grep, and list each with its line number.`

### Verification

- The two `SKILL.md` files are byte-identical before F2 and M1 are applied, and again afterwards

## F2: Description below the R21 minimum (goal G1)

**Problem:** `description` is `Summarizes TODO markers in one file.` (36 characters), under R21's 80-character minimum. It also gives no trigger context or exclusion. Once it is over 80 characters, R8 requires a `>-` block scalar.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `skills/demo-mirror/SKILL.md` — frontmatter `description` |
| MIRROR | `claude-mirror/skills/demo-mirror/SKILL.md` — same edit |

### Exact edits

Before: `description: Summarizes TODO markers in one file.`
After:
```
description: >-
  Summarizes TODO markers in one file by reading it, finding each TODO marker with Grep, and
  listing every marker with its line number. Use when asked to list or summarize TODO comments
  in a single file. Not for repository-wide TODO sweeps.
```
(about 238 characters once the lines are joined, inside the 80-1024 range)

### Verification

- `Skill(plugin-rulebook)` R21 reports OK for the description, and R8 reports OK
- Because the description text changed, step 9 (trigger-regression check) applies when this is implemented

## M1: Missing standard sections

**Problem:** SKILL.md has only `## Quick Start`. The standard sections `## When to Use`, `## When NOT to Use` and `## Reference Guide` are missing. `## Testing & Validation` is also missing, but the operator chose "Keep validation gates" at BATCH 1 Question 4, so it is not added.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `skills/demo-mirror/SKILL.md` — append three sections |
| MIRROR | `claude-mirror/skills/demo-mirror/SKILL.md` — same edit |

### Exact edits

Append after `## Quick Start`:
```markdown
## When to Use

- Listing or summarizing TODO markers in a single file

## When NOT to Use

- Sweeping TODO markers across a whole repository — search the repository directly instead

## Reference Guide

This skill has no reference files.
```

### Verification

- SKILL.md contains the `## When to Use`, `## When NOT to Use` and `## Reference Guide` headings
- No `## Testing & Validation` heading was added (excluded by the operator)

Note for the applying session: if step 10's `Skill(plugin-rulebook)` flags the missing Testing & Validation section as a REQUIRED FAIL, step 10 requires an `AskUserQuestion` ("Expand scope for this fix" / "Keep the exclusion") before adding it.

## Post-Implementation Verification

1. `Skill(plugin-rulebook)` reports no FAIL findings (run against both copies once they are identical)
2. `skill-reviewer` reports no Critical or Major issues
3. Each selected goal's verification passes (G1: R21 → OK)
