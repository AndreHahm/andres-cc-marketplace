# Transcript: skill-refiner-interactive dry run (iteration-13, eval-1)

Operator request: "Analyze the skill in OUTDIR/target and just write a changes.md, do not apply anything."
Target: `evals/skill-refiner-interactive/workspace/iteration-13/eval-1/with_skill/outputs/target/` (copy of the demo-skill fixture; original untouched).
Simulated answers: skill already located; select all goals offered; draft path OUTDIR/changes.md. Anything else: first option.

## Quick Start A: predating-context check
No skill text, code, problem description or discussion was provided beyond naming the skill and the action. That is not predating context, so the escape-hatch question is NOT asked. The interview runs as "Define explicitly" (full interview; no escape-hatch answer to skip BATCH 1).

## Quick Start B: "What skill do you want to work on?"
Skipped: the request names the skill.

## Quick Start C: Action question
Skipped: "analyze it and just write a changes.md" counts as refine.

## Quick Start D: routing
Refine, so go to Core Workflow: Refinement, step 1.

## Step 1: Locate the skill
- Operator answer (simulated): skill is already located, at the target path above (a project path, so the user-space/cache branches do not apply).
- Gitignore-exclusion check: `git check-ignore` shows the target path matches the global `target/` ignore rule (from the user's global gitignore). The operator has stated the skill is located there, so I proceed with it and note it.
- Mirror-pair check (R19): the target is not under `plugins/<plugin>/skills/` or `.claude/skills/`; no mirror exists. Skipped.

### Pre-analysis (step 1, immediately after locating)
Ran every check in `references/pre-analysis-checklist.md`.
- plugin-rulebook found at `plugins/plugin-devkit/skills/plugin-rulebook/`. Loaded R13 tiers (weak 100 / soft 300 / warning 490 / critical 500), R18 (10 / 20 / 30), R21 (description 80-1024, when_to_use max 512, combined 80-1536; critical description_low 20).
- SKILL.md is 13 lines: OK.

Report emitted:

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: none for R5; R8 not triggered (22-char description)
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md] [oversize ≥400 lines: none]
Workflow files: 0 [oversize ≥300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md line 5 -> references/b.md
Spawn anti-patterns: none
Intake pattern violations: none flagged (Quick Start "Ask the user which file to process" is unbounded file-path input, so plain text is correct)
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): 22 chars, below the 80 floor (warning tier, above the 20 critical line); no when_to_use; combined 22 chars, below the 80 combined floor
Tool scoping (R6): undeclared: Grep ("grep the file for TODO markers") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: reference cluster; missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation and selection (step 1, after the report)
Candidates per `references/goal-derivation.md`, priority order: (1) ref→ref chain; (2) undeclared tool; (2, frontmatter area) description size outside R21 tiers (the selection tiers do not name this row explicitly; I placed it with the frontmatter issues). Cluster and missing goal verification fall in the third tier, beyond the cap of 3, so they are deferred candidates.

AskUserQuestion (multiSelect: true):
- question: "Which goals should this session work toward?"
- header: "Goals"
- options:
  - "Zero reference chains": verify: re-run the chain scan over references/*.md, 0 matches
  - "Declare every tool": verify: re-run the tool-scoping scan, no undeclared tools
  - "R21-compliant description": verify: Skill(plugin-rulebook) R21 reports OK
- Simulated answer: select all three. Recorded as G1, G2, G3.

## Requirements Interview
### BATCH 1 (Define explicitly path; goals selected, so Question 1 is skipped)
Q2 AskUserQuestion: "What specific problems are you seeing?" header "Key Issues", multiSelect. Options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections". Answer (first option): "Hard-to-follow instructions".

Q3 AskUserQuestion: "What would success look like?" header "Success". Options: "Clearer workflow" / "Lower token cost" / "Production-ready". Answer (first option): "Clearer workflow".

Q4 AskUserQuestion: "Any areas to exclude or preserve as-is?" header "Scope Limits", multiSelect. Options: "Keep validation gates" / "Keep tool scoping". Answer (first option): "Keep validation gates". Consequence recorded: the Testing & Validation standard section is not auto-added later, and any fix needing it requires an "Expand scope" ask first. (Tool scoping is NOT excluded, so F2 is allowed.)

Approved scope documented: goals G1-G3, focus on instruction clarity, validation section excluded.

### BATCH 2
Triggered questions: Extraction no (no large section), Intake no (input is unbounded), Arguments no, Desc split no. Reference clusters are not asked here (step 3).
Prod checks, asked in every session. AskUserQuestion: "Which production checks should I run?" header "Prod checks", multiSelect. Options: "Security scan" / "Error handling" / "Tool scoping" / "None needed". Answer (first option): "Security scan". Ran a Grep-equivalent scan over SKILL.md and references/ for credentials, keys, tokens and `${VAR}` substitutions: none found.

Standard sections are auto-added in step 6, so no question.

## Step 2: Load workflow reference
Read `references/refinement-workflow.md` (preservation gates, validation phases, rollback, consolidation).

## Step 3: Consolidation opportunities
The target has a `references/` directory, so the step runs.
- `references/a.md`: 5 lines, covers how summaries list TODOs, and ends with a directive to read b.md.
- `references/b.md`: 4 lines, lists the marker formats.
- Both cover TODO marker summaries; total 9 lines; merge candidate.

AskUserQuestion: "Should we consolidate these files? Saves N lines, improves clarity." Wording filled: "Should we consolidate references/a.md and references/b.md into one file? Saves 0 net lines but removes a reference chain and one file." Options: "Consolidate" / "Leave as-is". Answer (first option): "Consolidate".

## Step 4: Preservation gates
- **Gate 1 (Content Audit):** SKILL.md, 13 lines, frontmatter plus Quick Start, core. `references/a.md`, 5 lines, marker-summary format, supplementary but tiny. `references/b.md`, 4 lines, marker formats, supplementary. No scripts/ or assets/.
- **Gate 2 (Capability Assessment):** consolidating a.md + b.md: will this impair execution? No, all 4 content lines carry over into the merged file; safe. Adding `Grep` to allowed-tools and lengthening `description`: no impairment. Adding sections: no impairment.
- **Gates 3 and 4:** applied at each move and deletion in step 6 when changes are applied. Not reached in a plan-only run; the draft marks each DELETE as pending Gate 4. The early consolidation-source ask described under Gate 4 is also not asked, because the operator chose not to apply.

## Step 5: Plan-only exit
The request used plan-only wording ("do not apply anything", "just write a changes.md"), so the Apply / Plan only / Stop ask is skipped. Only the draft path needs confirming.

AskUserQuestion: "Where should I write changes.md?" header "Draft path". Options: ".draft/_open/<plugin>/demo-skill/changes.md (default)" / "Other (type a path)". Simulated answer: OUTDIR/changes.md, i.e. `evals/skill-refiner-interactive/workspace/iteration-13/eval-1/with_skill/outputs/changes.md`.
No existing draft at that path (checked), so nothing to preserve.

On "Plan only": step 6 is NOT run. Steps 6 through 10 are all skipped: no edits to the target skill, no goal measurement (step 8), no trigger check (step 9), no rulebook or reviewer passes (step 10), and no `<skill-improvement-complete>` marker (a plan-only run ends with the draft).

Wrote `changes.md` per `references/changes-draft-format.md`: header, Selected Goals, complete Pre-Analysis Report, Implementation Order, findings F1-F3 and O1 (each with Problem, Files affected, Exact edits, Verification), and Post-Implementation Verification.

## Result
- Files written: `changes.md`, `transcript.md` (this file) under OUTDIR; `target/` is an unmodified copy of the fixture.
- Target skill edits: none.
- Open notes for the operator: (1) the target path is matched by the user's global `target/` ignore rule; (2) the description-size goal sits in the second priority tier by judgment; (3) "Keep validation gates" (first option, chosen by the dry-run default) is why the plan leaves out Testing & Validation.
