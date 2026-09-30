# Simulated transcript: skill-refiner-interactive, eval-12 (escape hatch, inferred)

Operator request: "Refine it." Predating context: operator pasted the skill's SKILL.md (= target/SKILL.md) and said "the intake is sloppy and a tool isn't declared". Target fixture copied to OUTDIR/target/.

## Quick Start A (escape hatch)
Predating context exists (skill file provided, problem described) -> ask:

- question: "I've reviewed the context you provided. How would you like to proceed?"
- header: "Interview"
- options: "Infer from context" / "Define explicitly"
- SIMULATED ANSWER: "Infer from context" -> BATCH 1 will be skipped; continue to B.

## Quick Start B
Request already names the skill (the pasted one) and skill is located at OUTDIR/target -> skipped the "What skill?" question.

## Quick Start C
Request already says "Refine it" -> Action question skipped.

## Quick Start D
Route: Refine -> Core Workflow: Refinement.

## Refinement step 1 (Locate)
- Skill located at OUTDIR/target (given). Not gitignored, not user-space, not cache.
- Mirror-pair check (R19): target is not under plugins/<plugin>/skills/ and has no .claude/skills/ twin -> single copy, no Mirror question.

### Pre-analysis (references/pre-analysis-checklist.md)
R13/R18/R21 tiers loaded from plugin-rulebook assets/settings.json (R13: 100/300/490/500; R18: 10/20/30; R21: description min 80 warn, 20 critical; when_to_use max 512; combined min 80).

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: description is single-line (needs >-); no forbidden fields
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details) ] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md -> "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none (no $ARGUMENTS use, no argument-hint)
when_to_use split candidate: no
Description size (R21): finding - description is 22 chars, below the 80-char warning floor (above 20-char critical floor): Warning
Tool scoping (R6): undeclared: Grep (body instructs "grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: see goal selection below
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation and selection (references/goal-derivation.md)
Findings by priority: (1) ref->ref chain, intake violation; (2) undeclared tool Grep, frontmatter single-line description, R21 description size; (3) cluster, goal verification.
Top 3 goals chosen: 1) Zero reference->reference chains; 2) All intake uses AskUserQuestion with options; 3) Every invoked tool is declared in allowed-tools.
Deferred candidates (listed in pre-analysis report): single-line description / R21 description size, reference cluster a.md+b.md (handled by step 3 ask), missing goal verification. Missing standard sections are auto-added in step 6, not goals.

AskUserQuestion (multiSelect: true):
- question: "Which goals should this refinement session commit to?"
- header: "Goals"
- options:
  - "Zero ref->ref chains": Verify: re-run chain scan over references/*.md -> 0 matches (source: references/a.md reads references/b.md)
  - "Intake via AskUserQuestion": Verify: re-run intake scan -> 0 matches (source: Quick Start "Ask the user which file")
  - "All tools declared": Verify: re-run tool-scoping scan -> no undeclared tools (source: Grep used, not in allowed-tools)
  - (Other: custom goal, needs a verification check)
- SIMULATED ANSWER: all three selected. Recorded.

## Requirements Interview
### BATCH 1
Operator chose "Infer from context" -> BATCH 1 skipped (and goals were selected, so Question 1 would be skipped anyway).

### BATCH 2 (Implementation Details)
Applicable questions, per pre-analysis triggers:
- Extraction: not triggered (no section >=50 lines) - not asked.
- Intake: triggered, and its finding maps to a selected goal -> ask:
  - question: "Section 'Quick Start' collects user input without AskUserQuestion (asks the user which file to process in free text). Convert it?"
  - header: "Intake"
  - options: "Yes" / "No"
  - SIMULATED ANSWER: "Yes"
- Arguments (R22): not triggered - not asked.
- Desc split: not triggered (no embedded trigger clause, description far under 400 chars) - not asked.
- Prod checks (asked in every session):
  - question: "Which production checks should I run?"
  - header: "Prod checks"
  - multiSelect: true
  - options: "Security scan" / "Error handling" / "Tool scoping" / "None needed"
  - SIMULATED ANSWER: no 'Yes' option exists here, so the default rule applied (first option): "Security scan".
- Reference clusters: not asked here (step 3 owns it).
Standard sections are auto-added in step 6; no question. Approved scope documented: goals 1-3, Intake conversion, Security scan.

## Step 2 (Load workflow reference)
Reviewed references/refinement-workflow.md (preservation gates, validation phases, rollback).

## Step 3 (Consolidation)
target has references/ -> not skipped. Files: a.md (5 lines), b.md (4 lines). Same topic (TODO marker details) -> potential merge.

AskUserQuestion:
- question: "Should we consolidate these files? Saves ~2 lines (header/link duplication), improves clarity. (a.md, b.md)"
- header: "Consolidate"
- options: "Consolidate" / "Leave as-is"
- No answer specified; default rule -> first option: "Consolidate".

## Step 4 (Preservation gates)
- GATE 1 Content Audit: SKILL.md core (Quick Start: intake, TODO summarize, pointer to a.md). a.md: summary format (supplementary, pointed to by core) plus chain directive; b.md: marker formats (supplementary). No item classified deletable outright.
- GATE 2 Capability Assessment: consolidating a.md+b.md does not impair execution provided all content migrates; no deletions of unmigrated content.
- GATE 4 (asked right after the consolidation approval, for the source files):
  - question: "Okay to delete the originals (references/a.md, references/b.md) once their content is in the consolidated file?"
  - header: "Delete"
  - options: "Delete" / "Keep"
  - No answer specified; default -> first option: "Delete" (approved).
- Gates 3 and 4 for moves/deletions are deferred to step 6 (not reached).

## Step 5 (Plan-only exit)
Request did not use plan-only wording, so ask:
- question: "Apply the approved scope to the target skill?"
- header: "Apply"
- options: "Apply changes" / "Plan only" / "Stop"
- SIMULATED ANSWER: "Stop"

Result: stop. Step 6 not run, no edits, no changes.md written, no goal measurement (steps 7-10 not run), no rollback set-up, and `<skill-improvement-complete>` NOT emitted. target/ left identical to the fixture.

## Final state
Files under OUTDIR/target unchanged (see final-tree.txt).
