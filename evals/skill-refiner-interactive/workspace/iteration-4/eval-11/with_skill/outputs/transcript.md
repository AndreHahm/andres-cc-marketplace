# Transcript: skill-refiner-interactive dry run (eval 11, big-skill)

Operator request: "Refine the skill in OUTDIR/target so it is lighter."
Fixture copied to OUTDIR/target (original untouched).

## Quick Start
- A (escape hatch): no predating context (a path was named in the request only) -> skipped.
- B: skill already located by the request (simulated: "skill already located") -> skipped.
- C: request says "refine" -> Action question skipped.
- D: route "Refine" -> Core Workflow: Refinement.

## Refinement step 1: Locate
- Target = OUTDIR/target (no project/user-space search needed; not in plugin cache; not a mirror pair, no `.claude/skills/big-skill` sibling).

### Pre-analysis (references/pre-analysis-checklist.md) - report
```
Pre-Analysis: big-skill
Lines: 307 - Soft Warning (R13)
Frontmatter issues: none (description uses >-, no forbidden fields)
Large sections (>=50 lines): Troubleshooting (Edge Cases) - 60 lines, self-declared <20% usage
Reference files: 1 [clusters: none] [oversize >=400 lines: none]
Workflow files: 0
Reference chain violations (ref->ref): none
Spawn anti-patterns: none
Intake pattern violations: none
Argument consistency (R22): none
when_to_use split candidate: no (description ~100 chars, under 400)
Tool scoping (R6): none undeclared / Grep, Glob declared but unused (Minor)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - flag as Missing
Deferred goal candidates: none
R13/R18 threshold source: plugin-rulebook/assets/settings.json (R13: weak 100 / soft 300 / warning 490 / critical 500; R18: 10/20/30)
```
**R13 tier logged: Soft Warning (307 lines >= soft_warning 300).**

### Goal selection (goal-derivation.md)
Question: "Which goals should this session pursue?" multiSelect, options (label - verification):
1. "No large low-frequency section stays inline" - re-run large-section scan -> none unapproved
2. "SKILL.md within a lower R13 tier (under 300 lines)" - wc -l SKILL.md -> < 300
3. "Target skill has a goal-measurement step" - Grep `## Goal Verification` -> present
Simulated answer: all three selected. Recorded.

## Requirements Interview
- BATCH 1: Q1 skipped (goals selected). Q2-Q4 asked one at a time, scoped to the selected goals. No answers were specified, so the first option was used: Q2 "Hard-to-follow instructions", Q3 "Clearer workflow", Q4 "Keep validation gates". Approved scope: extract low-frequency content, add standard sections, add goal verification.
- BATCH 2 (routing: goals selected, "Define explicitly" style): asked only triggered questions.
  - Extraction question: "Section 'Troubleshooting (Edge Cases)' is 60 lines and appears in <20% of activations. Extract to references/troubleshooting.md?" options "Yes" / "No". Answer: **Yes**.
  - Intake, Arguments, Desc split: not triggered -> not asked.
  - Prod checks question (asked every session): options Security scan / Error handling / Tool scoping / None needed. Answer (first option): Security scan.
- Approved scope documented.

## Step 2: Load workflow reference
- Read refinement-workflow.md (gates, Content Extraction procedure).

## Step 3: Consolidation
- references/ has one file (rules.md, 3 lines); no cluster -> no consolidation ask.

## Step 4: Preservation gates
- Gate 1 (Content Audit): SKILL.md core = Quick Start + Workflow Steps 1-7 (used every run); Troubleshooting 60 lines supplementary (<20%); references/rules.md 3 lines.
- Gate 2 (Capability Assessment): extraction leaves a pointer; execution unimpaired -> deletion allowed.
- Gates 3 and 4 applied at step 6.

## Step 5: Apply or plan-only
Question: "Apply the approved scope?" options "Apply changes" / "Plan only" / "Stop". Answer: **Apply changes**.

## Step 6: Make changes (CREATE -> LINK -> DELETE)
1. CREATE references/troubleshooting.md with the verbatim 60-line Troubleshooting section (55 failure modes; verified by count).
2. Gate 3 (Migration Verification): destination exists, 55/55 failure modes present -> pass.
3. LINK: inserted pointer in SKILL.md under "## Troubleshooting (Edge Cases)": "When a run fails, details are in `references/troubleshooting.md` (...)". Verified by Grep.
4. Gate 4 (Operator Confirmation): "Delete the inline Troubleshooting body from SKILL.md (now in references/troubleshooting.md)?" Simulated answer: approved.
5. DELETE: removed the inline 55-item body lines from SKILL.md (heading and pointer kept).
6. Standard sections auto-added (no approval needed, not a file action): When to Use, When NOT to Use, Testing & Validation, Reference Guide; plus Goal Verification section for goal 3.

Ordered file-action log:
1. CREATE references/troubleshooting.md
2. LINK SKILL.md -> references/troubleshooting.md
3. DELETE inline Troubleshooting body from SKILL.md (Gate 4 approved)

## Step 7: Validate (seven phases)
- P1 inventory before: SKILL.md, references/rules.md; after: SKILL.md, references/rules.md, references/troubleshooting.md.
- P2 read all: complete, no gaps.
- P3 frontmatter: name, description present; unchanged.
- P4 body: 279 lines -> R13 Weak Warning tier (was Soft Warning); 80% rule applied; no code blocks (R18 n/a).
- P5 references: both linked files exist, one level deep, no ref->ref chains.
- P6 tools: Read, Write, Grep, Glob declared; Grep/Glob unused (Minor, left as operator chose to keep tool scoping).
- P7 testing: activation phrases (clean/dedupe/summarize CSV) retained in description.

## Step 8: Measure goals
See goal-measurement.md. All 3 PASS.

## Step 9: Trigger regression
description/when_to_use unchanged -> skipped.

## Step 10: Compliance and reviewers
Skill(plugin-rulebook) and skill-reviewer cannot be dispatched in this dry run -> not run; noted. Manual spot check: no forbidden frontmatter, code blocks none, links valid.
Change summary:
```
Lines: 307 -> 279
Frontmatter: no changes
Sections added: When to Use, When NOT to Use, Testing & Validation, Goal Verification, Reference Guide
Files created: references/troubleshooting.md
Files deleted: none (inline section body removed from SKILL.md)
plugin-rulebook: not run (dry-run, dispatch unavailable)
```
`<skill-improvement-complete>` not emitted: its condition requires the plugin-rulebook and skill-reviewer passes, which could not run in this simulation.
