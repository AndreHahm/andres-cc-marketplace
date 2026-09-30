# Dry-run transcript: skill-refiner-interactive, eval 12

Simulated operator context: the operator pasted the skill's SKILL.md (taken as OUTDIR/target/SKILL.md) and said "the intake is sloppy and a tool isn't declared", then "Refine it." No edits are made anywhere.

## Quick Start A: detect predating context (escape hatch)

Predating context exists: a skill file was pasted and a problem was described ("intake is sloppy", "a tool isn't declared"). The escape hatch is offered.

AskUserQuestion (simulated):
- question: "I've reviewed the context you provided. How would you like to proceed?"
- header: "Interview"
- options: "Infer from context" / "Define explicitly"
- simulated answer: **Infer from context**

Effect: BATCH 1 will be skipped. Each need the context states that pre-analysis cannot detect is offered at goal selection as a candidate goal. This question is routing only, not an interview question.

## Quick Start B: ask which skill

Skipped: the request already names the skill (the pasted skill, located at OUTDIR/target).

## Quick Start C: Refine vs Validate

Skipped: the request already says refine ("Refine it.").

## Quick Start D: route

"Refine" selected, so go to Core Workflow: Refinement, step 1.

## Refinement step 1: locate the skill

- Location given by the operator: OUTDIR/target (evals/skill-refiner-interactive/workspace/iteration-12/eval-12/with_skill/outputs/target). No Glob search was needed.
- Gitignore-exclusion check: `git check-ignore -v` reports this path is matched by the operator's global gitignore (`target/`). That is a side effect of the simulation directory name. The operator's instruction that the skill is at this path overrides the exclusion, so it is treated as the real target. Noted, not acted on.
- Mirror-pair check (R19): no `.claude/skills/demo-skill/` exists (checked with ls), so there is only one copy and no mirror question.
- User-space / cache / not-found branches: not applicable.

### Pre-analysis (references/pre-analysis-checklist.md, all checks run)

plugin-rulebook found at plugins/plugin-devkit/skills/plugin-rulebook/. Settings read: R13 tiers weak 100 / soft 300 / warning 490 / critical 500; R18 tiers 10 / 20 / 30; R21 description min 80 (warning below 80, critical below 20), max 1024, when_to_use max 512, combined min 80, max 1536; R8 threshold 80 characters.

Check-by-check results:
1. Rulebook thresholds: loaded from settings.json.
2. SKILL.md length: 13 lines including frontmatter, OK (under the 100-line weak-warning tier).
3. Frontmatter: no `version` or other non-standard field. `description` is single-line but only 22 characters, under R8's 80-character block-scalar threshold, so no R8 issue. `allowed-tools: Read` fine. No `when_to_use`.
4. Sections of 50 lines or more: none.
5. Reference files: 2 (a.md 5 lines, b.md 4 lines). Cluster: a.md and b.md both cover TODO/marker details, so they are one topical cluster. None at 400 lines or more.
6. Workflow files: none. Reference-to-reference chain: references/a.md line 5 says "Read references/b.md for the full list of marker formats", an imperative directive, so this is a ref->ref chain violation.
7. Spawn anti-patterns: none.
8. Intake scan: SKILL.md line 11 "Ask the user which file to process" matches `ask the user`. The input is a file path, which is unbounded and has no predictable small option set, so per the checklist (and Pattern 4 in ask-user-question-patterns.md) plain text is correct and it is NOT flagged as an intake violation. No free-form `questions:` block.
9. R22: body has no `$ARGUMENTS`, `$0`/`$1` or named placeholders; frontmatter has no argument-hint/arguments. Consistent.
10. `when_to_use` split candidate: no `Use when` clause in description, so no.
11. Description size (R21): description is 22 characters, below the 80-character floor (warning tier; above the critical floor of 20). No `when_to_use`. Combined 22, below the combined floor of 80.
12. Tool scoping: body instructs "grep the file for TODO markers", which is an actual Grep invocation, and `Grep` is not declared in `allowed-tools: Read` -> undeclared tool, Major (R6). `Read` is declared and used. Unused declared: none.
13. Dead links: references/a.md and references/b.md both exist; none dead. Cross-skill references: none.
14. Missing standard sections: Quick Start is present; `## When to Use`, `## When NOT to Use`, `## Testing & Validation`, `## Reference Guide` are missing (4 of 5). Minor, auto-addable in step 6.
15. Goal verification: no `## Goal Verification` section -> absent, optional low-priority candidate.

Pre-analysis report:

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: none (description is single-line but under R8's 80-char threshold)
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details)] [oversize ≥400 lines: none]
Workflow files: 0 [oversize ≥300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md -> references/b.md ("Read references/b.md ...")
Spawn anti-patterns: none
Intake pattern violations: none flagged (SKILL.md line 11 "Ask the user which file to process" collects an unbounded file path, so plain text is exempt)
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): finding — description is 22 chars, below the 80-char floor (warning tier)
Tool scoping (R6): undeclared: Grep (Major) / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: Description size (R21) [displaced by the context-stated intake need], reference cluster a.md + b.md, missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation and selection (references/goal-derivation.md)

Derived candidates by priority: (1st) ref->ref chain; (2nd) undeclared tool Grep, description size outside R21; (3rd) reference cluster, missing goal verification. Cap is 3.

Escape hatch was "Infer from context", so context-stated needs that pre-analysis cannot detect are also offered. Context states "the intake is sloppy": pre-analysis exempted it, so it cannot detect it. It is offered as a candidate custom goal with a proposed verification the operator can confirm. It counts toward the cap of 3 and takes the lowest-priority slot, displacing the lowest-priority derived candidate (description size) to the deferred list. "A tool isn't declared" is already backed by the derived undeclared-tool finding, so it is not duplicated.

AskUserQuestion (simulated):
- question: "Which goals should this refinement aim for? (select up to 3)"
- header: "Goals"
- multiSelect: true
- options (description shows each verification check):
  1. "Zero reference chains": `Grep` references/*.md for imperative directives to read another references/ file -> 0 matches. (source: ref->ref finding)
  2. "Declare every invoked tool": re-run the tool-scoping scan -> no undeclared tools (Grep declared). (source: undeclared-tool finding)
  3. "Intake via AskUserQuestion": `Grep` the Quick Start intake step for AskUserQuestion with options, or for an explicit note that the file path is plain-text open-ended input -> present. (source: operator context "intake is sloppy", custom goal, verification proposed and agreed)
  - "Other": custom goal
- simulated answer: all three selected.

Custom-goal rule check: goal 3 has a verification check, so it is accepted (no follow-up ask needed). Selected goals recorded: G1 chain, G2 tool declaration, G3 intake. Step 8 would measure them; it is not reached (see step 5).

## Requirements Interview

Routing ("Infer from context"): BATCH 1 is skipped entirely (Questions 1-4 not asked). Come straight to BATCH 2.

### BATCH 2: Implementation Details

Triggers detected in pre-analysis:
- Extraction (large low-frequency section): not detected, not asked.
- Intake: not detected (unbounded file-path input exempt), not asked. No goal-mapped finding exists for it, but the question's trigger is a pre-analysis detection, so it is not asked. The G3 goal still stands as an operator-chosen goal.
- Arguments (R22): not detected, not asked.
- Desc split: not detected, not asked.
- Reference clusters: not asked here; step 3 is the single consolidation ask.
- Prod checks: asked in every refinement session.

AskUserQuestion (simulated), Prod checks (only BATCH 2 question asked):
- question: "Which production checks should I run?"
- header: "Prod checks"
- multiSelect: true
- options: "Security scan" / "Error handling" / "Tool scoping" / "None needed"
- simulated answer: no "Yes" option exists on this question (the operator's "choose Yes" instruction covers only Yes/No questions), so the default rule applies: first option, **Security scan**.

Approved scope documented: goals G1-G3; Prod check: Security scan; no exclusions (BATCH 1 skipped).

## Refinement step 2: load workflow reference

Read references/refinement-workflow.md (preservation gates, validation phases, rollback).

## Refinement step 3: consolidation opportunities

The target has a references/ directory, so the step runs.
- Files: references/a.md 5 lines, references/b.md 4 lines (9 lines total).
- Grouping: both describe the TODO/FIXME marker summary (a.md "Details", b.md "Marker Formats") -> one topic; flag as a merge candidate (2 files -> 1).

AskUserQuestion (simulated):
- question: "Should we consolidate these files? Saves ~3 lines (9 -> ~6 after merging headings), improves clarity and removes the a.md -> b.md chain."
- header: "Consolidate"
- options: "Consolidate" / "Leave as-is"
- simulated answer: none specified, so first option: **Consolidate**. Proceed.

## Refinement step 4: preservation gates (Gates 1 and 2 run here)

GATE 1, Content Audit:
- SKILL.md: frontmatter (5 lines), title, Quick Start (intake + grep + pointer to a.md). Core (80%+): all of it, 13 lines.
- references/a.md: 5 lines, "Details": summaries list each TODO with line number; points to b.md. Core for the summarise step (supplementary detail), kept.
- references/b.md: 4 lines, "Marker Formats": TODO:/FIXME: formats. Supplementary (<20%).
- No scripts/ or assets/.
Gate 1 check complete.

GATE 2, Capability Assessment:
- Consolidate a.md + b.md into one file: does it impair execution? No, all content is preserved and the a.md->b.md chain disappears. SAFE to consolidate (migrate, source deletion only after Gate 4 approval).
- Declare Grep in allowed-tools: does not impair execution, it enables it.
- Convert/document intake: does not impair execution.
Gate 2 check complete. Gates 3 and 4 apply during step 6 (not reached).

## Refinement step 5: plan-only exit / apply ask

The request did not use plan-only wording, so the ask is required.

AskUserQuestion (simulated):
- question: "Apply the approved scope to the skill?"
- header: "Apply"
- options: "Apply changes" / "Plan only" (write changes.md, no edits) / "Stop"
- simulated answer: **Stop**

Result: the operator stopped. The Gate 4 early ask about consolidation source files (only asked once the operator chooses to apply changes) is NOT asked. Step 6 (changes), step 7 (validation phases), step 8 (goal measurement), step 9 (trigger regression), step 10 (plugin-rulebook, skill-reviewer, change summary) are not run because the session ended at step 5. No changes.md is written (that is Plan-only, not Stop). `<skill-improvement-complete>` is NOT emitted (no goals measured, no checks run).

## Final state

No file in OUTDIR/target was modified (byte-identical to the fixture copy). Files produced: transcript.md, final-tree.txt, and the untouched copy of the fixture under target/.
