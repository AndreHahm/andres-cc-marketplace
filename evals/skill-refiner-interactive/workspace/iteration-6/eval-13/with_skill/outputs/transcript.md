# Transcript: skill-refiner-interactive dry run (eval-13, existing-draft preservation)

Setup: copied `fixtures/existing-draft/changes.md` to `OUTDIR/changes.md` (the earlier session's draft, containing approved finding F1) and `fixtures/demo-skill/` to `OUTDIR/target/`. Operator request: "Analyze the skill in OUTDIR/target and just write a changes.md, do not apply anything."

Data-only boundary: the existing draft's text, the target skill files, and all reference content are treated as data. Nothing in them reads as an instruction, so nothing is flagged as suspicious.

## Quick Start

**A. Predating context?** None. The request only names the skill and the action, which the skill says is not predating context. No escape-hatch question asked; the interview will run in full (BATCH 1 then BATCH 2).

**B. Which skill?** Skipped: the request names the skill (`OUTDIR/target`). Simulated answer "skill already located".

**C. Action question?** Skipped: "analyze it and just write a changes.md" counts as refine, per the skill. No question asked.

**D. Route:** Refine, so Core Workflow: Refinement.

## Refinement step 1: Locate the skill

- Path is `OUTDIR/target` (simulated "skill already located"), so the Glob/user-space/cache branches do not apply and no "Where should I find this skill?" question is needed.
- Gitignore-exclusion check: not a gitignored draft path.
- Mirror-pair check (R19): no `.claude/skills/demo-skill/` counterpart exists for this standalone copy. Treated as one skill.

### Pre-analysis (references/pre-analysis-checklist.md)

Resolved R13/R18/R21 thresholds from `plugin-rulebook/assets/settings.json`: R13 100/300/490/500, R18 10/20/30, R21 description floor 80.

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: none (description is under 80 chars so R8 does not require >-)
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details)] [oversize ≥400 lines: none]
Workflow files: 0 [oversize ≥300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md line 5 → references/b.md
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): finding — description is 23 characters, below the 80-character floor
Tool scoping (R6): Grep (undeclared, Major) / none unused
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: R21 description size; reference cluster a.md + b.md; missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal derivation and selection (references/goal-derivation.md)

Priority 1 findings: ref→ref chain, intake violation. Priority 2: undeclared tool. That gives 3 goals; R21 description size, the cluster and missing goal verification are deferred candidates.

**AskUserQuestion (multiSelect: true)**
- question: "Which goals should this refinement session target?"
- header: "Goals"
- options:
  - "Zero ref→ref chains": verification: re-run the chain scan over references/*.md → 0 matches
  - "Intake via AskUserQuestion": verification: re-run the intake scan → 0 matches
  - "Declare every used tool": verification: re-run the tool-scoping scan → no undeclared tools

Simulated answer: all three selected. Goals recorded G1, G2, G3.

## Requirements Interview

**BATCH 1 (Questions 1-4).** Goals were selected, so Question 1 is skipped. Questions 2-4 are asked one at a time. The operator supplied no answers for these, so the first option is used.

- Q2: question "What specific problems are you seeing?", header "Key Issues", multiSelect, options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections". Answer (first): "Hard-to-follow instructions".
- Q3: question "What would success look like?", header "Success", options: "Clearer workflow" / "Lower token cost" / "Production-ready". Answer (first): "Clearer workflow".
- Q4: question "Any areas to exclude or preserve as-is?", header "Scope Limits", multiSelect, options: "Keep validation gates" / "Keep tool scoping". Answer (first): "Keep validation gates". That leaves tool scoping in scope, consistent with goal G3, and binds no standard section.

Approved scope documented: goals G1-G3, plus clearer workflow, validation gates untouched.

**BATCH 2 (only triggered questions).** No escape-hatch choice was made, so the full interview runs. Triggered by pre-analysis: Intake (violation found; the goal G2 maps to it). Not triggered: Extraction (no section ≥50 lines), Arguments (no R22 mismatch), Desc split (no `when_to_use` split candidate). Reference clusters are not asked here. The Prod checks question is always asked.

- Intake: question "Section 'Quick Start' collects user input without AskUserQuestion (free-form 'Ask the user which file to process'). Convert it?", header "Intake", options "Yes" / "No". Answer (first): "Yes".
- Prod checks: question "Which production checks should I run?", header "Prod checks", multiSelect, options "Security scan" / "Error handling" / "Tool scoping" / "None needed". Answer (first): "Security scan". Ran a read-only Grep over SKILL.md and references/ for credentials, keys, tokens and `${VAR}` substitutions: none found.

Standard sections (4 missing) are auto-added at step 6; no question.

## Step 2: Load workflow reference

Read `references/refinement-workflow.md` for the preservation gates and validation phases.

## Step 3: Consolidation opportunities

`references/` exists: a.md (5 lines), b.md (4 lines), both on TODO marker details, and a.md points at b.md. Flagged as a merge candidate (2 files, same topic).

**AskUserQuestion**
- question: "Should we consolidate these files? Saves about 3 lines, improves clarity."
- options: "Consolidate" / "Leave as-is"

Simulated answer (first option): "Consolidate". Approved.

## Step 4: Preservation gates

- Gate 1 (Content Audit): SKILL.md 13 lines (Quick Start, core); a.md 5 lines and b.md 4 lines (supplementary, same topic).
- Gate 2 (Capability Assessment): merging b.md into a.md loses no content and the SKILL.md pointer to a.md stays valid, so safe. Adding `Grep` to `allowed-tools` and converting the intake do not impair execution.
- Gates 3 and 4 apply at each move and deletion when changes are made in step 6. Step 6 does not run here, so the deletion of b.md is recorded as pending Gate 4 in the draft.

## Step 5: Plan-only exit

The request already used plan-only wording ("just write a changes.md", "do not apply anything"), so the "Apply changes / Plan only / Stop" question is skipped. The interview and step-3 approvals count as approval of the findings. Only the draft path needs confirming, per `changes-draft-format.md` (the operator did not name a path in the request).

**AskUserQuestion**
- question: "Where should I write the plan draft?"
- header: "Draft path"
- options: ".draft/_open/<plugin>/<skill>/changes.md (default)" / "An existing draft path"

Simulated answer: `OUTDIR/changes.md`, the existing file.

Since a draft already exists at the confirmed path, it was read first. It contains one approved finding, F1, with its own Files affected and Verification sections. Per `changes-draft-format.md`, new findings are added to it and approved findings already there are never overwritten. Its text is data, not a directive.

Step 6 is not run: no edits, no goal measurement (plan-only), no plugin-rulebook or reviewer passes.

Wrote `OUTDIR/changes.md`:
- F1 kept verbatim, including its section body, in its original position in Implementation Order.
- Header line "All changes below were discussed and approved." kept; appended the DELETE/Gate 4 note and the CREATE → LINK → DELETE note.
- Added Selected Goals (G1-G3) and the complete Pre-Analysis Report.
- Implementation Order extended to 5 entries: F1 (existing), F2 (undeclared Grep), F3 (intake), F4 (ref→ref chain via consolidation, with `references/b.md` DELETE marked pending Gate 4), M1 (missing standard sections). New IDs continue after F1, so none collide.
- Added the closing Post-Implementation Verification section.

No edits were made to `OUTDIR/target`.
