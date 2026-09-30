# Transcript: skill-refiner-interactive dry run (eval 11, big-skill)

Operator request: "Refine the skill in OUTDIR/target so it is lighter."
Target: a copy of fixtures/big-skill in `target/` (originals untouched).

## Quick Start
- A (predating context): none. A request that only names the skill and action is not predating context. No escape-hatch question.
- B: skill already located (simulated operator answer); not asked.
- C: request says "refine"; action question skipped.
- D: route -> Core Workflow: Refinement.

## Step 1: Locate the skill
- Target given as OUTDIR/target (project path, not user-space, not cache, no mirror pair). Located.

### Pre-analysis (references/pre-analysis-checklist.md)
Threshold source: plugin-rulebook/assets/settings.json (R13: weak 100, soft 300, warning 490, critical 500; R18: 10/20/30; R21 description min 80).

```
Pre-Analysis: big-skill
Lines: 307 — Soft Warning (R13)
Frontmatter issues: none
Large sections (≥50 lines): Troubleshooting (Edge Cases) — 60 lines (self-declared failure-only, est. <20% usage, low-frequency)
Reference files: 1 [clusters: none] [oversize ≥400 lines: none]
Workflow files: 0 [oversize ≥300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): none
Spawn anti-patterns: none
Intake pattern violations: none
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): within tiers
Tool scoping (R6): none / unused declared: Grep, Glob (Minor, left as is)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: none
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

**R13 tier from pre-analysis report: Soft Warning (307 lines).**

### Goal selection (goal-derivation.md)
AskUserQuestion (multiSelect, up to 3 goals):
- question: "Which goals should this refinement session achieve?" header: "Goals"
  - "No low-frequency section inline": Troubleshooting not inline unless kept. Check: re-run large-section scan -> none unapproved
  - "SKILL.md under the Soft Warning tier": Check: wc -l SKILL.md -> ≤300
  - "Add goal verification": Check: Grep `## Goal Verification` -> present
- Simulated answer: all three selected.
Selected goals: G1 (large section), G2 (R13 ≤300), G3 (goal verification).

## Requirements Interview
- BATCH 1: goals selected, so Question 1 skipped. Questions 2-4 about selected goal areas:
  - Q2 "What specific problems are you seeing?" (Key Issues) options: Hard-to-follow instructions / Scattered references / Nested sections. Simulated answer: none in particular (select all goals answer; not constraining scope).
  - Q3 "What would success look like?" (Success) options: Clearer workflow / Lower token cost / Production-ready. Answer (first option per rules would be Clearer workflow; operator wants lighter) -> "Lower token cost".
  - Q4 "Any areas to exclude or preserve as-is?" (Scope Limits) options: Keep validation gates / Keep tool scoping. Answer: none excluded.
  Approved scope documented.
- BATCH 2: pre-analysis detected a large low-frequency section -> Extraction question; Prod checks question is asked every session.
  - Extraction: question "Section 'Troubleshooting (Edge Cases)' is 60 lines and appears in <20% of activations. Extract to references/troubleshooting.md?" header "Extraction" options: Yes / No. **Simulated answer: Yes.**
  - Prod checks: asked; scope kept minimal (no tool-scope change). Answer: skip extra production changes.
  - Intake / Arguments / Desc split: triggers not detected -> not asked.

## Step 2: Load workflow reference
- Read references/refinement-workflow.md (Content Extraction procedure, Gates).

## Step 3: Consolidation
- Skipped: references/ has only 1 file (rules.md, 3 lines); no cluster. No consolidation ask.

## Step 4: Preservation gates
- Gate 1 Content Audit: SKILL.md 307 lines: Quick Start (core), Workflow Steps 1-7 (core, 33 lines each), Troubleshooting (60 lines, supplementary <20%); references/rules.md (3 lines).
- Gate 2 Capability Assessment: moving failure-only troubleshooting does not impair normal execution; content is migrated, not removed.
- Gate 3 (at move): destination references/troubleshooting.md verified complete (55 failure modes, 60 lines) before LINK.
- Gate 4 (at delete): AskUserQuestion "Delete the inline body of 'Troubleshooting (Edge Cases)' from SKILL.md now that it lives in references/troubleshooting.md?" options: Approve deletion / Decline. **Simulated answer: approve.**

## Step 5: Plan-only exit
- AskUserQuestion: "Apply the approved scope?" options: Apply changes / Plan only / Stop. **Simulated answer: Apply changes.** Step 6 runs.

## Step 6: Make changes (CREATE -> LINK -> DELETE)
Rollback: fixture original kept untouched in evals/.../fixtures/big-skill (restorable).

1. CREATE `references/troubleshooting.md` — heading + intro + all 55 failure modes (60 lines).
2. LINK — SKILL.md `## Troubleshooting (Edge Cases)` now carries pointer "Details: `references/troubleshooting.md` ..." (link verified: file exists).
3. DELETE — inline Troubleshooting body (intro + 55 bullets, old lines 251-309) removed from SKILL.md via Bash (sed), after Gate 4 approval and link verification.

Standard sections (auto-add, no approval; none excluded):
4. UPDATE (standard-section auto-add) — SKILL.md: added `## When to Use` and `## When NOT to Use` after Quick Start.
5. UPDATE (standard-section auto-add) — SKILL.md: added `## Testing & Validation`, `## Goal Verification` (G3), `## Reference Guide` (lists rules.md, troubleshooting.md).

## Step 7: Validate (phases 1-7)
- P1 inventory: before SKILL.md + references/rules.md; after SKILL.md + rules.md + troubleshooting.md.
- P2 read-all: no gaps; all 55 modes present in troubleshooting.md.
- P3 frontmatter: name, description present; `>-`; unchanged.
- P4 body: 280 lines -> Weak Warning tier (R13, ≤300); Quick Start, When to Use etc. present.
- P5 references: both linked files exist, one level deep, no ref->ref chains.
- P6 tools: no change.
- P7 testing: trigger phrases "clean this CSV" etc. still match the unchanged description.

## Step 8: Measure goals
See goal-measurement.md: G1 PASS, G2 PASS, G3 PASS. No failures -> no accept/continue ask.

## Step 9: Trigger regression
- description/when_to_use unchanged -> skipped.

## Step 10: Compliance and reviewer passes
- Cannot dispatch Skill(plugin-rulebook) or skill-reviewer in a dry run; simulated as not executed. Manual sanity: R13 280 ≤300, R18 no code blocks >10 lines, R21 description ≥80.

Change summary:
```
Lines: 307 → 280
Frontmatter: no changes
Sections added: When to Use, When NOT to Use, Testing & Validation, Goal Verification, Reference Guide
Files created: references/troubleshooting.md
Files deleted: none (inline section body deleted from SKILL.md)
plugin-rulebook: not run (dry run; manually checked R13/R18/R21)
```
<skill-improvement-complete>
