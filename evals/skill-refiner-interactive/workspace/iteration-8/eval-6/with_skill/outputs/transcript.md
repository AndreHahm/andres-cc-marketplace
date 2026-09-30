# Transcript: skill-refiner-interactive dry run (eval-6)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: a copy of the demo-skill fixture at `OUTDIR/target/` (SKILL.md 13 lines, references/a.md 5 lines, references/b.md 4 lines).

## Quick Start A (escape hatch)
Predating context? The request only names the skill and the action, which is not predating context. No escape-hatch question. Interview style stays the full interview (BATCH 1 then BATCH 2).

## Quick Start B
Skipped: the request already names the skill.

## Quick Start C
Skipped: the request already says "Refine".

## Quick Start D
Route: Refine, so Core Workflow: Refinement.

## Step 1: Locate the skill
- Simulated operator answer: skill already located, at `OUTDIR/target/`. No location question asked.
- Gitignore exclusion: the target is not in `.temp/`, `.draft/` or `.backup/`.
- Mirror-pair check (R19): there is no `plugins/<plugin>/skills/demo-skill/` or `.claude/skills/demo-skill/` counterpart, so it is a single logical skill. No Mirror question.
- Not user-space and not in the plugin cache, so no warning or refusal.

### Step 1, pre-analysis (references/pre-analysis-checklist.md)
plugin-rulebook found at `plugins/plugin-devkit/skills/plugin-rulebook/`. Its assets/settings.json gave R13 thresholds weak 100, soft 300, warning 490, critical 500. R18 thresholds are weak 10, warning 20, critical 30. R21 description minimum is 80, maximum 1024.

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: single-line description (needs >- per R8 once over 80 chars; currently 22 chars, below the R21 floor of 80); no non-standard fields
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (both cover TODO summary details and marker formats) | oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md "Read references/b.md for the full list of marker formats"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no (no embedded trigger clause, description 22 chars)
Description size (R21): finding - description 22 chars, below the 80-char floor (warning tier; above the 20-char critical floor)
Tool scoping (R6): undeclared tools: Grep ("grep the file") / unused declared tools: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: frontmatter issues (R5/R8), description size (R21), reference cluster a.md + b.md, missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1, derive and select goals (references/goal-derivation.md)
Priority order gives 2 first-tier findings (ref->ref chain, intake violation) plus the first second-tier finding (undeclared tool). The other findings are deferred, as listed in the report.

AskUserQuestion (multiSelect: true):
- question: "Which goals should this refinement session aim for?"
- header: "Goals"
- options (description shows the verification check):
  1. "Zero reference chains" - verify: re-run the checklist's ref->ref scan over references/*.md, expect 0 matches
  2. "All intake uses AskUserQuestion" - verify: re-run the checklist's intake scan, expect 0 matches
  3. "Declare every invoked tool" - verify: re-run the checklist's tool-scoping scan, expect no undeclared tools
- Simulated operator answer: select all goals offered. Goals 1, 2 and 3 are recorded.

## Requirements Interview
### BATCH 1 (goals selected, so Question 1 is skipped)
Question 2 (multiSelect):
- question: "What specific problems are you seeing?", header "Key Issues"
- options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections"
- Simulated answer (first option): "Hard-to-follow instructions"

Question 3:
- question: "What would success look like?", header "Success"
- options: "Clearer workflow" / "Lower token cost" / "Production-ready"
- Simulated answer (first option): "Clearer workflow"

Question 4 (multiSelect):
- question: "Any areas to exclude or preserve as-is?", header "Scope Limits"
- options: "Keep validation gates" / "Keep tool scoping"
- Simulated answer (first option): "Keep validation gates". This leaves the target's validation gates and its Testing & Validation section unchanged, and it also stops step 6 from auto-adding a Testing & Validation section. "Keep tool scoping" was not chosen, so adding the undeclared Grep grant is allowed.

Approved scope documented: goals 1-3, clearer workflow, no Testing & Validation section added.

### BATCH 2 (full interview chosen, so it runs after BATCH 1)
Triggered questions only:
- Large low-frequency section: not triggered.
- Intake violation: triggered, and it maps to a selected goal, so it is asked.
  - question: "Section 'Quick Start' collects user input without AskUserQuestion (asks the user which file to process in free text). Convert it?", header "Intake"
  - options: "Yes" / "No". Simulated answer (first option): "Yes".
- Arguments (R22): not triggered.
- Desc split: not triggered.
- Prod checks (always asked), multiSelect:
  - question: "Which production checks should I run?", header "Prod checks"
  - options: "Security scan" / "Error handling" / "Tool scoping" / "None needed"
  - Simulated answer (first option): "Security scan". Grep of SKILL.md and references/ for credentials, keys, tokens and `${VAR}` substitutions found nothing.
- Reference clusters are not asked here (step 3 is the single consolidation ask).
- Standard sections are auto-added in step 6, so no question.

## Step 2: Load workflow reference
Read references/refinement-workflow.md (preservation gates, validation phases, rollback).

## Step 3: Consolidation opportunities
The target has a references/ directory. Files: a.md (5 lines), b.md (4 lines). Both cover TODO summary details and marker formats, so this is a potential merge (9 lines into about 8).

AskUserQuestion:
- question: "Should we consolidate these files? Saves 1 line, improves clarity."
- options: "Consolidate" / "Leave as-is"
- Simulated answer (first option): "Consolidate" (merge b.md into a.md).

## Step 4: Preservation gates 1 and 2
- GATE 1 Content Audit: SKILL.md (13 lines: frontmatter, Quick Start; core); references/a.md (5 lines, summary layout; supplementary); references/b.md (4 lines, marker formats; supplementary). No scripts/ or assets/.
- GATE 2 Capability Assessment: merging b.md into a.md loses no content, so execution is not impaired and the merge is safe. The Quick Start rewrite keeps its behavior (asks for a file, greps TODO markers, summarizes). Adding Grep to allowed-tools only grants a permission the body already uses. No deletion of core content.
- Gates 3 and 4 are applied in step 6.

## Step 5: Plan-only exit
AskUserQuestion:
- question: "Apply the approved scope?"
- options: "Apply changes" / "Plan only" / "Stop"
- Simulated answer: "Apply changes".

Gate 4 for the consolidation's source file, asked now before step 6 starts:
- question: "Okay to delete references/b.md once its content is in references/a.md?"
- options: "Delete" / "Keep"
- Simulated answer (first option): "Delete" (approved).

## Step 6: Make changes
Rollback: the copy in OUTDIR/target is the working copy, and the original fixture under evals/.../fixtures/demo-skill is untouched and serves as the pre-edit restore point.

CREATE -> LINK -> DELETE order:
1. CREATE: appended a "Marker Formats" section (the TODO: and FIXME: lines from b.md) to references/a.md.
2. Gate 3 Migration Verification: destination exists; all b.md content is present in a.md; no orphans. Approved.
3. LINK: removed the line "Read references/b.md for the full list of marker formats." from a.md (nothing in SKILL.md pointed at b.md; SKILL.md keeps the single pointer to references/a.md).
4. DELETE (Gate 4 already approved): ran `rm references/b.md`.
5. Quick Start intake converted: free-text "Ask the user which file to process" became an AskUserQuestion instruction with the options "File named in the request" and "Most recently edited file".
6. allowed-tools: `Read` became `Read Grep` (Grep was invoked but undeclared).
7. Standard sections auto-added: `## When to Use`, `## When NOT to Use`, `## Reference Guide`. `## Testing & Validation` was NOT added because BATCH 1 Question 4 excluded it. `## Quick Start` already existed.

## Step 7: Validate result
- Phase 1 File Inventory: before SKILL.md + references/a.md + references/b.md; after SKILL.md + references/a.md.
- Phase 2 Read All: complete, no gaps, no truncation.
- Phase 3 Frontmatter: name and description present, no non-standard fields.
- Phase 4 Body: SKILL.md is 27 lines, OK tier (R13); no spawn anti-patterns; no multi-step workflow pattern needed.
- Phase 5 References: references/a.md exists and is complete, one level deep, no reference->reference chains.
- Phase 6 Tools: Read and Grep declared and used; no undeclared or unused tools; no Bash.
- Phase 7 Testing: activation checked against "summarize the TODOs in this file" (should trigger) and "write a new skill" (should not).

## Step 8: Measure goals (goal-derivation.md)
- Goal 1, zero reference chains: re-ran the ref->ref scan, 0 matches. PASS.
- Goal 2, intake uses AskUserQuestion: re-ran the intake scan, 0 matches. PASS.
- Goal 3, every invoked tool declared: re-ran the tool-scoping scan, no undeclared tools. PASS.
All goals pass, so there is no "Accept with reason / Continue refining" question.

## Step 9: Trigger regression check
Skipped. Neither `description` nor `when_to_use` changed text (no edit so far touched either field).

## Step 10: Compliance and reviewer passes

### First run of both checks (not a round)
- Skill(plugin-rulebook), simulated: 1 FAIL, R8 (the description needs the `>-` block scalar).
- skill-reviewer (full mode, Structured output mode), simulated: counts.critical 0, counts.major 1 (missing example in Quick Start).
- Completion marker: **NO MARKER EMITTED** (1 rulebook FAIL and 1 Major finding remain).

### Round 1: fix pass
- Fixed R8: rewrote `description: Helps with demo tasks.` as a `>-` block scalar with the same words. A format-only change, so step 9 does not re-enter.
- Fixed the Major: added an example summary (fenced `text` block) to Quick Start.
- Re-ran the step-7 phases touched: Phase 3 (frontmatter) and Phase 4 (body, now 35 lines, OK tier, code block 2 lines). Phases 1, 2, 5, 6 and 7 re-verified unchanged.
- Re-measured goals (step 8): goals 1, 2 and 3 all PASS.

### Re-run of both checks (end of round 1)
- Skill(plugin-rulebook), simulated: clean, no FAIL.
- skill-reviewer, simulated: clean, no Critical or Major.
- All three conditions hold: every rulebook FAIL fixed, every Critical/Major fixed, every selected goal passed. The change summary is emitted, then the marker.

Change summary:

```
Lines: 13 → 35
Frontmatter: description converted to >- block scalar (R8); allowed-tools Read → Read Grep
Sections added: When to Use, When NOT to Use, Reference Guide (Testing & Validation not added: excluded at BATCH 1 Question 4)
Files created: none
Files deleted: references/b.md (merged into references/a.md)
plugin-rulebook: 1 FAIL findings fixed
```

Completion marker (emitted here, at the end of round 1 after the clean re-run):

```
<skill-improvement-complete>
```

## Final state
See final-tree.txt. Only files under OUTDIR/target were modified; the original fixture is untouched.
