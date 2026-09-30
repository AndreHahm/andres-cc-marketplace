# Transcript: skill-refiner-interactive dry-run (eval-5)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Fixture copied to OUTDIR/target/.

## Quick Start Step 0 (Detect Predating Context)
Predating context: the operator named the skill path in the request (a path, but no skill content or problem description). Treated as no predating escape hatch needed; the simulated operator says "skill already located", so Steps 1-3 are satisfied by the request wording ("Refine" = Step 2 answer, Step 3 routes to Core Workflow: Refinement).

## Refinement step 1: Locate the skill
- Target: OUTDIR/target/ (not gitignored, not cache, not user-space). Mirror-pair check (R19): no sibling .claude/skills copy -> N/A. Skill already located (simulated operator answer); no ask fired.

### Pre-analysis (pre-analysis-checklist.md, report)
```
Pre-Analysis: demo-skill
Lines: 5 body lines — OK (R13)
Frontmatter issues: single-line description (needs >-)
Large sections (>=50 lines): none
Reference files: 2 [clusters: none] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start "Ask the user which file to process" (no AskUserQuestion)
Argument consistency (R22): none
when_to_use split candidate: no (description ~21 chars)
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none (Read declared; not used as explicit invocation — Minor)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent — flag as Missing
Deferred goal candidates: Missing goal verification (Minor), missing standard sections (Minor)
R13/R18 threshold source: plugin-rulebook/assets/settings.json (not loaded in dry-run; simulated)
```

### Goal derivation and selection (goal-derivation.md)
ASK (AskUserQuestion, multiSelect: true, up to 3 goals + Other):
Question: "Which goals should this refinement session achieve?"
Options:
1. "Zero reference->reference chains" — verification: re-run checklist chain scan over references/*.md -> 0 matches
2. "All intake uses AskUserQuestion with options" — verification: re-run intake scan -> 0 matches
3. "Every invoked tool is declared in allowed-tools" — verification: re-run tool-scoping scan -> no undeclared tools
(+ Other)
Simulated operator answer: select all goals offered (G1 chains, G2 intake, G3 tools).
Goals recorded.

## Requirements Interview
BATCH 1: goals selected -> skip Question 1. Questions 2-4:
- Q2 "What specific problems are you seeing?" options: Hard-to-follow instructions / Scattered references / Nested sections. No simulated answer given -> first option chosen: "Hard-to-follow instructions".
- Q3 "What would success look like?" options: Clearer workflow / Lower token cost / Production-ready. First option: "Clearer workflow".
- Q4 "Any areas to exclude or preserve as-is?" options: Keep validation gates / Keep tool scoping / Nothing to exclude. First option: "Keep validation gates" (no validation gates exist in the target; no effect).
Scope documented.

BATCH 2 (conditional on findings and selected goals):
- Content extraction: none detected -> skipped. Consolidation: none -> skipped. R22: none -> skipped.
- Intake pattern (tied to selected goal G2): ASK "Section 'Quick Start' collects user input without AskUserQuestion... Convert?" options Yes / No. First option: Yes.
- when_to_use split: not a candidate -> skipped.
- Production hardening: ASK "Which production checks should I run?" (multiSelect) options Security scan / Error handling / Tool scoping / None needed. First option: "Security scan" (grep for credentials: none found; substitution variables: none).

## Step 2: Load workflow reference
Read references/refinement-workflow.md.

## Step 3: Consolidation opportunities
2 reference files (a.md 5 lines, b.md 4 lines), different topics (summary format vs marker formats) -> no consolidation proposed; ask not fired.

## Step 4: Preservation gates
Gate 1 audit: SKILL.md (13 lines, core), a.md, b.md (supplementary). Gate 2: no deletions/moves -> no capability impairment. Gate 3: no moves. Gate 4: no deletions -> nothing to confirm.

## Step 5: Plan-only exit
Request wording did not say plan-only, so ASK: "Apply the approved scope?" options: "Apply changes" / "Plan only (write changes.md, no edits)" / "Stop".
Simulated operator answer: "Apply changes".

## Step 6: Make changes (first round of edits)
Edited OUTDIR/target/SKILL.md: description to >- (single-line fix); allowed-tools Read -> Read Grep; intake converted to AskUserQuestion block; "grep" -> Grep tool; added When to Use, When NOT to Use, Testing & Validation, Reference Guide. (No files deleted; CREATE->LINK->DELETE N/A.)
Per simulation control, this first round MISSED the reference-chain fix (references/a.md untouched).

## Step 7: Validate result (seven phases)
P1 inventory: same 3 files, SKILL.md 13 -> ~55 lines. P2 read all ok. P3 frontmatter ok. P4 body ok (R13 OK). P5 references: files exist; ref->ref chain still present in a.md (noted, to be caught by step 8). P6 tools: Read, Grep declared; OK. P7 trigger phrases ok.

## Step 8: Measure goals — MEASUREMENT PASS 1
- G1 chains: FAIL (actual: references/a.md line 5 still says "Read references/b.md")
- G2 intake: PASS (0 matches for un-optioned intake)
- G3 tools: PASS (no undeclared tools)
See goal-measurement.md, round 1.
ASK (AskUserQuestion): "Goal 'Zero reference->reference chains' did not pass. Verification: chain scan -> 0 matches. Actual: references/a.md line 5 still says 'Read references/b.md'. Accept with a recorded reason, or continue refining?" options: "Accept with reason" / "Continue refining".
Simulated answer: "Continue refining".

## RETURN to Step 6 (focus: G1 chains)
Edited OUTDIR/target/references/a.md line 5: replaced the imperative "Read references/b.md ..." with a non-directive note that marker formats are listed in the skill's Reference Guide (SKILL.md links b.md directly, one level deep).

## Step 7 (re-run, relevant phases): P5 references: no ref->ref directive; all links exist. Other phases unchanged.

## Step 8: Measure goals — MEASUREMENT PASS 2
- G1 chains: PASS (Grep for read/see directives to references/ in references/*.md -> 0 matches)
- G2 intake: PASS
- G3 tools: PASS
All goals PASS. See goal-measurement.md, round 2.

## Step 9: Trigger regression check
description changed -> ASK "Verify trigger accuracy didn't regress?" options: Run trigger-eval check / Quick size check only / Skip. First option would delegate to Skill(skill-development); not possible in dry-run. Chosen per first-option rule: "Run trigger-eval check" — SIMULATED/not executed (cannot dispatch skills). Noted as not run.

## Step 10: Compliance and reviewer passes
Skill(plugin-rulebook) and skill-reviewer cannot be dispatched in dry-run: SIMULATED/not executed. Manual self-check: no non-standard frontmatter, description >-, allowed-tools valid. The completion marker below is emitted only as a simulation, noting these two dispatches were not actually run.
```
Lines: 13 -> ~55 (SKILL.md)
Frontmatter: description converted to >- and rewritten; allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: none
plugin-rulebook: not run (dry-run simulation)
Goals: G1 PASS (after 2nd measurement), G2 PASS, G3 PASS
```
<skill-improvement-complete>  (simulated; plugin-rulebook/skill-reviewer dispatch not executed)
