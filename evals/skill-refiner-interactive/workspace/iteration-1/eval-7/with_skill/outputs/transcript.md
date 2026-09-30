# Transcript: skill-refiner-interactive dry run, eval-7

Skill read from the `skill-refiner-interactive` worktree copy only. Target: copy of `demo-skill` fixture at `OUTDIR/target/`.
Simulated operator answers: skill already located; select all goals; consolidate at step 3; DECLINE every deletion at Gate 4; "Apply changes" at step 5.
Simulation limits: AskUserQuestion, Skill() and Agent() cannot be called. Operator answers are simulated. The `Grep` tool was unavailable in this session, so scans were run with `grep` via Bash. This is a tooling substitute for the simulation, not something the skill allows.

## Quick Start, Step 0 (predating context)
Conversation holds only the request "Refine the skill in OUTDIR/target so it follows best practices." No skill file, problem description or discussion is predating. Escape hatch NOT offered. Continue to Step 1.

## Quick Start, Step 1 (locate)
Simulated answer: skill already located (`OUTDIR/target`). Question not needed.

## Quick Start, Step 2 (Action)
The request says "refine". I would ask: "What would you like to do with this skill?" Options: Refine / Validate. Simulated pick: **Refine**. Step 3 routes to Core Workflow: Refinement.

## Core Workflow: Refinement, step 1 (Locate, MANDATORY)
- Project search: target is `OUTDIR/target/` (no `skills/` or `.claude/skills/` mirror). Not gitignored, not in `~/.claude/plugins/cache/`, not user-space.
- Mirror-pair check (R19): only one copy exists, so it does not apply.
- Located as given. No locate questions fired.

### Step 1 pre-analysis (pre-analysis-checklist.md)
`plugin-rulebook` thresholds: the skill cannot be dispatched here. I used the checklist's fallback (flat 500-line / 10-line limits).

```
Pre-Analysis: demo-skill
Lines: 7 body lines (13 incl. frontmatter) - OK (R13, fallback flat limit)
Frontmatter issues: single-line `description` (needs `>-`)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (both cover TODO-marker handling)] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md imperatively directs "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" (free-form, no AskUserQuestion)
Argument consistency (R22): none (no $ARGUMENTS, no argument-hint)
when_to_use split candidate: no (description is 22 chars, no embedded trigger clause)
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none (Read is used via "Read references/b.md")
Dead links: none (a.md and b.md exist) / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - flag as Missing
Deferred goal candidates: reference cluster (a+b); missing goal verification
R13/R18 threshold source: skill-development fallback (plugin-rulebook not dispatchable in simulation)
```

### Step 1 goal derivation (goal-derivation.md)
Severity order: Critical = ref->ref chain, intake violation. Major = undeclared tool. Minor = cluster, missing goal verification. The top 3 become goals and the rest are deferred.

AskUserQuestion (multiSelect: true, up to 3 goals + Other; each description shows its verification):
1. "Zero reference chains" - verify: re-run chain scan over `references/*.md` -> 0 matches (source: ref->ref chain)
2. "All intake uses AskUserQuestion with options" - verify: re-run intake scan -> 0 matches (source: intake violation)
3. "Every invoked tool is declared in allowed-tools" - verify: re-run tool-scoping scan -> no undeclared tools (source: undeclared Grep)
4. Other

Simulated answer: select all 3 goals. No custom goal, so no follow-up ask. Goals recorded. Deferred: cluster, goal-verification section.

## Requirements Interview, BATCH 1
Goals selected, so Question 1 (Focus Areas) is SKIPPED. Questions 2-4 were asked about the selected goal areas. No operator answers were given for them, so I used the first option.
- Q2 "What specific problems are you seeing?" (multiSelect) -> Hard-to-follow instructions
- Q3 "What would success look like?" -> Clearer workflow
- Q4 "Any areas to exclude or preserve as-is?" (multiSelect) -> Keep validation gates (irrelevant to this skill, which has none)
Approved scope documented. Proceed to BATCH 2.

## BATCH 2 (questions conditional on findings and selected goals)
- Content Extraction: no section >=50 lines. Skipped.
- Intake Pattern (goal 2 selected): "Section 'Quick Start' collects user input without AskUserQuestion (free-form 'Ask the user which file to process'). Convert?" Options: Yes / No. Simulated (first option): **Yes**.
- Consolidation (Consolidation question): the cluster finding's goal was NOT selected (deferred), so the BATCH 2 question is skipped per the routing note. The operator's consolidate wish is handled at step 3.
- R22 argument question: no mismatch. Skipped.
- Description Split: no candidate. Skipped.
- Production Checks (asked every session; multiSelect): options Security scan / Error handling / Tool scoping / None needed. Simulated (first option): **Security scan**. Result: no credentials or `${VAR}` substitutions in the target. Clean.
Approved scope documented.

## Step 2 (Load workflow reference)
Loaded `references/refinement-workflow.md` (gates, validation phases, movement pattern).

## Step 3 (Consolidation opportunities, BEFORE changes)
Inventory of `references/`: a.md (5 lines) and b.md (5 lines), both on TODO markers. Merge flagged: 2 files -> 1.
AskUserQuestion: "Should we consolidate these files? Saves N lines, improves clarity." Options: Consolidate / Leave as-is. Simulated: **Consolidate** (operator wish). Approved to proceed to the gates. A consolidation is a merge of a.md and b.md into one file, with the second file deleted.

## Step 4 (Preservation gates, in order)
- **GATE 1 Content Audit:** SKILL.md (Quick Start, 7 lines) = core. references/a.md (5 lines: summary format + chain directive) = supplementary. references/b.md (5 lines: marker formats `TODO:`/`FIXME:`) = supplementary but referenced.
- **GATE 2 Capability Assessment:** deleting a.md or b.md would impair execution, because b.md is the only place that lists the marker formats and a.md holds the summary format. So neither can be deleted, only migrated. Fixing the chain, the intake and the tool scope does not remove any content. The Quick Start wording changes but its capability is kept.
- **GATE 3 Migration Verification:** the planned merge (b -> a) would need a.md to contain all of b.md's content before b.md is removed. Not executed, see Gate 4.
- **GATE 4 Operator Confirmation:** the deletion of references/b.md (and of a.md if the merge went the other way) needs explicit approval. AskUserQuestion: "Consolidation requires deleting one of the two reference files. Approve the deletion?" Options: Approve deletion / Keep all existing files. Simulated: **Keep all existing files** (the operator declines every deletion).
  Consequence: consolidation is NOT performed and no file is deleted. A merge that leaves both files behind would only duplicate content, which is worse than the current state, so none was made. I disclose this deviation from the operator's step-3 "consolidate" answer here in the report. The ref->ref chain goal is met a different way: both files are linked directly from SKILL.md, and the "Read references/b.md" directive is removed from a.md. No content is lost, because b.md is kept intact and stays reachable.

## Step 5 (Plan-only exit)
The request did not use plan-only wording. AskUserQuestion: "Apply the approved scope?" Options: Apply changes / Plan only (write changes.md, no edits) / Stop. Simulated: **Apply changes**. Continue to step 6. `changes.md` is not written.

## Step 6 (Make changes, CREATE -> LINK -> DELETE)
No new destination file was needed and no deletion took place. Edits, only under `OUTDIR/target`:
1. LINK: SKILL.md now points to `references/a.md` and `references/b.md` directly, so b.md has a direct link and stops being reached through a.md.
2. UPDATE: `references/a.md` lost its line "Read references/b.md for the full list of marker formats." (the ref->ref directive). The rest of a.md is unchanged. Nothing was deleted from b.md.
3. Frontmatter: `description` changed from a single-line scalar to `>-` block style. The wording is unchanged. `allowed-tools` changed from `Read` to `Read Grep` (goal 3).
4. Intake: Quick Start now uses an AskUserQuestion block with options (Current file / A file I name). The options are inferred from the observed input, which is "which file to process" (goal 2).
5. Standard sections auto-added (no approval needed): `## When to Use`, `## When NOT to Use`, `## Testing & Validation` (3 activation checks + quality gates), `## Reference Guide` (table of both files). `## Quick Start` already existed. The deferred `## Goal Verification` section was not added, since it is a deferred candidate.
No file deleted. Files created: none.

## Step 7 (Validate result, seven phases)
1. File inventory: before SKILL.md, references/a.md, references/b.md. After: same three files.
2. Read all: re-read SKILL.md (58 lines), a.md (3 lines), b.md (4 lines incl. trailing blank). No gaps. b.md unchanged.
3. Frontmatter: `name` and `description` present, no forbidden fields.
4. Body: 58 lines is well under R13. The 80% rule holds (nothing moved). Workflow pattern is linear. No spawn anti-patterns.
5. References: both linked files exist, one level deep, no ref->ref chain.
6. Tools: body uses Read and Grep (plus AskUserQuestion, which is always callable). `allowed-tools: Read Grep` covers them. No unused declared tools.
7. Testing: activation phrases are in the new Testing & Validation section.

## Step 8 (Measure goals)
See `goal-measurement.md`. All 3 goals PASS. No FAIL ask was needed.

## Step 9 (Trigger regression check)
The `description` and `when_to_use` WORDING did not change, only the YAML scalar style. `description` is still "Helps with demo tasks." and no trigger phrase was altered, so a trigger-accuracy regression is not possible. This step is SKIPPED, with that stated reason. Had the ask fired, I would have chosen "Quick size check only": 22 characters, unchanged.

## Step 10 (Compliance and reviewer passes)
`Skill(plugin-rulebook)` and the `skill-reviewer` agent cannot be dispatched in this simulation. Neither was run. Standing requirement not met here: a real run must call both on the final state and fix any FAIL and Critical/Major findings. Without them the completion marker is NOT emitted in this simulation.

Change summary:
```
Lines: 13 -> 58 (SKILL.md; standard sections and the AskUserQuestion block were added)
Frontmatter: description converted to >-; allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: none (operator declined all deletions at Gate 4)
plugin-rulebook: not run (simulation limit)
Goals: 3/3 PASS
Consolidation of a.md + b.md: NOT done (declined at Gate 4); cluster remains a deferred candidate
```
`<skill-improvement-complete>` withheld: plugin-rulebook and skill-reviewer were not run.

## Final state
`final-tree.txt` lists the files under `OUTDIR/target`.
The original fixture was not modified.
