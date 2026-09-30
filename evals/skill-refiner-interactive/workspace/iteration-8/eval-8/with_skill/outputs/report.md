# Validation Report: demo-skill (OUTDIR/target)

## Status: Reject
skill-reviewer returned verdict Pass (score 82/100). Because plugin-rulebook reported a FAIL, the status shown here is downgraded to Reject. This is this skill's presentation logic only; skill-reviewer's own verdict is unchanged.

Counts from skill-reviewer: critical 0, major 1, minor 2.

## skill-reviewer findings
### Critical
None.
### Major
- M1: Quick Start has no example
### Minor
- m1: description is single-line
- m2: no Testing & Validation section

## plugin-rulebook FAIL findings
- R8 (FAIL, REQUIRED): description needs the `>-` block scalar

## Actionable summary
1. Add a Quick Start example (skill-reviewer top priority fix)
2. Convert `description` to the `>-` block scalar (R8 FAIL)

## Follow-up
Asked whether to run enhancement-suggestor: operator answered No. It was not invoked. No edits were made to the target.
