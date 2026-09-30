# Transcript: skill-refiner-interactive dry run, eval-11 (big-skill, "make it lighter")

Operator request: "Refine the skill in OUTDIR/target so it is lighter."
Target: copy of fixture `big-skill` at `OUTDIR/target/` (SKILL.md 307 lines, references/rules.md 3 lines). The original fixture was not touched.
Plugin-rulebook found at `plugins/plugin-devkit/skills/plugin-rulebook/`, so R13/R18/R21 tiers came from its `assets/settings.json`.

## Quick Start A-D
- A (predating context): none. The request only names the skill and the action, so the escape-hatch question is NOT asked.
- B (which skill?): skipped, request names the skill (operator: "skill already located").
- C (Refine vs Validate): skipped, request says "refine".
- D: route to Core Workflow: Refinement.

## Step 1: Locate the skill
- Path given: `OUTDIR/target/SKILL.md`. Not in cache, not user-space, not gitignored.
- Mirror-pair check (R19): no `plugins/*/skills/big-skill/` and no `.claude/skills/big-skill/` exist, so it is one logical skill with nothing to compare. No Mirror question.
- Operator said the skill is already located, so no "Where should I find this skill?" question.

### Pre-analysis (references/pre-analysis-checklist.md), run before any interview question

```
Pre-Analysis: big-skill
Lines: 307 - Soft Warning (R13)   [thresholds from plugin-rulebook: weak 100, soft 300, warning 490, critical 500]
Frontmatter issues: none (description uses >-, no forbidden field, allowed-tools space-separated)
Large sections (>=50 lines): "Troubleshooting (Edge Cases)" - 60 lines, self-declared "consulted only when a run fails" -> low-frequency (<20%)
Reference files: 1 [clusters: none] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): none
Spawn anti-patterns: none
Intake pattern violations: none
Argument consistency (R22): none (no $ARGUMENTS / $N in body, no argument-hint)
when_to_use split candidate: no (description ~108 chars, under 400)
Description size (R21): within tiers (description 108 chars >= 80 floor, no when_to_use)
Tool scoping (R6): undeclared tools: none / unused declared tools: Grep, Glob (Minor)
Dead links: none / Cross-skill references: none  (note: references/rules.md is not linked from SKILL.md, an orphan)
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: none
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

**R13 tier logged from the pre-analysis report: Soft Warning (307 lines).**

### Goal derivation and selection (goal-derivation.md)
Findings -> goals (2 of 3 findings are in higher priority tiers, the third fills the open slot). Question, as it would be asked:

```
AskUserQuestion (multiSelect: true, up to 3 goals; option description = verification check)
question: "Which goals should this refinement session meet?"
options:
  - "Extract the Troubleshooting section": no section >=50 lines stays inline (verify: re-run the large-section scan -> none unapproved)
  - "SKILL.md below Soft Warning": SKILL.md under 300 lines (verify: wc -l SKILL.md -> count <300)
  - "Add goal verification": target has a goal-measurement step (verify: Grep for a `## Goal Verification` heading -> present)
  (+ automatic "Other" for a custom goal)
```
Simulated operator answer: select all goals offered. Recorded goals G1, G2, G3 (above). The interview is scoped to them; step 8 measures them.

## Requirements Interview

### BATCH 1 (Question 1 skipped because goals were selected; Questions 2-4 asked one at a time)
- Q2 "What specific problems are you seeing?" (header "Key Issues", multiSelect) options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections". No answer given, first option chosen: **Hard-to-follow instructions**.
- Q3 "What would success look like?" (header "Success") options: "Clearer workflow" / "Lower token cost" / "Production-ready". No answer given, first option chosen: **Clearer workflow**.
- Q4 "Any areas to exclude or preserve as-is?" (header "Scope Limits", multiSelect) options: "Keep validation gates" / "Keep tool scoping". No answer given, first option chosen: **Keep validation gates**. Effect (per the template): the target's validation gates and its Testing & Validation section stay unchanged, and this exclusion binds step 6's auto-added standard sections, so `## Testing & Validation` is NOT auto-added. "Keep tool scoping" was not chosen, but no tool-scope change is needed anyway.
- Approved scope documented: goals G1-G3; exclusion = no Testing & Validation section added; everything else in scope.
- Disclosure: G3 adds a `## Goal Verification` heading, a new 3-line section rather than a change to an existing validation gate, so it was judged outside the "Keep validation gates" exclusion. Flagged here because the boundary is arguable.

### BATCH 2 (no escape hatch was taken, so it runs after BATCH 1)
Triggers detected in pre-analysis: large low-frequency section only. No intake, R22 or desc-split question. No cluster question (step 3 owns that).
- Extraction question (asked, maps to selected goal G1):
  ```
  question: "Section 'Troubleshooting (Edge Cases)' is 60 lines and appears in <20% of activations. Extract to references/troubleshooting.md?"
  header: "Extraction"
  options: "Yes": CREATE reference file, LINK in SKILL.md, DELETE inline / "No": keep inline
  ```
  Simulated answer: **Yes**.
- Prod checks question (asked in every refinement session): "Which production checks should I run?" (header "Prod checks", multiSelect) options: "Security scan" / "Error handling" / "Tool scoping" / "None needed". No answer given, first option chosen: **Security scan**. Ran it (Grep over SKILL.md and references/ for credentials, keys, tokens, `${VAR}` substitutions): 0 matches.
- Standard sections will be auto-added in step 6 (except Testing & Validation, excluded above). Approved scope documented.

## Step 2: Load workflow reference
Read `references/refinement-workflow.md` (Preservation Gates, Validation Phases, Content Extraction, Rollback).

## Step 3: Consolidation
`references/` has 1 file (`rules.md`, 3 lines). There are no 2-4 files on one topic, so there is nothing to merge and the single consolidation ask ("Consolidate" / "Leave as-is") is not raised. The step does not apply.

## Step 4: Preservation gates
- GATE 1 (Content Audit): SKILL.md: Quick Start (6 lines, core); Workflow Step 1-7 (33 lines each, core); Troubleshooting (60 lines, supplementary, <20%); references/rules.md (3 lines, supplementary).
- GATE 2 (Capability Assessment): moving the Troubleshooting body to a reference file does not impair the main workflow, since it is consulted only on failures and a pointer stays inline. Safe to migrate. Workflow Steps stay (core).
- GATES 3 and 4 are applied in step 6.

## Step 5: Plan-only exit
Question as asked: "Apply the approved scope?" options "Apply changes" / "Plan only" / "Stop". Simulated answer: **Apply changes**. (The request did not use plan-only wording.) No consolidation, so there are no consolidation source files needing a Gate 4 ask before step 6.

## Step 6: Make changes (CREATE -> LINK -> DELETE)
Rollback settled before the first edit: the target is a copy of a git-tracked fixture (`evals/skill-refiner-interactive/fixtures/big-skill/`). The pristine original is the restore source; restore list = Files created / deleted below.

Numbered actions in the order performed:

1. CREATE `target/references/troubleshooting.md` (59 lines: heading + the 57 lines of the section body, verbatim). GATE 3 (Migration Verification): destination did not exist, was created with the full extracted text, re-read, and `diff` of source lines 250-306 against the new file body showed them IDENTICAL, so the migration is complete.
2. LINK `target/SKILL.md` "Troubleshooting (Edge Cases)": inserted the pointer "When a run fails, details are in `references/troubleshooting.md` (55 failure modes with the delimiter to check for each)." in place of the intro sentence, while the inline body still existed.
3. LINK `target/SKILL.md` "Reference Guide": added a new `## Reference Guide` table linking `references/rules.md` (previously an orphan) and `references/troubleshooting.md`. Links verified: both paths exist (Glob).
4. DELETE the inline body of the Troubleshooting section in `target/SKILL.md` (55 `- Failure mode N` bullets plus a spare blank line, i.e. 57 lines; the heading and the 1-line pointer stay). GATE 4 (Operator Confirmation), asked at the deletion: "Delete the inline body of 'Troubleshooting (Edge Cases)' from SKILL.md? The content now lives in references/troubleshooting.md and the pointer is linked." options "Approve deletion" / "Keep inline". Simulated answer: **Approve deletion**. This was a content removal inside a file, so it ran as an Edit-type change, not a file delete, so no Bash `rm` and no second permission gate applied. No whole-file deletion was performed in this run.

Other edits in step 6 (non-CREATE/LINK/DELETE, unnumbered): auto-added `## When to Use` and `## When NOT to Use` after Quick Start; added `## Goal Verification` (G3). `## Testing & Validation` was not added (excluded at Q4). Frontmatter untouched. `allowed-tools` untouched (Tool scoping was not chosen at Prod checks).

## Step 7: Validate result (seven phases)
- Phase 1 File Inventory: before = SKILL.md (307), references/rules.md (3). After = SKILL.md (271), references/rules.md (3), references/troubleshooting.md (59).
- Phase 2 Read All: SKILL.md, both reference files load fully; 55 failure modes present in troubleshooting.md, none lost.
- Phase 3 Frontmatter: name and description present; `description` is `>-`; no non-standard fields; unchanged.
- Phase 4 Body: 271 lines, R13 tier Weak Warning (was Soft Warning); no inline code blocks (R18 n/a); 80% rule applied (core workflow kept inline, supplementary extracted); workflow is a flat sequence; no spawn anti-patterns.
- Phase 5 References: both linked files exist, one level deep, no reference->reference chains; no orphans (rules.md now linked).
- Phase 6 Tools: undeclared tools: none. Unused declared: Grep, Glob (Minor, reported, not changed because Tool scoping was not selected). No Bash-for-dedicated-tool misuse.
- Phase 7 Testing: activation phrases ("clean this CSV", "dedupe a CSV", "summarize this CSV file") still match the unchanged description.

## Step 8: Measure goals
See `goal-measurement.md`. G1 PASS, G2 PASS (271 < 300), G3 PASS. No failed goal, so no accept/continue question.

## Step 9: Trigger regression
Skipped: neither `description` nor `when_to_use` text changed.

## Step 10: Compliance and reviewer passes
Cannot dispatch `Skill(plugin-rulebook)` or the `skill-reviewer` agent in this dry run, so they were not run. Per the skill, the completion marker is therefore NOT emitted.

Change summary:
```
Lines: 307 -> 271
Frontmatter: no changes
Sections added: When to Use, When NOT to Use, Goal Verification, Reference Guide (Testing & Validation excluded by operator)
Files created: references/troubleshooting.md
Files deleted: none (inline Troubleshooting body removed from SKILL.md, migrated to references/troubleshooting.md)
plugin-rulebook: NOT RUN
```
Possible findings a real plugin-rulebook run may raise (not verified here): absence of `## Testing & Validation` (excluded by the Q4 choice) under R29.
