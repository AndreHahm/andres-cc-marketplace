# Dry-run transcript: skill-refiner-interactive, eval-10 (completion-marker gate, 3 failing rounds)

Operator: "Refine the skill in OUTDIR/target so it follows best practices."
Target: copy of fixture at OUTDIR/target (demo-skill, 13-line SKILL.md, references/a.md, references/b.md).

## Quick Start, Step 0 (predating context)
No skill file/problem provided in conversation beyond the path; no escape hatch offered. Continue to Step 1.

## Quick Start, Step 1
Plain-text question "What skill do you want to work on?" -> simulated: skill already located (OUTDIR/target).

## Quick Start, Step 2
AskUserQuestion "What would you like to do with this skill?" [Refine | Validate]. Answer (request says refine): Refine.

## Quick Start, Step 3
Route "Refine" -> Core Workflow: Refinement.

## Refinement step 1: Locate
Project path given directly, not gitignored, not cache, no mirror pair (no .claude/skills twin). No question needed (simulated: already located).

### Pre-analysis (references/pre-analysis-checklist.md)
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: single-line description (needs >-, R8)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (details/marker formats)] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md -> "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: frontmatter issues (R8), missing goal verification, reference cluster
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation/selection (references/goal-derivation.md)
AskUserQuestion (multiSelect, up to 3), each option's description = verification check:
1. "Zero reference->reference chains" (verify: chain scan over references/*.md -> 0 matches)
2. "All intake uses AskUserQuestion with options" (verify: intake scan -> 0 matches)
3. "Every invoked tool is declared in allowed-tools" (verify: tool-scoping scan -> no undeclared tools)
(+ Other: custom goal)
Simulated answer: select all three. Recorded as selected goals G1, G2, G3.

## Requirements Interview
BATCH 1: goals selected -> Question 1 skipped. Questions 2-4 asked one at a time (simulated: first option each):
- Q2 "What specific problems are you seeing?" [Hard-to-follow instructions | Scattered references | Nested sections] -> Hard-to-follow instructions
- Q3 "What would success look like?" [Clearer workflow | Lower token cost | Production-ready] -> Clearer workflow
- Q4 "Any areas to exclude or preserve as-is?" [Keep validation gates | Keep tool scoping | Nothing to exclude] -> Keep validation gates
Scope documented. (Note: "Keep validation gates" does not block G3, which edits allowed-tools; first-option default per simulation rules.)

BATCH 2 (only triggered questions):
- Intake Pattern question (trigger detected; maps to selected G2): "Section 'Quick Start' collects user input without AskUserQuestion ... Convert it?" [Yes | No] -> Yes
- Content Extraction: not triggered. Argument Consistency: not triggered. Description Split: not triggered.
- Production Checks (always asked) [Security scan | Error handling | Tool scoping | None needed] -> Security scan (first option). Result: no credentials or ${VAR} substitutions found.
Scope documented.

## Refinement step 2: Load workflow reference
Reviewed references/refinement-workflow.md.

## Refinement step 3: Consolidation
Files: references/a.md (5 lines), references/b.md (4 lines). Cluster: same topic. AskUserQuestion "Should we consolidate these files? Saves N lines, improves clarity." [Consolidate | Leave as-is] -> Consolidate (first option).

## Refinement step 4: Preservation gates
- Gate 1 Content Audit: all content core (tiny skill).
- Gate 2 Capability Assessment: no impairment; content migrated, not dropped.
- Gate 3/4 applied in step 6. Gate 4 question (deletion of consolidation sources a.md, b.md): [Approve deletion | Decline] -> Approve deletion (first option).

## Refinement step 5: Plan-only exit
AskUserQuestion [Apply changes | Plan only | Stop] -> Apply changes. Proceed to step 6.

## Refinement step 6: Make changes (CREATE -> LINK -> DELETE)
- CREATE references/details.md (merged a.md + b.md content). Gate 3 verified destination complete.
- LINK SKILL.md pointer -> references/details.md.
- DELETE references/a.md and references/b.md (Gate 4 approved).
- Intake: Quick Start converted to AskUserQuestion block.
- allowed-tools: Read -> Read Grep (G3).
- Auto-added standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present).
- Description left single-line at this point (frontmatter issue was deferred, not a selected goal).

## Refinement step 7: Validate (phases 1-7)
Inventory before/after ok; content read, no gaps; frontmatter has name/description; body 44 lines, well under R13; references one level deep, no chains; tool reconciliation: Read, Grep declared and used; activation phrases ok.

## Refinement step 8: Measure goals
- G1 zero ref->ref chains: re-ran scan -> 0 matches: PASS
- G2 intake via AskUserQuestion: re-ran scan -> 0 matches: PASS
- G3 no undeclared tools: re-ran scan -> none: PASS
All pass; no FAIL question asked. COMPLETION MARKER: NO MARKER EMITTED (step 10 not reached yet).

## Refinement step 9: Trigger regression
Neither description nor when_to_use changed so far -> skip (no question).

## Refinement step 10: Compliance and reviewer passes

### Compliance round 1
- Skill(plugin-rulebook) -> 1 FAIL (R8: description not in multiline >- form).
- skill-reviewer (Structured output) -> counts.critical=0, counts.major=1 (Quick Start lacks a worked example).
- Fix: rewrite description in `>-` folded form; add example line to Quick Start. Fix changes description, so step 9 re-entered first:
  - Trigger Regression Check [Run trigger-eval check | Quick size check only | Skip] -> Run trigger-eval check (first option). Skill(skill-development) cannot be dispatched in this dry run; simulated result: no eval set, ad hoc set of 4 queries, accuracy unchanged.
- Re-run both checks (simulation control: fix did NOT clear the findings): plugin-rulebook still 1 FAIL (R8); skill-reviewer still 1 Major.
- Round 1 outcome: findings remain. Marker gate: plugin-rulebook FAIL unfixed, Major unfixed -> NO MARKER EMITTED.

### Compliance round 2
- plugin-rulebook: 1 FAIL (R8). skill-reviewer: 1 Major (missing Quick Start example).
- Fix: reword description, keep `>-` form; expand Quick Start example. Description changed -> step 9 re-entered: Trigger Regression Check -> Run trigger-eval check (simulated: accuracy unchanged).
- Re-run (simulation control: still failing): plugin-rulebook 1 FAIL (R8); skill-reviewer 1 Major.
- Round 2 outcome: NO MARKER EMITTED.

### Compliance round 3
- plugin-rulebook: 1 FAIL (R8). skill-reviewer: 1 Major.
- Fix: reword description again; further expand example. Description changed -> step 9 re-entered: Trigger Regression Check -> Run trigger-eval check (simulated: accuracy unchanged).
- Re-run (simulation control: still failing): plugin-rulebook 1 FAIL (R8); skill-reviewer 1 Major.
- Round cap (3) reached with findings remaining. Marker gate not yet satisfied -> NO MARKER EMITTED (at this point).

### Round-cap question
AskUserQuestion: "Findings remain after round 3. How to proceed?" [Continue another round | Accept remaining findings with reason | Stop]
Simulated answer: Accept remaining findings with reason. Reason recorded: "cosmetic, tracked separately". Accepted: plugin-rulebook R8 FAIL; skill-reviewer Major (missing Quick Start example).

### Change summary
```
Lines: 13 -> 44
Frontmatter: description rewritten in >- form; allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: references/details.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: 1 accepted with reason (R8, "cosmetic, tracked separately"); skill-reviewer: 1 Major accepted with reason ("cosmetic, tracked separately")
```

### Marker gate evaluation
- plugin-rulebook FAIL: not fixed, but accepted by operator with recorded reason via the round-cap question -> does not block.
- skill-reviewer Major: accepted likewise -> does not block.
- Selected goals G1-G3: all PASS.
Conditions satisfied, so the skill emits, at this exact point (after the change summary):

<skill-improvement-complete>

Marker emitted exactly once (after round 3 acceptance). NO MARKER EMITTED at the end of rounds 1, 2 and 3-before-acceptance.

## Notes
- Edits only under OUTDIR/target; fixture untouched. The demo SKILL.md's final description in target is in `>-` form as produced by the (simulated failing) fixes; the R8 FAIL persisting is simulated per task control, not a real defect.
- Line count in summary (44) for the final target SKILL.md.
