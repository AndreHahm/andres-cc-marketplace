# Transcript (dry run, skill-refiner-interactive, Validation path)

Operator: "Validate the skill in OUTDIR/target."
Target: copy of fixtures/demo-skill at OUTDIR/target (original fixture untouched).

## Quick Start A (escape hatch)
Predating context check: the request only names the skill and the action, so this is NOT predating context. Escape-hatch question skipped.

## Quick Start B
Request already names the skill. "What skill do you want to work on?" skipped. (Simulated: skill already located.)

## Quick Start C (action question)
Request already says "validate", so the skip condition applies. For the record, the question would be:
  question: "What would you like to do with this skill?", header: "Action", options: "Refine" / "Validate"
Simulated operator answer: Validate.

## Quick Start D
Route: "Validate" -> skip the interview, go directly to Core Workflow: Validation. No pre-analysis, goal selection, BATCH 1/2, consolidation ask, gates, edits, step 9, or completion marker apply (those are Refinement only).

## Core Workflow: Validation, step 1 (Locate)
- Target given as OUTDIR/target (simulated "already located"), a project path, not user-space and not under ~/.claude/plugins/cache/.
- Gitignore-exclusion check: not a draft in .temp/.draft/.backup.
- Mirror-pair (R19) check: no plugins/<plugin>/skills/<name>/ + .claude/skills/<name>/ pair for this target, so no mirror question (Validation-form Mirror question not asked).

## Validation step 2 (Delegate)
2a. skill-reviewer (full mode, Structured output mode) on OUTDIR/target. Simulated return:
```
verdict: Pass
score: 82
counts: {critical: 0, major: 1, minor: 2}
findings:
  - {id: M1, severity: major, finding: 'Quick Start has no example'}
  - {id: m1, severity: minor, finding: 'description is single-line'}
  - {id: m2, severity: minor, finding: 'no Testing & Validation section'}
top_priority_fixes: ['Add a Quick Start example']
```
2b. Skill(plugin-rulebook) full compliance check. Simulated return: 1 FAIL finding, R8 (description needs the >- block scalar).

## Validation step 3 (Present the report)
- Rendered skill-reviewer YAML as narrative: verdict headline, findings grouped by severity, top_priority_fixes.
- Appended plugin-rulebook FAIL (R8) under its own heading.
- Downgrade rule: a plugin-rulebook FAIL displays any verdict (S-Tier or Pass) as Reject in the summary shown to the operator. skill-reviewer's Pass becomes displayed "Reject" (presentation only; skill-reviewer's own return stays Pass/82).
- Actionable summary = top_priority_fixes + plugin-rulebook FAIL together.
- Enhancement-suggestor gate: displayed verdict is Reject AND counts.major = 1 (nonzero), so the ask is REQUIRED. Question:
  question: "Run `enhancement-suggestor` against this report for a classified (complexity/risk/benefit) WHAT/WHY/HOW action plan?"
  options: "Yes" / "No"
  Simulated operator answer: No.
- Answer is No, so enhancement-suggestor is NOT invoked (never invoked without asking first).

## End
Validation is report-only: no edits to OUTDIR/target, no completion marker (<skill-improvement-complete> is Refinement-only and was not emitted), no change summary. Delivered report.md and final-tree.txt.
