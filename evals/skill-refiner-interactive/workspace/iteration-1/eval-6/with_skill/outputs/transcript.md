# Dry-run transcript: skill-refiner-interactive (eval-6, normal refine + compliance loop)

Target: OUTDIR/target (copy of fixtures/demo-skill). Skill read from the skill-refiner-interactive worktree copy only.

## Quick Start, Step 0 (predating context)
Only a path was given, with no skill content or problem description in conversation. No predating context, so no escape-hatch question; continue to Step 1.

## Quick Start, Step 1
Question: "What skill do you want to work on?" (open text). Simulated answer: skill already located (OUTDIR/target).

## Quick Start, Step 2
Question: "What would you like to do with this skill?" Options: Refine / Validate. Answer: Refine (request says "refine"; also the first option).

## Quick Start, Step 3
Route: Refine -> Core Workflow: Refinement.

## Refinement step 1: Locate the skill
- Located at OUTDIR/target/ (operator answer: already located). Not gitignored, not in plugin cache, no `.claude/skills/` mirror counterpart, so the R19 mirror-pair check is N/A (single copy).
- Pre-analysis (references/pre-analysis-checklist.md). plugin-rulebook settings.json read for R13/R18 tiers.

Pre-Analysis report:
```
Pre-Analysis: demo-skill
Lines: 12 body lines - OK (R13)
Frontmatter issues: description is single-line (needs >-)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details)] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md -> "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): Grep used ("grep the file") but undeclared / Read declared and used
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: reference cluster (a.md/b.md), missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation and selection (step 1, goal-derivation.md)
Goals derived, highest severity first, max 3:
1. Zero reference->reference chains (Critical) - verify: re-run chain scan over references/*.md -> 0 matches
2. All intake uses AskUserQuestion with options (Critical) - verify: re-run intake scan -> 0 matches
3. Every invoked tool declared in allowed-tools (Major) - verify: re-run tool-scoping scan -> no undeclared tools

AskUserQuestion (multiSelect: true): options = the 3 goals (each description shows its verification check) plus Other.
Simulated answer: select all three goals. Recorded.

## Requirements Interview
Goals were selected, so BATCH 1 Question 1 (Focus Areas) is skipped. Questions 2-4 asked, scoped to goal areas; first option used for each:
- Q2 "What specific problems are you seeing?" options: Hard-to-follow instructions / Scattered references / Nested sections. Answer: Hard-to-follow instructions.
- Q3 "What would success look like?" options: Clearer workflow / Lower token cost / Production-ready. Answer: Clearer workflow.
- Q4 "Any areas to exclude or preserve as-is?" options: Keep validation gates / Keep tool scoping / Nothing to exclude. Answer: Keep validation gates (none exist in the skill, so no effect).

BATCH 2 (conditional on findings whose goals were selected):
- Intake Pattern: "Section 'Quick Start' collects user input without AskUserQuestion... Convert?" options Yes / No. Answer: Yes.
- Content Extraction: skipped (no section >=50 lines).
- Consolidation question: skipped here (its goal was not selected); handled at step 3.
- R22: skipped (no mismatch). Description Split: skipped (not a candidate).
- Production Checks (asked every session): options Security scan / Error handling / Tool scoping / None needed (multiSelect). Answer: Security scan. Result: no credentials, no `${VAR}` substitutions found.
Approved scope documented.

## Refinement step 2: Load workflow reference
Read references/refinement-workflow.md.

## Refinement step 3: Consolidation opportunities
Listed references/: a.md (5 lines), b.md (4 lines), same topic (TODO marker details). Question: "Should we consolidate these files? Saves N lines, improves clarity." Options: Consolidate / Leave as-is. Answer: Consolidate (first option). Approved.

## Refinement step 4: Preservation gates
- Gate 1 Content Audit: SKILL.md (Quick Start, core), a.md and b.md (supplementary, small).
- Gate 2 Capability Assessment: merging b into a, removing the ref->ref directive, and adding AskUserQuestion do not impair execution.
- Gate 3 Migration Verification: destination (a.md "Marker Formats" section) created with all of b.md's content; SKILL.md pointer updated.
- Gate 4 Operator Confirmation: deletion of references/b.md requires approval. Question: "Okay to delete references/b.md (content migrated into a.md)?" Options: Delete / Keep. Answer: Delete (first option).

## Refinement step 5: Plan-only exit
Question: apply the approved scope? Options: "Apply changes" / "Plan only (write changes.md, no edits)" / "Stop". Simulated answer: Apply changes. Proceed to step 6.

## Refinement step 6: Make changes (CREATE -> LINK -> DELETE)
- CREATE: references/a.md now holds "Marker Formats" (content of b.md).
- LINK: SKILL.md Quick Start points to references/a.md for details and marker formats; the "Read references/b.md" directive removed from a.md.
- DELETE: references/b.md removed after links verified.
- Quick Start: intake converted to AskUserQuestion; "grep" replaced with `Grep`; allowed-tools: Read -> Read Grep.
- Standard sections auto-added: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start already present).
Note: description left single-line in this step (not one of the selected goals; left for the compliance gate).

## Refinement step 7: Validate result (7 phases)
1 Inventory: SKILL.md + references/a.md (b.md removed). 2 Read all: complete, no gaps. 3 Frontmatter: name/description present, no forbidden fields. 4 Body: 37 lines, OK tier, standard sections present. 5 References: a.md exists, one level deep, no ref->ref chain. 6 Tools: Read and Grep declared and used; nothing unused. 7 Testing: triggers "summarize the TODOs in this file" activate it.

## Refinement step 8: Measure goals
- Goal 1 zero ref->ref chains: chain scan over references/*.md -> 0 matches. PASS
- Goal 2 intake uses AskUserQuestion: intake scan -> 0 matches. PASS
- Goal 3 every invoked tool declared: Read, Grep both declared. PASS
No FAIL, so no accept/continue question.

## Refinement step 9: Trigger regression check
Not triggered at this point: neither description nor when_to_use changed during steps 6-8. (See the note under compliance round 1: the R8 fix is a scalar-style change only, with identical text, so this check stays skipped. Disclosed here rather than silently omitted.)

## Refinement step 10: Compliance and reviewer passes

### Compliance round 1
- Skill(plugin-rulebook) (simulated): 1 FAIL - R8: description needs the `>-` block scalar.
- skill-reviewer (simulated): 1 Major - missing example in Quick Start.
- Fixes applied: description converted to `>-` block scalar (text unchanged); Quick Start now includes an AskUserQuestion example block.
- Re-verified goals 1-3 after the fixes: all still PASS.
- Completion marker: NO MARKER EMITTED (plugin-rulebook FAIL and skill-reviewer Major both outstanding at the time of the round's report; loop must repeat).

### Compliance round 2
- Skill(plugin-rulebook) (simulated): clean, no FAIL.
- skill-reviewer (simulated): no Critical or Major.
- All selected goals PASS (goals 1-3).
Change summary:
```
Lines: 12 -> 54
Frontmatter: description converted to >- block scalar (R8); allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none (references/a.md extended with Marker Formats)
Files deleted: references/b.md
plugin-rulebook: 1 FAIL finding fixed
```
Completion marker emitted at this point:
```
<skill-improvement-complete>
```

Output files: OUTDIR/target/SKILL.md, OUTDIR/target/references/a.md; final-tree.txt lists them.
