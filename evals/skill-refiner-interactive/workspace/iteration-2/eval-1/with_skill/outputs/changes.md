# Approved Changes for demo-skill

All changes below were discussed and approved. Implementation follows
CREATE → LINK → DELETE wherever a file is removed.

## Selected Goals

1. **Zero reference→reference chains** — Verification: re-run the pre-analysis chain scan over `references/*.md` → 0 matches. Source: ref→ref chain finding.
2. **All intake uses `AskUserQuestion` with options** — Verification: re-run the pre-analysis intake scan over SKILL.md → 0 matches. Source: intake violation finding.
3. **Every invoked tool is declared in `allowed-tools`** — Verification: re-run the pre-analysis tool-scoping scan → no undeclared tools. Source: undeclared-tool finding.

## Pre-Analysis Report (complete)

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: none
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary details / marker formats)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md:5 -> references/b.md
Spawn anti-patterns: none
Intake pattern violations: SKILL.md Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): Grep used ("grep the file") but not declared / none unused
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — flag as Missing
Deferred goal candidates: missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json consulted; no resolvable R13 tiers found, 13 lines is OK regardless
```

## Implementation Order

1. **F1** — Declare `Grep` in `allowed-tools`
2. **F2** — Convert the free-form intake in Quick Start to `AskUserQuestion`
3. **O1** — Consolidate `references/a.md` + `references/b.md` into `references/details.md` (removes the ref→ref chain)
4. **M1** — Add the missing standard sections (auto-added, no further approval needed)

## F1: Tool used but not declared in allowed-tools

**Problem:** SKILL.md Quick Start (line 10) tells the operator to "grep the file for TODO markers", but `allowed-tools` (line 4) lists only `Read`. `Grep` is not pre-approved, so each use prompts (R6 tool-completeness, Major).

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — `allowed-tools` |

### Exact edits

Before: `allowed-tools: Read`
After: `allowed-tools: Read Grep`

### Verification

- The frontmatter `allowed-tools` line includes `Grep` (goal 3: tool-scoping scan → no undeclared tools)

## F2: Free-form intake without AskUserQuestion

**Problem:** Quick Start line 10 says "Ask the user which file to process." This collects input without `AskUserQuestion`; approved in BATCH 2 to convert it.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — Quick Start |

### Exact edits

Before: `Ask the user which file to process. Then grep the file for TODO markers and summarize them.`
After: `Use AskUserQuestion to ask which file to process, with options derived from candidate files found via Glob (the operator can type another path via "Other"). Then use Grep on the chosen file for TODO markers and summarize them.`
Note: the file-discovery `Glob` would also need to be declared — if kept, extend F1's edit to `allowed-tools: Read Grep Glob`; otherwise drop the `Glob` clause and offer a fixed set of options.

### Verification

- The intake scan finds no free-form "ask the user" intake in SKILL.md (goal 2)

## O1: Consolidate references (removes the reference→reference chain)

**Problem:** `references/a.md` line 5 ("Read references/b.md for the full list of marker formats.") is a reference→reference chain. `a.md` (5 lines) and `b.md` (4 lines) cover one topic, so the consolidation was approved (step 3) and deletion of the sources was approved at Gate 4.

### Files affected

| Action | Path |
|--------|------|
| CREATE | `references/details.md` (Details + Marker Formats merged, chain line dropped) |
| UPDATE | `SKILL.md` — change `See references/a.md for details.` to `See references/details.md for details.` |
| DELETE | `references/a.md` (after LINK verified) |
| DELETE | `references/b.md` (after LINK verified) |

### Exact edits

New `references/details.md`:
```
# Details

Summaries list each TODO with its line number.

## Marker Formats

- `TODO:` followed by text
- `FIXME:` followed by text
```
Order: CREATE details.md → LINK (update SKILL.md pointer, confirm path exists) → DELETE a.md and b.md.

### Verification

- The chain scan over `references/*.md` returns 0 matches (goal 1)
- `Glob` confirms `references/details.md` exists and both old files are gone; SKILL.md has no dangling link

## M1: Missing standard sections

**Problem:** SKILL.md lacks `## When to Use`, `## When NOT to Use`, `## Testing & Validation`, and `## Reference Guide` (Minor). These are auto-added in an apply run, with no extra approval.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` |

### Exact edits

Add: `## When to Use` (concrete triggers, e.g. summarizing TODO markers in a file), `## When NOT to Use` (named alternatives), `## Testing & Validation` (3-5 checks plus a quality-gates checklist), and `## Reference Guide` (table listing `references/details.md` with a purpose column).

### Verification

- All 5 standard sections are present

## Post-Implementation Verification

1. `Skill(plugin-rulebook)` reports no FAIL findings
2. `skill-reviewer` reports no Critical or Major issues
3. Each selected goal's verification passes (goals 1-3 above)
