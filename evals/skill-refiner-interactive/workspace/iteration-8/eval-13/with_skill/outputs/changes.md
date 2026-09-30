# Approved Changes for demo-skill

All changes below were discussed and approved, except that every DELETE
still needs Gate 4 confirmation when applied. Implementation follows
CREATE → LINK → DELETE wherever a file is removed.

## Selected Goals

- **G1 — Zero reference→reference chains.** Verification: re-run the checklist's chain scan over `references/*.md` → 0 matches. Source: ref→ref chain finding (`references/a.md` line 5).
- **G2 — All intake uses `AskUserQuestion` with options.** Verification: re-run the checklist's intake scan → 0 matches. Source: intake violation finding (SKILL.md Quick Start, line 10).
- **G3 — Every invoked tool is declared in `allowed-tools`.** Verification: re-run the checklist's tool-scoping scan → no undeclared tools. Source: undeclared-tool finding (`grep` in SKILL.md line 10, `Grep` not declared).

## Pre-Analysis Report (complete)

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13; tiers weak 100 / soft 300 / warning 490 / critical 500)
Frontmatter issues: none non-standard (no `version`); description is single-line but 22 chars, at or under the 80-char R8 threshold, so no `>-` needed
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO/FIXME marker details)] [oversize ≥400 lines: none]
Workflow files: 0 [oversize ≥300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md line 5 ("Read references/b.md for the full list of marker formats")
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" collects input without AskUserQuestion
Argument consistency (R22): none (no $ARGUMENTS/$N in body, no argument-hint/arguments)
when_to_use split candidate: no (description is 22 chars, no embedded trigger clause)
Description size (R21): finding — description 22 chars is under the 80-char floor (R21 critical_low is 20, so a warning-tier miss); combined length also under the 80-char combined floor; no when_to_use
Tool scoping (R6): undeclared: Grep (SKILL.md line 10 "grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: description size (R21); reference cluster a.md + b.md; missing goal-verification step
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

## Implementation Order

1. **F1** — Pre-existing finding that an earlier session approved
2. **F2** — Reference→reference chain (a.md → b.md), resolved by consolidating both into one file (goal G1)
3. **F3** — Quick Start intake converted to `AskUserQuestion` (goal G2)
4. **F4** — Declare `Grep` in `allowed-tools` (goal G3)
5. **M1** — Auto-add missing standard sections (F2 must land first so the Reference Guide lists the consolidated file)

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

## F2: Reference→reference chain between a.md and b.md

**Problem:** `references/a.md` line 5 tells the reader to "Read references/b.md", a reference→reference chain that violates the one-level-deep rule. Both files cover the same topic (TODO/FIXME marker handling; 5 and 4 lines), so the operator approved consolidating them at the step-3 ask, which also removes the chain. Consolidated content is about 6 lines, saving roughly 3 lines of duplicate headings and the chain sentence. Preservation-gate notes: Gate 1 classifies both files as supplementary (<20% of activations); Gate 2 found no impairment, since every line is kept in the merged file.

### Files affected

| Action | Path |
|--------|------|
| CREATE | `references/todo-markers.md` |
| UPDATE | `SKILL.md` — replace the `references/a.md` pointer with `references/todo-markers.md` |
| DELETE | `references/a.md` — pending Gate 4 |
| DELETE | `references/b.md` — pending Gate 4 |

### Exact edits

CREATE `references/todo-markers.md`:

```markdown
# TODO Markers

Summaries list each TODO with its line number.

## Marker Formats

- `TODO:` followed by text
- `FIXME:` followed by text
```

Before (SKILL.md): `See references/a.md for details.`
After (SKILL.md): `See references/todo-markers.md for details.`

Order: CREATE the new file, LINK the SKILL.md pointer, then DELETE a.md and b.md only after Gate 4 approval and with the pointer verified. If the operator declines deleting the sources at Gate 4, do not perform this consolidation and report it as declined.

### Verification

- `references/todo-markers.md` exists and contains the summary line and both marker formats
- No `references/*.md` file contains an imperative to read another `references/` file (goal G1)
- SKILL.md has no remaining pointer to `references/a.md` or `references/b.md`

---

## F3: Quick Start collects input without AskUserQuestion

**Problem:** SKILL.md Quick Start line 10 says "Ask the user which file to process" as free-form intake. The operator chose to convert it. Options are derived from observed inputs; the automatic "Other" choice covers a typed path.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — Quick Start |

### Exact edits

Before: `Ask the user which file to process. Then grep the file for TODO markers and summarize them.`

After:

```markdown
Use AskUserQuestion to ask which file to process (options: the candidate files found with Glob; the operator types any other path through "Other"). Then grep the file for TODO markers and summarize them.
```

### Verification

- The Quick Start intake names `AskUserQuestion` and offers options (goal G2: intake scan → 0 matches)

---

## F4: `Grep` used but not declared in allowed-tools

**Problem:** SKILL.md Quick Start tells the reader to grep the file, but frontmatter `allowed-tools` lists only `Read`, so each use needs a permission prompt (R6 tool-completeness, Major). `AskUserQuestion` (added by F3) is always callable and does not need declaring. `Glob` (named by F3's option source) is not yet declared either, so add it as well. Tool scoping was not excluded at BATCH 1 Question 4 (only "Keep validation gates" was chosen).

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — `allowed-tools` |

### Exact edits

Before: `allowed-tools: Read`
After: `allowed-tools: Read Grep Glob`

### Verification

- Frontmatter `allowed-tools` includes every tool the body invokes (goal G3: tool-scoping scan → no undeclared tools)

---

## M1: Missing standard sections

**Problem:** SKILL.md lacks `## When to Use`, `## When NOT to Use` and `## Reference Guide`. These are auto-added in step 6 with no separate approval. `## Testing & Validation` is NOT added: BATCH 1 Question 4 selected "Keep validation gates", which excludes that area from the auto-add.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — append three sections |

### Exact edits

Append after Quick Start:

```markdown
## When to Use

- Summarizing TODO and FIXME markers in a file

## When NOT to Use

- Fixing the marked issues themselves: edit the file directly instead
- Reviewing skill quality: use the `skill-reviewer` agent

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/todo-markers.md` | Summary format and TODO/FIXME marker formats |
```

### Verification

- SKILL.md contains the three headings above and no `## Testing & Validation` heading
- The Reference Guide lists `references/todo-markers.md` and every file in `references/`

---

## Post-Implementation Verification

1. `Skill(plugin-rulebook)` reports no FAIL findings
2. `skill-reviewer` reports no Critical or Major issues
3. Each selected goal's verification passes (G1, G2, G3)
