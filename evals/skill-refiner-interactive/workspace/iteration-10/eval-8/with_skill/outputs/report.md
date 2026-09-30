# Validation Report: demo-skill

Target: OUTDIR/target (copy of fixtures/demo-skill)

## Status: Reject (displayed)

skill-reviewer returned verdict Pass (score 82/100). Because plugin-rulebook reported a FAIL, the verdict is displayed to you as Reject. This downgrade is this skill's presentation logic only; it does not change what skill-reviewer returned.

## skill-reviewer findings (counts: critical 0, major 1, minor 2)

### Critical
None.

### Major
- M1: Quick Start has no example

### Minor
- m1: description is single-line
- m2: no Testing & Validation section

## plugin-rulebook FAIL findings

- R8 (REQUIRED): description needs the `>-` block scalar

## Actionable summary

1. Add a Quick Start example (skill-reviewer top priority fix)
2. Convert description to the `>-` block scalar (plugin-rulebook R8 FAIL)

## Follow-up

Asked whether to run `enhancement-suggestor` for a classified WHAT/WHY/HOW action plan. Operator answered No, so it was not invoked.

Validation is report-only: no files in the target were changed.
