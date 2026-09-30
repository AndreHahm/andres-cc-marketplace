# Transcript: skill-refiner-interactive dry run (eval-1, plan-only)

Operator request: "Analyze the skill in OUTDIR/target and just write a changes.md, do not apply anything."
Target: copy of fixtures/demo-skill at `target/` (original fixture untouched).

## Quick Start A (escape hatch)
Request only names the skill and the action, so there is no predating context. No escape-hatch question asked.

## Quick Start B
Request already names the skill. Skipped.

## Quick Start C
"analyze it and just write a changes.md" counts as refine. Action question skipped. D routes to Core Workflow: Refinement.

## Refinement step 1: Locate the skill
- Path given: `target/` with `SKILL.md`. Found in project, not gitignored (under evals/).
- Mirror-pair check (R19): no `plugins/<plugin>/skills/demo-skill/` or `.claude/skills/demo-skill/` counterpart. One logical skill.
- Not user-space, not cache. No "where should I find this skill" question needed. (Simulated operator answer "skill is already located" is consistent.)

### Pre-analysis (references/pre-analysis-checklist.md)
Rulebook settings read from plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json: R13 tiers weak 100 / soft 300 / warning 490 / critical 500; R18 10/20/30; R21 description 80-1024, when_to_use max 512, combined 80-1536.

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: single-line `description` (needs `>-`); no non-standard fields (no `version`); allowed-tools `Read` fine
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (both describe TODO/FIXME marker handling)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md:5 "Read references/b.md for the full list of marker formats" (imperative directive)
Spawn anti-patterns: none
Intake pattern violations: Quick Start (line 11) "Ask the user which file to process" — free-form intake without AskUserQuestion
Argument consistency (R22): none (no $ARGUMENTS/$N in body, no argument-hint)
when_to_use split candidate: no (description is 22 chars, no embedded "Use when" clause)
Description size (R21): FINDING — description 22 chars, below 80-char floor (combined also below 80 floor)
Tool scoping (R6): undeclared: Grep (line 11 "grep the file for TODO markers") / unused declared: none
Dead links: none (references/a.md and references/b.md exist) / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: see below
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation (references/goal-derivation.md)
Findings by priority: (1) ref chain, intake; (2) undeclared tool, frontmatter issue, description size; (3) cluster, missing goal verification.
Top 3 proposed: G1 ref chain, G2 intake, G3 undeclared tool. Deferred candidates: frontmatter single-line description, R21 description size, reference cluster (handled by step 3 ask), missing goal verification; missing standard sections are auto-added in step 6, not goals.

**AskUserQuestion (simulated)** — multiSelect, up to 3
- question: "Which goals should this refinement session measure?"
- header: "Goals"
- options:
  1. "Zero ref->ref chains": verify by re-running chain scan over references/*.md -> 0 matches
  2. "Intake uses AskUserQuestion": verify by re-running intake scan -> 0 matches
  3. "Every invoked tool declared": verify by re-running tool-scoping scan -> no undeclared tools
  (+ automatic "Other" for a custom goal)
- Simulated answer: all three selected. No custom goal, so no follow-up.

## Requirements Interview
Escape hatch not used, so BATCH 1 then BATCH 2 run. Goals were selected, so Question 1 is skipped.

### BATCH 1
Q2 — question "What specific problems are you seeing?", header "Key Issues", multiSelect. Options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections". No answer given, first option chosen: **Hard-to-follow instructions**.
Q3 — "What would success look like?", header "Success". Options: "Clearer workflow" / "Lower token cost" / "Production-ready". First option: **Clearer workflow**.
Q4 — "Any areas to exclude or preserve as-is?", header "Scope Limits", multiSelect. Options: "Keep validation gates" / "Keep tool scoping". First option: **Keep validation gates** (leave validation gates and any Testing & Validation section unchanged; this also excludes auto-adding `## Testing & Validation`). Tool scoping is NOT excluded, so G3 stands.
Approved scope documented: goals G1-G3, plus clearer workflow, with Testing & Validation left out.

### BATCH 2
Routing: "Define explicitly" path (no escape hatch chosen). Trigger check:
- Extraction: no section >=50 lines. Not asked.
- Intake: detected and maps to selected goal G2. ASKED. question "Section 'Quick Start' collects user input without AskUserQuestion (free-form 'Ask the user which file to process'). Convert it?", header "Intake", options "Yes" / "No". Simulated (first option): **Yes**.
- Arguments (R22): no mismatch. Not asked.
- Desc split: not a candidate. Not asked.
- Prod checks: asked every session. question "Which production checks should I run?", header "Prod checks", multiSelect, options "Security scan" / "Error handling" / "Tool scoping" / "None needed". First option: **Security scan**. (Read-only Grep of target for credential-like strings and `${VAR}` substitutions: no matches.)
- Reference clusters: not asked here; step 3 is the single ask.

## Step 2: Load workflow reference
Read references/refinement-workflow.md (preservation gates, validation phases, rollback).

## Step 3: Consolidation opportunities
| File | Lines | Topic |
|---|---|---|
| references/a.md | 5 | TODO summaries |
| references/b.md | 4 | Marker formats |
Same domain (TODO/FIXME marker handling), 2 files -> flagged merge.
**AskUserQuestion (simulated)** — question "Should we consolidate these files? Saves ~N lines, improves clarity.", options "Consolidate" / "Leave as-is". First option: **Consolidate** (merge b.md into a.md; removes the ref->ref chain as a side effect).

## Step 4: Preservation gates
- Gate 1 Content Audit: SKILL.md 13 lines: frontmatter (5), Quick Start (core, 100%), one-line pointer to a.md. a.md 5 lines core-ish (summary format) — used whenever a summary is produced. b.md 4 lines supplementary-to-core marker list, needed whenever markers are parsed. All small; nothing >=50 lines.
- Gate 2 Capability Assessment: consolidating a.md+b.md: no content lost, a single link still gives full info -> SAFE. Converting intake to AskUserQuestion: preserves behavior -> SAFE. Adding Grep to allowed-tools: adds a grant, no impairment -> SAFE. Nothing is deleted outright except the merged source file b.md (DELETE, pending Gate 4 at apply time).
- Gates 3 and 4: applied at each move/deletion when the plan is applied, not in this plan-only run. Gate 4 not asked now; the draft marks the DELETE as pending Gate 4.

## Step 5: Plan-only exit
Request used plan-only wording ("just write a changes.md", "do not apply anything"), so the apply/plan-only/stop question is skipped. Findings were approved via interview and step-3 ask. Only the draft path needs confirming: operator named it; simulated answer "draft path is OUTDIR/changes.md". No existing draft at that path (checked), so nothing to merge.
Plan-only: step 6 not run. No edits to target, no goal measurement (steps 6-10 skipped by design; no rulebook/reviewer passes since nothing was modified). Wrote `changes.md` per references/changes-draft-format.md and stopped.
