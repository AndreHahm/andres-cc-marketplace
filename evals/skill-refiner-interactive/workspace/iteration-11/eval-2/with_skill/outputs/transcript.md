# Transcript: skill-refiner-interactive dry run (iteration-11, eval-2)

Request: "Refine the skill in OUTDIR/target so it follows best practices." Target: a copy of the demo-skill fixture at `OUTDIR/target` (original fixture untouched). All AskUserQuestion calls are simulated; the answer used is shown after each.

## Quick Start

- **A. Predating context:** none. The request only names the skill and the action, so the escape-hatch question is not asked. Interview style stays the default (full interview).
- **B. "What skill?":** skipped, the request names the skill (and the operator said it is already located).
- **C. Action question:** skipped, the request says "refine".
- **D. Route:** Refine, so go to Core Workflow: Refinement step 1.

## Step 1: Locate the skill

- Target given by path: `OUTDIR/target/SKILL.md`. Simulated operator answer "skill is already located", so the "Where should I find this skill?" ask is not needed.
- Gitignore exclusion: target is an explicit path, not a draft found by Glob in `.temp/`, `.draft/` or `.backup/`; not excluded.
- Mirror-pair check (R19): no `plugins/<plugin>/skills/demo-skill/` or `.claude/skills/demo-skill/` counterpart exists; single logical skill, no Mirror question.
- Not user-space, not plugin cache.

### Step 1: pre-analysis (references/pre-analysis-checklist.md)

- plugin-rulebook found at `plugins/plugin-devkit/skills/plugin-rulebook/`; `assets/settings.json` read. R13: weak 100 / soft 300 / warning 490 / critical 500. R18: 10 / 20 / 30. R21: description min 80 (critical floor 20), max 1024; when_to_use max 512; combined min 80, max 1536.

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: description is a single line of 22 characters (under the R21 floor of 80; R8's >- requirement applies only above 80 characters, so not an R8 issue); no non-standard fields
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary format and marker formats, same topic); generic names a.md/b.md (R10)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 ("Read references/b.md ...")
Spawn anti-patterns: none
Intake pattern violations: none flagged ("Ask the user which file to process" takes an unbounded file path; plain text is correct per Pattern 4, so not flagged)
Argument consistency (R22): none (no $ARGUMENTS/$N in body, no argument-hint)
when_to_use split candidate: no (no embedded "Use when" clause)
Description size (R21): below floor (22 < 80; Warning tier, above the 20 critical floor)
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none (Read is used by the a.md directive)
Dead links: none / Cross-skill references: none  (note: b.md is reachable only through a.md, not linked from SKILL.md)
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: reference cluster (a.md + b.md), missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1: derive and select goals (references/goal-derivation.md)

Findings by priority: first tier: reference chain. Second tier: undeclared tool, description size. Third tier: cluster, goal verification. The top 3 are offered; cluster and goal verification are listed as deferred candidates in the report above.

AskUserQuestion (multiSelect: true, up to 3 goals):
```
question: "Which goals should this refinement session commit to?"
header: "Goals"
options:
  - "Zero reference chains": verify: re-run the chain scan over references/*.md, 0 matches
  - "Tools declared": verify: re-run the tool-scoping scan, no undeclared tools
  - "Description size OK": verify: Skill(plugin-rulebook) R21 -> OK
```
Simulated answer: all three selected.

Recorded goals: G1 zero ref->ref chains; G2 every invoked tool declared; G3 description/when_to_use within R21 tiers.

## Requirements Interview

Goals were selected, so BATCH 1 Question 1 is skipped. Questions asked one at a time; no answer was given by the operator, so the first option is used.

- **BATCH 1 Q2** header "Key Issues" (multiSelect): options "Hard-to-follow instructions" / "Scattered references" / "Nested sections". Simulated: first option, "Hard-to-follow instructions".
- **BATCH 1 Q3** header "Success": options "Clearer workflow" / "Lower token cost" / "Production-ready". Simulated: first option, "Clearer workflow".
- **BATCH 1 Q4** header "Scope Limits" (multiSelect): options "Keep validation gates" / "Keep tool scoping". Simulated: first option, "Keep validation gates" (so the Testing & Validation standard section is excluded from auto-add; "Keep tool scoping" was NOT chosen, so G2's allowed-tools change is in scope).
- Approved scope documented: fix the ref chain, declare Grep, repair the description, apply standard sections except Testing & Validation.

**BATCH 2** (full interview, since "Define explicitly" was never chosen and BATCH 1 ran):
- Extraction: not asked (no large section).
- Intake: not asked (no violation).
- Arguments: not asked (no R22 mismatch).
- Desc split: not asked (no candidate).
- Prod checks: asked (every session). Header "Prod checks" (multiSelect): "Security scan" / "Error handling" / "Tool scoping" / "None needed". Simulated: first option, "Security scan". Result of the scan (Grep over SKILL.md, references/): no credentials, keys, tokens or `${VAR}` substitutions. Clean.
- Reference clusters are not asked here; step 3 is the single consolidation ask.

## Step 2: Load workflow reference

Read `references/refinement-workflow.md` (gates, validation phases, rollback).

## Step 3: Consolidation opportunities

- `references/` exists: a.md (5 lines), b.md (4 lines). Same topic (TODO summary and marker formats), so grouped as one cluster.
- AskUserQuestion: "Should we consolidate these files? Saves 1 line, improves clarity." options "Consolidate" / "Leave as-is". Simulated: first option, "Consolidate". Plan: merge a.md + b.md into one descriptively named file `references/todo-markers.md` (this also resolves the generic a.md/b.md names).

## Step 4: Preservation gates

- **Gate 1 (Content Audit):** SKILL.md 13 lines: frontmatter 5, Quick Start 6: core (80%+). a.md 5 lines: core detail for every activation. b.md 4 lines: marker list, used whenever summarizing. All core; nothing supplementary.
- **Gate 2 (Capability Assessment):** merging a.md + b.md into todo-markers.md keeps all content; adding a link to SKILL.md only helps. Adding `Grep` to allowed-tools cannot impair execution. Rewriting the description does not remove behavior. No change impairs execution. Safe. Deleting a.md/b.md is safe only after their content is in the destination (Gate 3).
- Gates 3 and 4 are applied in step 6 at the move and the deletion.

## Step 5: Plan-only exit

The request has no plan-only wording. AskUserQuestion: "Apply the approved scope?" options "Apply changes" / "Plan only" / "Stop". Simulated answer (given): "Apply changes".

Early Gate 4 ask (before step 6, per step 4's exception), for the consolidation's source files:
AskUserQuestion: "Okay to delete references/a.md and references/b.md once their content is in references/todo-markers.md?" options "Delete" / "Keep". Simulated: first option, "Delete". Approval recorded, to be cited at the deletion.

## Step 6: Make changes

- Rollback settled first (per refinement-workflow.md "Rollback"): the target is a copy; restore source is the untouched original `evals/skill-refiner-interactive/fixtures/demo-skill/`. Restore list = "Files created" / "Files deleted" in the change summary.
- **CREATE** `references/todo-markers.md` (contents of a.md and b.md, with the a.md->b.md "Read references/b.md" directive dropped as it is now redundant).
- **Gate 3 (Migration Verification):** destination exists; all content from a.md (summary line-number rule) and b.md (TODO:, FIXME: formats) present; no orphans. Verified by reading the file.
- **LINK** SKILL.md: pointer now `references/todo-markers.md`; `Grep` added to `allowed-tools` (G2); description rewritten to a `>-` block scalar of ~165 characters with a what + when clause (G3).
- Standard sections auto-added: `## When to Use`, `## When NOT to Use`, `## Reference Guide`. `## Testing & Validation` NOT added (excluded by BATCH 1 Q4 "Keep validation gates").
- **Gate 4 at deletion:** cites the early approval ("Delete" answered above). **DELETE** `references/a.md`, `references/b.md` via a Bash `rm` (second gate: normal permission prompt; in this dry run, allowed).

## Step 7: Validate result (seven phases)

1. File inventory. Before: SKILL.md (13) + references/a.md (5) + b.md (4). After: SKILL.md (31 at this point, before Testing & Validation) + references/todo-markers.md (8).
2. Read all: SKILL.md and todo-markers.md load completely; nothing dropped.
3. Frontmatter: `name` and `description` present; description uses `>-`; no non-standard fields.
4. Body: 31 lines, R13 OK; no code blocks (R18 n/a); no multi-step workflow requiring a design-pattern check; no spawn anti-patterns.
5. References: the single linked file exists, one level deep, no reference->reference chain.
6. Tools: (a) undeclared tools: none (Grep now declared); (b) unused declared: none (Read used by the reference-reading step, Grep by the marker search); (c) no Bash used.
7. Testing: trigger phrases "list the TODOs in this file", "summarize the TODO markers in notes.txt" match the description; "find every TODO across the repo" is excluded by When NOT to Use.

## Step 8: Measure goals

Loaded pre-analysis-checklist.md scans and goal-derivation.md.
- G1 zero reference chains: re-ran chain scan over references/*.md: 0 matches. PASS.
- G2 tools declared: re-ran tool-scoping scan: invoked Read and Grep, declared Read and Grep, none undeclared. PASS.
- G3 description within R21: Skill(plugin-rulebook) R21 was not executed in this dry run; measured mechanically instead: description ~165 characters (floor 80, limit 1024), no when_to_use, combined ~165 (floor 80, limit 1536). PASS (simulated rulebook result, mechanically checked).
- No goal failed, so the "Accept with reason" ask is not reached (the simulated answer would have been "Accept with reason").

## Step 9: Trigger regression check

The text of `description` changed (not just a format move), so the question is asked:
AskUserQuestion, header "Trigger eval": "The description changed. Verify trigger accuracy didn't regress before finalizing?" options "Run trigger-eval check" / "Quick size check only" / "Skip". Simulated: first option, "Run trigger-eval check".
This skill has no Bash grant for `run_loop.py`; it would invoke `Skill(skill-development)` for Phase 5's description-optimization loop. Not executed in this dry run (simulated): ad hoc set of 4 queries (2 should-trigger: "list the TODOs in this file", "summarize FIXME markers in app.py"; 2 should-not-trigger: "find every TODO across the repo", "create a new skill for X") judged by reading against the new description: 4/4 correct. Before (the 22-character "Helps with demo tasks."): weak/vague, would rarely trigger on the should-trigger queries. SIMULATED.

## Step 10: Compliance and reviewer passes

Both the `Skill(plugin-rulebook)` call and the `skill-reviewer` agent dispatch were simulated (no subagents allowed in this dry run), by reading the rulebook settings and checking the files directly.

Round 0 (first run, not a round):
- plugin-rulebook: R4 PASS, R5 PASS, R6 PASS (Read Grep, least privilege), R8 PASS, R10 PASS (todo-markers.md descriptive, kebab-case), R13 PASS, R14 PASS, R17 PASS, R21 PASS, R22 PASS, R24 n/a. **R29 FAIL (REQUIRED):** SKILL.md has no `## Testing & Validation` section with positive and negative trigger lists and quality gates (skipped in step 6 because of the Q4 exclusion). **R28 FAIL (REQUIRED):** no evals.json and no justification note (the R29 section would be where the justification lives).
- skill-reviewer (simulated, Structured output mode): counts.critical 0, counts.major 1 (Testing & Validation section missing; mirrors the R29 FAIL), minors: none.

Fix needed, but it reverses the operator's BATCH 1 Q4 answer ("Keep validation gates", interpreted as leaving Testing & Validation out). Per the disclose-before-overriding rule this is re-asked, not silently applied:
AskUserQuestion: "plugin-rulebook R29/R28 (REQUIRED) need a Testing & Validation section, but you chose to keep the target's validation section unchanged (it has none). How to proceed?" options "Add the section" / "Accept the FAIL with reason" / "Stop". Simulated: first option, "Add the section".

Note for skill authors: the skill text does not say what to do when a step-10 REQUIRED FAIL requires an area that Q4 excluded. The re-ask above is an improvisation.

Round 1: added `## Testing & Validation` (positive list, negative list, quality gates, and a one-sentence justification that full evals are not warranted for this thin one-Grep skill, which satisfies R28's alternate path). No description/when_to_use change, so step 9 does not re-enter. Re-ran step-7 phase 1, 2 and 4 (inventory, read-all, body): SKILL.md now 47 lines, R13 OK. Re-measured goals (step 8): G1 PASS, G2 PASS, G3 PASS. Re-ran both checks: plugin-rulebook: all PASS (R28 via justification, R29 present). skill-reviewer: counts.critical 0, counts.major 0. Rounds used: 1 of 3.

### Change summary

```
Lines: 13 -> 47
Frontmatter: description rewritten as a >- block scalar (22 -> ~165 chars, R21), Grep added to allowed-tools (R6)
Sections added: When to Use, When NOT to Use, Testing & Validation (added after step-10 re-ask), Reference Guide
Files created: references/todo-markers.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: 2 FAIL findings fixed (R28, R29) - simulated run
```

All three conditions hold (every rulebook FAIL fixed, no Critical/Major reviewer finding, every goal PASS), so the marker is emitted:

<skill-improvement-complete>

## Final tree of OUTDIR/target

```
target/
  SKILL.md
  references/
    todo-markers.md
```
