# Transcript: eval-12 (skill-refiner-interactive dry run)

Context: operator pasted the skill's SKILL.md earlier (= target/SKILL.md) and said "the intake is sloppy and a tool isn't declared". Operator now says: "Refine it."
Setup: fixture copied to OUTDIR/target (SKILL.md, references/a.md, references/b.md). No edits made to any file.

## Quick Start A - Detect predating context
Predating context exists (skill file provided, problem described). Escape-hatch question:
- question: "I've reviewed the context you provided. How would you like to proceed?"
- header: "Interview"
- options: "Infer from context" / "Define explicitly"
- SIMULATED ANSWER: "Infer from context"
Effect: BATCH 1 will be skipped; continue to B. (Routing only, not an interview question.)

## Quick Start B - skill name
Skipped: the request and pasted file already identify the skill (located at OUTDIR/target).

## Quick Start C - Action question
Skipped: the request already says "Refine it".

## Quick Start D - Route
"Refine" -> Core Workflow: Refinement.

## Refinement step 1 - Locate the skill (MANDATORY)
- Skill located at OUTDIR/target (given). Not in cache, not user-space; no asks needed.
- Gitignore-exclusion: target is not in a gitignored draft path; n/a.
- Mirror-pair check (R19): no plugins/<plugin>/skills/demo-skill or .claude/skills/demo-skill pair; single copy, treat as one logical skill.

### Pre-analysis (pre-analysis-checklist.md)
Thresholds: plugin-rulebook found at plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json. R13: weak 100 / soft 300 / warning 490 / critical 500. R18: 10/20/30. R21: description 80..1024, when_to_use <=512, combined 80..1536; warning low 80, critical low 20. R8 threshold 80 chars.

Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: description is single-line but only 22 chars (<= 80, so R8 does not require >-); no non-standard fields; allowed-tools "Read" fine. None beyond the R21 item below.
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (both cover TODO/FIXME marker details)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md for the full list of marker formats" (imperative directive to read another reference)
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" collects input without AskUserQuestion
Argument consistency (R22): none (no $ARGUMENTS/$N in body; no argument-hint/arguments declared)
when_to_use split candidate: no (no embedded "Use when" clause; description 22 chars)
Description size (R21): below floor - description 22 chars (warning-low 80, critical-low 20 -> warning tier), no when_to_use, combined 22 < 80 min
Tool scoping (R6): undeclared: Grep ("grep the file for TODO markers" in Quick Start is an actual instruction) - Major / unused declared: none (Read is used to follow references)
Dead links: none (references/a.md and references/b.md exist) / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present) - Minor, auto-addable in step 6
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: see goal selection below
R13/R18 threshold source: plugin-rulebook/assets/settings.json

### Goal derivation (goal-derivation.md)
Findings mapped, in priority order (First: ref chains, intake, R22; Second: undeclared tools, dead links, oversize, tier, frontmatter/R21 size; Third: clusters, split, spawn, missing goal verification). Top 3 chosen:
1. Zero reference->reference chains. Verification: re-run checklist chain scan over references/*.md -> 0 matches. Source: ref chain in a.md.
2. All intake uses AskUserQuestion with options. Verification: re-run checklist intake scan -> 0 matches. Source: Quick Start intake.
3. Every invoked tool is declared in allowed-tools. Verification: re-run checklist tool-scoping scan -> no undeclared tools. Source: undeclared Grep.
Deferred candidates (listed in pre-analysis report): R21 description size (description 22 chars), reference cluster a.md+b.md, missing goal verification (optional).

Goal selection question:
- question: "Which goals should this refinement session measure?" (multiSelect: true, up to 3; each option description shows its verification check; "Other" = custom goal)
- header: "Goals"
- options: "Zero reference chains" (chain scan -> 0 matches) / "Intake via AskUserQuestion" (intake scan -> 0 matches) / "All tools declared" (tool-scoping scan -> no undeclared tools)
- SIMULATED ANSWER: all three selected.
Recorded goals: G1 chains, G2 intake, G3 tools. Interview is scoped to them; step 8 would measure them.

## Requirements Interview
### BATCH 1 - Refinement Focus
SKIPPED: operator chose "Infer from context" in the escape hatch (BATCH 1 is skipped; come straight to BATCH 2). Questions 1-4 not asked.

### BATCH 2 - Implementation Details
Triggers: Extraction (no large section) - not asked. Intake (violation detected; goal G2 selected) - asked. Arguments (no R22 mismatch) - not asked. Desc split (no candidate) - not asked. Prod checks - asked always. Reference clusters - not asked here (step 3 is the single consolidation ask).

Question (Intake):
- question: "Section 'Quick Start' collects user input without AskUserQuestion (\"Ask the user which file to process\" is free-form). Convert it?"
- header: "Intake"
- options: "Yes" (replace free-form intake with an AskUserQuestion block; derive options from observed inputs) / "No" (keep free-form)
- SIMULATED ANSWER: "Yes"

Question (Prod checks):
- question: "Which production checks should I run?"
- header: "Prod checks" (multiSelect: true)
- options: "Security scan" / "Error handling" / "Tool scoping" / "None needed"
- No "Yes" option exists here; interpreting the operator's "choose Yes" as affirmative: SIMULATED ANSWER: "Security scan", "Error handling", "Tool scoping" (not "None needed"). Ambiguity disclosed.

Approved scope documented: G1/G2/G3 goals; convert Quick Start intake to AskUserQuestion; production checks (security, error handling, tool scoping). Standard sections will be auto-added in step 6 (no Question 4 exclusions since BATCH 1 was skipped).

## Step 2 - Load workflow reference
Read references/refinement-workflow.md (gates 1-4, validation phases, rollback).

## Step 3 - Consolidation opportunities
references/ exists. Files with line counts: a.md 5 lines (details of TODO summaries, points to b.md), b.md 4 lines (marker formats). Same topic (TODO/FIXME markers) -> candidate merge into one file.
Question:
- question: "Should we consolidate these files? Saves N lines, improves clarity." (N ~ 3-4 lines: merged file drops duplicate heading/pointer)
- header: "Consolidate" (assumed short header)
- options: "Consolidate" / "Leave as-is"
- No answer specified; SIMULATED ANSWER: first option "Consolidate".

## Step 4 - Preservation gates
GATE 1 Content Audit: SKILL.md 13 lines - Quick Start (core, 80%+); references/a.md 5 lines (supplementary: TODO summary detail); references/b.md 4 lines (supplementary: marker formats). No scripts/assets.
GATE 2 Capability Assessment: (a) convert intake to AskUserQuestion - does not impair execution; add Grep to allowed-tools - safe; (b) merge a.md+b.md, removing a->b chain - content preserved, safe; (c) add 4 standard sections - additive, safe. No proposed deletion of unmoved content. Gates 3 and 4 apply during step 6 (Gate 4 for the consolidation's source files would be asked after step 5 only if the operator chooses to apply changes).

## Step 5 - Plan-only exit
Request did not use plan-only wording, so the ask fires.
- question: "Apply the approved scope?"
- header: "Apply"
- options: "Apply changes" / "Plan only" (write changes.md, no edits) / "Stop"
- SIMULATED ANSWER: "Stop"
Result: session ends. Gate 4 consolidation-source-deletion ask NOT asked (only after "Apply changes"). Step 6 (changes), 7 (validate), 8 (measure goals - skipped, nothing applied), 9, 10 not run. "Stop" is not "Plan only", so no changes.md written. No `<skill-improvement-complete>` marker emitted (no changes applied, goals unmeasured, compliance passes not run).

## Final state
No files edited. target/ is identical to the fixture. See final-tree.txt.
