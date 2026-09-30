# Transcript: skill-refiner-interactive dry run, iteration-9 eval-6

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: a copy of `evals/skill-refiner-interactive/fixtures/demo-skill/` at OUTDIR/target (13-line SKILL.md, references/a.md 5 lines, references/b.md 4 lines).

## Quick Start

### A. Predating context
The request only names the skill and the action. That is not predating context. No escape-hatch question asked. The BATCH 1 / BATCH 2 routing is therefore the full interview path.

### B. "What skill do you want to work on?"
Skipped. The request already names the skill (path given). Simulated answer: skill already located.

### C. "What would you like to do with this skill?" (Refine / Validate)
Skipped. The request already says "refine" ("follows best practices" is a refine request).

### D. Route
"Refine" -> Core Workflow: Refinement.

## Core Workflow: Refinement

### Step 1. Locate the skill
- Path supplied by operator under OUTDIR/target; contains SKILL.md. Located.
- Gitignore check: `git check-ignore` reports `target/` matches the user's global gitignore (`~/.gitignore_global:149`). The operator explicitly named this path and the simulation says "skill already located", so it is used as the target. Observation: the gitignore-exclusion guidance targets draft copies found by Glob, not an operator-named path.
- Mirror-pair check (R19): no `<repo root>/.claude/skills/demo-skill/` or `plugins/*/skills/demo-skill/`. Not a mirror pair.
- Not in user-space, not in the plugin cache. No user-space warning.

#### Pre-analysis (references/pre-analysis-checklist.md)
- plugin-rulebook settings.json found (plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json). R13 tiers: weak 100 / soft 300 / warning 490 / critical 500. R18: 10/20/30. R21: description min 80 (critical at <=20).

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: single-line description (needs >-); allowed-tools "Read" ok; no forbidden fields
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (marker formats) | oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md ..." -> b.md
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" with no AskUserQuestion
Argument consistency (R22): none (no $ARGUMENTS use, no argument-hint)
when_to_use split candidate: no
Description size (R21): 22 chars, below the 80-char floor (warning tier; above the 20-char critical line)
Tool scoping (R6): undeclared: Grep (Quick Start says "grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: single-line description / R21 description size, reference cluster a+b, goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

#### Goal derivation (references/goal-derivation.md)
Findings in priority order: (1) ref->ref chain, intake violation; (2) undeclared tool, frontmatter/description size; (3) cluster, goal verification. Top 3 selected for the question.

QUESTION (AskUserQuestion, multiSelect: true, up to 3 goals):
"Which goals should this refinement session meet?" header "Goals"
Options:
1. "Zero reference chains" - verification: re-run the chain scan over references/*.md -> 0 matches
2. "Intake uses AskUserQuestion" - verification: re-run the intake scan -> 0 matches
3. "Every invoked tool declared" - verification: re-run the tool-scoping scan -> no undeclared tools
(Other: custom goal, needs a verification check.)
SIMULATED ANSWER: select all goals offered -> all 3 selected.

Recorded goals:
- G1 Zero ref->ref chains (source: chain finding)
- G2 All intake uses AskUserQuestion with options (source: intake finding)
- G3 Every invoked tool declared in allowed-tools (source: Grep undeclared)
Deferred candidates (listed in the report above): single-line description, R21 description size, cluster, goal verification.

### Requirements Interview
Goals were selected, so BATCH 1 Question 1 is skipped (goals set the scope).

BATCH 1, Question 2
QUESTION: "What specific problems are you seeing?" header "Key Issues", multiSelect: true
Options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections"
ANSWER (no simulated answer, first option): "Hard-to-follow instructions"

BATCH 1, Question 3
QUESTION: "What would success look like?" header "Success", multiSelect: false
Options: "Clearer workflow" / "Lower token cost" / "Production-ready"
ANSWER (first option): "Clearer workflow"

BATCH 1, Question 4
QUESTION: "Any areas to exclude or preserve as-is?" header "Scope Limits", multiSelect: true
Options: "Keep validation gates" / "Keep tool scoping"
ANSWER (first option): "Keep validation gates"
Consequence per the skill: the Testing & Validation area is excluded from step 6's auto-added standard sections. Tool scoping is not excluded (G3 needs a grant for Grep).
Documented approved scope: clearer workflow; goals G1-G3; exclude Testing & Validation section; no other exclusions.

BATCH 2 (escape hatch not used, so this follows BATCH 1)
Triggers detected in pre-analysis: Intake (yes), Extraction (no), Arguments (no), Desc split (no). The description-size finding has no BATCH 2 question.
QUESTION (Intake): "Section 'Quick Start' collects user input without AskUserQuestion (Ask the user which file to process). Convert it?" header "Intake", options "Yes" / "No"
ANSWER (first option): "Yes"

QUESTION (Prod checks, asked every session): "Which production checks should I run?" header "Prod checks", multiSelect: true
Options: "Security scan" / "Error handling" / "Tool scoping" / "None needed"
ANSWER (first option): "Security scan"
Security scan run: Grep over SKILL.md and references/ for password|secret|token|api key|${...} -> no matches. No scripts/ directory. Clean.

Standard sections are auto-added in step 6, so no question is needed for them.

### Step 2. Load workflow reference
Read references/refinement-workflow.md (gates, validation phases, rollback).

### Step 3. Consolidation opportunities
references/ exists: a.md 5 lines, b.md 4 lines (9 total). Both cover TODO/marker details (a.md links b.md by directive). Flagged as a merge candidate.
QUESTION: "Should we consolidate these files? Saves ~1 line, improves clarity." options "Consolidate" / "Leave as-is"
ANSWER (first option): "Consolidate"
Plan: fold b.md's marker list into a.md (UPDATE destination), keep SKILL.md pointer to a.md, then delete b.md.

### Step 4. Preservation gates
- GATE 1 Content Audit: SKILL.md (13 lines, Quick Start core, 100%), a.md (5 lines, core/detail), b.md (4 lines, supplementary marker list). No scripts/ or assets/.
- GATE 2 Capability Assessment: merging b.md into a.md impairs nothing (all content preserved). Intake conversion and adding Grep do not impair execution. Standard-section additions add content only. Safe.
- GATE 3 and GATE 4 are applied in step 6. The early Gate 4 ask for the consolidation's source file comes after the operator chooses to apply (step 5).

### Step 5. Plan-only exit
QUESTION: "Apply the approved scope?" options "Apply changes" / "Plan only" / "Stop"
SIMULATED ANSWER: "Apply changes". Step 6 runs.

Early Gate 4 ask (before any edit, for the consolidation's source file):
QUESTION: "Okay to delete references/b.md once its content is in references/a.md?" options "Delete" / "Keep"
ANSWER (first option): "Delete" (approved).

### Step 6. Make changes
Rollback (settled before the first edit): the target is an untracked, globally gitignored copy, so version control cannot restore it. The pristine source is evals/skill-refiner-interactive/fixtures/demo-skill/, which is the restore source. Final change summary's Files created / Files deleted lists serve as the restore list.

1. Consolidation (CREATE -> LINK -> DELETE)
   - CREATE/UPDATE: references/a.md now carries b.md's marker list under "## Marker Formats" and the "Read references/b.md" directive is removed.
   - GATE 3 Migration Verification: destination a.md exists; both marker lines present (grep count 2); SKILL.md pointer `references/a.md` still resolves; nothing orphaned. APPROVED.
   - LINK: SKILL.md already pointed only at a.md; no pointer change needed.
   - GATE 4 check (at the deletion, citing the earlier approval): "Delete" approved for b.md. Deletion run as a Bash `rm` (second permission gate, normal prompt). references/b.md deleted.
2. Intake conversion (BATCH 2 "Yes"): Quick Start's free-form intake replaced with an AskUserQuestion block (2 options).
3. Tool scoping (G3): added Grep to `allowed-tools` (`Read` -> `Read Grep`). Quick Start now says "use Grep".
4. Standard sections, auto-added (no approval needed): `## When to Use`, `## When NOT to Use`, `## Reference Guide`. `## Testing & Validation` NOT added, because BATCH 1 Question 4 excluded that area ("Keep validation gates"). `## Quick Start` already present.
Edits made in place; line count 13 -> 39.

### Step 7. Validate result (seven phases)
- Phase 1 File Inventory: before: SKILL.md (13), references/a.md (5), references/b.md (4). After: SKILL.md (39), references/a.md (8). b.md deleted (approved).
- Phase 2 Read All: SKILL.md and a.md read fully; no truncation, no gaps.
- Phase 3 Frontmatter: name ok; allowed-tools `Read Grep` ok, YAML valid. Observed: `description` is still single-line, 22 chars, not a `>-` scalar, below the R21 80-char floor. It is outside the approved scope/goals (deferred candidate), so it is not edited here; carried to the step-10 compliance pass.
- Phase 4 Body: 39 lines, OK tier (R13); Quick Start is actionable; workflow pattern: simple linear; no spawn anti-patterns.
- Phase 5 References: a.md exists and is linked; no orphans; one level deep; no ref->ref chain.
- Phase 6 Tools: undeclared none (Read, Grep declared and used); unused none; no Bash-for-dedicated-tool misuse.
- Phase 7 Testing: "refine/summarize TODO markers in a file" style queries would activate; description is thin (noted above). Links resolve.

### Step 8. Measure goals
- G1 Zero ref->ref chains: re-ran chain scan over references/*.md -> 0 matches. PASS
- G2 Intake uses AskUserQuestion: re-ran intake scan for "ask the user"/"prompt the user" and a `questions:` block without options -> 0 matches. PASS
- G3 Every invoked tool declared: Read, Grep used; both in allowed-tools. PASS
No failed goal, so no accept/continue question.

### Step 9. Trigger regression check
Neither `description` nor `when_to_use` changed in wording so far. Step 9 skipped: no trigger-eval question asked.

### Step 10. Compliance and reviewer passes

#### Run 1 (first run of both checks)
- Skill(plugin-rulebook) (simulated): 1 FAIL finding: R8, the description needs the `>-` block scalar.
- skill-reviewer (Structured output mode, simulated): counts.critical 0, counts.major 1: Quick Start is missing an example.
- NO MARKER EMITTED (1 FAIL and 1 Major outstanding; the change summary is not final either).

#### Round 1 (fix pass)
Fixes:
- R8: `description` moved into a `>-` block scalar, same words ("Helps with demo tasks."). Format-only change, so step 9 does not re-enter (a format-only change does not count).
- Major: added a worked example to Quick Start ("Example: for `src/app.py` containing `# TODO: handle empty input` on line 12, reply with `- line 12: TODO: handle empty input`.").
Re-ran the touched step-7 phases: Phase 2 (read all: ok), Phase 3 (description now `>-`, valid YAML), Phase 4 (42 lines, OK tier; Quick Start has an example).
Re-measured goals (step 8): G1 PASS (0 chain matches), G2 PASS (0 intake matches; the added example has no "ask the user" text), G3 PASS (Read, Grep declared). Step 9 not re-entered: no text change to description.

#### Run 2 (re-run of both checks after round 1)
- Skill(plugin-rulebook) (simulated): clean, no FAIL.
- skill-reviewer (simulated): counts.critical 0, counts.major 0.
- NO MARKER EMITTED at this point. The summary is emitted next, then the marker, because all three conditions hold (next block).

#### Change summary and completion gate
Conditions: every plugin-rulebook FAIL fixed (R8 fixed); every skill-reviewer Critical/Major fixed (Quick Start example added); every selected goal PASS (G1-G3). All hold. Rounds used: 1 of 3.

```
Lines: 13 -> 42
Frontmatter: description converted to a >- block scalar (R8); allowed-tools Read -> Read Grep (G3)
Sections added: When to Use, When NOT to Use, Reference Guide (Testing & Validation not added: excluded by the operator's "Keep validation gates" answer); Quick Start gained an AskUserQuestion block and an example
Files created: none
Files deleted: references/b.md (content merged into references/a.md; deletion approved at Gate 4)
plugin-rulebook: 1 FAIL findings fixed
```

Completion marker emitted here (literal):

```
<skill-improvement-complete>
```

Notes for the eval reader:
- Observation: choosing the first option at BATCH 1 Question 4 ("Keep validation gates") makes the skill skip adding `## Testing & Validation`, so the final skill has no such section (R29 would normally want it; the simulated compliance run 2 reported clean per the control).
- The deferred candidates (R21 description floor at 22 chars, goal-verification section) remain unaddressed by design.

Final tree written to OUTDIR/final-tree.txt.
