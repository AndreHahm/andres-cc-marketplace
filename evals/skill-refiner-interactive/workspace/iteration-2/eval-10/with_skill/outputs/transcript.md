# Simulated run: skill-refiner-interactive (eval-10, iteration-2)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: copy of fixture demo-skill at OUTDIR/target (SKILL.md 13 lines, references/a.md 5 lines, references/b.md 4 lines).
Simulated operator answers: skill already located; select all goals; "Apply changes" at step 5; after round 3 choose "Accept remaining findings with reason" (reason: "cosmetic, tracked separately"). Anything unanswered: first option.

## Quick Start, Step 0 (predating context)
The request only names a path; no file contents, problem description, or ongoing skill discussion were provided. No predating context, so the escape hatch is NOT offered. Continue to Step 1.

## Quick Start, Step 1
Plain-text question "What skill do you want to work on?" -> skipped, operator's answer given: skill already located (OUTDIR/target).

## Quick Start, Step 2 (AskUserQuestion)
Question: "What would you like to do with this skill?" / header "Action" / options: "Refine", "Validate".
Simulated answer (first option, consistent with the request to refine): **Refine**.

## Quick Start, Step 3
Route: Refine -> Core Workflow: Refinement.

## Core Workflow: Refinement, step 1 (Locate the skill)
- Already located at OUTDIR/target (no project/user-space/cache search needed; not a cache path, not gitignored, not user-space).
- Mirror-pair check (R19): no `.claude/skills/demo-skill/` counterpart exists -> single logical skill, no Mirror Divergence question.

### Pre-analysis (references/pre-analysis-checklist.md)
plugin-rulebook found (.claude/skills/plugin-rulebook); R13/R18 tiers loaded from assets/settings.json.
```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: single-line `description` (needs `>-`, R8)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker docs)] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md -> references/b.md ("Read references/b.md")
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — flag as Missing
Deferred goal candidates: frontmatter issues (R8), missing goal verification, reference cluster
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation and selection (goal-derivation.md)
Priority order gives 2 first-tier goals + 1 second-tier goal (max 3). AskUserQuestion, multiSelect: true, header "Goals":
1. "Zero reference->reference chains" — verification: re-run checklist chain scan over references/*.md -> 0 matches (source: ref->ref chain finding)
2. "All intake uses AskUserQuestion with options" — verification: re-run checklist intake scan -> 0 matches (source: intake violation)
3. "Every invoked tool is declared in allowed-tools" — verification: re-run checklist tool-scoping scan -> no undeclared tools (source: Grep undeclared)
("Other" = custom goal, not used.)
Simulated answer: all three selected. Recorded as G1, G2, G3.

### Requirements Interview
BATCH 1 (Question 1 skipped because goals were selected; Questions 2-4 scoped to selected goal areas, first option chosen for each):
- Q2 "What specific problems are you seeing?" (multiSelect) options: Hard-to-follow instructions / Scattered references / Nested sections -> "Scattered references" (first option adapted to goal areas; scope documented)
- Q3 "What would success look like?" options: Clearer workflow / Lower token cost / Production-ready -> "Clearer workflow"
- Q4 "Any areas to exclude or preserve as-is?" options: Keep validation gates / Keep tool scoping / Nothing to exclude -> "Keep validation gates" (does not block G3; allowed-tools stays in scope)
Approved scope documented.

BATCH 2 (only triggered questions):
- Intake Pattern (triggered; maps to selected G2): "Section 'Quick Start' collects user input without AskUserQuestion (...). Convert it?" options Yes / No -> **Yes** (first option)
- Content Extraction: not triggered. Argument Consistency: not triggered. Description Split: not triggered.
- Production Checks (always asked), multiSelect, options: Security scan / Error handling / Tool scoping / None needed -> "Security scan" (first option). Result: no credentials or ${VAR} substitutions found.
Reference clusters are not asked here (step 3).

## Step 2 (Load workflow reference)
Read references/refinement-workflow.md (gates, validation phases).

## Step 3 (Consolidation)
references/ files: a.md 5 lines, b.md 4 lines; both cover TODO marker docs -> cluster flagged.
AskUserQuestion: "Should we consolidate these files? Saves N lines, improves clarity." options "Consolidate" / "Leave as-is". Simulated answer (first option): **Consolidate** (merge b.md into a.md).

## Step 4 (Preservation gates)
- Gate 1 Content Audit: SKILL.md 13 lines core; a.md 5 lines supplementary; b.md 4 lines supplementary.
- Gate 2 Capability Assessment: merging b into a and deleting b does not impair execution -> safe.
- Gate 3 Migration Verification: destination a.md gains the marker formats section; verified complete before removing b.md; SKILL.md pointer will target a.md.
- Gate 4 Operator Confirmation: AskUserQuestion "Okay to delete references/b.md?" options "Delete"/"Keep" -> **Delete** (first option).

## Step 5 (Plan-only exit)
AskUserQuestion: apply the approved scope? options "Apply changes" / "Plan only (write changes.md, no edits)" / "Stop". Simulated answer: **Apply changes**. Continue to step 6.

## Step 6 (Make changes, CREATE -> LINK -> DELETE)
- CREATE: references/a.md updated with "## Marker Formats" section (content of b.md).
- LINK: removed the "Read references/b.md" chain line; SKILL.md points only to references/a.md.
- DELETE: references/b.md removed (Gate 4 approved).
- SKILL.md: Quick Start intake converted to an AskUserQuestion block (G2); `allowed-tools: Read` -> `Read Grep` (G3).
- Standard sections auto-added (no approval needed): When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start already present).

## Step 7 (Validate, seven phases)
1 inventory before/after: SKILL.md + a.md + b.md -> SKILL.md + a.md. 2 read all: complete. 3 frontmatter: name/description present (description still single-line at this point). 4 body: 45 lines, R13 OK, no spawn anti-patterns. 5 references: a.md exists, one level deep, no ref->ref chain. 6 tools: Grep and Read declared; no unused. 7 testing: activation phrase "summarize the TODOs in this file" fits.

## Step 8 (Measure goals)
- G1 zero ref->ref chains: 0 matches -> PASS
- G2 intake via AskUserQuestion: 0 matches -> PASS
- G3 every invoked tool declared: no undeclared tools -> PASS
All goals PASS (no failure ask). Step 8 does not emit the marker. NO MARKER EMITTED.

## Step 9 (Trigger regression check)
Neither `description` nor `when_to_use` changed before this point -> step skipped. (Later compliance-round edits touch `description`; see note after round 3.)

## Step 10 (Compliance and reviewer passes)
Simulation control: every fix fails to clear its finding; each round plugin-rulebook reports 1 FAIL (R8) and skill-reviewer reports 1 Major (missing Quick Start example).

### Compliance round 1
- Skill(plugin-rulebook): 1 FAIL — R8 (description must use multiline `>-` syntax). skill-reviewer (full, Structured output mode): counts.critical 0, counts.major 1 (Quick Start lacks an example).
- Fix attempt: description converted to `>-` form; example summary block added to Quick Start. Re-run pending (round 2).
- Completion marker at this point: NO MARKER EMITTED (1 FAIL and 1 Major remain, round budget not exhausted, no operator acceptance).

### Compliance round 2
- Skill(plugin-rulebook): 1 FAIL — R8. skill-reviewer: counts.critical 0, counts.major 1 (missing Quick Start example).
- Fix attempt: description reworded to a what-sentence; example reworded ("Example: for a file with two markers...").
- Completion marker at this point: NO MARKER EMITTED.

### Compliance round 3
- Skill(plugin-rulebook): 1 FAIL — R8. skill-reviewer: counts.critical 0, counts.major 1 (missing Quick Start example).
- Fix attempt: description given a "Use when..." clause; example labelled with input and output.
- Re-run after the round-3 fix: still 1 FAIL (R8) and 1 Major. Round cap (3) reached with findings remaining.
- Completion marker at this point: NO MARKER EMITTED.

### Round cap ask (findings remain after round 3)
AskUserQuestion: "Findings remain after 3 rounds (plugin-rulebook: 1 FAIL R8; skill-reviewer: 1 Major, missing Quick Start example). How do you want to proceed?" options: "Continue another round" / "Accept remaining findings with reason" / "Stop".
Simulated answer: **Accept remaining findings with reason**, reason recorded: "cosmetic, tracked separately".

### Change summary
```
Lines: 13 -> 53
Frontmatter: allowed-tools Read -> Read Grep; description converted to `>-` and reworded with a "Use when" clause (R8 still reported FAIL, accepted)
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide; Quick Start example + AskUserQuestion block
Files created: none
Files deleted: references/b.md (merged into references/a.md)
plugin-rulebook: 1 accepted with reason ("cosmetic, tracked separately") — R8
skill-reviewer: 1 Major accepted with reason ("cosmetic, tracked separately") — missing Quick Start example
Goals: G1 PASS, G2 PASS, G3 PASS
```

### Completion marker
Gate check: plugin-rulebook's remaining FAIL and skill-reviewer's remaining Major were both accepted by the operator with a recorded reason, and every selected goal passed. Emitted marker (literal text):

<skill-improvement-complete>

Note on ambiguity (flagged, not resolved by the skill text): the marker rule says "after plugin-rulebook reports no FAIL findings ... (or the operator accepted them with a recorded reason)". The parenthetical grammatically attaches to skill-reviewer's findings; the step-10 bullet and the summary line "N accepted with reason" for plugin-rulebook treat accepting remaining findings as covering both. This simulation followed the latter reading and emitted the marker.
Note: the round-2/3 edits changed `description` after step 9 had been evaluated, yet the skill has no re-entry into step 9 from step 10; step 9's Trigger Regression Check was not run. A strict reading of step 9 ("if description changed ... before finalizing") would require it.
