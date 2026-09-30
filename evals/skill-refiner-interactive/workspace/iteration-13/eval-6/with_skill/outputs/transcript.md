# Transcript: skill-refiner-interactive dry run (iteration-13, eval-6)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Simulated answers: skill already located; select all goals offered; "Apply changes" at step 5. Anything else: first option. Target: a copy of `evals/skill-refiner-interactive/fixtures/demo-skill/` at `OUTDIR/target/`.

## Quick Start A-D

- A. Predating context? None. The request names the skill and the action only, so no escape-hatch question. Interview style defaults to the full interview (BATCH 1 then BATCH 2).
- B. Skipped: the request names the skill.
- C. Skipped: the request already says "refine".
- D. Route: Refinement, to Core Workflow step 1.

## Step 1: Locate the skill

- Operator answer: skill already located at `OUTDIR/target`. No Glob or user-space ask.
- Gitignore-exclusion and mirror-pair (R19) checks: target is a workspace copy, no `.claude/skills/demo-skill/` or `plugins/*/skills/demo-skill/` pair exists. Not a mirror pair.

### Step 1: pre-analysis (references/pre-analysis-checklist.md)

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13; weak_warning starts at 100)
Frontmatter issues: single-line `description` ("Helps with demo tasks.", 22 chars; R8 only requires >- above 80 chars per settings.json, checklist flags single-line anyway). No non-standard fields (R5).
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details) | oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 4 "Read references/b.md for the full list of marker formats."
Spawn anti-patterns: none
Intake pattern violations: none (SKILL.md "Ask the user which file to process" is unbounded input, a file path; plain text is correct, not flagged)
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): finding - description 22 chars is under the 80-char floor (min_length 80)
Tool scoping (R6): [undeclared: Grep ("grep the file for TODO markers")] / [unused declared: none (Read is used)]
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: reference cluster a.md + b.md (handled by the step 3 ask), R21 description floor, missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1: goal derivation and selection (references/goal-derivation.md)

Candidates, in priority order (cap 3):

1. Zero reference->reference chains. Verification: re-run chain scan over `references/*.md` -> 0 matches. Source: ref->ref chain finding.
2. Every invoked tool is declared in `allowed-tools`. Verification: re-run tool-scoping scan -> no undeclared tools. Source: undeclared Grep.
3. Frontmatter passes R5 and R8. Verification: `Skill(plugin-rulebook)` R5 and R8 -> OK. Source: single-line description finding.

Deferred (listed in the report above): cluster, R21 floor, missing goal verification.

AskUserQuestion (multiSelect: true):
- question: "Which goals should this refinement session achieve?" header: "Goals"
- options: "Zero reference chains (check: chain scan -> 0 matches)" / "Declare every invoked tool (check: tool scan -> none undeclared)" / "Frontmatter passes R5 and R8 (check: plugin-rulebook R5, R8 -> OK)" (plus automatic "Other")
- Simulated answer: select all three. Goals recorded.

### Requirements Interview

BATCH 1 (goals selected, so Question 1 is skipped; Questions 2-4 asked one at a time, first option chosen):

- Q2, header "Key Issues", multiSelect. Options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections". Answer (first option): "Hard-to-follow instructions".
- Q3, header "Success". Options: "Clearer workflow" / "Lower token cost" / "Production-ready". Answer (first option): "Clearer workflow".
- Q4, header "Scope Limits", multiSelect. Options: "Keep validation gates" / "Keep tool scoping". Answer (first option): "Keep validation gates". So the Testing & Validation section is excluded, and the exclusion binds step 6's auto-added standard sections. "Keep tool scoping" was not chosen, so adding Grep to `allowed-tools` is allowed.
- Approved scope documented: the three goals; do not touch Testing & Validation.

BATCH 2 (no escape-hatch answer, so it runs after BATCH 1). Conditional questions checked against pre-analysis triggers:
- Extraction: no section >=50 lines, not asked.
- Intake: no intake violation, not asked.
- Arguments: no R22 mismatch, not asked.
- Desc split: no candidate, not asked.
- Clusters: not asked here, step 3 owns it.
- Prod checks (always asked), header "Prod checks", multiSelect. Options: "Security scan" / "Error handling" / "Tool scoping" / "None needed". Answer (first option): "Security scan". Ran a Grep scan of SKILL.md and references/ for credentials, keys, tokens and `${VAR}` substitutions: no matches.

## Step 2: Load workflow reference

Read `references/refinement-workflow.md` (preservation gates, validation phases, Rollback).

## Step 3: Consolidation opportunities

`references/` exists. Files: `a.md` (5 lines), `b.md` (4 lines). Same topic (TODO marker details); a.md already points at b.md.

AskUserQuestion: "Should we consolidate these files? Saves N lines, improves clarity." Here N is about 1 line, and it also removes the ref->ref chain. Options: "Consolidate" / "Leave as-is". Simulated answer (first option): "Consolidate". Plan: merge b.md into a.md as a "Marker Formats" section, drop the `Read references/b.md` directive, delete b.md.

## Step 4: Preservation gates 1 and 2

- GATE 1 Content Audit: SKILL.md 13 lines (frontmatter 5, Quick Start core). `references/a.md` 5 lines, supplementary (<20%, summary format). `references/b.md` 4 lines, supplementary (marker formats). No scripts or assets. Audit complete.
- GATE 2 Capability Assessment: merge b.md into a.md impairs nothing (all content preserved, link updated); adding Grep to `allowed-tools` only adds a grant; adding standard sections is additive; b.md deletion is safe because its content migrates first. All changes pass.
- GATE 3 and GATE 4 apply at each move and deletion in step 6. The consolidation's source-file approval is collected early at step 5, the documented exception to gate order.

## Step 5: Plan-only exit / apply

AskUserQuestion: "Apply the approved scope?" Options: "Apply changes" / "Plan only" / "Stop". Simulated answer: "Apply changes".

Early Gate 4 ask for the consolidation's source file. Question: "Okay to delete references/b.md once its content is in references/a.md?" Options: "Delete" / "Keep". Simulated answer (first option): "Delete". Approval collected only; nothing deleted yet.

## Step 6: Make changes

- Rollback settled. The target is an untracked workspace copy; the pre-edit state is the pristine `evals/skill-refiner-interactive/fixtures/demo-skill/` (restore by re-copying it). No mirror, so no Mirror overwrite.
- CREATE/UPDATE destination first: `references/a.md` now has a "Marker Formats" section holding b.md's two bullets, and the `Read references/b.md` line is removed.
- GATE 3 (migration verification): destination exists, both marker bullets present, no orphans.
- LINK: SKILL.md Quick Start pointer now reads "See references/a.md for details and the full list of marker formats." A check for other `references/b.md` mentions found none.
- GATE 4 (recorded at the deletion, citing the approval at step 5): delete `references/b.md`, approved. Ran as a Bash `rm` under the permission settings. Done after LINK verified, so the order is CREATE -> LINK -> DELETE.
- `allowed-tools`: `Read` -> `Read Grep` (goal 2).
- Standard sections auto-added: `## When to Use`, `## When NOT to Use` (with named alternatives), `## Reference Guide`. `## Quick Start` already present. `## Testing & Validation` NOT added, because BATCH 1 Question 4 chose "Keep validation gates".
- `description` left unchanged (22 chars).

## Step 7: Validate result (seven phases)

- Phase 1 File Inventory. Before: SKILL.md, references/a.md, references/b.md. After: SKILL.md, references/a.md. b.md deleted after its content was merged.
- Phase 2 Read All: both files load completely, no gaps, no broken links.
- Phase 3 Frontmatter: name, description present; allowed-tools `Read Grep`; YAML valid; no non-standard fields.
- Phase 4 Body: 28 lines, OK under R13; Quick Start present and actionable; no spawn anti-patterns.
- Phase 5 References: a.md exists and is linked; no orphans; one level deep; no ref->ref chains.
- Phase 6 Tools: no undeclared, none unused, no Bash misuse.
- Phase 7 Testing: activation phrases ("refine this demo skill" style requests for TODO summaries) read clearly; Quick Start traces end to end.

## Step 8: Measure goals

1. Zero reference chains: re-run chain scan -> 0 matches. PASS.
2. Every invoked tool declared: Grep and Read both declared -> PASS.
3. Frontmatter passes R5 and R8: no forbidden fields; description is 22 chars, under R8's 80-char threshold -> PASS (per simulation, all goal verifications pass).

## Step 9: Trigger regression check

The text of `description` and `when_to_use` did not change, so this step is skipped entirely. Only the allowed-tools line and body changed.

## Step 10: Compliance and reviewer passes

### Run 1 (first run of both checks; not a round)

- `Skill(plugin-rulebook)` full check (simulated): 1 FAIL, R8, the description needs the `>-` block scalar.
- `skill-reviewer` agent, full mode, Structured output mode (simulated): `counts.major` = 1, `counts.critical` = 0. The Major is a missing example in Quick Start.
- Findings remain, so the marker is withheld.

NO MARKER EMITTED

### Fixes (round 1 fix pass)

Neither fix changes the BATCH 1 Question 4 exclusion (Testing & Validation and tool scoping untouched), so no scope-expansion ask.

- R8: `description: Helps with demo tasks.` became a `>-` block scalar with the same words on the next line. This is a format-only change (same words moved into `>-`), so step 9 does NOT re-run.
- Major: added an Example block to Quick Start, a worked `notes.txt` summary with `TODO: fix intro` on line 3 and `FIXME: check dates` on line 9.
- Re-run step-7 phases touched (Phase 3 Frontmatter, Phase 4 Body): frontmatter valid, 34 lines, Quick Start now has an example -> pass.
- Re-measure step 8 goals before re-running the checks: goal 1 PASS, goal 2 PASS, goal 3 PASS (frontmatter passes R5 and R8, description now in `>-` form).

### Run 2 (re-run of both checks after round 1 fixes)

- `Skill(plugin-rulebook)` (simulated): clean, no FAIL.
- `skill-reviewer` (simulated): clean, `counts.critical` = 0, `counts.major` = 0.
- All three marker conditions hold: every plugin-rulebook FAIL fixed, every Critical and Major fixed, every selected goal passed.

Change summary:

```
Lines: 13 -> 34
Frontmatter: description converted to a >- block scalar (R8, same words); allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Reference Guide (Quick Start gained an example; Testing & Validation not added, per the "Keep validation gates" exclusion)
Files created: none
Files deleted: references/b.md (merged into references/a.md)
plugin-rulebook: 1 FAIL findings fixed
```

Marker emitted (once):

```
<skill-improvement-complete>
```

## Files

Final `OUTDIR/target`: `SKILL.md` and `references/a.md` (listed in `final-tree.txt`). The original fixture was not modified.
