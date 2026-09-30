# Validation Report: demo-skill (OUTDIR/target)

## Headline status: REJECT
skill-reviewer returned Pass (score 82/100), but plugin-rulebook reported a REQUIRED-rule FAIL, which downgrades the status shown here from Pass to Reject. (The downgrade is this skill's presentation logic; skill-reviewer's own verdict stays Pass.)

Counts from skill-reviewer: Critical 0, Major 1, Minor 2.

## skill-reviewer findings
### Critical
None.
### Major
- M1: Quick Start has no example.
### Minor
- m1: description is single-line.
- m2: no Testing & Validation section.

## plugin-rulebook findings
### FAIL
- R8: description needs the `>-` block scalar.

## Actionable summary
1. Add a Quick Start example (skill-reviewer top priority fix).
2. Fix R8: convert `description` to the `>-` block scalar (plugin-rulebook FAIL; also addresses m1).
3. Add a Testing & Validation section (m2).

## Notes
- No mirror pair detected (R19 not applicable); validation ran once.
- The target path matches the operator's global gitignore rule `target/`; treated as the target because the operator named it explicitly.
- Enhancement-suggestor was offered (Reject, Major 1) and the operator declined; it was not run.
- Validate mode made no edits to the target.
