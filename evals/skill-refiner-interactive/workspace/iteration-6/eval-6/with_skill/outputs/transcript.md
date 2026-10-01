# Transcript: skill-refiner-interactive dry run (eval 6)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: copy of fixture demo-skill at OUTDIR/target (SKILL.md 13 lines, references/a.md, references/b.md).

## Quick Start (A-D)

- A. Predating context: none. The request only names the skill and the action, so the escape hatch is NOT offered. Interview style = full interview (BATCH 1 then BATCH 2).
- B. Skill already named in the request: plain-text question skipped.
- C. Request already says "refine": Action question skipped.
- D. Route: Refine -> Core Workflow: Refinement.

## Step 1: Locate the skill

- Simulated answer: skill already located (OUTDIR/target). No Glob search needed, no user-space or cache path, so no WARN/REFUSE.
- Gitignore-exclusion check: target is operator-specified, not a draft found by search. No action.
- Mirror-pair check (R19): target is not under plugins/<plugin>/skills/ and has no .claude/skills/ counterpart. Not a mirror pair.

### Pre-analysis (pre-analysis-checklist.md)

Report:
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13; tiers weak 100 / soft 300 / warning 490 / critical 500)
Frontmatter issues: single-line description (needs >-); no forbidden fields
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (both TODO marker details)] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md ..."
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" (intake without AskUserQuestion)
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): "Helps with demo tasks." is 22 chars, below the 80-char description floor
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none (AskUserQuestion excluded)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: frontmatter (single-line description + R21 floor), missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation and selection (goal-derivation.md)

QUESTION (AskUserQuestion, multiSelect: true, up to 3 goals), header "Goals":
1. "Zero reference chains" - verification: re-run chain scan over references/*.md -> 0 matches
2. "AskUserQuestion intake" - verification: re-run intake scan -> 0 matches
3. "Declare every invoked tool" - verification: re-run tool-scoping scan -> no undeclared tools
(Other: custom goal)
SIMULATED ANSWER: select all three. Recorded goals G1, G2, G3. Deferred (listed in report): frontmatter/R21, goal verification.

## Requirements Interview

Goals selected, so BATCH 1 Question 1 is skipped.

### BATCH 1

- Q2 "What specific problems are you seeing?" header "Key Issues", multiSelect. Options: Hard-to-follow instructions / Scattered references / Nested sections. SIMULATED (first option): "Hard-to-follow instructions".
- Q3 "What would success look like?" header "Success". Options: Clearer workflow / Lower token cost / Production-ready. SIMULATED (first option): "Clearer workflow".
- Q4 "Any areas to exclude or preserve as-is?" header "Scope Limits", multiSelect. Options: Keep validation gates / Keep tool scoping. SIMULATED (first option): "Keep validation gates". Interpretation: the target has no existing validation gates, so nothing is left unchanged by this and it does not bind the auto-added Testing & Validation section (recorded as an interpretation, since the option could be read more broadly).
- Approved scope documented: fix G1-G3, clearer workflow, auto-add standard sections.

### BATCH 2

- Extraction: not asked (no large low-frequency section).
- Intake: asked (violation detected, goal G2 selected).
  QUESTION header "Intake": "Section 'Quick Start' collects user input without AskUserQuestion (asks the user which file to process). Convert it?" Options: Yes / No. SIMULATED (first option): Yes.
- Arguments: not asked (no R22 mismatch).
- Desc split: not asked (no candidate).
- Prod checks: asked (always). QUESTION header "Prod checks", multiSelect: Security scan / Error handling / Tool scoping / None needed. SIMULATED (first option): "Security scan". Scan: no credentials, keys, tokens or ${VAR} substitutions in SKILL.md or references/. Result: clean.
- Reference clusters not asked here (step 3).

## Step 2: Load workflow reference

Read references/refinement-workflow.md (gates, validation phases, rollback).

## Step 3: Consolidation

Files: references/a.md (5 lines), references/b.md (4 lines). Same topic (TODO markers); a.md also holds the ref->ref chain.
QUESTION header (none specified): "Should we consolidate these files? Saves N lines, improves clarity." Options: Consolidate / Leave as-is. SIMULATED (first option): Consolidate. Approved.

## Step 4: Preservation gates

- Gate 1 Content Audit: SKILL.md 13 lines (Quick Start, core); a.md 5 lines ("Summaries list each TODO with its line number" + chain directive), b.md 4 lines (marker formats). All core/small.
- Gate 2 Capability Assessment: merging a.md + b.md into one file loses no content, only the chain directive, which becomes unnecessary. Will not impair execution: safe.
- Gate 3 and Gate 4 applied at each move/deletion in step 6.

## Step 5: Plan-only exit

QUESTION: "Apply the approved scope?" Options: Apply changes / Plan only / Stop. SIMULATED: "Apply changes". Continue to step 6.

## Step 6: Make changes

- Rollback settled: target is a scratch copy under OUTDIR; the pristine original is evals/skill-refiner-interactive/fixtures/demo-skill/ and is the restore source. No version-control baseline needed.
- CREATE: references/todo-markers.md (merged content of a.md and b.md, chain line dropped).
- Gate 3 Migration Verification: destination exists, complete (summary sentence, TODO:, FIXME: formats), no orphans.
- LINK: SKILL.md pointer changed to references/todo-markers.md; Reference Guide added.
- Gate 4 Operator Confirmation: QUESTION "Okay to delete the 2 originals (a.md, b.md) now that their content is in todo-markers.md?" Options: Delete / Keep. SIMULATED (first option): Delete. Each deletion runs as a Bash rm through a normal permission prompt (second gate); ran rm references/a.md references/b.md.
- Intake fix (G2): "Ask the user which file to process" replaced by an AskUserQuestion block with options.
- Tool scoping fix (G3): allowed-tools changed from `Read` to `Read Grep` (AskUserQuestion excluded, always callable).
- Standard sections auto-added (Q4 did not exclude them): When to Use, When NOT to Use, Testing & Validation (activation/non-activation checks + quality gates), Reference Guide.

## Step 7: Validate result (seven phases)

1. File inventory: before = SKILL.md, references/a.md, references/b.md; after = SKILL.md, references/todo-markers.md.
2. Read all: complete, no gaps.
3. Frontmatter: name, description, allowed-tools present; single-line description noted (deferred to rulebook pass).
4. Body: 53 lines at this point (61 after round-1 fixes), R13 tier OK (under 100); Quick Start actionable; no spawn anti-patterns.
5. References: todo-markers.md exists, linked, one level deep, no ref->ref chain.
6. Tools: Read and Grep declared and used; AskUserQuestion exempt; no Bash misuse.
7. Testing: trigger phrases in Testing & Validation; links follow.

## Step 8: Measure goals

- G1 Zero reference chains: re-ran chain scan over references/*.md -> 0 matches. PASS.
- G2 AskUserQuestion intake: re-ran intake scan (no "ask the user"/free-form questions: block without options) -> 0 matches. PASS.
- G3 Declare every invoked tool: re-ran tool-scoping scan -> Grep now declared, no undeclared tools. PASS.
All goals PASS; no FAIL question needed.

## Step 9: Trigger regression check

Neither description nor when_to_use changed in steps 6-8. Step skipped.

## Step 10: Compliance and reviewer passes

### Round 1

- Skill(plugin-rulebook) (simulated): 1 FAIL - R8: description needs the >- block scalar.
- skill-reviewer agent, Structured output mode (simulated): counts.major = 1 - missing example in Quick Start; counts.critical = 0.
- Completion marker check: a FAIL and a Major remain unfixed. NO MARKER EMITTED
- Fixes: description converted to `>-` block scalar (text value unchanged, so step 9 not re-entered); example summary added to Quick Start.

### Round 2

- Skill(plugin-rulebook) (simulated): clean, no FAIL.
- skill-reviewer (simulated): counts.critical = 0, counts.major = 0.
- All three marker conditions hold: every plugin-rulebook FAIL fixed, every Critical/Major fixed, every selected goal PASS. Round cap not reached (2 of 3).

Change summary:
```
Lines: 13 → 61
Frontmatter: description converted to >- block scalar; allowed-tools Read → Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start kept; intake converted to AskUserQuestion, example added)
Files created: references/todo-markers.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: 1 FAIL findings fixed
```

Marker emitted at this point (round 2):
```
<skill-improvement-complete>
```
