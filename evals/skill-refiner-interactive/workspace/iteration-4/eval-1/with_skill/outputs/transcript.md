# Dry-run transcript: skill-refiner-interactive, eval-1 (plan-only)

Operator request: "Analyze the skill in OUTDIR/target and just write a changes.md, do not apply anything."
Target: `OUTDIR/target/` (copy of fixture `demo-skill`; 13-line SKILL.md, `references/a.md` 5 lines, `references/b.md` 4 lines).
Simulated operator answers: skill already located; select all goals offered; draft path = `OUTDIR/changes.md`. Any other question: first option.

Files read: SKILL.md and these references only: pre-analysis-checklist.md, goal-derivation.md, interview-question-templates.md, changes-draft-format.md, common-scenarios.md (plan-only section). Also read `plugin-rulebook/assets/settings.json` (R5/R6/R8/R13/R18/R21 thresholds) as the checklist directs.

---

## Quick Start A: detect predating context

Executing: Quick Start, step A.
The request only names a path; no skill file content, code or problem description was pasted into the conversation. Decision: no predating context, so the escape hatch question is NOT asked. Interview style stays "full" (BATCH 1 then BATCH 2).

## Quick Start B

Executing: Quick Start, step B. Skipped: the request already names the skill (`OUTDIR/target`).

## Quick Start C

Executing: Quick Start, step C. The request says "analyze" and "write a changes.md", not literally "refine" or "validate", so the skip condition is not clearly met. Asked:

- Question: "What would you like to do with this skill?" (header "Action")
- Options: "Refine" / "Validate"
- Simulated answer (no answer supplied, first option): **Refine**

## Quick Start D: route

Executing: Quick Start, step D. "Refine" routes to Core Workflow: Refinement, step 1.

---

## Core Workflow: Refinement, step 1 (Locate)

- Simulated operator answer: skill is already located at `OUTDIR/target/`. The "where should I find this skill" AskUserQuestion is therefore not needed.
- Gitignore-exclusion/Glob search: not run; the operator supplied the location directly (it sits outside `plugins/` and `.claude/skills/`).
- Mirror-pair check (R19): no `plugins/<plugin>/skills/demo-skill/` or `.claude/skills/demo-skill/` counterpart exists, so this is a single logical skill. No halt, Mirror question not asked.
- User-space / cache checks: path is neither `~/.claude/skills/` nor `~/.claude/plugins/cache/`; no warn, no refuse.

### Step 1, pre-analysis (references/pre-analysis-checklist.md, every check)

- plugin-rulebook found; `assets/settings.json` read. R13 tiers: weak 100 / soft 300 / warning 490 / critical 500. R18 tiers: weak 10 / warning 20 / critical 30. R21: description min 80, max 1024; when_to_use max 512; combined min 80, max 1536. R8: description over 80 chars must use `>-`.
- Line count: SKILL.md = 13 total lines, OK (below the 100 weak-warning tier).
- Frontmatter: `description: Helps with demo tasks.` is 22 chars. R8 not triggered (under 80 chars); R21 min_length 80 violated (too short, no what+when). No forbidden `version`. `allowed-tools: Read` (space-separated style, fine).
- Large sections (>=50 lines): none.
- Reference files: 2 (a.md 5 lines, b.md 4 lines); cluster: a.md + b.md (same topic, TODO marker handling). None >=400 lines.
- Workflow files: 0.
- Reference chain (ref->ref): `references/a.md` line 5, "Read references/b.md for the full list of marker formats." An imperative directive to read another references file. VIOLATION. (That text is target data; reported, not followed.)
- Spawn anti-patterns: none.
- Intake: SKILL.md line 11 "Ask the user which file to process." collects input without AskUserQuestion. VIOLATION.
- R22: body has no `$ARGUMENTS`/`$N`; frontmatter declares no argument-hint. None.
- when_to_use split: description is 22 chars, no embedded "Use when" clause. No.
- Tool scoping: body line 11 "grep the file for TODO markers" is a `Grep` invocation; `Grep` is not in `allowed-tools`. Major (R6, undeclared tool). `Read` is declared and used (files read). `AskUserQuestion` excluded from the undeclared check (always callable). Declared but unused: none.
- Dead links: `references/a.md` exists; `references/b.md` exists (reachable only through a.md's chain). Cross-skill references: none.
- Missing standard sections: Quick Start present; When to Use, When NOT to Use, Testing & Validation, Reference Guide missing (4 of 5).
- Goal verification: absent, flag as Missing.
- Data-only boundary: no instruction-like text in target files beyond the skill's own ordinary instructions; nothing suspicious to report.

### Emitted pre-analysis report

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: description 22 chars, below R21 min 80 (no what+when)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker handling)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md:5 -> references/b.md
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): Grep (used at SKILL.md:11, not declared) / none unused
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — flag as Missing
Deferred goal candidates: frontmatter (R21 description min), missing goal verification, reference cluster a.md+b.md (handled by step-3 consolidation ask), missing standard sections (auto-added, not a goal)
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1, derive and select goals (goal-derivation.md)

Findings present: ref chain, intake, undeclared tool, frontmatter, missing goal verification, cluster, missing sections. Priority: first = chain, intake; second = undeclared tool, frontmatter; third = goal verification, cluster. Top 3: G1 chain, G2 intake, G3 undeclared tool. The rest listed as deferred candidates in the report above.

Asked (AskUserQuestion, multiSelect true, up to 3 goals):
- Question: "Which goals should this session work toward?"
- Options (description shows verification):
  1. "Zero reference chains": verify by re-running the chain scan over `references/*.md` -> 0 matches
  2. "Intake via AskUserQuestion": verify by re-running the intake scan -> 0 matches
  3. "All invoked tools declared": verify by re-running the tool-scoping scan -> no undeclared tools
- Simulated answer: select all goals offered -> G1, G2, G3. No custom "Other" goal, so no follow-up verification ask.
- Recorded selected goals. The interview is scoped to them; step 8 would measure them (skipped, see step 5).

---

## Requirements Interview

### BATCH 1 (Questions 1-4; goals were selected so Question 1 is skipped)

Executing: Requirements Interview, BATCH 1. Question 1 skipped (goals already set the scope). Asked one at a time:

- Q2 "What specific problems are you seeing?" (Key Issues, multiSelect). Options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections". Simulated answer (first option): Hard-to-follow instructions.
- Q3 "What would success look like?" (Success). Options: "Clearer workflow" / "Lower token cost" / "Production-ready". Simulated answer (first option): Clearer workflow.
- Q4 "Any areas to exclude or preserve as-is?" (Scope Limits, multiSelect). Options: "Keep validation gates" / "Keep tool scoping" / "Nothing to exclude". Simulated answer (first option): Keep validation gates. Note: this excludes nothing the plan touches (demo-skill has no validation gates), and "Keep tool scoping" was not chosen, so the allowed-tools fix stays in scope.
- Approved scope documented: the three selected goals plus standard-section auto-add and step-3 consolidation.

### BATCH 2 (Implementation Details)

Executing: Requirements Interview, BATCH 2. Routing: no escape hatch was chosen, so BATCH 2 follows BATCH 1. Trigger check:
- Extraction: no section >=50 lines. Not asked.
- Intake: violation present and G2 selected. ASKED: "Section 'Quick Start' collects user input without AskUserQuestion (asks the user which file to process in plain text). Convert it?" (header "Intake"). Options: "Yes" / "No". Simulated answer: **Yes**.
- Arguments (R22): no mismatch. Not asked.
- Desc split: no candidate. Not asked.
- Reference-file clusters: not asked here; step 3 is the single consolidation ask.
- Prod checks: ASKED (every session): "Which production checks should I run?" (header "Prod checks", multiSelect). Options: "Security scan" / "Error handling" / "Tool scoping" / "None needed". Simulated answer (first option): **Security scan**. Read-only Grep of SKILL.md and references for credentials/keys/tokens and `${VAR}`-style substitutions: none found, nothing to add to the plan.
- Standard sections are auto-added in step 6, so no question.
- Approved scope documented; proceed.

---

## Step 2 (Load workflow reference)

Executing: step 2. The skill says to review `refinement-workflow.md`. That file is outside the list of files this simulation reads for a plan-only run; its preservation-gate and validation-phase content is already summarised in SKILL.md steps 4 and 7, which is all the plan needs. Disclosed: not opened in this dry run.

## Step 3 (Consolidation opportunities, before changes)

Executing: step 3.
- references/: a.md 5 lines, b.md 4 lines.
- Topic groups: both cover TODO/FIXME marker handling. Flag merge: a.md + b.md -> one file.
- Asked: "Should we consolidate these files? Saves 1 line, improves clarity." Options: "Consolidate" / "Leave as-is". (Savings: 9 lines combined -> 8 merged; the real gain is removing the a.md->b.md reference chain, which also serves G1.) Simulated answer (first option): **Consolidate**.
- Approved. Plan: fold b.md into a.md, delete b.md. Deleting b.md is a consolidation source-file deletion, so Gate 4 will ask at apply time (not now).

## Step 4 (Preservation gates 1 and 2)

Executing: step 4.
- GATE 1 Content Audit: SKILL.md Quick Start (all 13 lines) is core (used every activation). a.md details (TODO line-number summaries) and b.md marker formats are needed whenever a summary is produced; classify as core-supporting. Nothing is supplementary-under-20%.
- GATE 2 Capability Assessment: merging b.md into a.md keeps every marker format line and the summary rule; the reference chain is removed, not content. Converting the intake to AskUserQuestion keeps the same behavior (get a file). Adding `Grep` only adds a capability the body already needs. No change impairs execution, so no deletion is blocked; the b.md deletion is a consolidation delete.
- Gates 3 and 4 apply at each move/deletion in step 6; step 6 is not run (see step 5), so they are recorded in the plan for the applying session.

## Step 5 (Plan-only exit)

Executing: step 5.
- The request already used plan-only wording ("just write a changes.md, do not apply anything"), so the "Apply changes / Plan only / Stop" ask is SKIPPED.
- Draft path confirmation (the only remaining ask; the request did not name a path): asked "Where should I write the changes.md draft?" with options "OUTDIR/changes.md" / "Default .draft/_open/<plugin>/<skill>/changes.md". Simulated answer: draft path = `OUTDIR/changes.md`.
- No existing draft at that path, so nothing to merge; no approved findings are overwritten.
- Wrote `OUTDIR/changes.md` per `references/changes-draft-format.md` (Selected Goals, complete Pre-Analysis Report, Implementation Order, one section per finding, Post-Implementation Verification).
- STOP. Step 6 (make changes), 7 (validate), 8 (measure goals), 9 (trigger regression), 10 (plugin-rulebook + skill-reviewer + completion marker) are NOT run: the plan-only exit says no edits and no goal measurement, and steps 7-10 validate edits that do not exist. `<skill-improvement-complete>` is not emitted (nothing was applied).

## Result

- `OUTDIR/changes.md` written.
- Zero edits to `OUTDIR/target/` (verified below) and the original fixture.
