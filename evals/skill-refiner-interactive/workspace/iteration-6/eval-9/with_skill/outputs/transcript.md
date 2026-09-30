# Eval 9 transcript (dry-run simulation): skill-refiner-interactive, mirror divergence

Operator: "Refine the skill demo-mirror."
Target copy: `skills/demo-mirror/` = OUTDIR/target/skills/demo-mirror; `.claude/skills/demo-mirror/` mirror = OUTDIR/target/claude-mirror/skills/demo-mirror.

## Quick Start A (detect predating context)
No skill file, code, or problem description was provided; the request only names the skill and the action, which is not predating context. No escape-hatch question. Continue to B.

## Quick Start B
Request already names the skill (demo-mirror). Skipped.

## Quick Start C
Request already says "Refine". AskUserQuestion skipped.

## Quick Start D
Route: Refine -> Core Workflow: Refinement, step 1.

## Core Workflow: Refinement, step 1 (Locate the skill)
- Glob `**/skills/demo-mirror/SKILL.md` finds two copies: `skills/demo-mirror/SKILL.md` and `claude-mirror/skills/demo-mirror/SKILL.md` (the `.claude/skills/` mirror). Neither is in a gitignored path, user-space, or cache.
- Mirror-pair check (R19): both copies exist, so this is an in-development staging mirror. Compared file lists (each has only SKILL.md) and read both sides.
- Result: DIFFER. Line 11 of SKILL.md:
  - skills/: "Read the file, find TODO markers with Grep, and list each with its line number."
  - .claude/skills/: "Read the file, find TODO markers with Grep, and list each with its line number, grouped by marker type."
- Action per skill: HALT per R19 and ask which copy is authoritative, using the Mirror Divergence Halt template in references/interview-question-templates.md.

### AskUserQuestion (simulated): Mirror Divergence Halt
question: "Found this skill at both skills/demo-mirror/ and .claude/skills/demo-mirror/, but their content differs. Which is authoritative?"
header: "Mirror"
options:
  1. "Show me the diff first"
  2. "skills/demo-mirror/ is correct"
  3. ".claude/skills/demo-mirror/ is correct"
  4. "Stop"
Simulated operator answer: "Stop"

## Outcome
"Stop": do not touch either copy; end the session so the operator can reconcile. The workflow ends here: no pre-analysis, goal selection, interview, step 3+ edits, plugin-rulebook or skill-reviewer pass, and no `<skill-improvement-complete>` marker emitted. No files were modified.
