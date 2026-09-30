# Dry-run transcript: skill-refiner-interactive, eval-10 (round cap, accept with reason)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: OUTDIR/target (copy of fixtures/demo-skill: SKILL.md 13 lines, references/a.md 5, references/b.md 4).

## Quick Start (A-D)

- A. Detect predating context: none. The request only names the skill and the action. Escape-hatch question NOT asked. Continue to B.
- B. Skipped: the request already names the skill.
- C. Skipped: the request already says "refine".
- D. Route: Refine -> Core Workflow: Refinement.

## Step 1: Locate the skill

- Simulated operator answer: skill already located (path OUTDIR/target). No "Where should I find this skill?" ask.
- Gitignore-exclusion and mirror-pair (R19) checks: target is a standalone copy, no mirror pair, nothing to compare.
- Pre-analysis (references/pre-analysis-checklist.md). Note: under the simulation rules I may read only this skill's own directory, so plugin-rulebook's settings.json was not readable; used the documented fallback (flat limits: 500 lines SKILL.md, 30 lines inline code block, R5 fallback: `version` only forbidden field).

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13, flat fallback limit 500)
Frontmatter issues: single-line description (needs `>-`)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary format / marker formats) ] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md ("Read references/b.md ...")
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" collects input without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): not measurable against rulebook tiers (settings.json not readable in this simulation); "Helps with demo tasks." is very short, flagged as likely under the floor
Tool scoping (R6): Grep (body says "grep the file") undeclared / unused declared tools: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (only Quick Start present)
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: frontmatter issues (R5/R8), reference cluster (a.md + b.md), missing goal verification
R13/R18 threshold source: skill-development fallback
```

- Goal derivation (references/goal-derivation.md), priority order, max 3:
  1. Zero ref->ref chains (from chain finding). Verification: re-run chain scan over references/*.md -> 0 matches.
  2. All intake uses AskUserQuestion with options (from intake violation). Verification: re-run intake scan -> 0 matches.
  3. Every invoked tool declared in allowed-tools (from tool scoping). Verification: re-run tool-scoping scan -> no undeclared tools.
- AskUserQuestion (multiSelect: true):
  - question: "Which goals should this refinement session target?"; header: "Goals"
  - options: "No ref->ref chains" (check: chain scan returns 0 matches) / "AskUserQuestion intake" (check: intake scan returns 0 matches) / "Declare used tools" (check: tool-scoping scan shows no undeclared tools) / Other (automatic)
  - Simulated answer: select all three.
- Goals recorded: G1 chains, G2 intake, G3 tools.

## Requirements Interview

### BATCH 1 (goals selected, so Question 1 is skipped)

- Question 2. question: "What specific problems are you seeing?"; header: "Key Issues"; options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections". Simulated answer (first option): "Hard-to-follow instructions".
- Question 3. question: "What would success look like?"; header: "Success"; options: "Clearer workflow" / "Lower token cost" / "Production-ready". Simulated answer (first option): "Clearer workflow".
- Question 4. question: "Any areas to exclude or preserve as-is?"; header: "Scope Limits"; options: "Keep validation gates" / "Keep tool scoping". Simulated answer (first option): "Keep validation gates". Interpretation: the target has no existing validation gates to preserve, so this does not exclude the Testing & Validation section from step 6's auto-add. Noted as an interpretation; allowed-tools is NOT excluded (Keep tool scoping not chosen), which G3 needs.
- Approved scope documented: clarity of the workflow, reference structure, intake, tool declaration, standard sections.

### BATCH 2 (no escape-hatch choice was made, so it follows BATCH 1)

- Extraction: not asked (no large low-frequency section).
- Intake: triggered, and it maps to selected goal G2, so asked. question: "Section 'Quick Start' collects user input without AskUserQuestion (free-form 'Ask the user which file to process'). Convert it?"; header: "Intake"; options: "Yes" / "No". Simulated answer (first option): "Yes".
- Arguments (R22): not asked (no mismatch).
- Desc split: not asked (no candidate).
- Prod checks (always asked). question: "Which production checks should I run?"; header: "Prod checks"; multiSelect; options: "Security scan" / "Error handling" / "Tool scoping" / "None needed". Simulated answer (first option): "Security scan". Result: Grep for credentials/keys/tokens/${VAR} in SKILL.md and references/ -> none found.
- Reference-file cluster not asked here (step 3 owns it).

## Step 2: Load workflow reference

- Read references/refinement-workflow.md (preservation gates, validation phases, rollback).

## Step 3: Consolidation

- references/ files: a.md (5 lines), b.md (4 lines). Same topic (TODO summary and marker formats) -> merge candidate 2 -> 1.
- AskUserQuestion: question: "Should we consolidate these files? Saves 1 lines, improves clarity."; options: "Consolidate" / "Leave as-is". Simulated answer (first option): "Consolidate".

## Step 4: Preservation gates

- Gate 1 Content Audit: SKILL.md (13 lines: Quick Start, core); references/a.md (5 lines, supplementary: summary format + pointer to b.md); references/b.md (4 lines, supplementary: marker formats).
- Gate 2 Capability Assessment: merging a.md + b.md into one file keeps all content and the skill still works -> SAFE. Converting free-form intake to AskUserQuestion keeps the same behavior -> SAFE.
- Gate 3 and Gate 4 applied at each move and deletion in step 6.

## Step 5: Plan-only exit

- AskUserQuestion: question: "Apply the approved scope?"; options: "Apply changes" / "Plan only" / "Stop". Simulated answer: "Apply changes". Step 6 runs.

## Step 6: Make changes

- Rollback: target is an eval copy of a git-tracked fixture (original fixture untouched), restorable from version control.
- CREATE: references/details.md (merged a.md + b.md; ref->ref directive removed). Gate 3 verified: destination exists, complete (summary sentence + both marker formats), nothing orphaned.
- LINK: SKILL.md pointer now targets references/details.md; Quick Start intake converted to an AskUserQuestion block; "grep" -> Grep; `allowed-tools: Read` -> `Read Grep`.
- Gate 4 AskUserQuestion: question: "Okay to delete references/a.md and references/b.md once their content is in references/details.md?"; options: "Delete" / "Keep". Simulated answer (first option): "Delete". Then DELETE via Bash `rm` (second permission gate, simulated as approved).
- Standard sections auto-added (no approval needed): When to Use, When NOT to Use, Testing & Validation, Reference Guide. (Quick Start already present.)

## Step 7: Validate result (seven phases)

- Phase 1 inventory: before SKILL.md 13 + a.md 5 + b.md 4; after SKILL.md 50 + details.md 8.
- Phase 2 read all: complete, no gaps.
- Phase 3 frontmatter: name and description present; description is still single-line (not `>-`), recorded for step 10; allowed-tools `Read Grep`.
- Phase 4 body: 50 lines, within the OK tier; Quick Start actionable; no spawn anti-patterns.
- Phase 5 references: details.md exists, linked, one level deep, no ref->ref chain.
- Phase 6 tools: Read, Grep declared and used; AskUserQuestion is always callable; Glob appears only as an option description inside the AskUserQuestion example. No Bash use.
- Phase 7 testing: activation phrases present in Testing & Validation.
- NO MARKER EMITTED (step 7).

## Step 8: Measure goals

- G1 zero ref->ref chains: re-ran chain scan over references/*.md -> 0 matches. PASS.
- G2 AskUserQuestion intake: re-ran intake scan -> 0 matches. PASS.
- G3 every invoked tool declared: re-ran tool-scoping scan -> no undeclared tools. PASS.
- All goals PASS (simulation rule). No failure ask. NO MARKER EMITTED (step 8).

## Step 9: Trigger regression check

- Skipped: neither `description` nor `when_to_use` has changed in this session so far. Trigger eval question NOT asked.

## Step 10: Compliance and reviewer passes

Round definition used: an initial check run, then each numbered round is fix attempt followed by a re-run of both checks; the cap is 3 rounds.

Initial check run:
- Skill(plugin-rulebook) on OUTDIR/target: 1 FAIL (R8, description is single-line; needs `>-`).
- skill-reviewer agent (full mode, Structured output mode): counts.critical 0, counts.major 1 (Quick Start lacks an example).

### Compliance round 1

- Fix attempt: R8: reformatted `description` to a `>-` folded block (two-space indent). Major: added an example line to Quick Start. The scalar style change leaves the description value text identical ("Helps with demo tasks."), so trigger phrasing is unchanged and step 9 is not re-entered.
- Re-run (simulation control: fixes do not clear findings): plugin-rulebook 1 FAIL (R8); skill-reviewer counts.critical 0, counts.major 1 (missing Quick Start example).
- Findings remain. NO MARKER EMITTED.

### Compliance round 2

- Fix attempt: R8: re-indented the `>-` block (four spaces). Major: extended the Quick Start example with a two-marker case. Description value unchanged, so no step 9.
- Re-run (simulation control): plugin-rulebook 1 FAIL (R8); skill-reviewer major 1 (missing Quick Start example).
- Findings remain. NO MARKER EMITTED.

### Compliance round 3

- Fix attempt: R8: wrapped the `>-` block across two lines. Major: relabeled the example "Example input and output". Description value unchanged, so no step 9.
- Re-run (simulation control): plugin-rulebook 1 FAIL (R8); skill-reviewer major 1 (missing Quick Start example).
- Findings remain after round 3, cap reached. NO MARKER EMITTED.

### Round-cap question

- AskUserQuestion: question: "Findings remain after 3 compliance rounds (plugin-rulebook R8 FAIL; skill-reviewer Major: missing Quick Start example). How should we proceed?"; options: "Continue another round" / "Accept remaining findings with reason" / "Stop".
- Simulated answer: "Accept remaining findings with reason". Reason recorded: "cosmetic, tracked separately".

### Change summary

```
Lines: 13 → 54
Frontmatter: description reformatted to a `>-` block (value unchanged); allowed-tools Read → Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: references/details.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: 1 accepted with reason (R8 FAIL, reason: "cosmetic, tracked separately")
Accepted skill-reviewer finding: Major, missing Quick Start example, reason: "cosmetic, tracked separately"
Goals: G1 PASS, G2 PASS, G3 PASS
```

### Completion marker

All three conditions hold: every selected goal passed; the remaining plugin-rulebook FAIL and skill-reviewer Major were accepted with a recorded reason through the round-cap question. The marker is emitted:

```
<skill-improvement-complete>
```

## Marker summary

- Step 7: NO MARKER EMITTED
- Step 8: NO MARKER EMITTED
- Compliance round 1: NO MARKER EMITTED
- Compliance round 2: NO MARKER EMITTED
- Compliance round 3 (before the cap question): NO MARKER EMITTED
- After "Accept remaining findings with reason": `<skill-improvement-complete>` emitted (exactly once)
