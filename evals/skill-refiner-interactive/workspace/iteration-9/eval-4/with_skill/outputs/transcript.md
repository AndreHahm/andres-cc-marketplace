# Transcript: skill-refiner-interactive dry run (iteration 9, eval-4)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: a copy of the demo-skill fixture at `OUTDIR/target`. The original fixture was not touched.
Simulation rules: AskUserQuestion and other skills or agents cannot be dispatched. Each question is written out with its options, then answered with the simulated operator answer. Where none was given, the first option is used.

## Quick Start (A-D)

- A. Predating context? The request only names the skill and the action, which is not predating context. No escape-hatch question.
- B. Skip. The request already names the skill (and the operator says it is already located).
- C. Skip. The request says "refine".
- D. Route: Refine, so Core Workflow: Refinement runs.

## Step 1: Locate the skill

- Simulated answer: "skill already located". Target is `OUTDIR/target` (SKILL.md plus `references/a.md` and `references/b.md`).
- Gitignore-exclusion check: the path is not under `.temp/`, `.draft/` or `.backup/`.
- Mirror-pair check (R19): no `plugins/<plugin>/skills/demo-skill/` or `.claude/skills/demo-skill/` counterpart exists, so this is a single copy.
- User-space and cache checks do not apply.

### Pre-analysis (references/pre-analysis-checklist.md)

- R13/R18/R21 thresholds were read from `plugin-rulebook/assets/settings.json`. R13: weak 100, soft 300, warning 490, critical 500. R18: 10/20/30. R21: description floor 80.

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: none (no non-standard field; description is under 80 chars so `>-` not required)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary and marker formats) | oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md for the full list of marker formats."
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" (free-form intake, no AskUserQuestion)
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): description is 22 chars, under the 80-char floor (warning tier); no when_to_use
Tool scoping (R6): undeclared: Grep (Quick Start says to grep the file) / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: reference cluster (covered by step 3), description size (R21), missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation and selection (goal-derivation.md)

Candidate goals by priority: first tier has 2 findings (chain, intake), second tier has the undeclared tool. That makes 3 goals, which is the cap.

QUESTION (AskUserQuestion, multiSelect: true, up to 3 goals):
- question: "Which goals should this refinement session commit to?"
- header: "Goals"
- options:
  - "Zero reference chains": no reference file tells the reader to read another reference file. Verification: re-run the chain scan over references/*.md, expect 0 matches.
  - "AskUserQuestion intake": all user intake uses AskUserQuestion with options. Verification: re-run the intake scan, expect 0 matches.
  - "Declare every tool": every invoked tool is declared in allowed-tools. Verification: re-run the tool-scoping scan, expect no undeclared tools.
- Simulated answer: select all (3 of 3). Recorded as G1, G2, G3. Custom goals: none.

## Requirements Interview

### BATCH 1: Refinement Focus

Goals were selected, so Question 1 is skipped. Questions 2-4 are asked one at a time. No operator answer was given for them, so the first option is chosen.

QUESTION Q2 (multiSelect): "What specific problems are you seeing?" (header "Key Issues"). Options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections". Answer (first option): "Hard-to-follow instructions".

QUESTION Q3: "What would success look like?" (header "Success"). Options: "Clearer workflow" / "Lower token cost" / "Production-ready". Answer (first option): "Clearer workflow".

QUESTION Q4 (multiSelect): "Any areas to exclude or preserve as-is?" (header "Scope Limits"). Options: "Keep validation gates" / "Keep tool scoping". Answer (first option): "Keep validation gates". Consequence: per step 6, this exclusion binds the auto-added standard sections, so the `## Testing & Validation` section is NOT added. "Keep tool scoping" was not chosen, so adding the Grep grant for G3 is allowed.

Approved scope documented: G1, G2, G3. Exclusion: validation gates and Testing & Validation.

### BATCH 2: Implementation Details

No escape-hatch answer exists (none was asked), so BATCH 2 follows BATCH 1. Triggers detected: intake violation (its goal G2 is selected), so ask. Extraction, Arguments and Desc split: no trigger. Reference clusters are not asked here (step 3 is the single consolidation ask). Prod checks is always asked.

QUESTION Intake: "Section 'Quick Start' collects user input without AskUserQuestion (free-form 'Ask the user which file to process'). Convert it?" (header "Intake"). Options: "Yes" / "No". Answer (first option): "Yes".

QUESTION Prod checks (multiSelect): "Which production checks should I run?" (header "Prod checks"). Options: "Security scan" / "Error handling" / "Tool scoping" / "None needed". Answer (first option): "Security scan".

Approved scope documented.

## Step 2: Load workflow reference

Read `references/refinement-workflow.md` (preservation gates, validation phases, consolidation procedure, rollback).

## Step 3: Consolidation opportunities

Target has a `references/` directory, so the step runs.
- `references/a.md`: 5 lines ("Details"; summaries list each TODO with its line number; directs the reader to b.md).
- `references/b.md`: 4 lines ("Marker Formats"; TODO: and FIXME: formats).
- Grouping: both cover TODO marker summaries and formats. Flagged as a merge candidate: 2 files to 1.

QUESTION (AskUserQuestion, the single consolidation ask): "Should we consolidate these files? Saves N lines, improves clarity." (a.md + b.md, 9 lines into about 10 lines including headings, so the benefit is clarity and removing the chain, not line count). Options: "Consolidate" / "Leave as-is". Answer: "Consolidate".

## Step 4: Preservation gates (Gates 1 and 2 here)

1. **Gate 1 (Content Audit).** SKILL.md (13 lines): frontmatter, Quick Start. Core, 80%+. `references/a.md` (5 lines): TODO summary format plus a chain directive. Supplementary. `references/b.md` (4 lines): marker formats. Supplementary. No scripts/ or assets/.
2. **Gate 2 (Capability Assessment).**
   - Consolidate a.md + b.md into one file: does it impair execution? No. All content is retained in the merged file and the SKILL.md pointer is updated. Safe to consolidate.
   - Delete a.md and b.md after the merge: does it impair execution? No, once their content lives in the merged file. Deletion still needs Gate 4.
   - Replace the free-form intake line: an in-place edit that adds an AskUserQuestion block and loses no content. Safe.
   - Add Grep to allowed-tools: widens the grant, in line with G3. Safe.

## Step 5: Plan-only exit

QUESTION (AskUserQuestion): "Apply the approved scope?" Options: "Apply changes" / "Plan only" / "Stop". Answer: "Apply changes". Step 6 will run and goals will be measured.

3. **Gate 4 early ask (the one exception to gate order; it collects approval only):**
   QUESTION (AskUserQuestion): "The consolidation merges references/a.md and references/b.md into references/todo-marker-details.md. Okay to delete the two original files (a.md, b.md) once their content is in the new file?" Options: "Delete" / "Keep". Answer: "Delete" (approved). This approval is cited at each deletion in step 6.

## Step 6: Make changes (CREATE -> LINK -> DELETE)

Rollback settled before the first edit: the target is an untracked copy, so the restore source is the original fixture `evals/skill-refiner-interactive/fixtures/demo-skill/`. Restore list is taken from the change summary's "Files created" and "Files deleted".

Numbered action log, in the exact order performed (Gates 1 and 2 and the early Gate 4 ask are items 1-3 above; this log continues the numbering):

4. **CREATE** `references/todo-marker-details.md`: destination written first, with "Summaries" (from a.md, minus the "Read references/b.md" directive) and "Marker Formats" (from b.md) sections.
5. **Gate 3 (Migration Verification)** for the a.md + b.md to todo-marker-details.md move: destination exists; content complete (summary sentence from a.md present; both marker bullets from b.md present); no gaps; no orphans. Approved. The link is updated next.
6. **LINK** in SKILL.md: the Quick Start pointer `references/a.md` is now `references/todo-marker-details.md`.
7. **LINK** in SKILL.md: a `## Reference Guide` table is added with a row for `references/todo-marker-details.md`. Link verification: grep of SKILL.md for `references/a.md` and `references/b.md` finds 0 matches (the only remaining mentions are inside the two source files, which are about to be deleted). Links are verified.
8. **Gate 4 check** before deleting `references/a.md`: content migrated and Gate 3 passed; explicit operator approval on record (item 3, "Delete"). Clear.
9. **DELETE** `references/a.md`: run as a `Bash` `rm` (normal permission prompt, the second gate; simulated as granted).
10. **Gate 4 check** before deleting `references/b.md`: content migrated and Gate 3 passed; approval on record (item 3). Clear.
11. **DELETE** `references/b.md`: `Bash` `rm` (permission prompt simulated as granted). `references/` now holds only `todo-marker-details.md`.

Edits that are not CREATE, LINK or DELETE (in-place, no deletion, no move):
- EDIT frontmatter: `allowed-tools: Read` becomes `Read Grep` (G3).
- EDIT Quick Start: the free-form intake line is replaced with an AskUserQuestion block (question "Which file should I scan for TODO markers?", header "File", two options), followed by "Then use Grep to find TODO markers in that file and summarize them." (G2).
- EDIT standard sections, auto-added: `## When to Use`, `## When NOT to Use` (names `code-review` as the alternative for reviewing code for bugs). `## Reference Guide` was added in item 7. `## Testing & Validation` was NOT added because BATCH 1 Question 4 excluded it.
- Security scan (Prod checks answer): `grep` for api key, secret, token, password and `${VAR}` patterns across the target finds 0 matches. No findings.

Consolidation report: Consolidated a.md + b.md (9 lines) into todo-marker-details.md (10 lines, including section headings). Links updated: SKILL.md (1 pointer, plus a Reference Guide row). Old files deleted after the link check.

## Step 7: Validate result (seven phases)

- Phase 1, File Inventory. Before: SKILL.md (13 lines), references/a.md (5), references/b.md (4). After: SKILL.md (39), references/todo-marker-details.md (10). Final tree is in `final-tree.txt`.
- Phase 2, Read All. SKILL.md and the merged reference read in full. No gaps.
- Phase 3, Frontmatter. `name` and `description` present. `allowed-tools: Read Grep`. No forbidden fields. Note: the description is 22 chars (R21 warning tier). It was not in a selected goal and was left unchanged, so step 9 is not triggered.
- Phase 4, Body. 39 lines (R13 OK). Code block 6 lines (R18 OK). Quick Start is actionable. No spawn anti-patterns. No multi-step workflow pattern applies.
- Phase 5, References. The linked file exists. No orphans. One level deep. No ref-to-ref chains.
- Phase 6, Tools. Undeclared: none. Unused declared: none. Bash-for-dedicated-tool misuse: none.
- Phase 7, Testing. Activation phrases "refine/validate this skill" are not applicable to demo-skill. Its own triggers ("summarize TODOs") are weak because the description is short. Noted as a follow-up; not fixed here.

## Step 8: Measure goals

Per `goal-derivation.md`, recorded in `goal-measurement.md`.
- G1, zero ref chains: PASS.
- G2, AskUserQuestion intake: PASS.
- G3, declare every tool: PASS.
No goal failed, so no "Accept with reason" or "Continue refining" question is asked.

## Step 9: Trigger regression check

Skipped, with reason: neither `description` nor `when_to_use` changed text during this session.

## Step 10: Compliance and reviewer passes

- `Skill(plugin-rulebook)` and the `skill-reviewer` agent (Structured output mode) cannot be dispatched in this dry run. Both are recorded as NOT RUN. No fix rounds were run.
- Per step 10, if either check cannot be run the completion marker is NOT emitted.

Change summary:

```
Lines: 13 -> 39
Frontmatter: allowed-tools: Read -> Read Grep
Sections added: When to Use, When NOT to Use, Reference Guide
Files created: references/todo-marker-details.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: NOT RUN
```

Not emitted: `<skill-improvement-complete>` (plugin-rulebook and skill-reviewer were NOT RUN).

## Ordered action log (Gates 1-4, CREATE, LINK, DELETE only)

1. Gate 1 (Content Audit)
2. Gate 2 (Capability Assessment)
3. Gate 4 early ask (approved deletion of a.md and b.md)
4. CREATE references/todo-marker-details.md
5. Gate 3 (Migration Verification)
6. LINK SKILL.md pointer (a.md to todo-marker-details.md)
7. LINK SKILL.md Reference Guide row
8. Gate 4 check (a.md)
9. DELETE references/a.md
10. Gate 4 check (b.md)
11. DELETE references/b.md
