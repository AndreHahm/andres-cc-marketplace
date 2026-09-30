# Transcript: skill-refiner-interactive dry run, eval-13 (existing draft preserved)

Setup: copied fixtures/existing-draft/changes.md to OUTDIR/changes.md and fixtures/demo-skill/ to OUTDIR/target/. Read SKILL.md and the references it directs (pre-analysis-checklist, goal-derivation, changes-draft-format, interview-question-templates, refinement-workflow). Operator request: "Analyze the skill in OUTDIR/target and just write a changes.md, do not apply anything."

## Quick Start A (detect predating context)
No skill file, code, or problem description was supplied; the request only names the skill and the action, which is not predating context. Escape-hatch question NOT asked. Interview style stays full ("Define explicitly" path). Continue to B.

## Quick Start B (what skill?)
Skipped: the request names the skill (OUTDIR/target).

## Quick Start C (action question)
Skipped: "analyze it and just write a changes.md" counts as refine.

## Quick Start D (route)
Route to Core Workflow: Refinement.

## Refinement step 1: Locate the skill
- Simulated operator answer: "skill already located" (OUTDIR/target). Not user-space, not cache, so no warn/refuse, and no "Where should I find this skill?" question.
- Note: the target sits under a `target/` directory matched by the global gitignore. The operator named it explicitly, so I proceed with it as the real target.
- Mirror-pair check (R19): target is not under `plugins/<plugin>/skills/` and has no `.claude/skills/` sibling, so no mirror pair; no Mirror question.

### Step 1, pre-analysis (references/pre-analysis-checklist.md)
Resolved thresholds from plugin-rulebook assets/settings.json: R13 weak 100 / soft 300 / warning 490 / critical 500; R18 10/20/30; R21 description min 80, max 1024, when_to_use max 512, combined min 80, max 1536.

Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: none non-standard; description 22 chars (under the 80-char R8 threshold, no `>-` needed)
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md] [oversize ≥400 lines: none]
Workflow files: 0 [oversize: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md line 5 ("Read references/b.md ...")
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): 22 chars is under the 80-char floor; combined also under 80
Tool scoping (R6): undeclared: Grep ("grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: description size (R21); reference cluster a.md + b.md; missing goal-verification step
R13/R18 threshold source: plugin-rulebook/assets/settings.json

### Step 1, goal derivation and selection (references/goal-derivation.md)
Findings with goals, by priority: first tier: ref chain, intake; second tier: undeclared tool, (description size); third tier: cluster, goal verification. Top 3 proposed, the rest deferred.

AskUserQuestion (multiSelect: true):
- question: "Which goals should this refinement target?"
- header: "Goals"
- options:
  - "Zero reference chains": verification: re-run the chain scan over references/*.md, expect 0 matches
  - "Intake via AskUserQuestion": verification: re-run the intake scan, expect 0 matches
  - "All tools declared": verification: re-run the tool-scoping scan, expect no undeclared tools
- Simulated operator answer: select all three. Goals G1, G2, G3 recorded; the interview is scoped to them.

## Requirements Interview, BATCH 1 (Refinement Focus)
Goals were selected, so Question 1 is skipped. Questions 2-4 asked one at a time, about the selected goal areas. No answers were given, so the first option is used each time.

Question 2
- question: "What specific problems are you seeing?" header: "Key Issues" multiSelect: true
- options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections"
- Simulated answer: "Hard-to-follow instructions"

Question 3
- question: "What would success look like?" header: "Success" multiSelect: false
- options: "Clearer workflow" / "Lower token cost" / "Production-ready"
- Simulated answer: "Clearer workflow"

Question 4
- question: "Any areas to exclude or preserve as-is?" header: "Scope Limits" multiSelect: true
- options: "Keep validation gates" / "Keep tool scoping"
- Simulated answer: "Keep validation gates" (first option). This excludes the Testing & Validation section from step 6's auto-added standard sections. Tool scoping is not excluded.

Approved scope documented: goals G1-G3; focus on clearer instructions; Testing & Validation left alone.

## BATCH 2 (Implementation Details)
Escape hatch was not used, so BATCH 2 follows BATCH 1. Triggers detected in pre-analysis:
- Extraction: no large low-frequency section, so NOT asked
- Intake: detected, and its goal (G2) was selected, so asked
- Arguments (R22): no mismatch, NOT asked
- Desc split: no candidate, NOT asked
- Prod checks: asked in every session
- Reference clusters: not asked here (step 3 owns the single consolidation ask)

Intake question
- question: "Section 'Quick Start' collects user input without AskUserQuestion (free-form 'Ask the user which file to process'). Convert it?"
- header: "Intake" options: "Yes" / "No"
- Simulated answer: "Yes"

Prod checks question
- question: "Which production checks should I run?" header: "Prod checks" multiSelect: true
- options: "Security scan" / "Error handling" / "Tool scoping" / "None needed"
- Simulated answer: "Security scan". A Grep over SKILL.md and references/ for credentials, keys, tokens and ${VAR}-style substitutions finds none; nothing to add to the plan.

## Step 2: Load workflow reference
Read references/refinement-workflow.md (preservation gates, validation phases, rollback). Loaded; no question.

## Step 3: Consolidation opportunities
The target has references/, so the step runs. Files: a.md (5 lines), b.md (4 lines). Same topic (TODO/FIXME marker details), so flagged as a merge; a.md also chains to b.md.

AskUserQuestion
- question: "Should we consolidate these files? Saves about 3 lines, improves clarity."
- header: "Consolidate"
- options: "Consolidate" / "Leave as-is"
- Simulated answer: "Consolidate" (first option). Only this ask covers consolidation.

## Step 4: Preservation gates
- Gate 1 (Content Audit): SKILL.md 13 lines, core. references/a.md (5 lines, supplementary <20%), references/b.md (4 lines, supplementary). No scripts/ or assets/.
- Gate 2 (Capability Assessment): consolidating a.md + b.md into one file, pointer updated; nothing is lost, so execution is not impaired. Safe. Intake conversion and Grep declaration are in-place edits that do not impair execution.
- Gates 3 and 4 apply at change time (step 6). Gate 4 for the consolidation's source files would be asked once the operator chooses to apply changes (step 5), which does not happen in this run. The draft marks both DELETEs as pending Gate 4.

## Step 5: Plan-only exit
The ask (Apply changes / Plan only / Stop) is SKIPPED: the request already used plan-only wording ("just write a changes.md", "do not apply anything"). The interview and step-3 approvals count as approval of the findings. Only the draft path needs confirming, so the confirmation is asked.

AskUserQuestion (draft path)
- question: "Where should the changes draft be written?"
- header: "Draft path"
- options: "OUTDIR/changes.md (existing draft)" / "Default .draft/_open/<plugin>/<skill>/changes.md"
- Simulated answer: OUTDIR/changes.md (the existing file).

A draft already exists at the confirmed path, so per references/changes-draft-format.md (Draft Location) it was read first. It holds one approved finding, F1, which must be kept. New findings are added to it; F1 is not overwritten or renumbered. Its section was kept verbatim. Only additions were made:
- added a Selected Goals section and a Pre-Analysis Report section to the header (the draft had neither)
- extended the Implementation Order list after F1
- appended F2 (ref chain, consolidation, DELETEs pending Gate 4), F3 (intake), F4 (declare Grep and Glob) and M1 (missing standard sections, Testing & Validation excluded per Question 4)
- added the closing Post-Implementation Verification section

Per the plan-only branch: step 6 NOT run, no edits to OUTDIR/target, and steps 7-10 (validation, goal measurement, trigger regression, compliance passes, completion marker) are not run, because nothing was applied. No `<skill-improvement-complete>` marker emitted.

Gate 4 was not run for any deletion; F2's DELETEs are pending Gate 4 when the plan is applied.

## Result
- OUTDIR/changes.md updated (F1 preserved verbatim, F2-F4 and M1 added)
- OUTDIR/transcript.md written
- OUTDIR/target unmodified (still identical to fixtures/demo-skill)
