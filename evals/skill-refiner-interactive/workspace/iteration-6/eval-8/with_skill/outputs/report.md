# Validation Report: demo-skill (OUTDIR/target)

**Status: Reject** (skill-reviewer verdict: Pass, score 82/100; shown as Reject in this summary because plugin-rulebook reported a FAIL. The downgrade is presentation-only and does not change what skill-reviewer returned.)

Counts: critical 0, major 1, minor 2

## Major
- M1: Quick Start has no example

## Minor
- m1: description is single-line
- m2: no Testing & Validation section

## plugin-rulebook FAIL findings
- R8: description needs the `>-` block scalar

## Actionable summary
1. Add a Quick Start example (skill-reviewer top priority fix, M1)
2. Convert `description` to a `>-` block scalar (R8 FAIL)

enhancement-suggestor: offered, operator declined ("No"); not invoked.
No edits were made to the target.
