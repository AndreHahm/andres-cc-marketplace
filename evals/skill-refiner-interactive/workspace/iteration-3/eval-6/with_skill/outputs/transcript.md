# Dry-run transcript: skill-refiner-interactive on demo-skill (eval-6)

Operator: "Refine the skill in OUTDIR/target so it follows best practices."
Fixture copied to OUTDIR/target. Skill files read from the worktree copy only.

## Step 0 (Detect Predating Context)
The operator request names a skill path but provides no skill file contents, problem description, or ongoing discussion. No predating context -> continue to Step 1.

## Step 1 (Quick Start)
Plain-text question "What skill do you want to work on?" -> simulated answer: already located (OUTDIR/target).

## Step 2 (Quick Start) AskUserQuestion
Q: "What would you like to do with this skill?" header "Action"; options: "Refine" / "Validate".
Simulated answer: Refine (the request says "refine", first option).

## Step 3 (Quick Start) Route
"Refine" -> Core Workflow: Refinement.

## Refinement step 1: Locate the skill
Skill already located at OUTDIR/target (per operator). Not gitignored, not in cache, no mirror pair (.claude/skills counterpart absent), so no R19 halt and no user-space warning.

### Pre-analysis (pre-analysis-checklist.md)
```
Pre-Analysis: demo-skill
Lines: 11 - OK (R13)
Frontmatter issues: single-line `description` (needs `>-`)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary details / marker formats)] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md -> references/b.md ("Read references/b.md")
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none (Read is referenced via "See references/a.md")
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - flag as Missing
Deferred goal candidates: see below
R13/R18 threshold source: skill-development fallback (plugin-rulebook settings not consulted in simulation)
```

### Goal derivation and selection (goal-derivation.md)
Findings -> top 3 by priority: (1) reference chain, (2) intake violation, (3) undeclared tool (second tier; ties with frontmatter, table order picks tool scoping).
Deferred candidates (listed in report): frontmatter issues (single-line description), missing goal verification, reference cluster.

AskUserQuestion (multiSelect: true), "Select refinement goals":
- "Zero reference->reference chains" (verify: chain scan over references/*.md -> 0 matches)
- "All intake uses AskUserQuestion with options" (verify: intake scan -> 0 matches)
- "Every invoked tool is declared in allowed-tools" (verify: tool-scoping scan -> no undeclared tools)
- (Other: custom goal, needs verification check)
Simulated answer: all three selected.

## Requirements Interview
### BATCH 1 (Question 1 skipped because goals were selected)
Q2 "What specific problems are you seeing?" header "Key Issues" (multiSelect) - "Hard-to-follow instructions" / "Scattered references" / "Nested sections" -> first option: "Hard-to-follow instructions".
Q3 "What would success look like?" header "Success Metric" - "Clearer workflow" / "Lower token cost" / "Production-ready" -> "Clearer workflow".
Q4 "Any areas to exclude or preserve as-is?" header "Scope Limits" - "Keep validation gates" / "Keep tool scoping" / "Nothing to exclude" -> "Keep validation gates" (note: no conflict, since the tool-scoping goal adds Grep, and tool scoping is not excluded).
Approved scope documented: the three goals.

### BATCH 2
- Content Extraction: not triggered (no large section).
- Intake Pattern: triggered, maps to selected goal. Q "Section 'Quick Start' collects user input without AskUserQuestion (...). Convert it?" header "Intake Pattern"; "Yes" / "No" -> Yes.
- Argument Consistency (R22): not triggered. Description Split: not triggered.
- Production Checks (always asked): Q "Which production checks should I run?" multiSelect; "Security scan" / "Error handling" / "Tool scoping" / "None needed" -> first option "Security scan". Ran it: no credentials or ${VAR} substitutions in SKILL.md or references.

## Refinement step 2: Load workflow reference
refinement-workflow.md consulted for gates and validation phases.

## Refinement step 3: Consolidation
Files: references/a.md (5 lines), references/b.md (4 lines). Same topic (TODO marker summary details) -> merge candidate.
Q "Should we consolidate these files? Saves N lines, improves clarity." options "Consolidate" / "Leave as-is" -> Consolidate (first option).

## Refinement step 4: Preservation gates
- Gate 1 Content Audit: SKILL.md Quick Start = core; a.md summary format = core; b.md marker list = supplementary but retained (migrated).
- Gate 2 Capability Assessment: merging b.md into a.md removes no capability -> OK.
- Gate 3 (at move): destination a.md updated first with "## Marker Formats" section, both marker lines verified present before deletion.
- Gate 4: deleting b.md (source of consolidation) needs explicit approval. Q "Delete references/b.md now that its content lives in references/a.md?" options "Approve" / "Decline" -> Approve (first option).

## Refinement step 5: Plan-only exit
Q "Apply the approved scope?" options "Apply changes" / "Plan only (write changes.md, no edits)" / "Stop" -> Apply changes (operator answer). Proceed to step 6.

## Refinement step 6: Make changes (CREATE -> LINK -> DELETE)
1. CREATE/UPDATE: references/a.md now contains "## Marker Formats" with both markers; the "Read references/b.md" line removed.
2. LINK: SKILL.md rewritten - Quick Start intake converted to an AskUserQuestion block; "See references/a.md for details, including the marker formats"; allowed-tools `Read Grep` (Grep added); standard sections auto-added: When to Use, When NOT to Use, Testing & Validation, Reference Guide. Grep confirmed no remaining references to b.md.
3. DELETE: references/b.md removed only after links verified.
Gate 1-4 order honored.

## Refinement step 7: Validate (seven phases)
1 inventory: SKILL.md + references/a.md (before: SKILL.md + a.md + b.md). 2 read all: complete. 3 frontmatter: name present; description present (still single-line, to be fixed in step 10). 4 body: 40 lines, OK tier; workflow pattern fine; no spawn anti-patterns. 5 references: a.md exists, one level deep, no chains. 6 tools: Read declared (referenced by Quick Start), Grep declared and used, no undeclared tools, no Bash misuse. 7 testing: activation phrase "summarize the TODOs in this file" plausible.

## Refinement step 8: Measure goals
- Zero ref->ref chains: re-scan references/*.md for directives to read another reference -> 0 matches. PASS
- Intake uses AskUserQuestion: scan -> 0 free-form intake. PASS
- Every invoked tool declared: Grep now in allowed-tools. PASS
No FAIL, so no accept/continue question asked.

## Refinement step 9: Trigger regression check
description and when_to_use unchanged so far -> skipped (for now).

## Refinement step 10: Compliance and reviewer passes

### Round 1
- Simulated Skill(plugin-rulebook): 1 FAIL (R8: description needs the `>-` block scalar).
- Simulated skill-reviewer (Structured output mode): counts.critical=0, counts.major=1 (missing example in Quick Start).
- Change summary not finalized; unresolved FAIL + Major.
**NO MARKER EMITTED** (round 1)

Fixes:
- Major: added an example line to Quick Start ("for a file containing `# TODO: add tests` on line 12 ...").
- R8: description changed to `>-` block scalar. This edits `description`, so step 9 runs first:
  Step 9 Q "The description changed. Verify trigger accuracy didn't regress before finalizing?" header "Trigger Regression Check"; options "Run trigger-eval check" / "Quick size check only" / "Skip" -> first option "Run trigger-eval check". In the real skill this would invoke Skill(skill-development) for its description-optimization loop; it cannot be dispatched in this simulation, so no accuracy numbers are reported (text of description is unchanged, only the YAML scalar form).

### Round 2
- Simulated Skill(plugin-rulebook): clean, no FAIL. Simulated skill-reviewer: counts.critical=0, counts.major=0.
- Conditions for marker: every plugin-rulebook FAIL fixed (yes), every Critical/Major fixed (yes), every selected goal passed (yes; goals were verified in step 8 and the later edits did not touch chain, intake, or tool-scoping state).
- Round cap (3) not reached; no cap question.

Change summary:
```
Lines: 11 -> 50
Frontmatter: description converted to >- block scalar (R8); allowed-tools gained Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide (plus an example in Quick Start)
Files created: none
Files deleted: references/b.md (merged into references/a.md)
plugin-rulebook: 1 FAIL finding fixed
```
Marker emitted at this point (round 2, all three conditions hold):

<skill-improvement-complete>

## Final state
OUTDIR/target contains SKILL.md and references/a.md (see ../final-tree.txt).
