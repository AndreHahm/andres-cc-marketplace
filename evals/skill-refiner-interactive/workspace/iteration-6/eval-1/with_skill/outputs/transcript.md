# Dry-run transcript: skill-refiner-interactive, eval-1 (plan-only)

Operator request: "Analyze the skill in OUTDIR/target and just write a changes.md, do not apply anything."
Simulated answers: skill already located; select all goals offered; draft path is OUTDIR/changes.md. Anything else: first option.

## Quick Start

### A. Detect predating context
Conversation holds only the request naming the skill and the action. That is not predating context (no skill file provided, no problem described). Escape-hatch question NOT asked. Interview style stays "full interview".

### B. "What skill do you want to work on?"
Skipped: the request already names the skill (OUTDIR/target).

### C. Action question (Refine / Validate)
Skipped: "analyze it and just write a changes.md" counts as refine per step C.

### D. Route
Refine -> Core Workflow: Refinement.

## Core Workflow: Refinement

### Step 1: Locate the skill
- Operator answer given up front: skill already located at OUTDIR/target. I copied evals/skill-refiner-interactive/fixtures/demo-skill/ to OUTDIR/target/ (SKILL.md, references/a.md, references/b.md). The original fixture is untouched.
- Gitignore exclusion: target lives under evals/.../workspace/, not .temp/.draft/.backup; accepted as the real target (the operator named it).
- Mirror-pair check (R19): no `<repo root>/.claude/skills/demo-skill/` and no `plugins/*/skills/demo-skill/` exists. Single copy, no halt, Mirror question NOT asked.
- User-space / cache / not-found branches: not applicable (no AskUserQuestion fired).

### Step 1 (continued): Pre-analysis (pre-analysis-checklist.md)
plugin-rulebook found at plugins/plugin-devkit/skills/plugin-rulebook/; read assets/settings.json. Resolved tiers: R13 weak 100 / soft 300 / warning 490 / critical 500; R18 weak 10 / warning 20 / critical 30; R21 description min 80, max 1024, critical-low 20, when_to_use max 512, combined max 1536. R5 allowed fields (skill) include name, description, allowed-tools; `version` not present here.

Measured facts: SKILL.md 13 lines; references/a.md 5 lines; references/b.md 4 lines; no workflows/; no scripts/.

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: none non-standard (name, description, allowed-tools only). description is single-line but 22 chars (<80), so the >- rule (R8, >80 chars) does not apply.
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (both about TODO/FIXME marker handling)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md for the full list of marker formats."
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" collects input without AskUserQuestion
Argument consistency (R22): none (no $ARGUMENTS/$N in body, no argument-hint/arguments in frontmatter)
when_to_use split candidate: no (description has no embedded "Use when" clause and is 22 chars)
Description size (R21): finding - description is 22 chars, below the 80 floor (Warning tier 20-79); no when_to_use
Tool scoping (R6): undeclared: Grep (SKILL.md "grep the file for TODO markers") - Major / unused declared: none (Read is used by the "Read references/b.md" directive)
Dead links: none (references/a.md and references/b.md both exist) / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: see goal derivation below
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1 (continued): Derive and select goals (goal-derivation.md)
Findings with a goal row: ref->ref chain, intake violation, undeclared tool (Grep), description size, reference cluster, missing goal verification.
Priority order: First = chain, intake; Second = undeclared tool; Third = cluster, missing goal verification. The description-size finding has a goal row but is not named in any of the three priority groups, so I ranked it after Second. Top 3: G1, G2, G3. Deferred candidates: description size (R21), reference cluster (handled by the step-3 consolidation ask, which also resolves G1), missing goal verification.

AskUserQuestion (multiSelect: true, up to 3 goals):
```
question: "Which goals should this refinement session work toward?"
header: "Goals"
options:
  - "Zero ref->ref chains": verify: re-run the chain scan over references/*.md -> 0 matches
  - "All intake uses AskUserQuestion": verify: re-run the intake scan -> 0 matches
  - "Every invoked tool declared": verify: re-run the tool-scoping scan -> no undeclared tools
```
Simulated operator answer: select all (G1, G2, G3). Recorded. No custom goal typed, so no follow-up verification ask.

### Requirements Interview - BATCH 1 (Refinement Focus)
Goals were selected, so Question 1 is SKIPPED (goals set the scope). Questions 2-4 asked one at a time (first option, no answer given):

Q2 header "Key Issues" (multiSelect): "What specific problems are you seeing?" options: Hard-to-follow instructions / Scattered references / Nested sections -> simulated: "Hard-to-follow instructions".
Q3 header "Success" (single): "What would success look like?" options: Clearer workflow / Lower token cost / Production-ready -> simulated: "Clearer workflow".
Q4 header "Scope Limits" (multiSelect): "Any areas to exclude or preserve as-is?" options: Keep validation gates / Keep tool scoping -> simulated: "Keep validation gates". (The target has no validation gates, so this excludes nothing in practice; "Keep tool scoping" was NOT chosen, so G3's allowed-tools edit stays in scope; standard sections are not excluded.)
Approved scope documented: G1-G3, clearer workflow, no exclusions that bind.

### BATCH 2 (Implementation Details)
Routing: no escape-hatch answer, so the full interview applies; BATCH 2 follows BATCH 1. Only questions whose pre-analysis trigger fired:
- Extraction: no large low-frequency section -> not asked.
- Intake: fired (and G2 selected) -> asked. header "Intake", "Section 'Quick Start' collects user input without AskUserQuestion (asks the user for a file path in free text). Convert it?" options Yes / No -> simulated first option: "Yes".
- Arguments (R22): no mismatch -> not asked.
- Desc split: no candidate -> not asked.
- Prod checks: asked in every session. header "Prod checks" (multiSelect) options: Security scan / Error handling / Tool scoping / None needed -> simulated first option: "Security scan".
- Reference-file clusters: not asked here (step 3 is the single consolidation ask).
Standard sections: auto-added in step 6, no question.
Approved scope documented.

### Step 2: Load workflow reference
Read references/refinement-workflow.md (preservation gates, validation phases, rollback).

### Step 3: Consolidation opportunities
target has references/, so the step runs.
- references/a.md: 5 lines (details of TODO summaries); references/b.md: 4 lines (marker formats). One topic cluster: TODO/FIXME marker handling. Merge -> 1 file (references/todo-markers.md).
AskUserQuestion: "Should we consolidate these files? Saves ~2 lines (9 -> ~7: one H1 and one directive line disappear), improves clarity, and removes the a.md -> b.md chain." options: "Consolidate" / "Leave as-is" -> simulated first option: "Consolidate".

### Step 4: Preservation gates (Gates 1 and 2 here)
- Gate 1 Content Audit: SKILL.md 13 lines (Quick Start: core 80%+, frontmatter: core); references/a.md 5 lines (supplementary: summary format details, read when summarizing); references/b.md 4 lines (supplementary: marker formats). scripts/, assets/: none.
- Gate 2 Capability Assessment: merging a+b keeps every line of content (only a.md's "Read references/b.md" pointer becomes unnecessary). Replacing free-text intake with AskUserQuestion and adding Grep to allowed-tools do not impair execution. Decision: all safe; nothing is deleted except the two source files after a verified CREATE and LINK.
- Gates 3 and 4 apply at step 6 when the plan is applied; not run now. The deletions of a.md and b.md are marked pending Gate 4 in the draft.

### Step 5: Plan-only exit
The request already used plan-only wording ("just write a changes.md, do not apply anything"), so the "Apply changes / Plan only / Stop" question is SKIPPED. Interview and step-3 approvals count as approval of the findings. Only the draft path needs confirming: operator answer says draft path = OUTDIR/changes.md (named up front, so no separate path question). No draft exists at that path, so nothing to preserve or merge. Step 6 NOT run. No edits to OUTDIR/target. No goal measurement (step 8 skipped per goal-derivation "Plan-Only Runs"). Steps 7, 9, 10 not reached.

Wrote OUTDIR/changes.md per references/changes-draft-format.md. Also wrote this transcript.

## Verification of plan-only constraint
- OUTDIR/target/ is byte-identical to the fixture copy (no edits).
- Original fixture not modified.
- No file written outside OUTDIR.
- No `<skill-improvement-complete>` marker emitted (plan-only run, step 10 not reached).
