# Dry-run transcript: skill-refiner-interactive (eval-2)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: copy of fixtures/demo-skill at OUTDIR/target (original untouched).

## Quick Start
- Step 0 (predating context): The operator named the skill path in the request. No escape-hatch question was written. Treated as "skill already located", then went on to Step 1/2 handling.
- Step 1 (What skill?): ASK skipped. Simulated answer: skill already located (OUTDIR/target).
- Step 2 (Action) — QUESTION: "What would you like to do with this skill?" Options: [Refine] [Validate]. Simulated answer: request says "refine" -> **Refine**.
- Step 3 (route): Refine -> Core Workflow: Refinement.

## Core Workflow: Refinement
### Step 1 Locate the skill
- Found at OUTDIR/target (not gitignored, not in plugin cache, not user-space).
- Mirror-pair check (R19): no `.claude/skills/demo-skill` counterpart; single copy. No Mirror Divergence question.
- Pre-analysis (references/pre-analysis-checklist.md) — report:

```
Pre-Analysis: demo-skill
Lines: 10 body — OK (R13)   [rulebook settings not found in target env; flat fallback used]
Frontmatter issues: description is a single line, no when_to_use (not a goal; deferred)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker docs)] [oversize: none]
Workflow files: 0
Reference chain violations (ref->ref): references/a.md -> "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start "Ask the user which file to process" (free-form, no AskUserQuestion)
Argument consistency (R22): none
when_to_use split candidate: no (description far under 400 chars)
Tool scoping (R6): undeclared: Grep (body says grep the file) / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent — flag as Missing
Deferred goal candidates: missing goal verification; reference cluster; when_to_use n/a
R13/R18 threshold source: skill-development fallback (500/10)
```

- Goal derivation (references/goal-derivation.md) — QUESTION (multiSelect, up to 3 + Other): "Select refinement goals"
  1. Zero reference->reference chains — verify: Grep references/*.md for directives to read another references/ file -> 0 matches (Critical)
  2. All intake uses AskUserQuestion with options — verify: intake scan (ask/prompt the user, options-less questions) -> 0 free-form (Critical)
  3. Every invoked tool declared in allowed-tools — verify: tool-scoping scan -> no undeclared tools (Major)
  Simulated answer: select all three.
  Deferred (not selected, per 3-goal cap): missing goal verification (Minor), cluster (Minor).

### Requirements Interview
- BATCH 1: goals selected -> Question 1 skipped.
  - Q2 "What specific problems are you seeing?" options [Hard-to-follow instructions] [Scattered references] [Nested sections]; simulated (first option, none given): Hard-to-follow instructions.
  - Q3 "What would success look like?" options [Clearer workflow] [Lower token cost] [Production-ready]; simulated: Clearer workflow.
  - Q4 "Any areas to exclude or preserve?" options [Keep validation gates] [Keep tool scoping] [Nothing to exclude]; simulated: Keep validation gates (no gates exist in target; no effect).
- BATCH 2 (conditional):
  - Intake pattern violation — QUESTION: "Section 'Quick Start' collects user input without AskUserQuestion (free-form 'Ask the user which file'). Convert?" [Yes] [No]; simulated: Yes.
  - Content extraction: no large sections -> skipped.
  - Consolidation question: tied to a finding whose goal wasn't selected -> skipped (handled at step 3).
  - R22: none. when_to_use split: no.
  - Production hardening — QUESTION: "Which production checks should I run?" [Security scan] [Error handling] [Tool scoping] [None needed]; simulated (first option): Security scan. Result: no credentials, no ${VAR} substitutions in SKILL.md or references -> clean.

### Step 2 Load workflow reference
- references/refinement-workflow.md consulted as directed (context only; not simulated in detail).

### Step 3 Consolidation opportunities
- references/: a.md (5 lines), b.md (4 lines) — same topic (TODO marker docs), merge candidate, saves ~3 lines + removes the chain.
- QUESTION: "Should we consolidate these files? Saves N lines, improves clarity." [Consolidate] [Leave as-is]; simulated (first option): Consolidate.

### Step 4 Preservation gates
- GATE 1 Content audit: a.md = summary-format note (core); b.md = marker formats (supplementary, all must survive).
- GATE 2 Capability assessment: merging loses nothing if both contents kept -> OK.
- GATE 3 Migration verification: destination a.md gets "Marker Formats" section before b.md removed.
- GATE 4 Operator confirmation: deletion of b.md covered by the "Consolidate" approval (migration auto-approved, deletion explicitly approved in step 3).

### Step 5 Plan-only exit
- QUESTION: "Apply the approved scope?" [Apply changes] [Plan only (write changes.md, no edits)] [Stop]; simulated answer: Apply changes. -> proceeds to step 6.

### Step 6 Make changes (CREATE -> LINK -> DELETE)
- CREATE: references/a.md now includes "## Marker Formats" (b.md content copied).
- LINK: SKILL.md updated to point only at references/a.md; Quick Start free-form ask replaced with AskUserQuestion block; allowed-tools `Read` -> `Read Grep`.
- DELETE: references/b.md removed after link verified.
- Standard sections auto-added: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start already present).

### Step 7 Validate result (7 phases)
1 inventory: SKILL.md, references/a.md. 2 read all: no gaps. 3 frontmatter: name + description present (description unchanged). 4 body: ~55 lines, OK. 5 references: a.md exists, one level deep, no ref->ref links. 6 tools: Grep declared and used, Read declared and used; AskUserQuestion always callable. 7 testing: activation phrases documented in Testing & Validation.

### Step 8 Measure goals
See goal-measurement.md. All 3 goals PASS; no "Accept with reason" prompt needed.

### Step 9 Trigger regression check
- description/when_to_use unchanged -> step skipped (per its own rule).

### Step 10 Compliance and reviewer passes
- Skill(plugin-rulebook) and skill-reviewer were NOT actually dispatched (dry-run; no sub-skill calls). Manually checked: no version field, R6 tools consistent, sections present, no FAIL-level issues seen. Noted for completeness: description is single-line/short (advisory).
- Change summary:
```
Lines: 10 -> ~55 (body; added standard sections and AskUserQuestion block)
Frontmatter: allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: references/b.md (merged into references/a.md)
plugin-rulebook: not run in dry-run (manual check: no FAIL findings observed)
```
- All selected goals PASS -> `<skill-improvement-complete>` would be emitted.
