# Approved Changes for demo-skill

All changes below were discussed and approved.

## Selected Goals

1. **G1 — Zero reference→reference chains.** Verification: re-run the checklist's chain scan over `references/*.md` → 0 matches. Source: ref→ref chain finding (`references/a.md` says "Read references/b.md").
2. **G2 — All intake uses `AskUserQuestion` with options.** Verification: re-run the checklist's intake scan → 0 matches. Source: intake violation in `## Quick Start` ("Ask the user which file to process").
3. **G3 — Every invoked tool is declared in `allowed-tools`.** Verification: re-run the checklist's tool-scoping scan → no undeclared tools. Source: `Grep` invoked in `## Quick Start` but `allowed-tools` lists only `Read`.

## Pre-Analysis Report (complete)

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: single-line `description` (needs `>-`)
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary / marker formats)] [oversize ≥400 lines: none]
Workflow files: 0 [oversize ≥300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md → references/b.md ("Read references/b.md ...")
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" collects input without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): Grep (used in Quick Start, not declared) / none unused
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — flag as Missing
Deferred goal candidates: frontmatter (single-line description), reference cluster a.md + b.md (handled by F2 consolidation), missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

## Implementation Order

1. **F1** — Pre-existing finding that an earlier session approved
2. **F2** — Merge `references/b.md` into `references/a.md` (removes the ref→ref chain; serves G1)
3. **F3** — Convert free-form intake to `AskUserQuestion` (serves G2)
4. **F4** — Declare `Grep` in `allowed-tools` (serves G3)
5. **M1** — Add the four missing standard sections (depends on F2: the Reference Guide table lists the post-merge `references/` files)

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

## F2: Reference chain a.md → b.md; consolidate the two files

**Problem:** `references/a.md` line 5 tells the reader to "Read references/b.md for the full list of marker formats", a reference→reference chain. The two files also cover one topic (TODO summaries and the marker formats they use), so the operator approved consolidating them at step 3. Merging `b.md` into `a.md` removes the chain. Deleting `b.md` needs Gate 4 confirmation again when this plan is applied.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `references/a.md` (CREATE/UPDATE destination first) |
| DELETE | `references/b.md` (only after `a.md` holds the content and no link points at `b.md`; Gate 4 approval at apply time) |

### Exact edits

`references/a.md` before:
```
Read references/b.md for the full list of marker formats.
```
After (chain line replaced by the merged content):
```
## Marker Formats

- `TODO:` followed by text
- `FIXME:` followed by text
```

### Verification

- `references/a.md` contains both TODO-summary guidance and the two marker-format bullets
- No file under `references/` contains "references/b.md"; `references/b.md` no longer exists
- G1: the chain scan over `references/*.md` returns 0 matches

---

## F3: Free-form intake in Quick Start

**Problem:** `SKILL.md` Quick Start says "Ask the user which file to process.", which collects input without `AskUserQuestion`. The operator approved converting it.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — `## Quick Start` |

### Exact edits

Before: `Ask the user which file to process. Then grep the file for TODO markers and summarize them.`
After:
```
Use AskUserQuestion:

question: "Which file should I process?"
header: "File"
options:
  - "Current file": the file already open or discussed in this session
  - "Choose a path": the operator types a path through the automatic "Other"

Then use Grep to find TODO markers in that file and summarize them.
```

### Verification

- The intake scan finds no `ask the user` / free-form intake in `SKILL.md` (G2)
- The Quick Start block has an `options:` list

---

## F4: Grep used but not declared in allowed-tools

**Problem:** `SKILL.md` Quick Start invokes Grep ("grep the file for TODO markers") but frontmatter `allowed-tools: Read` does not list it, so the call is not pre-approved and prompts on every use (R6, Major).

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` — `allowed-tools` |

### Exact edits

Before: `allowed-tools: Read`
After: `allowed-tools: Read Grep`

### Verification

- `allowed-tools` includes `Grep`; the tool-scoping scan reports no undeclared tools (G3)

---

## M1: Missing standard sections

**Problem:** Only `## Quick Start` is present. `## When to Use`, `## When NOT to Use`, `## Testing & Validation` and `## Reference Guide` are absent. Standard sections are auto-added when the plan is applied (no extra approval needed).

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `SKILL.md` |

### Exact edits

Add after Quick Start: `## When to Use` (bullet triggers: summarizing TODO markers in a file), `## When NOT to Use` (named alternatives), `## Testing & Validation` (3-5 checks plus quality-gates checklist), `## Reference Guide` (table listing `references/a.md` — the only file left after F2 — with a purpose column).

### Verification

- All five standard headings are present in `SKILL.md`
- The Reference Guide table lists every file in `references/`

---

## Post-Implementation Verification

1. `Skill(plugin-rulebook)` reports no FAIL findings
2. `skill-reviewer` reports no Critical or Major issues
3. Each selected goal's verification passes (G1, G2, G3)
4. Security scan (selected at "Prod checks"): Grep `SKILL.md` and `references/` for credentials, keys, tokens and `${VAR}`-style substitutions
