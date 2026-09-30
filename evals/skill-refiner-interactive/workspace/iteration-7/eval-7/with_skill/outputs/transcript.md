# Transcript: skill-refiner-interactive dry run (eval 7, declined deletion)

Operator: "Refine the skill in OUTDIR/target so it follows best practices."
Fixture copied to OUTDIR/target (original untouched).

## Quick Start A (escape hatch)
No predating context (request only names the skill and action). Escape-hatch question NOT asked. Continue to B.

## Quick Start B
Request names the skill; simulated answer "skill already located". Plain-text question skipped.

## Quick Start C
Request says "refine" -> question skipped. D: route to Core Workflow: Refinement.

## Step 1: Locate the skill
Target is OUTDIR/target (given path). No mirror pair (no .claude/skills copy), not user-space, not cache, not gitignored. Located.

### Pre-analysis (references/pre-analysis-checklist.md)
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: single-line description (needs >-) - description is a short plain scalar
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (markers/details) | oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md "Read references/b.md ..." (imperative directive)
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" (free-form intake, no AskUserQuestion)
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): "Helps with demo tasks." = 22 chars, below the 80 floor (warning tier; above the 20 critical floor)
Tool scoping (R6): undeclared: Grep (body says grep the file) / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: description size (R21), cluster a.md+b.md, frontmatter single-line description, missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation and selection (goal-derivation.md)
Priority order: first tier = ref chain, intake. Second tier = undeclared tool. Max 3.

AskUserQuestion (multiSelect, header "Goals"): "Which goals should this session pursue?"
Options:
 - "Zero reference->reference chains" - check: re-run chain scan over references/*.md -> 0 matches
 - "All intake uses AskUserQuestion with options" - check: re-run intake scan -> 0 matches
 - "Every invoked tool is declared in allowed-tools" - check: re-run tool-scoping scan -> no undeclared tools
Simulated answer: all three selected.

## Requirements Interview
Goals selected -> BATCH 1 Question 1 skipped.

### BATCH 1 (one question at a time; no answer supplied -> first option)
- Q2 "What specific problems are you seeing?" (Key Issues; Hard-to-follow instructions / Scattered references / Nested sections) -> "Hard-to-follow instructions"
- Q3 "What would success look like?" (Success; Clearer workflow / Lower token cost / Production-ready) -> "Clearer workflow"
- Q4 "Any areas to exclude or preserve as-is?" (Scope Limits; Keep validation gates / Keep tool scoping) -> "Keep validation gates" (so no Testing & Validation section is auto-added in step 6)
Approved scope documented: the 3 goals; Testing & Validation area excluded.

### BATCH 2
Escape hatch not used -> proceeds after BATCH 1.
- Extraction: trigger not detected, not asked.
- Intake: detected and its finding maps to a selected goal -> asked.
  AskUserQuestion (header "Intake"): "Section 'Quick Start' collects user input without AskUserQuestion (free-form 'Ask the user which file to process'). Convert it?" Options: "Yes" / "No". -> "Yes" (first option)
- Arguments (R22): not detected, not asked.
- Desc split: not detected, not asked.
- Prod checks (asked every session): "Which production checks should I run?" options: Security scan / Error handling / Tool scoping / None needed -> "Security scan" (first option). Scan of SKILL.md, references/: no credentials, keys, tokens or ${VAR} substitutions found.
- Reference clusters: not asked here (step 3 is the single consolidation ask).

## Step 2: Load workflow reference
Read references/refinement-workflow.md (gates, validation phases, rollback).

## Step 3: Consolidation opportunities
Target has references/. Files: a.md (5 lines), b.md (4 lines), same topic (TODO summaries and marker formats) -> one merge candidate.
AskUserQuestion: "Should we consolidate these files? Saves ~2 lines, improves clarity." Options: "Consolidate" / "Leave as-is". Simulated answer: Consolidate.

## Step 4: Preservation gates
- GATE 1 Content Audit: SKILL.md 13 lines (frontmatter, Quick Start; core). a.md: detail text (core to the Quick Start), directive to read b.md. b.md: marker formats (supplementary). All classified; nothing supplementary over 20 lines.
- GATE 2 Capability Assessment: Consolidation merges content only; would not impair execution. Removing the ref->ref directive and linking b.md from SKILL.md preserves access to b.md. Safe.
- GATE 4 (asked right after the consolidation approval, before step 6, because the consolidation's sources would be deleted):
  AskUserQuestion: "Okay to delete references/a.md and references/b.md once their content is in the consolidated file?" Options: "Delete" / "Keep". Simulated operator: DECLINES every deletion -> "Keep".
  Per step 4: declined -> the consolidation is NOT performed (merging without deleting only duplicates content). Reported: "Consolidation of a.md + b.md: declined (source deletion not approved); both files kept unchanged in place." No consolidated file created.
- GATE 3 (migration verification): applies to the one migration below (the pointer to b.md moving from a.md into SKILL.md): destination (SKILL.md Quick Start) exists and links to references/b.md; verified.

## Step 5: Plan-only exit ask
AskUserQuestion: "Apply the approved scope?" Options: "Apply changes" / "Plan only" / "Stop". Simulated: "Apply changes". Step 6 runs.

## Step 6: Make changes
Rollback: target is a scratch copy under OUTDIR; original fixture at evals/skill-refiner-interactive/fixtures/demo-skill/ is the pre-edit state (restore by re-copying). Files created: none. Files deleted: none.

Changes (CREATE -> LINK -> DELETE order; no deletion happened):
1. Tool scoping goal: allowed-tools "Read" -> "Read Grep" (frontmatter edit).
2. Intake goal: Quick Start free-form "Ask the user..." replaced by an AskUserQuestion block (options with real choices).
3. Ref chain goal: CREATE/LINK step - SKILL.md Quick Start now links references/b.md as well as a.md; then the imperative "Read references/b.md for the full list of marker formats." line removed from a.md (a pointer relocation, a migration auto-approved under Gate 4; no content file deleted). Gate 3 verified destination first.
4. Standard sections auto-added (no approval needed): ## When to Use, ## When NOT to Use, ## Reference Guide (table of both references files). NOT added: ## Testing & Validation (excluded by BATCH 1 Q4 "Keep validation gates"). Quick Start already present.
No further Gate 4 asks arose: no other deletion was proposed (the removed directive line is a relocated pointer, not a deleted content file or section; a.md and b.md kept).

## Step 7: Validate (seven phases)
1. File inventory: before: SKILL.md 13, a.md 5, b.md 4 (3 files). After: SKILL.md 38, a.md 3, b.md 4 (3 files), none added/removed.
2. Read all: all three files load completely; no truncation.
3. Frontmatter: name and description present; allowed-tools "Read Grep" valid; no forbidden field. Note: description is a single-line plain scalar, 22 chars (deferred candidate, not in approved scope).
4. Body: 38 lines, within R13 OK tier; 80% rule unaffected; Quick Start actionable; no spawn anti-patterns. Workflow pattern check (design-patterns.md) is not run in detail in this dry run (tiny skill, sequential workflow).
5. References: a.md and b.md exist, linked from SKILL.md, one level deep, no ref->ref chain.
6. Tools: undeclared Grep now declared; Read declared and used; AskUserQuestion excluded; no Bash-for-dedicated-tool misuse.
7. Testing/trigger phrases: description is too vague ("Helps with demo tasks.") to verify real-world activation; flagged, deferred.

## Step 8: Measure goals
See goal-measurement.md: all 3 PASS. No "Accept with reason" / "Continue refining" asks needed.

## Step 9: Trigger regression
Neither description nor when_to_use text changed -> skipped.

## Step 10: Compliance and reviewer passes
Cannot be run in this dry run (Skill(plugin-rulebook) and skill-reviewer agent cannot be dispatched). Per the skill, if either check cannot be run, do NOT emit <skill-improvement-complete>; say so in the change summary.

Change summary:
```
Lines: 13 -> 38 (SKILL.md)
Frontmatter: allowed-tools "Read" -> "Read Grep"; description unchanged (R21 low-length and single-line remain, deferred)
Sections added: When to Use, When NOT to Use, Reference Guide (Testing & Validation not added: excluded at BATCH 1 Q4)
Files created: none
Files deleted: none
Consolidation: a.md + b.md consolidation DECLINED at Gate 4 (source deletion not approved) - not performed
plugin-rulebook: NOT RUN (cannot dispatch in dry run)
```
Completion marker: NOT emitted (plugin-rulebook and skill-reviewer could not be run).
