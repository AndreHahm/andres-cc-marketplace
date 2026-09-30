# Dry-run transcript: skill-refiner-interactive (plan-only request)

Operator request: "Analyze the skill in OUTDIR/target and just write a changes.md, do not apply anything."
Skill files read from the worktree copy only. Target = copy of fixture `demo-skill` in `OUTDIR/target/` (original fixture untouched). Steps below are labeled with the SKILL.md numbering. "SIM" marks a simulated operator answer.

## Quick Start — Step 0: Detect Predating Context
- The conversation contains a path to the skill but no skill file contents, no problem description, no active discussion of the skill. Treated as NO predating context (a bare path is not "skill file or code provided" / "problem described"). No escape-hatch question asked. Continue to Step 1.

## Quick Start — Step 1 (AskUserQuestion, open-form)
- Q: "What skill do you want to work on?"
- SIM answer: skill is already located (`OUTDIR/target`).

## Quick Start — Step 2 (AskUserQuestion)
- Q: "What would you like to do with this skill?" Header: Action. Options: [Refine] [Validate]
- SIM answer: no answer given for this one; the operator's request ("analyze ... write a changes.md") is refinement/plan work, and first option is Refine. -> **Refine**.

## Quick Start — Step 3: route
- "Refine" -> Core Workflow: Refinement. (Validation workflow not run.)

## Core Workflow: Refinement — step 1 "Locate the skill"
- Target given by operator: `OUTDIR/target/` (SKILL.md + references/a.md, b.md).
- Gitignore-exclusion check: target is not under `.temp/`, `.draft/`, `.backup/` (the path is the eval workspace). (Did not need to open gitignore-exclusion.md; the path is an explicit operator-supplied location.)
- Mirror-pair check (R19): no `skills/<name>/` + `.claude/skills/<name>/` pair exists for this target -> single logical skill; no divergence question asked.
- User-space / cache checks: not applicable (not found via search; operator supplied it). No AskUserQuestion for "Where should I find this skill?" (SIM: already located).

### Step 1 — Pre-analysis (references/pre-analysis-checklist.md, every check)
- R13/R18 thresholds: plugin-rulebook found at `plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json`. Body is ~8 lines, far below every tier -> OK.
- Frontmatter: `description: Helps with demo tasks.` is single-line, not `>-` (flagged per checklist). No `version`. `allowed-tools: Read` fine.
- Sections >= 50 lines: none.
- Reference files: 2 (a.md 5 lines, b.md 4 lines); related cluster (both cover TODO/marker summaries); none >= 400.
- workflows/: none.
- Ref->ref chain: `references/a.md` line 5: "Read references/b.md for the full list of marker formats." -> VIOLATION.
- Spawn anti-patterns: none.
- Intake: SKILL.md line 11 "Ask the user which file to process." with no AskUserQuestion -> VIOLATION.
- R22: body uses no `$ARGUMENTS`/`$N`; frontmatter declares none -> none.
- when_to_use split: no `when_to_use`, description is 25 chars, no embedded trigger clause -> no.
- Tool scoping: body line 11 "grep the file for TODO markers" invokes Grep; not in `allowed-tools: Read` -> undeclared (Major, R6). `AskUserQuestion` excluded by rule. Unused declared: none (Read is used by the ref read instruction).
- Dead links: `references/a.md` and `b.md` both exist -> none. Cross-skill refs: none.
- Missing standard sections: present = Quick Start. Missing = When to Use, When NOT to Use, Testing & Validation, Reference Guide.
- Goal verification: absent.

Pre-analysis report emitted:
```
Pre-Analysis: demo-skill
Lines: 8 body (13 total) - OK (R13)
Frontmatter issues: description is single-line (not >-); no when_to_use
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker formats)] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md:5 -> references/b.md
Spawn anti-patterns: none
Intake pattern violations: Quick Start (line 11) - asks the user for a file with no AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): Grep (used line 11, not declared) / none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: reference cluster a.md+b.md; missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1 — Derive and select goals (references/goal-derivation.md)
Selection by severity, max 3: Critical (chain, intake) then Major (undeclared tool) fills 3. Deferred: cluster (Minor), missing goal verification (Minor).

AskUserQuestion (multiSelect: true):
- Q: "Select the goals for this session (each shows its verification)"
- Options:
  1. "Zero reference->reference chains" - verify: re-run checklist chain scan over references/*.md -> 0 matches
  2. "All intake uses AskUserQuestion with options" - verify: re-run checklist intake scan -> 0 matches
  3. "Every invoked tool is declared in allowed-tools" - verify: re-run checklist tool-scoping scan -> no undeclared tools
  (+ Other)
- SIM answer: select all goals offered -> G1, G2, G3.

## Requirements Interview — BATCH 1 (goals selected)
- Question 1 (Focus Areas): SKIPPED — goals already set the scope (per "If goals were selected").
- Question 2 "What specific problems are you seeing?" options [Hard-to-follow instructions][Scattered references][Nested sections]. No SIM answer given -> first option: Hard-to-follow instructions.
- Question 3 "What would success look like?" options [Clearer workflow][Lower token cost][Production-ready]. SIM default -> Clearer workflow.
- Question 4 "Any areas to exclude or preserve as-is?" options [Keep validation gates][Keep tool scoping][Nothing to exclude]. SIM default -> first option, Keep validation gates. (Note: this demo skill has no validation gates, so it has no effect. Keep tool scoping was NOT chosen, so G3 (add Grep to allowed-tools) stays in scope.)
- Approved scope documented: G1, G2, G3 + the answers above.

## BATCH 2 — Implementation Details (conditional on findings AND selected goals)
Routing: "Define explicitly" path (no escape hatch was offered in Step 0, so full BATCH 1 + BATCH 2).
- Large low-frequency section extraction: no such finding -> skipped.
- Intake pattern violation (goal G2 selected): ASKED.
  Q: "Section 'Quick Start' collects user input without AskUserQuestion (asks the user which file to process). Convert to structured AskUserQuestion with options?" Header: Intake Pattern. Options [Yes][No]. SIM default -> Yes.
- Related reference cluster consolidation: SKIPPED here — its finding's goal was deferred (not selected), and BATCH 2 says to skip a question tied to a finding whose goal wasn't selected. (Step 3 below still asks the consolidation question by its own unconditional text; see observation at end.)
- R22 mismatch: no finding -> skipped.
- when_to_use split: no finding -> skipped.
- Production hardening (asked every session): ASKED.
  Q: "Which production checks should I run?" multiSelect. Options [Security scan][Error handling][Tool scoping][None needed]. SIM default -> Security scan.
- Standard sections note: auto-added in step 6 (no question) — step 6 is not reached in a plan-only run.
- Approved scope documented; proceed.

## Step 2: Load workflow reference
- Read `references/refinement-workflow.md` headings/gates (Preservation Gates 1-4, consolidation strategy, validation phases).

## Step 3: Identify consolidation opportunities (BEFORE changes)
- references/: a.md (5 lines), b.md (4 lines). Same topic (TODO marker summaries) -> flag merge of 2 files into 1; saves ~1 file and removes the chain.
- AskUserQuestion: "Should we consolidate these files? Saves 1 file, improves clarity." Options [Consolidate][Leave as-is]. SIM default -> Consolidate.

## Step 4: Preservation gates (four, in order)
- Gate 1 Content Audit: a.md = "Summaries list each TODO with its line number" (core, read every activation via SKILL.md line 13) + pointer; b.md = two marker formats (TODO:, FIXME:) (core). All of it is preserved, nothing supplementary to drop.
- Gate 2 Capability Assessment: inlining b.md's two bullets into a.md loses nothing; removing the pointer line removes a chain only. No capability impaired -> deletion of b.md allowed after migration.
- Gate 3 Migration Verification: destination a.md (updated first) must contain both bullets before b.md is removed; no other file links b.md (SKILL.md links only a.md). Verified by reading; will be a verification step in changes.md.
- Gate 4 Operator Confirmation (deletion of references/b.md): AskUserQuestion "Delete references/b.md after its content is merged into a.md?" Options [Approve][Keep file]. SIM default -> Approve. (Migration itself auto-approved.)

## Step 5: Plan-only exit
- Request already used plan-only wording ("just write a changes.md, do not apply anything") -> the "Apply changes / Plan only / Stop" ask is SKIPPED per the step's skip-rule. Prior BATCH/Gate 4 approvals count as approval of the findings; only the draft path needs confirming.
- Step 6 NOT run (no edits). Step 8 (measure goals) NOT run (no edits). Steps 7, 9, 10 not reached — the plan-only branch says "write ... and stop".
- Draft path AskUserQuestion (per changes-draft-format.md "Draft Location"): Q: "Where should changes.md be written?" Options ["Default: .draft/_open/<plugin>/<skill>/changes.md"] [Other]. SIM answer: `OUTDIR/changes.md`.
- Existing draft at that path? Checked: none -> nothing to merge/overwrite.
- Approval-before-writing: findings included = approved only. Final approved set: F1 (chain), F2 (intake), F3 (undeclared Grep), O1 (merge/delete b.md). Not included (not approved / not asked): frontmatter `>-` style note, missing standard sections (auto-added in the apply session's step 6), missing goal verification (deferred candidate) — they appear only in the complete pre-analysis report.
- Wrote `OUTDIR/changes.md` per references/changes-draft-format.md. Ended the run ("stop").

## Verification of constraints
- Target skill copy in OUTDIR/target was NOT edited (byte-identical to fixture); original fixture unmodified; no file outside OUTDIR changed.
- No `<skill-improvement-complete>` marker emitted (plan-only run; step 10 not reached).

## Observations on the skill (for the eval reviewer)
1. BATCH 2 skips the consolidation question when its goal is deferred, but step 3 asks the same consolidation question unconditionally. The two rules disagree on whether a deferred-goal finding gets asked; I followed both literally (skip in BATCH 2, ask in step 3).
2. Plan-only wording check worked: the "Apply/Plan only/Stop" ask was skipped, only the path was asked.
3. BATCH 1 Q4 first option ("Keep validation gates") is generic and irrelevant to a skill without gates.
4. The changes-draft-format "Fixes before optimizations" ordering and "dependency order" can conflict (O1 depends on F1 here; happens to be consistent).
