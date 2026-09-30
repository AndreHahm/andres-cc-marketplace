# Transcript: eval-8 (Validation mode dry run)

Operator: "Validate the skill in OUTDIR/target."
Fixture copied to OUTDIR/target (SKILL.md, references/a.md, references/b.md). Original fixture untouched.

## Quick Start
- A (escape hatch): no predating context (the request only names the skill and the action). No question asked; continue to B.
- B: request already names the skill (OUTDIR/target). Skipped.
- C: request already says "Validate", so the action question is skipped per the skill. (Simulated answer was also "Validate".)
- D: "Validate" -> skip the interview, go directly to Core Workflow: Validation.

## Core Workflow: Validation, step 1 (Locate the skill)
- Skill already located by the operator (OUTDIR/target). Gitignore-exclusion check: path is not in .temp/.draft/.backup and is not in the plugin cache.
- Mirror-pair check (R19): no plugins/<plugin>/skills/ or .claude/skills/ twin of this target exists; single logical skill.

## Step 2 (Delegate; no reimplementation of checks)
- Simulated skill-reviewer (full mode, Structured output mode) returned:
  verdict: Pass, score: 82, counts: {critical: 0, major: 1, minor: 2}
  findings: M1 (major) Quick Start has no example; m1 (minor) description is single-line; m2 (minor) no Testing & Validation section
  top_priority_fixes: [Add a Quick Start example]
- Simulated Skill(plugin-rulebook) returned 1 FAIL: R8 (description needs the >- block scalar).

## Step 3 (Present the report)
- Headline: verdict Pass, but a plugin-rulebook FAIL exists -> displayed as Reject (presentation-only downgrade; skill-reviewer's own verdict is unchanged).
- Findings grouped by severity; plugin-rulebook FAIL under its own heading; top_priority_fixes and the FAIL merged into the actionable summary.
- Ask condition met: verdict Reject after downgrade, and counts.major = 1.

AskUserQuestion (simulated):
  question: "Run `enhancement-suggestor` against this report for a classified (complexity/risk/benefit) WHAT/WHY/HOW action plan?"
  options: "Yes" / "No"
  simulated operator answer: "No"
-> enhancement-suggestor NOT invoked. Report presented; no edits made to the target (Validation mode is read-only).
