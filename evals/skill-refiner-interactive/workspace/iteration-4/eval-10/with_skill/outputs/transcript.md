# Transcript: skill-refiner-interactive dry run (iteration-4, eval-10)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: a copy of fixtures/demo-skill in OUTDIR/target (13-line SKILL.md, references/a.md, references/b.md).
Simulation note: nothing can be dispatched, so every AskUserQuestion is written out with its options and answered with the simulated operator answer (or the first option when none was given).

## Quick Start, A-D

- A (escape hatch): the request names a path only. No skill content, code or problem description was supplied in the conversation, so there is no predating context. Escape hatch NOT offered; BATCH 1 will run (the "Define explicitly" path).
- B: skipped. The request already names the skill.
- C: skipped. The request already says "refine".
- D: route to Core Workflow: Refinement.

## Refinement step 1: Locate the skill

- Operator answer: "skill already located", so no "Where should I find this skill?" ask.
- Path is OUTDIR/target (not a gitignored draft, not the plugin cache, not user-space). No `.claude/skills/<name>` sibling mirror, so the R19 mirror-pair check finds nothing and there is no Mirror question.
- Pre-analysis (references/pre-analysis-checklist.md). The plugin-rulebook settings were not loaded for the dry run, so the skill-development flat-limit fallback applies (500 lines / 30 lines).

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: single-line description (needs >-, R8)
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md (marker details) | oversize ≥400 lines: none]
Workflow files: 0 [oversize ≥300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md → "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" with no AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): Grep (body says "grep the file") undeclared / Read declared and used (none unused)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — flag as Missing
Deferred goal candidates: frontmatter R5/R8 issue, missing goal verification, reference cluster (a.md + b.md)
R13/R18 threshold source: skill-development fallback
```

### Goal selection (goal-derivation.md)

Findings ordered by priority. The top 3 become goals and the rest are deferred candidates.

AskUserQuestion (multiSelect: true):
- question: "Which goals should this refinement session measure?"
- header: "Goals"
- options:
  1. "Zero reference→reference chains": verification: re-run the checklist chain scan over references/*.md → 0 matches
  2. "All intake uses AskUserQuestion with options": verification: re-run the checklist intake scan → 0 matches
  3. "Every invoked tool is declared in allowed-tools": verification: re-run the checklist tool-scoping scan → no undeclared tools

Simulated operator answer: all three. No custom goal, so no follow-up ask. Selected goals: G1 chain, G2 intake, G3 tools.

## Requirements Interview

### BATCH 1 (Question 1 skipped because goals were selected; Questions 2-4 asked one at a time)

- Q2 "What specific problems are you seeing?" (Key Issues, multiSelect). Options: Hard-to-follow instructions / Scattered references / Nested sections. Simulated answer: first option, "Hard-to-follow instructions".
- Q3 "What would success look like?" (Success). Options: Clearer workflow / Lower token cost / Production-ready. Simulated answer: first option, "Clearer workflow".
- Q4 "Any areas to exclude or preserve as-is?" (Scope Limits, multiSelect). Options: Keep validation gates / Keep tool scoping / Nothing to exclude. Simulated answer: first option, "Keep validation gates".
- Scope documented: G1-G3 plus clearer workflow; validation gates preserved.

### BATCH 2

Routing: the operator did not choose "Infer from context" (the escape hatch was never offered), so BATCH 2 follows BATCH 1. Only the questions whose trigger was detected are asked.
- Extraction: no large section, not asked.
- Intake: detected, and it maps to selected goal G2. Asked:
  - question: "Section 'Quick Start' collects user input without AskUserQuestion (\"Ask the user which file to process\"). Convert it?" header: "Intake"; options: "Yes" / "No". Simulated answer: first option, "Yes".
- Arguments (R22): no mismatch, not asked.
- Desc split: not a candidate, not asked.
- Prod checks (asked in every session): question "Which production checks should I run?" header "Prod checks" multiSelect; options: Security scan / Error handling / Tool scoping / None needed. Simulated answer: first option, "Security scan". Result: no credentials, keys or `${VAR}` substitutions found in SKILL.md or references.
- Reference-file cluster is not asked here; step 3 is the single consolidation ask.
- Standard sections will be auto-added in step 6. Scope documented and approved.

## Step 2: Load workflow reference

Read references/refinement-workflow.md (preservation gates, validation phases, consolidation procedure).

## Step 3: Consolidation opportunities

- references/a.md (4 lines), references/b.md (4 lines). Same topic (TODO marker details), and a.md links to b.md, so they are a merge candidate.
- AskUserQuestion: "Should we consolidate these files? Saves 0 lines (8 → 10 with headings), improves clarity and removes the ref→ref chain." options "Consolidate" / "Leave as-is". Simulated answer: first option, "Consolidate".

## Step 4: Preservation gates

- Gate 1 (content audit): SKILL.md Quick Start = core (80%+); references/a.md = supplementary (summary format); references/b.md = supplementary (marker formats).
- Gate 2 (capability assessment): consolidating a.md + b.md into details.md keeps all content, so execution is not impaired. Safe.
- Gates 3 and 4 are applied in step 6 at the move and deletion.

## Step 5: Plan-only exit

The request does not use plan-only wording, so the ask is made.
- AskUserQuestion: "Apply the approved scope?" options "Apply changes" / "Plan only" / "Stop". Simulated answer: "Apply changes". Continue to step 6.

## Step 6: Make changes (CREATE → LINK → DELETE)

1. CREATE references/details.md with both files' content as two sections (Summary Format, Marker Formats). The "Read references/b.md" directive is dropped because the content is inlined.
2. Gate 3 (migration verification): destination exists, all lines from a.md and b.md are present, no orphans. Approved (migration, no question).
3. LINK: SKILL.md pointer changed from references/a.md to references/details.md; Quick Start intake converted to an AskUserQuestion block (G2); `Grep` added to `allowed-tools` (G3); standard sections auto-added (When to Use, When NOT to Use, Testing & Validation, Reference Guide). A Quick Start example was also added.
4. Gate 4 (before the deletion), AskUserQuestion: "Okay to delete references/a.md and references/b.md now that their content is in references/details.md?" options "Delete" / "Keep". Simulated answer: first option, "Delete".
5. DELETE references/a.md, references/b.md.
- Report: "Consolidated 2 files into 1. Clearer organization."

## Step 7: Validate result (seven phases)

- Phase 1: before: SKILL.md (13 lines), references/a.md, references/b.md. After: SKILL.md (50 lines), references/details.md.
- Phase 2: all content loads; nothing lost.
- Phase 3: frontmatter: name present, description present (still single-line at this point, a known R8 item), allowed-tools `Read Grep`.
- Phase 4: within the OK R13 tier; Quick Start actionable; workflow pattern and spawn anti-patterns: none.
- Phase 5: SKILL.md link to references/details.md resolves; no orphans; no ref→ref chains.
- Phase 6: Read (declared), Grep (declared), AskUserQuestion excluded from the undeclared check. Undeclared: none. Unused: none.
- Phase 7: activation phrases "find the TODOs in this file" and "summarize the TODO markers" are covered.

## Step 8: Measure goals

- G1: re-run the chain scan over references/*.md → 0 matches. PASS.
- G2: re-run the intake scan → 0 matches (Quick Start now uses AskUserQuestion with options). PASS.
- G3: re-run the tool-scoping scan → no undeclared tools. PASS.
- All goals pass, so no "Accept with reason / Continue refining" ask.

## Step 9 (first pass)

Neither `description` nor `when_to_use` changed in steps 1-8. Skipped entirely, and the skip is stated here.

## Step 10: Compliance and reviewer passes

### Compliance round 1

- Skill(plugin-rulebook) on OUTDIR/target: simulated 1 FAIL (R8, description is single-line).
- skill-reviewer (full mode, Structured output mode): simulated `counts.critical` 0, `counts.major` 1 (missing Quick Start example).
- Fix attempt: description converted to `>-` folded form (R8); the Quick Start example output block was changed. The fix changes `description`, so step 9 re-enters first:
  - Step 9 (re-entry, round 1). AskUserQuestion "The description changed. Verify trigger accuracy didn't regress before finalizing?" (Trigger eval). Options: "Run trigger-eval check" / "Quick size check only" / "Skip". No answer was specified, so the first option, "Run trigger-eval check", is used. The skill would call Skill(skill-development) for its Phase 5 loop. That dispatch is simulated here with no regression reported.
- Re-run both checks: simulated still 1 FAIL (R8) and 1 Major (Quick Start example).
- NO MARKER EMITTED (round 1: a rulebook FAIL and a Major finding remain).

### Compliance round 2

- Skill(plugin-rulebook): 1 FAIL (R8). skill-reviewer: 1 Major (missing Quick Start example). Both simulated.
- Fix attempt: description reworded to "Summarizes TODO and FIXME markers in a single file."; the Quick Start example lead-in reworded. The fix changes `description`, so step 9 re-enters:
  - Step 9 (re-entry, round 2): the same Trigger eval question, first option "Run trigger-eval check" (simulated, no regression).
- Re-run: simulated still 1 FAIL (R8) and 1 Major.
- NO MARKER EMITTED (round 2: findings remain).

### Compliance round 3

- Skill(plugin-rulebook): 1 FAIL (R8). skill-reviewer: 1 Major. Both simulated.
- Fix attempt: description extended with "Not for creating new skills."; a one-line "Quick run" example sentence was added to Quick Start. The fix changes `description`, so step 9 re-enters:
  - Step 9 (re-entry, round 3): the same Trigger eval question, first option "Run trigger-eval check" (simulated, no regression).
- Re-run: simulated still 1 FAIL (R8) and 1 Major.
- NO MARKER EMITTED (round 3: findings remain). The 3-round cap is reached, so the round-cap question is asked.

### Round-cap question

- AskUserQuestion: "Findings remain after round 3 (plugin-rulebook: 1 FAIL R8; skill-reviewer: 1 Major, missing Quick Start example). How to proceed?" options "Continue another round" / "Accept remaining findings with reason" / "Stop".
- Simulated operator answer: "Accept remaining findings with reason". Reason: "cosmetic, tracked separately". The accepted findings and this reason are recorded in the change summary.

### Change summary

```
Lines: 13 → 61
Frontmatter: description converted to >- and reworded; allowed-tools Read → Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide (plus Quick Start example and AskUserQuestion intake block)
Files created: references/details.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: 1 accepted with reason (R8 FAIL: "cosmetic, tracked separately"); skill-reviewer: 1 Major accepted with the same reason (missing Quick Start example)
Goals: G1 PASS, G2 PASS, G3 PASS
```

### Completion marker

All conditions hold: every selected goal passed, and the remaining plugin-rulebook FAIL and skill-reviewer Major were accepted with a recorded reason through the round-cap question. Marker emitted here:

<skill-improvement-complete>

## Files

Final tree is in OUTDIR/final-tree.txt (target/SKILL.md, target/references/details.md). The original fixture was not modified.
