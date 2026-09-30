# Dry-run transcript: skill-refiner-interactive, eval-17

Context: earlier the operator pasted the skill's SKILL.md (treated as target/SKILL.md) and said "the Quick Start is unclear to a first-time reader, please fix that". Operator now says: "Refine it."
Fixture copied to OUTDIR/target/ (SKILL.md, references/a.md, references/b.md). The original fixture is untouched. No edits were made to target.

## Quick Start A: detect predating context
Predating context exists: a skill file was already provided, a problem was already described (unclear Quick Start). "Refine it." alone would not count, but the earlier paste does.

### ASK (escape hatch)
- question: "I've reviewed the context you provided. How would you like to proceed?"
- header: "Interview"
- options:
  1. "Infer from context" - infer refinement needs from what you shared, skip the detailed interview (faster)
  2. "Define explicitly" - define improvement areas and goals explicitly (full interview)
- Simulated answer: **Infer from context**
Effect: BATCH 1 will be skipped; needs stated in the operator's context that pre-analysis cannot detect are offered as candidate goals at goal selection. This question is routing only.

## Quick Start B
Skipped: the skill is already identified (simulated: already located at OUTDIR/target).

## Quick Start C
Skipped: the request already says refine ("Refine it.").

## Quick Start D
Route: "Refine" -> Core Workflow: Refinement.

## Core Workflow: Refinement, step 1 (locate the skill)
- Located at OUTDIR/target (operator-supplied; no Glob needed).
- Gitignore exclusion: not applicable (target is not in a gitignored draft directory).
- Mirror-pair check (R19): only one copy exists (no plugins/<plugin>/skills/demo-skill/ or .claude/skills/demo-skill/), so no mirror question.
- Not user-space, not cache.

### Pre-analysis (references/pre-analysis-checklist.md)
Rulebook found at plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json. Thresholds loaded: R13 weak 100 / soft 300 / warning 490 / critical 500; R18 weak 10 / warning 20 / critical 30; R21 description min 80 (warning below 80, critical below 20), when_to_use max 512, combined max 1536.

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13; under the weak-warning tier of 100)
Frontmatter issues: description is single-line and 22 characters (R8 not triggered, it is under 80 chars); no non-standard fields; allowed-tools "Read" is fine
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md for the full list of marker formats."
Spawn anti-patterns: none
Intake pattern violations: none flagged. Quick Start "Ask the user which file to process" collects an unbounded input (a file path), so plain text is correct and it is exempt per the checklist
Argument consistency (R22): none (no $ARGUMENTS / $N / $name in body, no argument-hint)
when_to_use split candidate: no (no embedded trigger clause, description far under 400 chars)
Description size (R21): finding - description is 22 chars, under the 80-char floor (warning tier; above the critical floor of 20)
Tool scoping (R6): undeclared tools: Grep ("grep the file for TODO markers" in Quick Start is an instruction to use Grep; allowed-tools declares only Read) / unused declared tools: none (Read is used)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (4 missing; Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: see goal derivation below
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation (references/goal-derivation.md)
Findings mapped to goal rows, priority order:
1. First tier: reference chain (ref->ref) -> goal "Zero reference->reference chains"
2. Second tier: undeclared tool (Grep) -> goal "Every invoked tool is declared in allowed-tools"; R21 description size -> goal "description within R21 tiers"
3. Third tier: a.md/b.md cluster; missing goal verification
Plus, because the operator chose "Infer from context": the need stated in the predating context that pre-analysis cannot detect, "the Quick Start is unclear to a first-time reader", is offered as a candidate custom goal with a proposed verification check. It counts toward the cap of 3 and takes the lowest-priority slot, displacing the lowest derived goal (R21 description size) to the deferred candidates.
Missing standard sections are not goals (auto-added in step 6).
Deferred goal candidates: R21 description size (displaced by the context-stated need); a.md/b.md cluster; missing goal verification.

### ASK (goal selection)
- question: "Which goals should this refinement session aim for? (verification shown per option)"
- header: "Goals"  (multiSelect: true, up to 3 goals, "Other" offers a custom goal)
- options:
  1. "No ref->ref chains" - Verification: re-run the checklist's chain scan over references/*.md (Grep for imperative directives to read another references/ file) -> 0 matches. Source finding: references/a.md tells the reader to read references/b.md.
  2. "All invoked tools declared" - Verification: re-run the checklist's tool-scoping scan over SKILL.md and references/*.md -> no undeclared tools (today: Grep is used but allowed-tools is only "Read"). Source finding: undeclared Grep.
  3. "Clear Quick Start" (custom, from your context: "the Quick Start is unclear to a first-time reader") - Proposed verification, for you to confirm: Read the Quick Start and check that it (a) says what the skill does, (b) gives numbered first actions, (c) states the input needed and the expected output, and (d) needs no reference file opened to complete the first step; you confirm it reads clearly to a first-time reader.
- Simulated answer: all three selected. The operator confirms the proposed verification check for option 3, so the custom goal is accepted (it has an agreed check).
Recorded goals: G1 no ref->ref chains; G2 all invoked tools declared; G3 clear Quick Start.

## Requirements Interview
"Infer from context" -> BATCH 1 is skipped; proceed straight to BATCH 2. (BATCH 1 would also have skipped Question 1 because goals were selected.)

### BATCH 2 (only questions whose pre-analysis trigger was detected, plus Prod checks)
- Extraction: trigger not detected (no >=50-line section) - not asked.
- Intake: trigger not detected (the one intake is unbounded and exempt) - not asked.
- Arguments (R22): not detected - not asked.
- Desc split: not detected - not asked.
- Reference-file clusters: not asked here (step 3 is the single consolidation ask).
- Prod checks: asked in every refinement session.

### ASK (Prod checks)
- question: "Which production checks should I run?"
- header: "Prod checks"  (multiSelect: true)
- options:
  1. "Security scan" - Grep SKILL.md, references/ and scripts/ for credentials, keys and tokens, and for ${VAR}-style substitutions that corrupt example code
  2. "Error handling" - verify the skill handles missing files, malformed YAML and permission errors
  3. "Tool scoping" - audit allowed-tools: remove unused tools, narrow Bash wildcards
  4. "None needed" - skip production checks for this session
- Simulated answer: the operator said "Yes" for BATCH 2 questions, but this question has no "Yes" option. Deviation recorded: I applied the default (first option), "Security scan". (Possible skill/eval-wording gap: the "Yes" instruction does not map to a multiSelect question.)
Approved scope documented: goals G1-G3, security scan, no exclusions (BATCH 1 Question 4 skipped, so nothing excluded).

## Step 2: load workflow reference
Read references/refinement-workflow.md (preservation gates, validation phases, rollback).

## Step 3: consolidation opportunities (target has references/)
references/ listing (line counts): a.md 5, b.md 4.
Grouped by topic: both cover TODO/FIXME marker handling (one cluster). Potential merge: a.md + b.md -> 1 file, about 9 lines -> 7 lines (saves 2 lines). Unsure whether two tiny files share a topic? They clearly do, so they are included in the ask.

### ASK (step 3, the only consolidation ask)
- question: "Should we consolidate these files? Saves 2 lines, improves clarity."
- header: "Consolidate"
- options:
  1. "Consolidate"
  2. "Leave as-is"
- Simulated answer: none specified, so the first option: **Consolidate**. Approval covers merging content only; deleting the source files still needs Gate 4 later.

## Step 4: preservation gates (Gates 1 and 2 run here)
**GATE 1 - Content Audit**
- SKILL.md (13 lines): frontmatter (5 lines, core); "Quick Start" (7 lines, core - 80%+ usage); pointer to references/a.md (core link).
- references/a.md (5 lines): "Details" - summaries list each TODO with its line number (supplementary, <20%); directive to read b.md.
- references/b.md (4 lines): "Marker Formats" - TODO:/FIXME: (supplementary).
- scripts/, assets/: none.
**GATE 2 - Capability Assessment**
- Proposed: fix Quick Start wording/structure -> impairs execution? NO (clarifies). Safe.
- Proposed: declare Grep in allowed-tools -> NO. Safe (an edit, not a deletion).
- Proposed: merge a.md + b.md and remove the ref->ref directive -> NO, merged file keeps all content. Safe to consolidate; deleting b.md (source) is a deletion and needs Gate 4 at step 6.
- Gates 3 and 4 are deferred to step 6 (applied at each move and deletion). The early Gate 4 ask for the consolidation's source files happens only once the operator chooses to apply changes at step 5.

## Step 5: plan-only exit
The request did not use plan-only wording, so the ask is required.

### ASK (step 5)
- question: "Apply the approved scope?"
- header: "Apply"
- options:
  1. "Apply changes"
  2. "Plan only" - write changes.md, no edits
  3. "Stop"
- Simulated answer: **Stop**

## Outcome
Operator chose Stop at step 5. The session ends here:
- No step 6 (no edits), so the early Gate 4 ask for consolidation source files was never triggered and no deletions were approved.
- No changes.md written (that is only the "Plan only" branch).
- No goal measurement (step 8) and no step 9/10; no `<skill-improvement-complete>` marker emitted.
- target/ is unchanged from the fixture copy.
