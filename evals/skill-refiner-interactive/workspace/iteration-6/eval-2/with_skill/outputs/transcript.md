# Transcript (dry-run simulation, eval-2, iteration-6)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: copy of fixture demo-skill at outputs/target/ (original fixture untouched).

## Quick Start
- A. Detect predating context: none (request only names skill and action). Escape hatch NOT offered. Interview style defaults to full.
- B. "What skill do you want to work on?": skipped (request names the skill/path).
- C. Action question: skipped (request says "refine").
- D. Route: Refine -> Core Workflow: Refinement.

## Core Workflow: Refinement
### Step 1: Locate the skill
- Simulated operator answer: skill is already located (outputs/target/). No gitignore/mirror/user-space/cache issue; no mirror pair (no `.claude/skills/demo-skill`).
- Pre-analysis (pre-analysis-checklist.md). R13/R18/R21 thresholds from plugin-rulebook assets/settings.json (R13 weak 100 / soft 300 / warn 490 / crit 500; R21 description min 80, critical-low 20).

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: none (no `version`; description is single-line but short, see R21)
Large sections (>=50 lines): none
Reference files: 2 [clusters: none flagged (a.md details, b.md marker formats; tiny) | oversize >=400: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md "Read references/b.md ..." (imperative directive to read another references file)
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" (free-form intake, no AskUserQuestion)
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): description 22 chars, below the 80-char floor (Warning tier; above critical-low 20) - Minor/Warning
Tool scoping (R6): undeclared: Grep (body says "grep the file for TODO markers") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: R21 description size; missing standard sections (auto-added at step 6); goal verification (optional)
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

- Goal derivation (goal-derivation.md). Priority: (1) ref chains, intake; (2) undeclared tools, description is same tier-2 but capped at 3.
- AskUserQuestion (goal selection): "Which goals should this refinement session measure?" header "Goals", multiSelect true. Options:
  1. "Zero reference chains" - verify: re-run chain scan over references/*.md -> 0 matches
  2. "All intake uses AskUserQuestion" - verify: re-run intake scan -> 0 matches
  3. "Every invoked tool is declared" - verify: re-run tool-scoping scan -> no undeclared tools
  - Simulated answer: all three selected. Recorded as G1, G2, G3.

### Requirements Interview
- BATCH 1 (goals selected -> Question 1 skipped; Questions 2-4 asked one at a time). Simulated answer = first option each:
  - Q2 "What specific problems are you seeing?" (header Key Issues; options: Hard-to-follow instructions / Scattered references / Nested sections) -> "Hard-to-follow instructions"
  - Q3 "What would success look like?" (header Success; options: Clearer workflow / Lower token cost / Production-ready) -> "Clearer workflow"
  - Q4 "Any areas to exclude or preserve as-is?" (header Scope Limits; options: Keep validation gates / Keep tool scoping) -> "Keep validation gates" (no standard-section area excluded; note: "Keep tool scoping" was NOT chosen so G3 is in scope)
  - Approved scope documented: G1-G3 plus auto-added standard sections.
- BATCH 2 (escape hatch not used, so runs after BATCH 1). Only triggered questions:
  - Extraction: not triggered (no section >=50 lines)
  - Intake: triggered, maps to selected goal G2. Question "Section 'Quick Start' collects user input without AskUserQuestion (Ask the user which file to process). Convert it?" header "Intake"; options Yes / No -> simulated first option "Yes"
  - Arguments (R22): not triggered
  - Desc split: not triggered
  - Prod checks (always asked): "Which production checks should I run?" header "Prod checks", multiSelect; options Security scan / Error handling / Tool scoping / None needed -> simulated first option "Security scan". Result: Grep of SKILL.md and references for credentials/keys/tokens/${VAR}: none found.
- Standard sections will be auto-added in step 6.

### Step 2: Load workflow reference
- Read references/refinement-workflow.md (gates, validation phases, rollback).

### Step 3: Consolidation opportunities (target has references/)
- Files: references/a.md (5 lines, summary format + pointer), references/b.md (4 lines, marker formats). Group: same domain (TODO summary). Potential merge 2 -> 1, saves ~1-2 lines and removes the a.md->b.md chain.
- AskUserQuestion: "Should we consolidate these files? Saves ~2 lines, improves clarity." options "Consolidate" / "Leave as-is" -> simulated first option "Consolidate". (Noted: operator's "first option" default, not an organic pre-analysis cluster finding.)

### Step 4: Preservation gates
- Gate 1 Content Audit: SKILL.md (13 lines) Quick Start = core; a.md (5) summary format = core; b.md (4) marker formats = core (needed to recognize markers). Nothing supplementary.
- Gate 2 Capability Assessment: merge a+b into details.md - no execution impairment; all content preserved. Add Grep to allowed-tools - required for execution. Safe.
- Gate 3 (applied in step 6): verified destination references/details.md holds all content of a.md and b.md and SKILL.md link points to it, before any deletion.
- Gate 4 (applied in step 6): AskUserQuestion "Okay to delete the 2 originals (references/a.md, references/b.md) once their content is in references/details.md?" options "Delete" / "Keep" -> simulated first option "Delete". Migrations auto-approved.

### Step 5: Plan-only exit
- Request has no plan-only wording. AskUserQuestion: "Apply the approved scope?" options "Apply changes" / "Plan only" / "Stop" -> simulated answer "Apply changes". Proceed to step 6.

### Step 6: Make changes (CREATE -> LINK -> DELETE)
- Rollback: target is a scratch copy under OUTDIR; original restorable from the fixture (evals/.../fixtures/demo-skill/).
- CREATE references/details.md (content of a.md + b.md; dropped the "Read references/b.md" directive).
- LINK SKILL.md pointer changed from references/a.md to references/details.md (verified file exists).
- DELETE references/a.md and references/b.md via Bash `rm` (Gate 4 approved above).
- Frontmatter: allowed-tools `Read` -> `Read Grep` (G3).
- Quick Start intake: "Ask the user which file to process" -> "Use AskUserQuestion to select which file to process" (G2); "grep the file" -> "use Grep" .
- Auto-added standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide.
- Not changed: description (R21 short-description finding was a deferred candidate, not a selected goal; operator did not ask for it).

### Step 7: Validate result (seven phases)
- P1 inventory: before SKILL.md + references/{a,b}.md (13+5+4 lines); after SKILL.md (33) + references/details.md (8).
- P2 read all: complete, no gaps. P3 frontmatter: name + description present, no non-standard fields (description short - R21 note). P4 body: 33 lines, R13 OK; workflow pattern simple; no spawn anti-patterns. P5 references: details.md exists, one level deep, no ref->ref chains. P6 tools: Read (declared, used), Grep (declared, used), AskUserQuestion (always callable) - no undeclared/unused. P7 testing: trigger phrases in Testing & Validation ("summarize the TODOs in this file").

### Step 8: Measure goals (see goal-measurement.md)
- G1 PASS, G2 PASS, G3 PASS. No failures, so "Accept with reason" question was not needed.

### Step 9: Trigger regression check
- description/when_to_use unchanged -> step skipped.

### Step 10: Compliance and reviewer passes
- Skill(plugin-rulebook) and skill-reviewer agent were NOT actually dispatched in this dry-run (simulation limited to files under OUTDIR; target is an eval scratch copy outside plugins/). Noted as simulated/not executed. Expected: R21 description below 80-char floor would remain flagged (description unchanged, not a selected goal); operator would be asked at the round cap if it stayed.
- Change summary:
```
Lines: 13 -> 33 (SKILL.md); references 9 -> 8 lines
Frontmatter: allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: references/details.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: not executed in dry-run (R21 short description remains a known, unaddressed finding)
```
- Completion marker withheld strictly speaking, since step 10's checks were not run; all selected goals passed. (Would emit `<skill-improvement-complete>` once step 10 is run and clean/accepted.)
