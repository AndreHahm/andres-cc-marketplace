# Transcript: skill-refiner-interactive, eval-7 (declined deletion)

Dry-run simulation. Every AskUserQuestion is written out with its simulated answer. Target: a copy of `evals/skill-refiner-interactive/fixtures/demo-skill/` at `OUTDIR/target/`.

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."

## Quick Start

**A. Predating context?** None. The request only names the skill and the action, which the skill says is not predating context. No escape hatch offered.

**B. "What skill do you want to work on?"** Skipped: request already names the skill (OUTDIR/target). Simulated operator answer "skill already located" noted.

**C. Action question:** skipped, the request already says "refine".

**D. Route:** Refine -> Core Workflow: Refinement.

## Refinement step 1: Locate the skill

- Glob `**/skills/<name>/SKILL.md` equivalent: the target is `OUTDIR/target/SKILL.md` (simulated "already located").
- Gitignore exclusion: the target sits under an eval workspace outputs directory, not a `.temp/`, `.draft/` or `.backup/` draft; treated as the real target.
- Mirror-pair check (R19): no `plugins/<plugin>/skills/demo-skill/` and no `.claude/skills/demo-skill/` exist. Not a mirror pair; one logical skill.
- Not user-space, not plugin cache. No warnings.

### Pre-analysis (references/pre-analysis-checklist.md)

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: description is single-line (needs >-)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary / marker formats) ] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md for the full list of marker formats"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" (free-form intake, no AskUserQuestion)
Argument consistency (R22): none
when_to_use split candidate: no (description is short, no embedded trigger clause)
Description size (R21): "Helps with demo tasks." is under the floor
Tool scoping (R6): undeclared: Grep ("grep the file" is an invocation) / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: see below
R13/R18 threshold source: skill-development fallback (plugin-rulebook settings not read in this dry run; 500-line SKILL.md / 30-line code block flat limits used)
```

### Goal derivation and selection (references/goal-derivation.md)

Findings mapped to goals in priority order; max 3:

1. Reference chain (ref->ref) -> "Zero reference->reference chains" (first priority)
2. Intake violation -> "All intake uses AskUserQuestion with options" (first priority)
3. Undeclared tool -> "Every invoked tool is declared in allowed-tools" (second priority)

Deferred candidates (not offered, listed in the report): description size / single-line description (frontmatter), reference cluster a.md + b.md (handled by step 3 consolidation ask), missing standard sections (auto-added in step 6), missing goal verification (optional).

**AskUserQuestion (goal selection)** - `multiSelect: true`, up to 3 goals, each option shows its verification check:
- "Zero reference-to-reference chains" - verify: chain scan over `references/*.md` -> 0 matches
- "All intake uses AskUserQuestion with options" - verify: intake scan -> 0 matches
- "Every invoked tool is declared in allowed-tools" - verify: tool-scoping scan -> no undeclared tools
- (Other: custom goal, needs a verification check)

Simulated operator answer: select all goals offered. All 3 goals recorded; interview is scoped to them; step 8 will measure them.

## Requirements Interview

Goals were selected, so BATCH 1 Question 1 is skipped. Questions 2-4 asked one at a time. No simulated answers were given for them, so the first option is chosen.

**BATCH 1 Question 2 - AskUserQuestion:** "What specific problems are you seeing?" header "Key Issues", multiSelect. Options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections". Simulated answer (first option): "Hard-to-follow instructions".

**BATCH 1 Question 3 - AskUserQuestion:** "What would success look like?" header "Success". Options: "Clearer workflow" / "Lower token cost" / "Production-ready". Simulated answer (first option): "Clearer workflow".

**BATCH 1 Question 4 - AskUserQuestion:** "Any areas to exclude or preserve as-is?" header "Scope Limits", multiSelect. Options: "Keep validation gates" / "Keep tool scoping". Simulated answer (first option): "Keep validation gates". Nothing excluded that binds the standard sections; tool scoping not excluded. Approved scope documented: the three goals plus standard sections.

**BATCH 2** (reached after BATCH 1; no "Infer from context" choice existed). Only questions whose trigger pre-analysis detected, plus Prod checks:

- Extraction: no trigger (no section >=50 lines). Not asked.
- **Intake** (trigger: Quick Start free-form intake; its goal was selected) - AskUserQuestion: "Section 'Quick Start' collects user input without AskUserQuestion (free-form 'Ask the user which file to process'). Convert it?" header "Intake". Options: "Yes" / "No". Simulated answer (first option): "Yes".
- Arguments (R22): no mismatch. Not asked.
- Desc split: no trigger. Not asked.
- Reference clusters: not asked here; step 3 is the single consolidation ask.
- **Prod checks** (asked every session) - AskUserQuestion: "Which production checks should I run?" header "Prod checks", multiSelect. Options: "Security scan" / "Error handling" / "Tool scoping" / "None needed". Simulated answer (first option): "Security scan". Grep of target files for credentials, keys, tokens and `${VAR}` substitutions: none found.

Standard sections are auto-added in step 6, no question needed.

## Step 2: Load workflow reference

Read `references/refinement-workflow.md` (preservation gates, seven validation phases, consolidation, rollback).

## Step 3: Identify consolidation opportunities

`references/` exists, so the step runs.

| File | Lines | Topic |
|---|---|---|
| references/a.md | 5 | TODO summary format |
| references/b.md | 4 | Marker formats (TODO:, FIXME:) |

Group: one related cluster (2 files, same domain, a.md points at b.md). Flagged as a merge candidate (2 files -> 1, about 9 lines, small saving).

**AskUserQuestion:** "Should we consolidate these files? Saves N lines, improves clarity." Options: "Consolidate" / "Leave as-is". Simulated answer: "Consolidate" (per the simulated operator). This is the only consolidation ask.

## Step 4: Preservation gates

- **Gate 1 - Content Audit:** SKILL.md (13 lines: frontmatter, Quick Start; core, used every activation); references/a.md (5 lines, supplementary: summary format); references/b.md (4 lines, supplementary: marker formats). No scripts/ or assets/.
- **Gate 2 - Capability Assessment:** proposed changes are (a) consolidate a.md + b.md into one file, (b) convert intake to AskUserQuestion, (c) add `Grep` to allowed-tools, (d) remove the ref->ref directive, (e) add standard sections. None impairs execution. The consolidation merges content losslessly, so it is safe to merge; it needs deletions of a.md and b.md.
- **Gates 3 and 4:** applied at each move and deletion in step 6.

**Gate 4 (deletion of the consolidation's source files)** - AskUserQuestion: "Okay to delete references/a.md and references/b.md once their content is in the consolidated file?" Options: "Delete" / "Keep". Simulated answer: the operator DECLINES any deletion, so "Keep".

Per step 4 / Gate 4: if the operator declines deleting a consolidation's source files, the consolidation is not performed (merging without deleting only duplicates content) and is reported as declined. Result: **consolidation of a.md + b.md is declined and not performed; no consolidated file is created; a.md and b.md both stay.** No other deletion was proposed.

The ref->ref chain goal (goal 1) does not depend on the consolidation: it is met by editing a.md in place (an edit, not a deletion, so no Gate 4 needed).

## Step 5: Plan-only exit

**AskUserQuestion:** "Apply the approved scope?" Options: "Apply changes" / "Plan only" / "Stop". The request did not use plan-only wording, so the ask is shown. Simulated answer: "Apply changes". Proceed to step 6.

## Step 6: Make changes

Rollback: target is a scratch copy of the fixture; the pre-edit state is `evals/skill-refiner-interactive/fixtures/demo-skill/`. No user-space or mirror-pair concerns.

Edits, in CREATE -> LINK -> DELETE order (no create or delete needed here, so edits only):

1. `references/a.md`: replaced the imperative "Read references/b.md for the full list of marker formats." with "Marker formats are listed separately; SKILL.md's Reference Guide links that file." (removes the ref->ref directive; b.md is now reached from SKILL.md).
2. `SKILL.md` frontmatter: `description` changed to a `>-` multi-line block that states what the skill does and when to use it; `allowed-tools` changed from `Read` to `Read Grep`.
3. `SKILL.md` Quick Start: free-form intake replaced with an AskUserQuestion block (question, header, options); the prose now says "Grep the file".
4. `SKILL.md`: auto-added `## When to Use`, `## When NOT to Use`, `## Testing & Validation` (activation / non-activation phrases, quality gates), `## Reference Guide` (table linking both reference files). Step 4's Gate 3 not triggered (no moved content).
5. No deletions performed, so no Bash delete and no second permission prompt.

## Step 7: Validate result (seven phases)

- Phase 1 File inventory: before: SKILL.md (13 lines), references/a.md (5), references/b.md (4). After: SKILL.md (50), references/a.md (5), references/b.md (4). Same three files, none added or deleted.
- Phase 2 Read all: all three files load completely; nothing dropped.
- Phase 3 Frontmatter: name and description present, `>-` multi-line, no `version` field, YAML valid, `allowed-tools: Read Grep` is least privilege.
- Phase 4 Body: 50 lines, well under R13 tiers; Quick Start actionable; workflow is a simple single-path flow; no spawn anti-patterns. (design-patterns.md from skill-development not needed for a trivial skill; no load-bearing technique missing.)
- Phase 5 References: a.md and b.md both exist and are both linked from SKILL.md; one level deep; no ref->ref chains.
- Phase 6 Tools: undeclared none; unused declared none; no Bash.
- Phase 7 Testing: "summarize the TODOs in this file" triggers via description; Quick Start traced end to end.

## Step 8: Measure goals

See `goal-measurement.md`. Goals 1, 2 and 3 all PASS; no failure ask needed.

## Step 9: Trigger regression check

`description` changed, so the step applies.

**AskUserQuestion:** "The description changed. Verify trigger accuracy didn't regress before finalizing?" header "Trigger eval". Options: "Run trigger-eval check" / "Quick size check only" / "Skip". No simulated answer was given, so the first option is chosen: "Run trigger-eval check". That would invoke `Skill(skill-development)`'s description-optimization loop, which cannot be dispatched in this dry run. Recorded as not executed. Substitute inline check: the new description names the trigger phrases "list", "summarize", "triage TODO markers", matching the Testing & Validation activation phrases.

## Step 10: Compliance and reviewer passes

`Skill(plugin-rulebook)` and the `skill-reviewer` agent cannot be dispatched in this dry run. Recorded as not executed. Self-check in their place: frontmatter fields valid, `description` is `>-`, no forbidden fields, standard sections present. No rounds run, so the 3-round cap is not reached.

Change summary:

```
Lines: 13 -> 50
Frontmatter: description converted to >- multi-line with trigger context; allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: none
plugin-rulebook: not run (dry run, cannot dispatch); self-check found no FAIL
Consolidation: declined at Gate 4, not performed (operator kept every file)
```

All selected goals passed and no REQUIRED finding is open, so the completion marker applies:

```
<skill-improvement-complete>
```

(The marker is emitted on the strength of the goal measurements and the self-check; the real plugin-rulebook and skill-reviewer passes were not run.)

## Final state

`OUTDIR/target/` holds SKILL.md, references/a.md, references/b.md. Listed in `final-tree.txt`. The original fixture was not touched.
