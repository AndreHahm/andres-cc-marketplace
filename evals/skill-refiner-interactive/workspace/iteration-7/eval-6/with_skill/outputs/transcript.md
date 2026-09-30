# Transcript: skill-refiner-interactive dry run (eval-6)

Operator: "Refine the skill in OUTDIR/target so it follows best practices."
Target: copy of fixtures/demo-skill at OUTDIR/target.

## Quick Start A (escape hatch detection)
No predating context (request only names the skill and the action). Escape-hatch question NOT asked. Continue to B.

## Quick Start B
Skill already located (simulated answer; request names it). "What skill do you want to work on?" skipped.

## Quick Start C
Request already says "refine". Action question skipped.

## Quick Start D
Route: Refine -> Core Workflow: Refinement.

## Step 1: Locate the skill
- Found at OUTDIR/target (project path). Not user-space, not cache. No gitignored-path concern. No mirror pair (single copy), R19 check n/a.

### Step 1: Pre-analysis (references/pre-analysis-checklist.md)
```
Pre-Analysis: demo-skill
Lines: 12 - OK (R13)
Frontmatter issues: single-line description (needs >-)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (same topic: TODO summaries/marker formats) | oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): not evaluated against floors here; rulebook pass at step 10 covers it
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: frontmatter (single-line description), missing standard sections, reference cluster, goal-verification section
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1: Goal derivation and selection (goal-derivation.md)
AskUserQuestion:
- question: "Which goals should this session pursue? (select up to 3)"
- header: "Goals"
- multiSelect: true
- options:
  - "Zero reference chains": verify: re-run chain scan over references/*.md -> 0 matches
  - "Intake uses AskUserQuestion": verify: re-run intake scan -> 0 matches
  - "Every invoked tool declared": verify: re-run tool-scoping scan -> no undeclared tools
  (plus automatic "Other")

Simulated answer: select all goals offered -> G1 zero ref chains, G2 intake via AskUserQuestion, G3 all invoked tools declared.

## Requirements Interview
BATCH 1 (goals selected, so Question 1 skipped; Questions 2-4 asked about selected goal areas, first option chosen since no answer was given):

- Q2: "What specific problems are you seeing?" header "Key Issues", multiSelect. Options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections". Answer (first option): Hard-to-follow instructions.
- Q3: "What would success look like?" header "Success". Options: "Clearer workflow" / "Lower token cost" / "Production-ready". Answer: Clearer workflow.
- Q4: "Any areas to exclude or preserve as-is?" header "Scope Limits", multiSelect. Options: "Keep validation gates" / "Keep tool scoping". Answer (first option): Keep validation gates -> the Testing & Validation section is excluded from step 6's auto-added standard sections (exclusions bind them). allowed-tools remains changeable.

Approved scope documented: goals G1-G3; Testing & Validation not added; tool scoping may change.

BATCH 2 (escape hatch not used, so run after BATCH 1; only detected triggers asked):
- Extraction: not triggered (no large section). Skipped.
- Intake (triggered, goal G2 selected): question "Section 'Quick Start' collects user input without AskUserQuestion (asks the user in plain prose). Convert it?" header "Intake". Options: "Yes" / "No". Answer (first): Yes.
- Arguments: not triggered. Skipped.
- Desc split: not triggered. Skipped.
- Prod checks (asked every session): "Which production checks should I run?" header "Prod checks", multiSelect. Options: "Security scan" / "Error handling" / "Tool scoping" / "None needed". Answer (first): Security scan. Result: Grep of SKILL.md and references/ for credentials/keys/tokens and ${VAR} substitutions -> none found.
- Reference clusters not asked here (step 3 is the single ask).

## Step 2: Load workflow reference
Reviewed references/refinement-workflow.md (preservation gates, validation phases, rollback).

## Step 3: Consolidation opportunities
references/: a.md (4 lines), b.md (4 lines). Same topic (TODO summary and marker formats); unsure-case rule applies, so both included in the ask.
AskUserQuestion: "Should we consolidate these files? Saves ~2 lines, improves clarity." Options: "Consolidate" / "Leave as-is". Answer (first): Consolidate.

## Step 4: Preservation gates
- Gate 1 Content Audit: SKILL.md 12 lines core (Quick Start); a.md 4 lines supplementary; b.md 4 lines supplementary.
- Gate 2 Capability Assessment: merging b.md into a.md does not impair execution (all content preserved) -> safe.
- Gate 4 (asked now for the consolidation's source file, before step 6): AskUserQuestion "Okay to delete references/b.md once its content is in references/a.md?" Options: "Delete" / "Keep". Answer (first): Delete.
- Gates 3 and 4 otherwise applied during step 6.

## Step 5: Plan-only exit
AskUserQuestion: "Apply the approved scope?" Options: "Apply changes" / "Plan only" / "Stop". Simulated answer: Apply changes. Proceed to step 6 (no changes.md written).

## Step 6: Make changes
Rollback: pre-edit state is the untouched fixture (fixtures/demo-skill) and git; target is a copy.
1. CREATE/UPDATE destination first: references/a.md now includes the "Marker Formats" section from b.md.
2. Gate 3 migration verification: destination exists, content complete (both marker lines present), links: a.md no longer points at b.md (chain removed). Approved.
3. LINK: SKILL.md pointer to references/a.md retained; Reference Guide row added for a.md only.
4. DELETE: references/b.md removed via Bash `rm` (normal permission prompt, second gate after Gate 4 approval; simulated as granted).
5. Intake: Quick Start now asks the file via an AskUserQuestion block with options.
6. Tool scoping: allowed-tools `Read` -> `Read Grep` (Grep was invoked in body but undeclared).
7. Standard sections auto-added: When to Use, When NOT to Use, Reference Guide. Quick Start already present. Testing & Validation NOT added (excluded by Q4 "Keep validation gates").

## Step 7: Validate result (seven phases)
- Phase 1 File Inventory: before SKILL.md, references/a.md, references/b.md; after SKILL.md, references/a.md.
- Phase 2 Read All: SKILL.md and a.md complete, no gaps.
- Phase 3 Frontmatter: name, description present; no non-standard fields (single-line description still pending, handled by rulebook at step 10).
- Phase 4 Body: 43-ish lines, OK tier; 80% rule applied; workflow pattern fine; no spawn anti-patterns.
- Phase 5 References: a.md exists and linked, one level deep, no ref->ref chains.
- Phase 6 Tools: undeclared none (Grep now declared), unused declared none, no Bash-for-dedicated-tool.
- Phase 7 Testing: activates on "summarize TODOs in this file" style triggers (description is minimal).

## Step 8: Measure goals
- G1 zero reference chains: re-ran chain scan over references/*.md -> 0 matches. PASS
- G2 intake via AskUserQuestion: re-ran intake scan -> 0 matches. PASS
- G3 every invoked tool declared: re-ran tool-scoping scan -> none undeclared. PASS
All goals pass (simulation control); no FAIL asks.

## Step 9: Trigger regression check
description/when_to_use text unchanged so far -> step skipped. (Later step-10 R8 fix is format-only, same words moved into a >- block, so it does not re-enter step 9. The Quick Start example fix does not touch either field.)

## Step 10: Compliance and reviewer passes

### Compliance round 1 (first run of both checks)
- Skill(plugin-rulebook) on OUTDIR/target (simulated): 1 FAIL - R8: description needs the >- block scalar.
- skill-reviewer agent, Structured output mode (simulated): counts.critical 0, counts.major 1 - missing example in Quick Start.
Not clean, so no completion marker.
NO MARKER EMITTED

Fix pass (round 1 of max 3):
- R8: description converted to a `>-` block scalar (same text; format-only).
- Quick Start: added a concrete example summary block.

### Compliance round 2 (re-run of both checks after round-1 fix)
- Skill(plugin-rulebook) (simulated): clean, no FAIL.
- skill-reviewer (simulated): clean, counts.critical 0, counts.major 0.
All goals PASS (step 8). No 3-round-cap question needed.

Change summary:
```
Lines: 12 -> 47
Frontmatter: description converted to >- block scalar (R8); allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Reference Guide (Quick Start example and AskUserQuestion block added to existing Quick Start; Testing & Validation not added, per operator exclusion)
Files created: none
Files deleted: references/b.md (content consolidated into references/a.md)
plugin-rulebook: 1 FAIL finding fixed
```

Completion marker emitted at this point (all three conditions hold: rulebook FAIL fixed, skill-reviewer Major fixed, all goals passed):

<skill-improvement-complete>
