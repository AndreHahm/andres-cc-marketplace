# Dry-run transcript: skill-refiner-interactive, eval-4 (consolidate + Gate 4 approve)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: copy of fixture demo-skill at OUTDIR/target (OUTDIR = evals/skill-refiner-interactive/workspace/iteration-6/eval-4/with_skill/outputs).
Simulated answers: skill already located; select all goals; Consolidate at step 3; approve deletions at Gate 4; "Apply changes" at step 5; first option anywhere else.

## Quick Start (A-D)
- A: no predating context (request only names skill + action). Escape hatch NOT offered.
- B: skipped (request names the skill; operator: already located).
- C: skipped (request says "refine" / "follow best practices" -> Refine).
- D: routed to Core Workflow: Refinement.

## Step 1: Locate the skill
- Operator-supplied path OUTDIR/target; Glob of `**/skills/<name>/` does not apply (path given, skill already located). Not in user-space or plugin cache.
- Gitignore-exclusion check: target/ matches a global gitignore pattern, but it is the operator-named path, not a draft copy; proceeding (noted, not a block).
- R19 mirror-pair check: no `plugins/*/skills/demo-skill/` or `.claude/skills/demo-skill/` copy exists -> single skill, no mirror question.

### Pre-analysis (references/pre-analysis-checklist.md)
plugin-rulebook settings.json found: R13 tiers 100/300/490/500; R18 10/20/30; R21 description min 80, max 1024.
```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: description is single-line, 22 chars (<=80 so R8 fine); no forbidden fields
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary/marker formats)] [oversize >=400: none]
Workflow files: 0
Reference chain violations (ref->ref): references/a.md "Read references/b.md ..."
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): 22 chars, under the 80 floor (finding)
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: R21 description size; reference cluster; missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation + selection (goal-derivation.md)
QUESTION (AskUserQuestion, multiSelect, up to 3): "Which goals should this session pursue?"
Options:
- G1 "Zero reference chains": re-run chain scan over references/*.md -> 0 matches
- G2 "Intake uses AskUserQuestion": re-run intake scan -> 0 matches
- G3 "All invoked tools declared": re-run tool-scoping scan -> no undeclared tools
SIMULATED ANSWER: all three selected. Goals recorded. Deferred candidates stay in the report.

## Requirements Interview
Goals selected -> BATCH 1 Question 1 skipped.
### BATCH 1
- Q2 "What specific problems are you seeing?" (Key Issues; options: Hard-to-follow instructions / Scattered references / Nested sections). ANSWER (first option): Hard-to-follow instructions.
- Q3 "What would success look like?" (options: Clearer workflow / Lower token cost / Production-ready). ANSWER (first option): Clearer workflow.
- Q4 "Any areas to exclude or preserve as-is?" (options: Keep validation gates / Keep tool scoping). ANSWER (first option): Keep validation gates. Interpretation recorded: the target has no existing validation gates, so the exclusion preserves nothing and does not bar adding a new Testing & Validation section; flagged here as an ambiguity.
Scope documented.
### BATCH 2
Routing: operator not on "Infer from context", so BATCH 2 follows BATCH 1. Triggered questions only:
- Extraction: not triggered. Arguments: not triggered. Desc split: not triggered.
- Intake (triggered, maps to selected G2): "Section 'Quick Start' collects user input without AskUserQuestion (asks the user in plain prose). Convert it?" options Yes / No. ANSWER (first option): Yes.
- Prod checks (always asked; multiSelect): Security scan / Error handling / Tool scoping / None needed. ANSWER (first option): Security scan.
  Security scan result: Grep for credentials/keys/tokens and ${VAR} substitutions in SKILL.md and references/ -> none found.
- Reference clusters not asked here (step 3 owns it).

## Step 2: Load workflow reference
Read references/refinement-workflow.md (gates, validation phases, Rollback).

## Step 3: Consolidation
Files: references/a.md (5 lines), references/b.md (4 lines). Same topic (TODO summaries + marker formats); 2 files -> 1.
QUESTION (AskUserQuestion): "Should we consolidate these files? Saves 1 line (9 -> 8), improves clarity." options: Consolidate / Leave as-is.
SIMULATED ANSWER: Consolidate.

## Step 4: Preservation gates
1. GATE 1 (Content Audit): SKILL.md 13 lines: frontmatter, Quick Start (core); references/a.md 5 lines (summary format + directive to read b.md; supplementary); references/b.md 4 lines (marker formats; supplementary). No scripts/assets.
2. GATE 2 (Capability Assessment): consolidate a.md+b.md into one file -> does not impair execution (all content kept, link repointed); drop the ref->ref directive (now internal) -> safe. Intake rewrite and adding Grep to allowed-tools do not impair execution. All safe; deletions still need Gate 4.
(Gates 3 and 4 are applied in step 6.)

## Step 5: Plan-only exit
Request did not use plan-only wording -> ask.
QUESTION (AskUserQuestion): "Apply the approved scope?" options: Apply changes / Plan only / Stop.
SIMULATED ANSWER: Apply changes. (Step 6 runs.)

## Step 6: Make changes (CREATE -> LINK -> DELETE)
Rollback settled before the first edit: target is a scratch copy of a git-tracked fixture (evals/skill-refiner-interactive/fixtures/demo-skill/); restore = recopy the fixture; fixture untouched and had no uncommitted changes of its own.

1. CREATE: references/todo-marker-details.md (8 lines; merges a.md summary line and b.md marker formats).
2. GATE 3 (Migration Verification): destination exists; contains the "line number" sentence and both marker formats (TODO:, FIXME:); no content left behind in a.md/b.md. APPROVED.
3. LINK: SKILL.md pointer "See references/a.md for details." -> "See references/todo-marker-details.md for details."; new Reference Guide table row lists the consolidated file.
4. UPDATE (non-movement edits, standard sections auto-added): frontmatter allowed-tools `Read` -> `Read Grep` (G3); Quick Start prose intake replaced with AskUserQuestion block (G2); added When to Use, When NOT to Use, Testing & Validation, Reference Guide.
5. LINK verified: Grep of SKILL.md shows every `references/` path; Glob/test confirms references/todo-marker-details.md exists.
6. GATE 4 (Operator Confirmation), deletion of references/a.md (source of consolidation).
   QUESTION (AskUserQuestion): "Okay to delete references/a.md (content now in references/todo-marker-details.md)?" options: Delete / Keep. SIMULATED ANSWER: Delete (approved).
7. DELETE: references/a.md (Bash rm; no delete tool pre-approved, so a normal permission prompt, treated as granted by the simulation).
8. GATE 4 (Operator Confirmation), deletion of references/b.md.
   QUESTION (AskUserQuestion): "Okay to delete references/b.md (content now in references/todo-marker-details.md)?" options: Delete / Keep. SIMULATED ANSWER: Delete (approved).
9. DELETE: references/b.md (Bash rm, permission prompt treated as granted).

Consolidation report: Consolidated a.md + b.md (9 lines) into todo-marker-details.md (8 lines, saves 1). Links updated: SKILL.md (1 pointer + Reference Guide row); old files deleted after link check.

## Step 7: Validate result (seven phases)
- P1 File inventory: before SKILL.md + references/{a,b}.md; after SKILL.md + references/todo-marker-details.md (see final-tree.txt).
- P2 Read all: both files load completely.
- P3 Frontmatter: name, description present; allowed-tools `Read Grep`; YAML valid. description 22 chars is still under the R21 floor (deferred candidate, not a selected goal, left unchanged).
- P4 Body: 53 lines, R13 OK; Quick Start present and actionable; no spawn anti-patterns.
- P5 References: all linked files exist, no orphans, one level deep, no ref->ref chain.
- P6 Tools: Read, Grep used and declared; AskUserQuestion excluded; no Bash use.
- P7 Testing: activation phrases in the Testing & Validation section checked by reading.

## Step 8: Measure goals
Loaded pre-analysis-checklist.md scans again (see goal-measurement.md): G1 PASS, G2 PASS, G3 PASS. No FAIL, so no accept/continue question.

## Step 9: Trigger regression
description and when_to_use unchanged -> skipped.

## Step 10: Compliance and reviewer passes
Not dispatchable in this dry run (no Skill/Agent calls). Skill(plugin-rulebook) and the skill-reviewer agent were NOT run. Expected finding for a real run: R21 description below the 80-char floor (deferred candidate), which would need a round of fixes (and then step 9). Because neither pass ran, `<skill-improvement-complete>` is NOT emitted.
```
Lines: 13 -> 53
Frontmatter: allowed-tools gained Grep; description unchanged
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: references/todo-marker-details.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: not run (dry run)
```

## Gate/CREATE/LINK/DELETE action order (as performed)
1. CREATE references/todo-marker-details.md
2. GATE 3 migration verification
3. LINK SKILL.md pointer + Reference Guide row
4. LINK verified
5. GATE 4 ask for a.md -> Delete
6. DELETE references/a.md
7. GATE 4 ask for b.md -> Delete
8. DELETE references/b.md
(Gate 1 and Gate 2 ran earlier, in step 4, before step 6.)
