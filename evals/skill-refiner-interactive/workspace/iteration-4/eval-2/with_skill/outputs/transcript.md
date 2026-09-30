# Dry-run transcript: skill-refiner-interactive (eval-2)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: copy of fixture demo-skill in OUTDIR/target.

## Quick Start
- A (escape hatch): no predating context beyond the request itself -> not offered.
- B: skill already named/located by the request -> skipped.
- C: request says "refine" -> Action question skipped.
- D: routed to Core Workflow: Refinement.

## Core Workflow: Refinement
### Step 1 Locate the skill
Simulated answer: "skill is already located". Target is OUTDIR/target (not a gitignored draft, not user-space, not cache). No mirror pair exists (R19 check: no `.claude/skills/demo-skill` counterpart). No plugin-rulebook settings consulted for target; fallback to skill-development size-limits defaults (500 / 30).

#### Pre-analysis report (pre-analysis-checklist.md)
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: single-line `description` (needs >-)
Large sections (>=50 lines): none
Reference files: 2 [clusters: none (a.md = summary format, b.md = marker syntax: different topics)] [oversize >=400: none]
Workflow files: 0
Reference chain violations (ref->ref): references/a.md "Read references/b.md ..." 
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none (Read used by the workflow)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: frontmatter single-line description; missing standard sections (auto-added); missing goal verification
R13/R18 threshold source: skill-development fallback
```

#### Goal derivation and selection (goal-derivation.md)
AskUserQuestion (multiSelect, up to 3):
 - "Zero reference->reference chains" (verify: chain scan over references/*.md -> 0 matches)
 - "All intake uses AskUserQuestion with options" (verify: intake scan -> 0 matches)
 - "Every invoked tool is declared in allowed-tools" (verify: tool-scoping scan -> no undeclared tools)
 - Other (custom goal)
Simulated answer: select all three goals.

### Requirements Interview
Goals selected -> BATCH 1 Question 1 skipped. Questions 2-4 asked one at a time; first option chosen each time:
 - Q2 "What specific problems are you seeing?" options: Hard-to-follow instructions / Scattered references / Nested sections -> "Hard-to-follow instructions"
 - Q3 "What would success look like?" options: Clearer workflow / Lower token cost / Production-ready -> "Clearer workflow"
 - Q4 "Any areas to exclude or preserve as-is?" options: Keep validation gates / Keep tool scoping / Nothing... -> "Keep validation gates" (no gates exist in this skill; no effect)
Approved scope documented: the three goals.

BATCH 2 (escape hatch not used, so reached after BATCH 1): only triggered questions.
 - Intake question (trigger detected; maps to a selected goal): "Section 'Quick Start' collects user input without AskUserQuestion. Convert it?" options Yes / No -> first option "Yes".
 - Extraction: not triggered. Arguments: not triggered. Desc split: not triggered.
 - Prod checks (always asked): options Security scan / Error handling / Tool scoping / None needed -> first option "Security scan": grepped SKILL.md and references for credentials/keys/tokens and ${VAR} substitutions: none found.

### Step 2 Load workflow reference
refinement-workflow.md loaded for preservation gates and validation phases.

### Step 3 Consolidation
references/ files: a.md (5 lines), b.md (4 lines). Different topics, no merge candidate -> no ask (the consolidation ask applies only when a cluster was flagged).

### Step 4 Preservation gates
 - Gate 1 content audit: all content core (tiny skill). 
 - Gate 2 capability: edits only add content / remove an imperative read directive; no capability impaired.
 - Gate 3: destination for the a.md->b.md pointer (SKILL.md Reference Guide + Quick Start link) created before the directive was removed.
 - Gate 4: no deletions of files; the only removal is one sentence in a.md, whose content was migrated (b.md link now lives in SKILL.md). No Gate 4 ask needed.

### Step 5 Plan-only exit
AskUserQuestion: "Apply changes" / "Plan only" / "Stop". Simulated answer: "Apply changes". Proceed to step 6.

### Step 6 Make changes (CREATE -> LINK -> DELETE)
 - CREATE/UPDATE: SKILL.md gained AskUserQuestion block, `Grep AskUserQuestion` in allowed-tools, `>-` description, four standard sections (When to Use, When NOT to Use, Testing & Validation, Reference Guide).
 - LINK: SKILL.md now points to references/b.md directly.
 - DELETE: removed the "Read references/b.md ..." sentence from references/a.md (only after the link existed).

### Step 7 Validate (seven phases)
 1 inventory unchanged (SKILL.md, a.md, b.md). 2 read all: complete. 3 frontmatter: name, description present; description folded `>-`. 4 body: 47 lines, OK; linear workflow. 5 references: both exist, one level deep, no ref->ref. 6 tools: Read, Grep, AskUserQuestion declared; all used. 7 testing: activation phrases listed in Testing & Validation.

### Step 8 Measure goals
See goal-measurement.md: all three PASS. No FAIL, so no "Accept with reason" question arose.

### Step 9 Trigger regression
`description` was reformatted to `>-` but its text is unchanged ("Helps with demo tasks."); no trigger phrase change. Treated as unchanged content -> step skipped (no Trigger eval question asked).

### Step 10 Compliance and reviewer passes
Not executed in this dry-run (Skill(plugin-rulebook) and skill-reviewer agent not dispatchable here). Noted as a limitation: the description "Helps with demo tasks." is likely to draw a skill-reviewer activation finding; not fixed, since the pre-analysis did not flag it.
Change summary:
```
Lines: 13 -> 47
Frontmatter: description folded to >-; allowed-tools Read -> Read Grep AskUserQuestion
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: none
plugin-rulebook: not run (dry-run)
```
Completion marker withheld only because step 10 was not actually run; all selected goals passed.
