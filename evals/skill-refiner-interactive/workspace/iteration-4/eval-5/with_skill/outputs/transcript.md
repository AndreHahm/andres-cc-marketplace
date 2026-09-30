# Dry-run transcript: skill-refiner-interactive (eval-5, iteration 4)

Target: OUTDIR/target (copy of fixture demo-skill). Operator: "Refine the skill in OUTDIR/target so it follows best practices."

## Quick Start
- A (escape hatch): no predating context (no skill file pasted, no problem described beyond the request). Escape-hatch question NOT asked.
- B: skipped, the request already names the skill.
- C: skipped, the request already says "refine".
- D: route "Refine" -> Core Workflow: Refinement.

## Step 1: Locate the skill
- Skill already located by operator (OUTDIR/target). No project-glob ambiguity, not gitignored, not user-space, not cache.
- Mirror-pair check (R19): no `.claude/skills/demo-skill/` counterpart; one logical skill.

### Pre-analysis (references/pre-analysis-checklist.md)
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13; plugin-rulebook settings.json found, tiers loaded)
Frontmatter issues: single-line `description` (needs `>-`)
Large sections (>=50 lines): none
Reference files: 2 [clusters: none (a.md = summary output, b.md = marker syntax; different topics) | oversize >=400: none]
Workflow files: 0
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md ..."
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no (description ~22 chars)
Tool scoping (R6): undeclared: Grep ("grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: frontmatter single-line description, missing standard sections (auto-added step 6), missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal selection (goal-derivation.md)
AskUserQuestion (multiSelect, up to 3), options with verification shown:
1. "Zero reference->reference chains" - re-run chain scan over references/*.md -> 0 matches
2. "All intake uses AskUserQuestion with options" - re-run intake scan -> 0 matches
3. "Every invoked tool is declared in allowed-tools" - re-run tool-scoping scan -> no undeclared tools
(+ "Other" for custom goal)
Simulated operator answer: select all three. Selected goals recorded: G1 chain, G2 intake, G3 tools.

## Requirements Interview
- BATCH 1: goals selected -> Question 1 skipped. Questions 2-4 asked one at a time (no operator answers supplied -> first option):
  - Q2 "What specific problems are you seeing?" options: Hard-to-follow instructions / Scattered references / Nested sections -> "Hard-to-follow instructions"
  - Q3 "What would success look like?" options: Clearer workflow / Lower token cost / Production-ready -> "Clearer workflow"
  - Q4 "Any areas to exclude or preserve as-is?" options: Keep validation gates / Keep tool scoping / Nothing to exclude -> "Keep validation gates" (tool scoping remains in scope)
  - Approved scope documented: goals G1-G3, plus standard sections.
- BATCH 2 (escape hatch not used, so runs after BATCH 1):
  - Extraction: not asked (no large section). R22: not asked. Desc split: not asked.
  - Intake: asked ("Section 'Quick Start' collects user input without AskUserQuestion ... Convert it?", Yes / No) -> "Yes"
  - Prod checks: asked (Security scan / Error handling / Tool scoping / None needed) -> "Security scan" (first option). Result: no credentials or ${VAR} substitutions found.

## Step 2: Load workflow reference
Reviewed references/refinement-workflow.md (gates, validation phases).

## Step 3: Consolidation opportunities
references/ files: a.md (5 lines), b.md (4 lines). Different topics, no merge candidates -> consolidation ask NOT asked (nothing to propose).

## Step 4: Preservation gates
- Gate 1 content audit: SKILL.md (13 lines, all core), a.md (core detail), b.md (core detail). Nothing supplementary.
- Gate 2: planned changes (intake rewrite, Grep declared, chain fix, standard sections, `>-`) impair nothing.
- Gates 3/4 at step 6: no content moved, no deletions planned -> no Gate 4 ask.

## Step 5: Plan-only exit
AskUserQuestion: "Apply the approved scope?" options: Apply changes / Plan only / Stop -> simulated answer "Apply changes". Continue to step 6.

## Step 6: Make changes (round 1)
Edits in OUTDIR/target/SKILL.md: folded `description: >-`; `allowed-tools: Read Grep`; Quick Start intake converted to AskUserQuestion block; "grep the file" -> "use Grep"; added standard sections (When to Use, When NOT to Use, Testing & Validation, Reference Guide). Per simulation control, this round MISSED the reference-chain fix (references/a.md untouched).

## Step 7: Validate result (seven phases)
Phases 1-7 run. Phase 5 (References): links exist; chain check deferred to goal measurement. Phase 6 tools: Read, Grep declared and used; AskUserQuestion excluded.

## Step 8: Measure goals - MEASUREMENT PASS 1
(see goal-measurement.md)
- G1 FAIL (actual: references/a.md line 5 still says "Read references/b.md"), G2 PASS, G3 PASS.
AskUserQuestion: "Goal 'Zero reference->reference chains' did not pass. Verification: chain scan -> 0 matches. Actual: references/a.md line 5 'Read references/b.md'. Accept with a recorded reason, or continue refining?" options: Accept with reason / Continue refining
Simulated answer: "Continue refining".

## RETURN to Step 6 (focus: G1 reference chain)
Edits: references/a.md line 5 now "Marker formats are listed in `SKILL.md`'s Reference Guide." (no directive to read another reference); SKILL.md Quick Start now points to both references/a.md and references/b.md (one level deep from SKILL.md).

## Step 7 re-run (Phase 5 References) after the fix
All linked files exist, one level deep, no reference->reference directives.

## Step 8: Measure goals - MEASUREMENT PASS 2
All three goals PASS (see goal-measurement.md). No ask needed.

## Step 9: Trigger regression check
`description` text unchanged (only reformatted to folded `>-` style), no `when_to_use` added -> trigger-eval ask skipped, stated explicitly.

## Step 10: Compliance and reviewer passes (simulated; Skill/Agent cannot be dispatched in dry-run)
- Skill(plugin-rulebook) on target: simulated PASS (no FAIL findings expected after fixes).
- skill-reviewer (structured output) : simulated counts.critical=0, counts.major=0.
- Round 1 of max 3 sufficed; no round-cap ask.
Change summary:
```
Lines: 13 -> 51
Frontmatter: description folded to >-, allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: none
plugin-rulebook: PASS (simulated)
```
All conditions hold (rulebook FAILs fixed, no Critical/Major, all goals PASS):
<skill-improvement-complete>

Final file list written to final-tree.txt.
