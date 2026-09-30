# Dry-run transcript: skill-refiner-interactive on demo-skill (eval 6)

Target: OUTDIR/target (copy of fixtures/demo-skill). Operator request: "Refine the skill in OUTDIR/target so it follows best practices."

## Quick Start A-D
- A (escape hatch): no predating context (no skill file pasted, no problem described; the request only names a path). Escape-hatch question NOT asked.
- B: request names the skill; "What skill do you want to work on?" skipped.
- C: request says "Refine"; Action question skipped.
- D: route -> Core Workflow: Refinement.

## Refinement step 1: Locate the skill
- Simulated operator: skill already located (OUTDIR/target). No project/user-space/cache search question asked. Not in the plugin cache, not user-space.
- Mirror-pair check (R19): no sibling copy under plugins/ or .claude/skills/ -> not a mirror pair; single logical skill.

### Pre-analysis (references/pre-analysis-checklist.md)
```
Pre-Analysis: demo-skill
Lines: 11 — OK (R13)
Frontmatter issues: single-line description (needs >-)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary / marker formats)] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md -> "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no (description ~22 chars, no embedded trigger clause)
Tool scoping (R6): Grep (body says "grep the file") undeclared / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent — flag as Missing
Deferred goal candidates: frontmatter single-line description (R8), missing goal verification, reference cluster a+b
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```
(Note: the cluster finding is handled by the step-3 consolidation ask, not a goal, per priority order it would be third tier; the 3-goal cap was filled by higher-priority findings.)

### Goal derivation/selection (goal-derivation.md)
Priority order: 1st tier: ref chain, intake; 2nd tier: undeclared tool (frontmatter, dead links... ); 3rd tier: goal verification, cluster. Top 3 = ref chain, intake, undeclared tool.

AskUserQuestion (multiSelect, up to 3):
- "Zero reference->reference chains" — verification: re-run chain scan over references/*.md -> 0 matches
- "All intake uses AskUserQuestion with options" — verification: re-run intake scan -> 0 matches
- "Every invoked tool is declared in allowed-tools" — verification: re-run tool-scoping scan -> no undeclared tools
- (Other: custom goal, needs verification check)
Simulated answer: select all three. Recorded as selected goals G1, G2, G3.

## Requirements Interview
### BATCH 1 (goals selected -> skip Question 1; ask Q2-Q4, one at a time; no answers given so first option chosen)
- Q2 "What specific problems are you seeing?" (header Key Issues; multiSelect) options: Hard-to-follow instructions / Scattered references / Nested sections -> first: Hard-to-follow instructions
- Q3 "What would success look like?" (header Success) options: Clearer workflow / Lower token cost / Production-ready -> first: Clearer workflow
- Q4 "Any areas to exclude or preserve as-is?" (header Scope Limits; multiSelect) options: Keep validation gates / Keep tool scoping / Nothing to exclude -> first: Keep validation gates
- Approved scope documented: G1-G3, plus clarity.
  (Observation: Q4 default "Keep validation gates" is harmless here; demo-skill has none.)

### BATCH 2 (Escape hatch not used -> entered after BATCH 1)
Asked only triggered questions:
- Extraction: not triggered (no >=50-line section). Not asked.
- Intake: triggered, maps to selected goal G2. Asked: "Section 'Quick Start' collects user input without AskUserQuestion (asks the user which file in prose). Convert it?" options Yes / No -> first: Yes
- Arguments (R22): not triggered.
- Desc split: not triggered.
- Prod checks (always asked): "Which production checks should I run?" options Security scan / Error handling / Tool scoping / None needed -> first: Security scan. (Grep of SKILL.md/references for credentials and ${VAR} substitutions: none found.)
- Reference clusters are not asked here (step 3).

## Step 2: Load workflow reference
Read references/refinement-workflow.md (preservation gates, validation phases).

## Step 3: Consolidation
Files: references/a.md (5 lines), references/b.md (5 lines); same topic (TODO summary and marker formats) -> merge candidate.
AskUserQuestion: "Should we consolidate these files? Saves ~2 lines, improves clarity." options Consolidate / Leave as-is -> first: Consolidate.

## Step 4: Preservation gates
- Gate 1 Content Audit: SKILL.md (11 lines, core Quick Start), a.md (summary format, supplementary), b.md (marker formats, supplementary).
- Gate 2 Capability Assessment: merging a+b into references/marker-details.md loses nothing; intake conversion keeps the same behavior; adding Grep to allowed-tools only narrows prompts. No change impairs execution.
- Gate 3 (applied in step 6 at each move): destination marker-details.md created with all content of a.md and b.md before deletion.
- Gate 4 (before deletion): AskUserQuestion "Delete references/a.md and references/b.md (sources of the approved consolidation)? Content is fully migrated to references/marker-details.md." options "Approve deletion" / "Decline deletion" -> first: Approve deletion.

## Step 5: Plan-only exit
AskUserQuestion: "Apply the approved scope?" options "Apply changes" / "Plan only" / "Stop" -> simulated answer: Apply changes. Proceed to step 6 (no changes.md written).

## Step 6: Make changes (CREATE -> LINK -> DELETE)
- CREATE references/marker-details.md (merged a.md + b.md; the ref->ref "Read references/b.md" directive is gone since both parts now live in one file).
- LINK SKILL.md pointer changed from references/a.md to references/marker-details.md; Quick Start intake converted to an AskUserQuestion block with options; Grep added to allowed-tools.
- DELETE references/a.md, references/b.md (only after link verified and Gate 4 approved).
- Standard sections auto-added without approval: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start already present).
- Disclosure: in this simulation the file writes for step 6 and for the round-1 compliance fixes below were applied in one write; the description was left as a single-line `Helps with demo tasks.` plus nothing else at the step-6 point, then fixed in round 1 as described (final file on disk contains the round-1 and round-2 state).

## Step 7: Validate result (seven phases)
1. File inventory: before SKILL.md + references/a.md,b.md; after SKILL.md + references/marker-details.md.
2. Read all: complete, no content gaps (TODO summary and both marker formats preserved).
3. Frontmatter: name, description present (description form addressed in compliance round 1).
4. Body: 52 lines, OK vs R13 tiers; 80% rule ok; workflow pattern ok; no spawn anti-patterns.
5. References: marker-details.md exists, one level deep, no reference->reference chain.
6. Tools: body invokes Read and Grep (plus AskUserQuestion, always callable); declared Read Grep -> no undeclared/unused; no Bash misuse.
7. Testing: activates on "summarize the TODOs in this file"; not on "create a new skill".

## Step 8: Measure goals
- G1 zero ref->ref chains: scan references/*.md -> 0 matches. PASS
- G2 intake via AskUserQuestion: scan -> 0 free-form intake. PASS
- G3 every invoked tool declared: Read, Grep declared. PASS
All goals PASS; no failed-goal question.

## Step 9: Trigger regression check
Description did not change before step 10 -> skipped at this point (re-entered below after the round-1 description fix).

## Step 10: Compliance round 1
- Skill(plugin-rulebook) (simulated): 1 FAIL — R8: description needs the >- block scalar.
- skill-reviewer agent, full/Structured output mode (simulated): counts.critical 0, counts.major 1 — Quick Start missing an example.
- Fixes: description converted to `>-` block scalar (and extended to a what-clause plus a Not-for clause); Quick Start given a concrete example (`notes.md` line 4 -> `line 4 - TODO: fix intro`).
- Because the description changed: step 9 re-entered before re-running checks.
  - AskUserQuestion "The description changed. Verify trigger accuracy didn't regress before finalizing?" options Run trigger-eval check / Quick size check only / Skip -> first: Run trigger-eval check.
  - Would invoke Skill(skill-development) for its Phase 5 description-optimization loop (this skill has no run_loop.py access via Bash). Cannot dispatch in dry-run; result not available, recorded as "delegation simulated, no accuracy numbers produced". Description is 2 short lines, well within R21 tiers.
- Completion gate: plugin-rulebook FAIL and a Major finding were open at the time of the round-1 report, so:

NO MARKER EMITTED

## Step 10: Compliance round 2
- Re-run Skill(plugin-rulebook) (simulated): clean, no FAIL.
- Re-run skill-reviewer (simulated): counts.critical 0, counts.major 0.
- Goals G1-G3 all PASS (re-checked after the fixes: unchanged scans still 0 matches/no undeclared tools).
- Change summary:
```
Lines: 11 -> 52
Frontmatter: description converted to >- block scalar with Not-for clause; Grep added to allowed-tools
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start enriched with AskUserQuestion block and example)
Files created: references/marker-details.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: 1 FAIL finding fixed
```
- All three conditions hold (rulebook FAIL fixed, no Critical/Major reviewer finding, all goals PASS). Marker emitted:

<skill-improvement-complete>

## Simulation observations
- Step ordering held: step 9's conditional re-entry on a step-10 description fix worked as written.
- Ambiguity noted: the step-6 auto-add of standard sections means the step-8 goal check sees a SKILL.md whose description is still single-line; this is fine because the frontmatter goal was not selected (deferred), and R8 is caught by the step-10 gate.
