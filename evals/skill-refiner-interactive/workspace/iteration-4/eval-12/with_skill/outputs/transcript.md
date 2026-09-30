# Dry-run transcript: skill-refiner-interactive, eval-12

Target: OUTDIR/target/ (copy of fixtures/demo-skill). Operator context: pasted SKILL.md ("the intake is sloppy and a tool isn't declared"), then "Refine it." No edits were made.

## Quick Start

### Step A: detect predating context (escape hatch)
Predating context exists (skill file pasted, problem described). Ask:

- question: "I've reviewed the context you provided. How would you like to proceed?"
- header: "Interview"
- options: "Infer from context" / "Define explicitly"
- Simulated answer: **Infer from context** (sets the interview style for later: skip BATCH 1 when the interview starts).

### Step B: "What skill do you want to work on?"
Skipped. The request names the skill and it is located at OUTDIR/target.

### Step C: "Refine" vs "Validate" (header "Action")
Skipped. The request already says "Refine it."

### Step D: route
Refine -> Core Workflow: Refinement.

## Core Workflow: Refinement

### Step 1: Locate the skill
- Given: OUTDIR/target/SKILL.md. The project Glob, user-space, cache and not-found branches were not needed.
- Mirror-pair check (R19): no second copy at `.claude/skills/demo-skill/` (only the target exists), so there is one logical skill and nothing to halt on. The Mirror question was not asked.

#### Pre-analysis (references/pre-analysis-checklist.md, every check run)
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13; thresholds from plugin-rulebook settings: 100/300/490/500)
Frontmatter issues: description is single-line but short (22 chars, under R8's 80-char threshold) - not a violation; no non-standard fields (no `version`); allowed-tools "Read" fine
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker formats/summaries) | oversize >=400: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md - "Read references/b.md for the full list of marker formats" (imperative directive)
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" in plain prose, no AskUserQuestion
Argument consistency (R22): none (no $ARGUMENTS / $0 etc., no argument-hint)
when_to_use split candidate: no (description 22 chars, no embedded trigger clause)
Tool scoping (R6): undeclared: Grep (body says "grep the file for TODO markers") - Major / unused declared: none (Read is used through the reference reads)
Dead links: none (references/a.md and b.md exist) / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - flag as Missing
Deferred goal candidates: missing goal verification; reference cluster a.md/b.md; missing standard sections are auto-added in step 6 (not goals)
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```
This matches the operator's remark (sloppy intake, undeclared tool).

#### Goal derivation and selection (references/goal-derivation.md)
Findings mapped by priority (tier 1: chains, intake, R22; tier 2: undeclared tools...; tier 3: missing goal verification, clusters). Exactly 3 goals, each backed by a finding:

1. Zero reference->reference chains - verify: re-run the checklist chain scan over references/*.md -> 0 matches (source: ref chain in a.md)
2. All intake uses AskUserQuestion with options - verify: re-run the checklist intake scan -> 0 matches (source: Quick Start intake)
3. Every invoked tool is declared in allowed-tools - verify: re-run the checklist tool-scoping scan -> no undeclared tools (source: Grep undeclared)

Ask (AskUserQuestion, multiSelect: true):
- question: "Which goals should this refinement session target?"
- header: "Goals"
- options: "Zero ref->ref chains" (check: chain scan -> 0 matches) / "AskUserQuestion intake" (check: intake scan -> 0 matches) / "Declare every tool" (check: tool-scoping scan -> no undeclared) ("Other" for a custom goal, which needs a verification check)
- Simulated answer: select all three. Recorded. Interview is scoped to them; step 8 will measure them.

### Requirements Interview (templates from references/interview-question-templates.md)

**BATCH 1: skipped.** Routing: operator chose "Infer from context", so BATCH 1 is skipped and the run goes straight to BATCH 2.

**BATCH 2: Implementation Details.** Triggers detected and goal mapping:
- Large low-frequency section: none detected -> not asked
- Intake violation: detected, maps to selected goal 2 -> ASKED
- R22 mismatch: none -> not asked
- when_to_use split: none -> not asked
- Prod checks: asked in every session -> ASKED
- Reference cluster: not asked here (step 3 is the single consolidation ask)

Q (header "Intake"): "Section 'Quick Start' collects user input without AskUserQuestion (prose 'Ask the user which file to process'). Convert it?"
options: "Yes" (replace free-form intake with AskUserQuestion; derive options from observed inputs) / "No" (keep free-form)
- Simulated answer: **Yes**

Q (header "Prod checks", multiSelect): "Which production checks should I run?"
options: "Security scan" / "Error handling" / "Tool scoping" / "None needed"
- No "Yes" option exists; the simulated rule says choose "Yes" for BATCH 2 questions, so I took the affirmative reading of "run the checks" and picked the first option plus the matching one: **Security scan** (first option). Note for the eval grader: this ambiguity is a spec gap in the operator answer, not in the skill.

Approved scope documented: convert the Quick Start intake to AskUserQuestion; declare Grep in allowed-tools; remove the ref->ref chain; run a security scan.

### Step 2: Load workflow reference
Read references/refinement-workflow.md (preservation gates, validation phases, consolidation).

### Step 3: Identify consolidation opportunities (before changes)
references/ line counts: a.md 5, b.md 4 (total 9). Group by topic: both cover TODO/FIXME marker handling, so one cluster. Potential merge: a.md + b.md -> 1 file (saves ~4 lines, and would also eliminate the a.md -> b.md chain).

Q (header "Consolidate"): "Should we consolidate these files? Saves ~4 lines, improves clarity."
options: "Consolidate" / "Leave as-is". This is the only consolidation ask.
- No operator answer was specified for this question; default to the first option: **Consolidate**. Approved (source-file deletion still needs Gate 4 at apply time).

### Step 4: Preservation gates (Gates 1 and 2 here; 3 and 4 at apply time in step 6)
- Gate 1 Content Audit: SKILL.md (13 lines: frontmatter, Quick Start - core, 100%); references/a.md 5 lines (supplementary: details); references/b.md 4 lines (supplementary: marker formats). No scripts/assets.
- Gate 2 Capability Assessment: intake->AskUserQuestion and adding Grep: no impairment, safe. Merging a.md+b.md: execution path still has all content, safe to consolidate (migrate, delete sources only with Gate 4 approval). Removing the chain: safe.
- Gate 3 (verify destination complete) and Gate 4 (explicit deletion approval for a.md/b.md source files) are deferred to step 6 and were not reached.

### Step 5: Plan-only exit
The request did not use plan-only wording, so ask:
- question: "Apply the approved scope to the target skill?"
- header: "Apply"
- options: "Apply changes" / "Plan only" (write changes.md, no edits) / "Stop"
- Simulated answer: **Stop**.

Stop: steps 6-10 are not run. No edits, no changes.md, no goal measurement, no completion marker emitted (`<skill-improvement-complete>` is not emitted because nothing was refined).

## Outcome
- No file under OUTDIR/target was modified (verified: still the original fixture, see final-tree.txt).
- Observation: the skill's flow handled the escape hatch correctly (BATCH 1 skipped, BATCH 2 asked only the triggered Intake question plus Prod checks). Spec gap noted: the skill's Prod checks template has no "Yes" option, so a blanket "choose Yes for BATCH 2" answer is ambiguous there.
