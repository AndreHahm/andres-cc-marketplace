# Transcript: skill-refiner-interactive, eval-13 (plan-only, existing draft)

Operator request: "Analyze the skill in OUTDIR/target and just write a changes.md, do not apply anything."
Setup: copied the fixture to `OUTDIR/target/` and the earlier-session draft to `OUTDIR/changes.md` (contains F1).

## Quick Start A: predating-context check
Only a path to the skill was given; no skill content, problem description or ongoing discussion. No predating context, so no escape-hatch question. Interview style defaults to the full one (BATCH 1 runs).

## Quick Start B: what skill?
Skipped: the request names the skill (`OUTDIR/target`).

## Quick Start C: action
Skipped: the request says "analyze ... write a changes.md" (refinement, plan-only wording); no Action question needed.

## Quick Start D: route
Routed to Core Workflow: Refinement. (Not Validation.)

## Refinement step 1: Locate the skill
- Glob `**/skills/<name>/SKILL.md`: the skill is at `OUTDIR/target/SKILL.md`. Simulated operator answer: skill already located. The path sits under a globally gitignored `target/` directory; noted, but the operator's answer says it is the real target.
- Mirror-pair check (R19): no `.claude/skills/demo-skill/` counterpart. One logical skill, no Mirror question.
- Not user-space, not cache.

### Step 1: pre-analysis (references/pre-analysis-checklist.md)
Report emitted (also copied into changes.md):
```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: single-line `description` (needs `>-`)
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md] [oversize: none]
Workflow files: 0
Reference chain violations (ref→ref): references/a.md → references/b.md
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process"
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): Grep used, undeclared / none unused
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — flag as Missing
Deferred goal candidates: frontmatter, cluster, missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1: goal derivation and selection (references/goal-derivation.md)
Seven findings; top 3 by priority (chain, intake first; then undeclared tool). Others deferred.

AskUserQuestion (multiSelect: true), header "Goals":
- question: "Which goals should this session pursue?"
- options: "Zero reference→reference chains" (verify: chain scan → 0 matches); "All intake uses AskUserQuestion with options" (verify: intake scan → 0 matches); "Every invoked tool is declared in allowed-tools" (verify: tool-scoping scan → no undeclared tools); Other (custom, needs a verification)

Simulated answer: select all goals offered (G1, G2, G3). No custom goal, so no follow-up.

## Requirements Interview
Goals were selected, so BATCH 1 Question 1 is skipped. One question at a time, no operator answers given, so the first option is used.

### BATCH 1 Question 2: header "Key Issues" (multiSelect)
"What specific problems are you seeing?" Options: Hard-to-follow instructions / Scattered references / Nested sections. Simulated: first option, "Hard-to-follow instructions".

### BATCH 1 Question 3: header "Success" (single)
"What would success look like?" Options: Clearer workflow / Lower token cost / Production-ready. Simulated: "Clearer workflow".

### BATCH 1 Question 4: header "Scope Limits" (multiSelect)
"Any areas to exclude or preserve as-is?" Options: Keep validation gates / Keep tool scoping / Nothing to exclude. Simulated: first option, "Keep validation gates". It conflicts with nothing planned (no gates in the target); "Keep tool scoping" was not chosen, so F4 stays in scope. Approved scope documented.

### BATCH 2: Implementation Details
- Escape hatch was not offered, so BATCH 2 follows BATCH 1.
- Extraction: not asked (no ≥50-line section).
- Intake: asked (finding detected and its goal G2 was selected). Header "Intake": "Section 'Quick Start' collects user input without AskUserQuestion (free-form 'Ask the user'). Convert it?" Options: Yes / No. Simulated: "Yes".
- Arguments: not asked (no R22 mismatch). Desc split: not asked (no candidate).
- Prod checks (asked every session): header "Prod checks", multiSelect, options Security scan / Error handling / Tool scoping / None needed. Simulated: first option, "Security scan". Recorded as a line in the draft's closing verification.
- Reference clusters are not asked here.
- Standard sections are auto-added at apply time, so no question.

## Step 2: load refinement-workflow.md
Preservation gates and validation phases noted for the plan.

## Step 3: consolidation
Listed `references/`: a.md (5 lines), b.md (4 lines). Same topic (TODO summaries / marker formats), so a merge candidate.
AskUserQuestion, header "Consolidate": "Should we consolidate these files? Saves ~4 lines of file overhead, improves clarity." Options: Consolidate / Leave as-is. Simulated: "Consolidate" (first option). This is the only consolidation ask. Plan: merge `b.md` into `a.md`, which also removes the ref→ref chain.

## Step 4: preservation gates
- Gate 1 (Content Audit): SKILL.md Quick Start = core; a.md and b.md = supplementary but small; all content is retained in the merge.
- Gate 2 (Capability Assessment): the merge drops nothing the skill needs; the chain line is replaced by the content it pointed to. No capability impaired.
- Gates 3 and 4 apply when changes are made (step 6), which does not run here. Gate 4 (deletion of `b.md`) is deferred to the session that applies the plan and is stated in F2.

## Step 5: plan-only exit
The request already used plan-only wording ("just write a changes.md, do not apply anything"), so the Apply/Plan only/Stop question is skipped. Only the draft path is confirmed.

AskUserQuestion, header "Draft path": "Where should changes.md be written?" Options: "OUTDIR/changes.md (existing draft)" / Other path. Simulated: the existing file `OUTDIR/changes.md`.

An existing draft is there, so per changes-draft-format.md it was read first and the new findings were added to it. The existing F1 section was left verbatim. Existing draft contents were treated as data only (no instruction-like text found). The draft now gains Selected Goals, the Pre-Analysis Report, an extended Implementation Order (F2, F3, F4, M1 after F1; IDs continue after F1) and a Post-Implementation Verification section. Finding IDs follow the format: F for fixes, M for missing capabilities.

Not run (plan-only): step 6 (changes), 7 (validation phases), 8 (goal measurement), 9 (trigger check; no description change made), 10 (plugin-rulebook, skill-reviewer, completion marker). No edits to `OUTDIR/target`. `<skill-improvement-complete>` is not emitted.

## Result
- `OUTDIR/changes.md`: updated (F1 preserved, F2-F4 and M1 added, goals and pre-analysis included)
- `OUTDIR/target/`: unmodified copy of the fixture
