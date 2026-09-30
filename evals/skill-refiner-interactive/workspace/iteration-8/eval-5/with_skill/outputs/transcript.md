# Transcript: skill-refiner-interactive dry run (eval-5)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Simulation notes: AskUserQuestion and sub-skill/agent dispatch are not callable here; each ask is written out and answered with the simulated answer (or the first option when none was given). The Grep tool was also unavailable, so scans ran with `grep` through Bash in the simulation only (the skill itself would use Grep).

## Quick Start

### A. Predating context
No predating context (the request only names the skill and the action). Escape-hatch question not asked; continue to B.

### B. Which skill
Request already names the skill (OUTDIR/target). Skipped. Simulated operator answer "skill already located" noted.

### C. Action
Request says "Refine". Skipped.

### D. Route
"Refine" -> Core Workflow: Refinement.

## Core Workflow: Refinement

### Step 1 - Locate the skill
- Target: `OUTDIR/target` (copy of fixtures/demo-skill). Not gitignored, not in cache, not user-space.
- Mirror-pair check (R19): no `.claude/skills/demo-skill/` counterpart; one logical skill.

### Step 1 - Pre-analysis (pre-analysis-checklist.md)
- plugin-rulebook settings read: R13 tiers 100/300/490/500, R18 tiers 10/20/30, R21 description 80-1024.

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: none (no forbidden field; description is short, single-line is allowed at <=80 chars)
Large sections (>=50 lines): none
Reference files: 2 [clusters: none (a.md = summary format, b.md = marker formats; 9 lines total, no merge candidate)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md:5 "Read references/b.md ..."
Spawn anti-patterns: none
Intake pattern violations: Quick Start (line 11) - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): finding - description is 22 chars, under the 80-char floor
Tool scoping (R6): undeclared: Grep (body says "grep the file") [Major] / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: description size (R21); missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1 - Goal derivation and selection (goal-derivation.md)
Priority order gives first tier: ref chain, intake; second tier: undeclared tool (Grep). Three goals proposed; the R21 description-size and goal-verification findings are deferred (listed above). Missing standard sections are auto-added in step 6, not goals.

ASK (AskUserQuestion, multiSelect: true, max 3):
- question: "Which goals should this refinement session meet?"
- options:
  - "Zero reference chains": verify: chain scan over references/*.md -> 0 matches
  - "AskUserQuestion intake": verify: intake scan -> 0 matches
  - "Declare every used tool": verify: tool-scoping scan -> no undeclared tools
- Simulated answer: select all goals offered (all three). Goals recorded: G1, G2, G3.

### Requirements Interview
Goals were selected, so BATCH 1 Question 1 is skipped. Questions asked one at a time. No answer was given in the simulation, so the first option is used.

BATCH 1
- Q2 "What specific problems are you seeing?" (header "Key Issues", multiSelect) options: Hard-to-follow instructions / Scattered references / Nested sections. Answer (first option): Hard-to-follow instructions.
- Q3 "What would success look like?" (header "Success") options: Clearer workflow / Lower token cost / Production-ready. Answer (first option): Clearer workflow.
- Q4 "Any areas to exclude or preserve as-is?" (header "Scope Limits", multiSelect) options: Keep validation gates / Keep tool scoping. Answer (first option): Keep validation gates. Consequence: step 6 must NOT auto-add `## Testing & Validation` (exclusion binds auto-added sections). "Keep tool scoping" was not chosen, so adding `Grep` to `allowed-tools` (goal G3) is allowed.
- Approved scope documented: goals G1-G3, clearer workflow, leave Testing & Validation out.

BATCH 2 (only triggered questions)
- Extraction: not triggered (no large section). Arguments: not triggered. Desc split: not triggered.
- Intake: triggered. ASK: "Section 'Quick Start' collects user input without AskUserQuestion (Ask the user which file to process). Convert it?" header "Intake", options: Yes / No. Answer (first option): Yes.
- Prod checks: asked every session. ASK: "Which production checks should I run?" header "Prod checks", multiSelect, options: Security scan / Error handling / Tool scoping / None needed. Answer (first option): Security scan. Result: no credentials, keys, tokens or ${VAR} substitutions in SKILL.md or references/ (no scripts/ directory).
- Approved scope documented.

### Step 2 - Load workflow reference
Read `references/refinement-workflow.md` (gates, validation phases, rollback).

### Step 3 - Consolidation
Target has references/ (a.md 5 lines, b.md 4 lines). Different topics, nothing to save, so no merge candidate is flagged and the consolidation ask is not asked (recorded, not silently skipped).

### Step 4 - Preservation gates
- Gate 1 (content audit): SKILL.md 13 lines: frontmatter (core), Quick Start (core). a.md 5 lines: summary format (core for output); its line 5 is a pointer (supplementary navigation). b.md 4 lines: marker formats (core).
- Gate 2 (capability assessment): rewriting the intake line, adding Grep, adding sections and moving the b.md pointer into SKILL.md do not impair execution. Removing a.md line 5 is safe only because the pointer is migrated to SKILL.md first (Gate 3: destination exists, link correct).
- Gates 3 and 4 apply inside step 6. No deletions of files or of non-migrated content are planned, so no Gate 4 ask is needed (the a.md line is a migration, auto-approved).

### Step 5 - Plan-only exit
Request does not use plan-only wording, so ask.
ASK: "Apply the approved scope to the skill now?" options: "Apply changes" / "Plan only" / "Stop". Simulated answer: Apply changes. Continue to step 6.

### Step 6 - Make changes (round 1)
- Rollback: `OUTDIR/target` is a copy of the fixture, which is version controlled, so the pre-edit state is restorable.
- CREATE/UPDATE: SKILL.md Quick Start converted to an AskUserQuestion block (G2); `allowed-tools: Read Grep` (G3); the b.md pointer moved into SKILL.md Quick Start and a Reference Guide table (destination first, LINK).
- Standard sections auto-added: When to Use, When NOT to Use, Reference Guide. Testing & Validation NOT added (BATCH 1 Q4 exclusion).
- Simulation control: this first round missed the reference-chain fix. `references/a.md` line 5 left unchanged.

### Step 7 - Validate (seven phases, pass 1)
1 Inventory: SKILL.md 13 -> 36 lines, a.md/b.md unchanged. 2 Read all: complete. 3 Frontmatter: name, description, allowed-tools valid; description short (R21 deferred, not in scope). 4 Body: 36 lines, OK under R13. 5 References: both linked files exist and are one level deep (chain check under the simulation control was not picked up here). 6 Tools: Grep declared and used, Read declared and used; no Bash. 7 Testing: activation phrases ("find TODOs in a file") still match.

### Step 8 - Measure goals (MEASUREMENT PASS 1)
- G1 FAIL (a.md:5 still reads "Read references/b.md"), G2 PASS, G3 PASS. Details in goal-measurement.md.
- ASK: "Goal 'Zero reference->reference chains' did not pass. Verification: chain scan -> 0 matches. Actual: references/a.md line 5 still says 'Read references/b.md'. Accept with a recorded reason, or continue refining?" options: "Accept with reason" / "Continue refining". Simulated answer: Continue refining.

### RETURN TO STEP 6 (focus: G1)
- The b.md pointer already lives in SKILL.md (Gate 3 verified: destination exists and link correct). Removed line 5 (and its blank separator) from `references/a.md`. This is a migration, so no Gate 4 ask.

### Step 7 - Validate (pass 2, phases touched)
Phase 1 inventory: a.md 5 -> 3 lines. Phase 2: a.md complete. Phase 5: both files exist, one level deep, no reference->reference chains.

### Step 8 - Measure goals (MEASUREMENT PASS 2)
G1 PASS, G2 PASS, G3 PASS. All selected goals pass. Details in goal-measurement.md.

### Step 9 - Trigger regression
Skipped: neither `description` nor `when_to_use` text changed.

### Step 10 - Compliance and reviewer passes
`Skill(plugin-rulebook)` and the `skill-reviewer` agent cannot be dispatched in this dry run, so both are NOT RUN. Per the skill, `<skill-improvement-complete>` is therefore NOT emitted. Expected findings if run, for the operator to know: R21 description below the 80-char floor (deferred candidate) and R29 (Testing & Validation absent, by the operator's Q4 exclusion) may be reported.

Change summary:
```
Lines: 13 -> 36
Frontmatter: allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Reference Guide
Files created: none
Files deleted: none
plugin-rulebook: NOT RUN
```
Goals: G1, G2, G3 all PASS after second measurement.
