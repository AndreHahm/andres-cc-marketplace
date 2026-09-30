# Transcript: skill-refiner-interactive dry run (eval-7, declined deletion)

Target: OUTDIR/target (copy of fixture demo-skill). Files read: SKILL.md and references/pre-analysis-checklist.md, goal-derivation.md, interview-question-templates.md, refinement-workflow.md from the skill directory.

## Quick Start A (escape hatch)
Request "Refine the skill in OUTDIR/target so it follows best practices" only names the skill and the action: no predating context. Escape-hatch question NOT asked.

## Quick Start B / C / D
- B skipped (request names the skill). C skipped (request says refine). D: route to Core Workflow: Refinement.

## Step 1: Locate the skill
Simulated: skill already located at OUTDIR/target. No gitignore draft, no mirror pair (no `.claude/skills/demo-skill` copy in scope), not user-space, not cache.

### Step 1: pre-analysis (pre-analysis-checklist.md)
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: single-line description "Helps with demo tasks." (22 chars; R8 needs >- only above 80 chars, so not an R8 violation); no forbidden fields
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (same topic: TODO summaries and marker formats) | oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md for the full list of marker formats."
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" (intake without AskUserQuestion)
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): 22 chars, below the 80-char floor (Warning tier; critical floor is 20)
Tool scoping (R6): undeclared: Grep (body says "grep the file", an actual instruction) / unused declared: none
Dead links: none / Cross-skill references: none (note: b.md is linked only from a.md, not from SKILL.md)
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: frontmatter/R21 description size, reference cluster, missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1: goal derivation and selection (goal-derivation.md)
AskUserQuestion (multiSelect: true, up to 3 goals):
- question: "Which goals should this refinement session achieve?"
- header: "Goals"
- options:
  - "Zero ref->ref chains": verification: re-run the chain scan over references/*.md -> 0 matches
  - "All intake uses AskUserQuestion": verification: re-run the intake scan -> 0 matches
  - "Every invoked tool declared": verification: re-run the tool-scoping scan -> no undeclared tools
Simulated operator answer: select all three. (Goal priority: first tier chain + intake; second tier undeclared tool; frontmatter and cluster deferred.)

## Requirements Interview
Goals selected, so BATCH 1 Question 1 is skipped; Questions 2-4 asked one at a time. No operator answers were given for these, so the first option is used.

### BATCH 1, Question 2
question "What specific problems are you seeing?", header "Key Issues", multiSelect. Options: Hard-to-follow instructions / Scattered references / Nested sections. Answer: "Hard-to-follow instructions" (first option).

### BATCH 1, Question 3
question "What would success look like?", header "Success". Options: Clearer workflow / Lower token cost / Production-ready. Answer: "Clearer workflow".

### BATCH 1, Question 4
question "Any areas to exclude or preserve as-is?", header "Scope Limits", multiSelect. Options: Keep validation gates / Keep tool scoping. Answer: "Keep validation gates" (first option). Effect: leave validation gates and a Testing & Validation section unchanged, so step 6 will NOT auto-add `## Testing & Validation`. Tool scoping not excluded (Grep declaration is allowed). Approved scope documented.

### BATCH 2
Questions asked: only those whose trigger was detected (large section: none; R22: none; desc split: none; consolidation is step 3's job).
- Intake (detected, goal selected): question "Section 'Quick Start' collects user input without AskUserQuestion (Ask the user which file to process). Convert it?", header "Intake", options Yes / No. Answer: "Yes" (first option).
- Prod checks (always asked): question "Which production checks should I run?", header "Prod checks", multiSelect, options Security scan / Error handling / Tool scoping / None needed. Answer: "Security scan" (first option). Security scan result: no credentials, keys, tokens or ${VAR} substitutions in SKILL.md or references.

## Step 2: Load workflow reference
Read references/refinement-workflow.md (gates, validation phases, rollback, consolidation).

## Step 3: Consolidation opportunities
Files: references/a.md (5 lines), references/b.md (4 lines). Same topic, flagged as a merge candidate.
AskUserQuestion: question "Should we consolidate these files? Saves N lines, improves clarity." (N = about 1 line: a.md and b.md merge saves only the duplicate title block), options "Consolidate" / "Leave as-is". Simulated answer: "Consolidate".

## Step 4: Preservation gates 1 and 2
- GATE 1 Content Audit: SKILL.md 13 lines (core: Quick Start); a.md 5 lines (supplementary: summary format); b.md 4 lines (supplementary: marker formats).
- GATE 2 Capability Assessment: intake conversion, Grep declaration, chain fix, consolidation, standard sections: none impairs execution (proposed consolidation only merges content). Passed.
Gates 3 and 4 apply during/after step 5-6.

## Step 5: Plan-only exit
Request does not use plan-only wording, so ask:
AskUserQuestion: question "Apply the approved scope?" options "Apply changes" / "Plan only" / "Stop". Simulated answer: "Apply changes".

### Gate 4 (consolidation source files, asked before step 6)
AskUserQuestion: question "Okay to delete a.md and b.md once their content is in the consolidated file?", options "Delete" / "Keep". Simulated answer: Keep (operator declines any deletion).
Result per SKILL.md step 4: the consolidation is NOT performed (merging without deleting only duplicates content). Reported as declined. a.md and b.md stay; no consolidated file created.

## Step 6: Make changes
Rollback (refinement-workflow.md): the target is a scratch copy of a git-tracked fixture; pre-edit state = the fixture original (unmodified), restore by re-copying. Done before the first edit.
Edits applied only under OUTDIR/target, no deletions, no files created or removed:
1. SKILL.md Quick Start: "Ask the user which file to process" replaced by an AskUserQuestion block (yaml fence, 2 options) and "Use Grep to find TODO markers". (Intake conversion, in-place edit.)
2. SKILL.md frontmatter: `allowed-tools: Read` -> `Read Grep` (declares the invoked Grep tool).
3. Ref chain: a.md's imperative "Read references/b.md ..." rewritten in place as a non-directive mention; b.md now linked directly from SKILL.md (Quick Start pointer and Reference Guide). Content migrated to SKILL.md (Gate 3: destination SKILL.md pointer exists before a.md line is reworded); nothing removed without a home, so no Gate 4 ask needed (an in-place rewrite is an edit).
4. Standard sections auto-added: `## When to Use`, `## When NOT to Use`, `## Reference Guide` (table with a.md and b.md). `## Testing & Validation` NOT added (excluded by BATCH 1 Q4). Quick Start already present.
Not changed (not in approved scope): description text and its single-line form, name.

## Step 7: Validate (seven phases)
1. File inventory before: SKILL.md(13), references/a.md(5), references/b.md(4). After: SKILL.md(38), a.md(5), b.md(4). No files added/removed.
2. Read all: complete, no gaps.
3. Frontmatter: name and description present; description 22 chars (R21 floor 80, flagged, unapproved so left); allowed-tools `Read Grep`.
4. Body: 38 lines, R13 OK; Quick Start before other sections; no spawn anti-patterns; multi-step workflow pattern: not applicable (simple skill).
5. References: a.md and b.md exist and are linked from SKILL.md; one level; no ref->ref chain.
6. Tools: Grep and Read declared and used; AskUserQuestion always callable; none unused.
7. Testing: activation wording is weak (description minimal) - reported, deferred.

## Step 8: Measure goals
See goal-measurement.md: all 3 PASS. No failure question needed.

## Step 9: Trigger regression
description and when_to_use text unchanged: step skipped.

## Step 10: Compliance and reviewer passes
Skill(plugin-rulebook) and the skill-reviewer agent cannot be dispatched in this dry run, so neither was run. Change summary:
```
Lines: 13 -> 38
Frontmatter: allowed-tools Read -> Read Grep; description unchanged (R21 floor violation left, not approved)
Sections added: When to Use, When NOT to Use, Reference Guide (Testing & Validation excluded by operator)
Files created: none
Files deleted: none
plugin-rulebook: NOT RUN
Consolidation of references/a.md + b.md: declined at Gate 4 (source deletion declined), not performed
```
Because neither check could run, `<skill-improvement-complete>` is NOT emitted; stated here instead.
