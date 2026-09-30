# Transcript: eval-8 (Validation mode)

Operator: "Validate the skill in OUTDIR/target."
Setup: fixture demo-skill copied to OUTDIR/target/ (SKILL.md, references/a.md, references/b.md).

## Quick Start A (escape hatch detection)
Request only names the skill and the action -> not predating context. No escape-hatch question asked. Continue to B.

## Quick Start B
Request already names the skill (path OUTDIR/target), and the simulated operator says the skill is already located. Plain-text "What skill?" question skipped.

## Quick Start C (Action question)
Request already says "Validate", so the skill says it may be skipped. Simulated operator answer is given anyway:
Question: "What would you like to do with this skill?" (header "Action")
Options: "Refine" / "Validate"
Simulated answer: Validate.

## Quick Start D
Validate -> skip the interview, go to Core Workflow: Validation. No pre-analysis, goal selection, BATCH 1/2 (those are Refinement only).

## Validation step 1: Locate the skill
Skill already located at OUTDIR/target. Gitignore exclusion: target is an eval-workspace copy, not a draft under .temp/.draft/.backup. Mirror-pair check (R19): no plugins/<plugin>/skills/<name>/ + .claude/skills/<name>/ pair exists for demo-skill -> single logical skill; no Mirror question.

## Validation step 2: Delegate
2a. skill-reviewer (full mode, Structured output mode) - simulated return:
verdict: Pass, score: 82, counts {critical 0, major 1, minor 2}
findings: M1 major "Quick Start has no example"; m1 minor "description is single-line"; m2 minor "no Testing & Validation section"
top_priority_fixes: ["Add a Quick Start example"]
2b. Skill(plugin-rulebook) - simulated return: 1 FAIL: R8 (description needs the >- block scalar).
No reimplementation of either check here.

## Validation step 3: Present the report
- Headline verdict from skill-reviewer: Pass. plugin-rulebook has a FAIL, so the displayed verdict is downgraded to Reject (presentation only; reviewer's own return unchanged).
- Findings grouped by severity; plugin-rulebook FAIL under its own heading; top_priority_fixes + FAIL merged as actionable summary. See report.md.
- Enhancement-suggestor gate: verdict is Reject (after downgrade) and counts.major = 1, so the ask is required.
Question: "Run `enhancement-suggestor` against this report for a classified (complexity/risk/benefit) WHAT/WHY/HOW action plan?"
Options: "Yes" / "No"
Simulated answer: No.
-> enhancement-suggestor NOT invoked.

## Close
Validation is report-only: no edits to OUTDIR/target, no completion marker (<skill-improvement-complete> belongs to Refinement step 10), no changes.md.
