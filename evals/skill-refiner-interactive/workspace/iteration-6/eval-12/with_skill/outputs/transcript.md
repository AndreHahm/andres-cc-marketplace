# Dry-run transcript: skill-refiner-interactive, eval 12

Operator request: "Refine it." Earlier context: operator pasted the skill's SKILL.md (= OUTDIR/target/SKILL.md) and said "the intake is sloppy and a tool isn't declared".
Target: evals/skill-refiner-interactive/workspace/iteration-6/eval-12/with_skill/outputs/target (copy of demo-skill fixture). No edits made.

## Quick Start, step A (detect predating context)
Predating context exists: a skill file was already provided and a problem already described. So the escape hatch is offered.

AskUserQuestion:
- question: "I've reviewed the context you provided. How would you like to proceed?"
- header: "Interview"
- options: "Infer from context" / "Define explicitly"

Simulated answer: **Infer from context** -> skips BATCH 1 when the interview starts. Continue to B.

## Quick Start, step B
The request already names the skill (pasted content). Plain-text "What skill do you want to work on?" is skipped.

## Quick Start, step C
The request already says refine ("Refine it."). The Action question is skipped.

## Quick Start, step D
Route: "Refine" -> Core Workflow: Refinement.

## Core Workflow: Refinement, step 1 (Locate the skill)
Simulated answer: already located at OUTDIR/target. Glob, user-space and cache searches not needed. Gitignore exclusion: the target is an eval workspace copy, not a draft in `.temp/`/`.draft/`/`.backup/`; treated as the real target per the operator.
Mirror-pair check (R19): the target has no counterpart under `plugins/<plugin>/skills/` or `.claude/skills/` (no `demo-skill` there), so it is one logical skill; Mirror question not asked.

### Step 1, pre-analysis (references/pre-analysis-checklist.md)
Resolved thresholds: plugin-rulebook found (plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json). R13: weak 100 / soft 300 / warning 490 / critical 500. R18: 10/20/30. R21: description min 80 (critical below 20), when_to_use max 512, combined min 80 / max 1536. R8: description over 80 chars needs `>-`.

Pre-analysis report:
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: none non-standard (no `version`); description is single-line but only 22 chars, so R8's >80-char `>-` requirement does not apply
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details); a.md links to b.md] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md for the full list of marker formats." (imperative directive to read another reference)
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" collects input in free text without AskUserQuestion
Argument consistency (R22): none (no $ARGUMENTS/$N in body, no argument-hint/arguments)
when_to_use split candidate: no (description is 22 chars, no embedded "Use when" clause)
Description size (R21): finding - description 22 chars is under the 80-char floor (above the 20-char critical line); no when_to_use; combined 22 < 80
Tool scoping (R6): undeclared: Grep (body says "grep the file for TODO markers", Major) / unused declared: none (Read is used)
Dead links: none (references/a.md and references/b.md exist) / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: description size (R21), reference cluster a.md + b.md, missing goal verification; also noted: references/b.md is linked only from a.md, not from SKILL.md
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```
This matches the operator's own observations: sloppy intake and an undeclared tool.

### Step 1, derive and select goals (references/goal-derivation.md)
Findings in priority order: (1st tier) ref->ref chain, (1st tier) intake violation, (2nd tier) undeclared tool Grep. Exactly 3, so all are proposed; the rest are deferred candidates (listed in the report above). Custom goal: none.

AskUserQuestion (multiSelect: true):
- question: "Which goals should this refinement session be measured against?"
- header: "Goals"
- options (description = verification check):
  - "No reference chains": Zero ref->ref chains. Check: re-run the checklist's chain scan over references/*.md -> 0 matches (source: a.md line 5)
  - "Intake via AskUserQuestion": All intake uses AskUserQuestion with options. Check: re-run the checklist's intake scan -> 0 matches (source: Quick Start "Ask the user")
  - "Declare every tool": Every invoked tool is declared in allowed-tools. Check: re-run the checklist's tool-scoping scan -> no undeclared tools (source: Grep)
  - ("Other" offered automatically for a custom goal)

Simulated answer: select all three goals. Recorded goals: G1 no ref chains, G2 intake via AskUserQuestion, G3 declare every tool. Step 8 would measure these (and would load pre-analysis-checklist.md again).

## Requirements Interview
BATCH 1: skipped. The operator chose "Infer from context", which skips BATCH 1 and comes straight to BATCH 2. (Goals were also selected, which would have skipped Question 1 anyway.) Approved scope so far: the three goals above.

BATCH 2 (templates: references/interview-question-templates.md). Which questions are asked:
- Extraction: not asked (no section >=50 lines).
- Intake: asked (intake violation detected; its goal G2 was selected).
- Arguments (R22): not asked (no mismatch).
- Desc split: not asked (no split candidate).
- Reference clusters: not asked here; step 3 is the single consolidation ask.
- Prod checks: asked (every refinement session).

AskUserQuestion (Intake):
- question: "Section 'Quick Start' collects user input without AskUserQuestion (it says 'Ask the user which file to process'). Convert it?"
- header: "Intake"
- options: "Yes" (replace free-form intake with an AskUserQuestion block; derive options from observed inputs) / "No" (keep free-form; this section intentionally takes open-ended input)
Simulated answer: **Yes**.

AskUserQuestion (Prod checks), multiSelect: true:
- question: "Which production checks should I run?"
- header: "Prod checks"
- options: "Security scan" / "Error handling" / "Tool scoping" / "None needed"
Simulated answer: the rule "choose Yes" does not map onto this non-Yes/No question, and no answer was given for it, so the first option **Security scan** is chosen (default rule).

Standard sections (When to Use, When NOT to Use, Testing & Validation, Reference Guide) need no question; they would be auto-added in step 6. Approved scope documented: goals G1-G3, intake conversion, security scan, auto-added standard sections.

## Step 2 (Load workflow reference)
Reviewed references/refinement-workflow.md: preservation Gates 1-4, validation Phases 1-7, consolidation, extraction, rollback.

## Step 3 (Identify consolidation opportunities)
Target has references/, so the step is not skipped.
Files (line counts): references/a.md 5 lines (how TODOs are summarized), references/b.md 4 lines (marker formats). Total 9 lines.
Grouping: one topic (TODO marker summarizing); a.md links to b.md. Flagged merge: a.md + b.md -> 1 file (about 7 lines, saves about 2). The merge would also remove the ref->ref chain of G1.

AskUserQuestion:
- question: "Should we consolidate these files? Saves 2 lines, improves clarity."
- header: "Consolidate"
- options: "Consolidate" / "Leave as-is"
Simulated answer: none specified for this question (the "Yes" rule covers BATCH 2 only), so the first option **Consolidate** is chosen. Approved. (Gate 4 still applies to deleting the source files later.)

## Step 4 (Preservation gates; Gates 1 and 2 run here)
GATE 1 Content Audit:
- SKILL.md (13 lines): frontmatter (name, description, allowed-tools) core; Quick Start core (used every activation).
- references/a.md (5 lines): supplementary (<20%), details of summaries.
- references/b.md (4 lines): supplementary, marker formats.
- scripts/, assets/: none.
GATE 2 Capability Assessment:
- Convert intake to AskUserQuestion: no impairment; the instruction is preserved, made structured. SAFE.
- Add `Grep` to allowed-tools: only adds a grant. SAFE.
- Consolidate a.md + b.md and redirect links: content migrates, nothing lost; execution path still complete. SAFE (migrate first; delete sources only with Gate 4 approval).
- Add standard sections: additive. SAFE.
Gates 3 and 4 are applied at each move/deletion in step 6 (not reached).

## Step 5 (Plan-only exit)
The request did not use plan-only wording ("Refine it."), so the ask is not skipped.

AskUserQuestion:
- question: "Apply the approved scope to the target skill?"
- header: "Apply"
- options: "Apply changes" / "Plan only" (write changes.md, no edits) / "Stop"
Simulated answer: **Stop**.

Result: the run ends here. Step 6 (make changes), step 7 (validation), step 8 (goal measurement), step 9 (trigger regression) and step 10 (compliance, reviewer passes, completion marker) are not executed. No `<skill-improvement-complete>` marker is emitted (nothing was applied, goals were never measured). No changes.md written, since "Stop" is not "Plan only". No file in OUTDIR/target was modified.
