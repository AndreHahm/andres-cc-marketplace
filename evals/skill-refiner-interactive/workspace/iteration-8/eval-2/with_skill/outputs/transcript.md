# Transcript: skill-refiner-interactive dry run (iteration-8, eval-2)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Simulated operator answers: skill already located; select all goals; "Apply changes" at step 5; "Accept with reason" on any failed goal.

## Quick Start A (escape hatch)
Predating context? The request only names the skill and the action, so this is not predating context. Escape-hatch question NOT asked. Continue to B.

## Quick Start B
Request names the skill (the target copy). Plain-text "What skill do you want to work on?" skipped.

## Quick Start C
Request says "Refine", so the Action question is skipped. Routed (D) to Core Workflow: Refinement.

## Step 1: Locate the skill
- Simulated operator answer: skill already located at OUTDIR/target (a copy of the fixture demo-skill). No Glob search needed.
- Gitignore-exclusion: target is not in .temp/.draft/.backup. OK.
- Mirror-pair check (R19): no `.claude/skills/demo-skill/` or `plugins/*/skills/demo-skill/` exists. One logical skill. No Mirror question.
- Not user-space, not cache. No location questions.

### Step 1: Pre-analysis (pre-analysis-checklist.md)
R13/R18/R21 thresholds loaded from plugin-rulebook assets/settings.json (R13: weak 100 / soft 300 / warn 490 / crit 500; R18: 10/20/30; R21: description min 80, critical below 20).

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: none under R5 (no forbidden field); description is a single line of 22 chars, under the R8 80-char threshold so >- is not required
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker summaries and formats) | oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md for the full list of marker formats"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" collects input without AskUserQuestion
Argument consistency (R22): none (no $ARGUMENTS/$N use, no argument-hint)
when_to_use split candidate: no (no embedded "Use when" clause, description under 400 chars)
Description size (R21): finding - description is 22 chars, below the 80-char floor (warning tier; critical is under 20)
Tool scoping (R6): undeclared: Grep (body says "grep the file for TODO markers") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: R21 description size; reference cluster (handled at step 3); missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1: Goal derivation and selection (goal-derivation.md)
Priority order gives: (1) ref chain, (2) intake violation, then second tier: (3) undeclared tool. Description size, cluster and missing goal verification are deferred/lower priority.

AskUserQuestion (multiSelect: true):
- question: "Which goals should this refinement session commit to?"
- header: "Goals"
- options:
  1. "Zero reference chains": verification - re-run ref->ref chain scan over references/*.md -> 0 matches
  2. "AskUserQuestion intake": verification - re-run intake scan -> 0 matches
  3. "Declare every tool": verification - re-run tool-scoping scan -> no undeclared tools
  4. "Other" (automatic)

Simulated answer: select all three. Recorded goals:
- G1 Zero reference->reference chains (source: ref chain finding)
- G2 All intake uses AskUserQuestion with options (source: intake finding)
- G3 Every invoked tool is declared in allowed-tools (source: Tool scoping finding, Grep)

## Requirements Interview
Goals selected, so BATCH 1 Question 1 is skipped. Each question below is asked one at a time; simulated answer is the first option.

### BATCH 1
- Q2 "What specific problems are you seeing?" header "Key Issues" (multiSelect) options: Hard-to-follow instructions / Scattered references / Nested sections. Answer: "Hard-to-follow instructions" (first option).
- Q3 "What would success look like?" header "Success" options: Clearer workflow / Lower token cost / Production-ready. Answer: "Clearer workflow".
- Q4 "Any areas to exclude or preserve as-is?" header "Scope Limits" (multiSelect) options: Keep validation gates / Keep tool scoping. Answer: first option would be "Keep validation gates", but that would contradict nothing for this skill (it has no validation gates or Testing section). Note: "Keep tool scoping" was NOT chosen, since G3 requires adding a Grep grant. Exclusion "Keep validation gates" recorded, but the target has no existing Testing & Validation section, so the auto-add in step 6 is not excluded as an existing section being changed. Approved scope documented.

  Deviation disclosed: because the first option, read literally ("leave the target's validation gates and its Testing & Validation section unchanged"), would bar auto-adding a Testing & Validation section, I treated it as applying to existing content only. The target has none.

### BATCH 2
Routing: no escape hatch chosen, so full interview. Questions asked only for detected triggers:
- Extraction: not triggered (no section >=50 lines).
- Intake: triggered, and the finding maps to selected goal G2. Asked:
  - question: "Section 'Quick Start' collects user input without AskUserQuestion (Ask the user which file to process). Convert it?" header "Intake" options: "Yes" / "No". Simulated answer: "Yes".
- Arguments: not triggered (no R22 mismatch).
- Desc split: not triggered.
- Prod checks (always asked): question "Which production checks should I run?" header "Prod checks" (multiSelect) options: Security scan / Error handling / Tool scoping / None needed. Simulated answer: "Security scan". Result: Grep of SKILL.md and references/ for credentials, keys, tokens and ${VAR}-style substitutions found none.
- Reference-file clusters are not asked here (step 3).
Standard sections are auto-added in step 6 (not excluded).

## Step 2: Load workflow reference
Read references/refinement-workflow.md (preservation gates, validation phases, rollback).

## Step 3: Consolidation opportunities
Target has references/. Files: a.md (5 lines, details/summary format), b.md (4 lines, marker formats). Same topic (TODO marker handling), 2 files -> merge candidate.
AskUserQuestion: "Should we consolidate these files? Saves N lines, improves clarity." (N = about 2 lines; it also removes the chain) options: "Consolidate" / "Leave as-is". Simulated answer (no answer given, first option): "Consolidate". Plan: merge b.md into a.md.

## Step 4: Preservation gates
- Gate 1 Content Audit: SKILL.md (13 lines, core: Quick Start), references/a.md (5 lines, core-ish: summary format), references/b.md (4 lines, core: marker formats needed to search). All content is small and on the execution path.
- Gate 2 Capability Assessment: merging b.md into a.md keeps every marker format; removing the "Read references/b.md" directive loses nothing once the content is inline. Replacing free-text intake with AskUserQuestion keeps the same step. Adding Grep to allowed-tools only declares an already-used tool. Decision: all safe; b.md content is migrated, not dropped.
- Gate 3 (applied in step 6 at the move): destination exists and complete before deletion.
- Gate 4 (applied for consolidation source files before step 6): see step 5.

## Step 5: Plan-only exit
Request did not use plan-only wording, so asked.
AskUserQuestion: "Apply the approved scope?" options: "Apply changes" / "Plan only" / "Stop". Simulated answer: "Apply changes".
Gate 4 for consolidation source file: AskUserQuestion "Delete references/b.md after its content is merged into references/a.md?" options "Delete" / "Keep (decline consolidation)". Answer (first option): "Delete".

## Step 6: Make changes
Rollback: the target is an untracked scratch copy of a git-tracked fixture (evals/skill-refiner-interactive/fixtures/demo-skill/ is the pristine original), so restoring means re-copying the fixture. Settled before first edit.
Order followed CREATE -> LINK -> DELETE:
1. CREATE: appended "## Marker Formats" (TODO:/FIXME: entries) to references/a.md; Gate 3 verified destination complete.
2. LINK: removed the ref->ref "Read references/b.md" directive from a.md; SKILL.md still links references/a.md.
3. DELETE: `rm references/b.md` (Gate 4 approved; would be a Bash permission prompt in a live run, a second gate).
SKILL.md edits:
- Intake: replaced "Ask the user which file to process" with an AskUserQuestion block (question/header/options, 2 options, "Other" automatic), tagged ```yaml (R12).
- Tool scoping: "grep the file" now "use Grep on the chosen file"; allowed-tools changed from `Read` to `Read Grep`.
- Auto-added standard sections: When to Use, When NOT to Use, Testing & Validation (positive/negative triggers, quality gates), Reference Guide (table with references/a.md). Quick Start already present.
- description left unchanged (R21 warning is a deferred goal candidate, not selected; changing it would also trigger step 9).

## Step 7: Validate result (seven phases)
- Phase 1 File Inventory: before = SKILL.md, references/a.md, references/b.md; after = SKILL.md (53 lines), references/a.md (8 lines).
- Phase 2 Read All: re-read both files; no gaps, marker formats preserved.
- Phase 3 Frontmatter: name and description present; allowed-tools `Read Grep`; no forbidden fields.
- Phase 4 Body: 53 lines, R13 OK; no 80%-rule moves needed; code block 8 lines (under R18 weak 10); no spawn anti-patterns. No multi-step workflow pattern check needed (2-step quick start).
- Phase 5 References: references/a.md exists and is linked; one level deep; no ref->ref chains.
- Phase 6 Tools: undeclared tools: none (Grep now declared; AskUserQuestion exempt); unused declared: Read (Minor - SKILL.md tells the operator nothing explicit, but processing a file implies reading it; left); no Bash misuse.
- Phase 7 Testing: trigger phrases "summarize the TODOs in this file", "list FIXME markers" consistent with the description "Helps with demo tasks." (weakly; flagged as R21 deferred).

## Step 8: Measure goals (goal-derivation.md)
See goal-measurement.md. G1 PASS, G2 PASS, G3 PASS. No goal failed, so the "Accept with reason" path was not needed.

## Step 9: Trigger regression
Text of description and when_to_use did not change. Step skipped (stated explicitly).

## Step 10: Compliance and reviewer passes
In this dry run, Skill(plugin-rulebook) and the skill-reviewer agent were NOT executed (dispatch is out of scope for the simulation). Manual inspection against the loaded rules: R5 ok, R8 ok (description under 80 chars), R11 ok, R12 ok (```yaml), R13 OK (53 lines), R16 ok, R18 ok, R21 WARNING (description 22 chars < 80 floor, non-blocking, deferred), R29 ok (positive, negative and pass criteria present).

Change summary:
```
Lines: 13 -> 53
Frontmatter: allowed-tools `Read` -> `Read Grep`
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: references/b.md (merged into references/a.md)
plugin-rulebook: NOT RUN (manual inspection only; R21 warning on description remains, deferred)
```
Because the plugin-rulebook pass and the skill-reviewer pass could not be run, the `<skill-improvement-complete>` marker is NOT emitted (per step 10). All three selected goals passed.
