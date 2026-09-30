# Transcript: skill-refiner-interactive dry run (eval-18)

Operator request: "Refine the skill in OUTDIR/target."
OUTDIR = evals/skill-refiner-interactive/workspace/iteration-13/eval-18/with_skill/outputs
Target (copy of fixtures/one-finding-skill): OUTDIR/target/SKILL.md

## Quick Start A: detect predating context (escape hatch)

The request only names the skill and the action ("Refine"). No skill file was pasted, no problem was described, and no skill is being discussed. The skill says such a request is not predating context. Result: NO predating context, so the escape-hatch question is NOT asked.

(The task brief listed a simulated answer "Define explicitly" for that question. Because the skill's own rule means the question never fires, it is not asked and the simulated answer is unused. The interview style is the default full interview: BATCH 1 then BATCH 2.)

## Quick Start B: "What skill do you want to work on?"

Skipped: the request already names the skill (OUTDIR/target).

## Quick Start C: Action question

Skipped: the request already says "Refine".

## Quick Start D: route

"Refine" -> Core Workflow: Refinement. No interview question is asked before step 1's pre-analysis and goal selection.

## Refinement step 1: Locate the skill

- The skill is at OUTDIR/target/SKILL.md (simulated operator: already located). Project search by Glob `**/skills/<name>/SKILL.md` is unnecessary because the path was given.
- Gitignore exclusion: the path is not a gitignored draft directory (.temp/, .draft/, .backup/). Not excluded.
- Mirror-pair check (R19): the target is not at plugins/<plugin>/skills/<name>/ or .claude/skills/<name>/, so there is no mirror pair. Nothing to compare, no Mirror question.
- Not user-space, not plugin cache, found. No locate question asked.

### Step 1 pre-analysis (references/pre-analysis-checklist.md)

- plugin-rulebook found at plugins/plugin-devkit/skills/plugin-rulebook/; read assets/settings.json. R13 tiers: weak_warning 100, soft_warning 300, warning 490, critical 500. R18 tiers: weak_warning 10, warning 20, critical 30. R21: description min 80 / max 1024, when_to_use max 512, combined min 80 / max 1536 (warning: description_low 80, description_high 1018, when_to_use_high 506, combined_high 1524; critical: 20 / 1024 / 512 / 1536). R8: descriptions over 80 characters must use the `>-` block scalar.
- Line count: 40 total lines -> OK (under 100, R13).
- Frontmatter: `description` is a single-line plain scalar of 138 characters, over R8's 80-character threshold, so it needs `>-`. FINDING. `allowed-tools: Read Grep` fine. No `version` field (R5 ok). `when_to_use` is a `>-` block (ok).
- Sections >= 50 lines: none (whole file is 40 lines).
- References: no references/ directory. Clusters: none. Oversize: none.
- Workflows: no workflows/ directory. Chains: none.
- Reference->reference chains: none (no references).
- Spawn anti-patterns: none (no Agent spawning).
- Intake: no `ask the user`, `prompt the user` or free-form `questions:` blocks. None.
- R22: no $ARGUMENTS / $0 / $1 / $name in body; no argument-hint/arguments in frontmatter. Consistent.
- when_to_use split candidate: a `when_to_use` field is already present. No.
- Description size (R21): description 138, when_to_use 66, combined 204. All within tiers (>= 80 floor, under limits).
- Tool scoping: body invokes Read and Grep, both declared; no undeclared tool. Declared tools all used (Read, Grep). None unused.
- Dead links / cross-skill references: none.
- Missing standard sections: Quick Start, When to Use, When NOT to Use, Testing & Validation, Reference Guide all present.
- Goal verification: `## Goal Verification` present.

### Pre-analysis report

```
Pre-Analysis: one-finding-skill
Lines: 40 - OK (R13)
Frontmatter issues: single-line description of 138 chars exceeds R8's 80-char threshold and needs a `>-` block scalar
Large sections (>=50 lines): none
Reference files: 0 [clusters: none] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): none
Spawn anti-patterns: none
Intake pattern violations: none
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): within tiers
Tool scoping (R6): none / none
Dead links: none / Cross-skill references: none
Missing standard sections: all 5 present
Goal verification: present
Deferred goal candidates: none
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

## Refinement step 1 (cont.): derive and select goals

Per references/goal-derivation.md: one finding, "Frontmatter issues (non-standard field, single-line description)" -> goal "Frontmatter passes R5 and R8", verification `Skill(plugin-rulebook)` R5 and R8 -> OK. Source finding: single-line description of 138 chars (R8). Exactly one candidate goal, so the tool needs at least 2 options: ask single-select with "Select this goal" / "No goals". Escape-hatch answer was not given, so there are no context-stated needs to add.

### QUESTION (AskUserQuestion): goal selection

```
question: "Pre-analysis found one issue that can become a goal for this session. Select it?"
header: "Goals"
multiSelect: false
options:
  - label: "Select this goal"
    description: "Goal: frontmatter passes R5 and R8 (the single-line description becomes a >- block scalar). Verification: Skill(plugin-rulebook) R5 and R8 -> OK. Source finding: single-line description of 138 chars (R8)."
  - label: "No goals"
    description: "Record no goals; the interview runs with BATCH 1 as written (Question 1 included)."
(plus the automatic "Other" for a custom goal, which would need a verification check in a follow-up question)
```

Simulated operator answer: "Select this goal". Recorded goal G1: "Frontmatter passes R5 and R8"; verification: Skill(plugin-rulebook) R5 and R8 -> OK; source: R8 description finding.

## Requirements Interview

### BATCH 1: Refinement Focus (goals selected, so Question 1 is skipped)

The escape-hatch question did not fire, so nothing skips BATCH 1; it runs as written, Questions 2-4 scoped to the selected goal area (frontmatter).

#### QUESTION 2 (AskUserQuestion)

```
question: "What specific problems are you seeing?"
header: "Key Issues"
multiSelect: true
options:
  - "Hard-to-follow instructions": instructions are hard to follow
  - "Scattered references": references scattered and redundant
  - "Nested sections": too many nested sections
```
Simulated answer (first option): "Hard-to-follow instructions".

#### QUESTION 3 (AskUserQuestion)

```
question: "What would success look like?"
header: "Success"
multiSelect: false
options:
  - "Clearer workflow": instructions are easier to follow end to end
  - "Lower token cost": fewer tokens loaded per activation
  - "Production-ready": production-ready with error handling
```
Simulated answer (first option): "Clearer workflow".

#### QUESTION 4 (AskUserQuestion)

```
question: "Any areas to exclude or preserve as-is?"
header: "Scope Limits"
multiSelect: true
options:
  - "Keep validation gates": leave the target's validation gates and its Testing & Validation section unchanged
  - "Keep tool scoping": don't change allowed-tools, and add no tool grants
```
Simulated answer (first option): "Keep validation gates". Exclusion recorded: Testing & Validation section stays unchanged (also binds step 6's standard-section auto-add and step 10 fixes).

Approved scope documented: goal G1 (frontmatter R5/R8); focus "hard-to-follow instructions" / "clearer workflow"; exclusion: Testing & Validation section.

### BATCH 2: Implementation Details

Routing: "Define explicitly" / default full interview -> BATCH 2 after BATCH 1. Trigger-based questions, each checked against pre-analysis:
- Extraction (large low-frequency section >= 50 lines): not detected -> not asked.
- Intake (intake violation): not detected -> not asked.
- Arguments (R22 mismatch): not detected -> not asked.
- Desc split (when_to_use split candidate): not detected -> not asked.
- Prod checks: asked in every refinement session.
- Reference-file clusters: not asked here (no references/ anyway).

#### QUESTION (AskUserQuestion): Prod checks

```
question: "Which production checks should I run?"
header: "Prod checks"
multiSelect: true
options:
  - "Security scan": Grep SKILL.md, references/ and scripts/ for credentials, keys and tokens, and for ${VAR}-style substitutions that corrupt example code
  - "Error handling": verify the skill handles missing files, malformed YAML and permission errors
  - "Tool scoping": audit allowed-tools: remove unused tools, narrow Bash wildcards
  - "None needed": skip production checks for this session
```
Simulated answer (first option): "Security scan". (Not executed in this dry run, since the session stops at step 5 with no edits; a scan would be read-only and the fixture has no credentials.)

Standard sections are auto-added in step 6 and all five are already present, so no question.

## Refinement step 2: Load workflow reference

Read references/refinement-workflow.md (preservation gates, validation phases, rollback, evidence-gated editing).

## Refinement step 3: Consolidation opportunities

Skipped: the target has no references/ directory. No consolidation ask.

## Refinement step 4: Preservation gates (Gates 1 and 2 run here)

- GATE 1, Content Audit: SKILL.md only (40 lines; no references/, scripts/, assets/). Frontmatter (name, description, when_to_use, allowed-tools): core. Quick Start, When to Use, When NOT to Use, Testing & Validation, Goal Verification, Reference Guide: all core (used in essentially every activation or required-standard). Nothing supplementary.
- GATE 2, Capability Assessment: proposed change is converting `description` from a single-line plain scalar to a `>-` block scalar, same words, no deletion or move. Will it impair execution? NO. Decision: SAFE. Testing & Validation is excluded by the operator and is untouched.
- Gates 3 and 4: apply at each move and deletion in step 6. The proposed change has no move and no deletion, so they would be trivially satisfied.

## Refinement step 5: Plan-only exit

The request did not use plan-only wording, so the ask is made.

### QUESTION (AskUserQuestion)

```
question: "Apply the approved scope (goal G1: make description a >- block scalar; Testing & Validation left unchanged)?"
header: "Apply"
multiSelect: false
options:
  - "Apply changes": run step 6 and make the edits
  - "Plan only": write changes.md, make no edits
  - "Stop": end the session here with no changes
```
Simulated answer: "Stop".

On "Stop": the session ends here. Step 6 (make changes), step 7 (validation phases), step 8 (goal measurement), step 9 (trigger regression) and step 10 (plugin-rulebook, skill-reviewer, completion marker) are NOT run. No changes.md is written. `<skill-improvement-complete>` is NOT emitted, since nothing was applied and goal G1 was never measured.

## Result

- No edits were made to OUTDIR/target/SKILL.md (it is byte-identical to the fixture; verified with diff).
- The original fixture at evals/skill-refiner-interactive/fixtures/one-finding-skill/ was not modified.
- Session stopped at step 5 by operator choice.
