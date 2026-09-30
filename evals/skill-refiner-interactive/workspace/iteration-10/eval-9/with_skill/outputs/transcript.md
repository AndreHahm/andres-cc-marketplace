# Transcript: skill-refiner-interactive, eval-9 (mirror divergence, operator chooses Stop)

Operator: "Refine the skill demo-mirror."
Target copy: OUTDIR/target (skills/demo-mirror = `skills/demo-mirror/` copy; claude-mirror/skills/demo-mirror = `.claude/skills/demo-mirror/` mirror).

## Quick Start A (escape hatch)
No predating context (request only names skill and action). Escape-hatch question NOT asked. Continue to B.

## Quick Start B
Request already names the skill (demo-mirror). Skipped "What skill do you want to work on?".

## Quick Start C
Request already says "refine". Skipped the Action question. D: route to Core Workflow: Refinement.

## Core Workflow: Refinement, step 1 (Locate the skill), sub-block: Locate
Glob `**/skills/demo-mirror/SKILL.md` in target found two copies:
- skills/demo-mirror/SKILL.md
- claude-mirror/skills/demo-mirror/SKILL.md
Neither is in a gitignored path. No user-space or cache lookup needed.

## Step 1, sub-block: Mirror-pair check (R19)
Both copies exist, so this is an in-development staging mirror. Compared file lists (each has only SKILL.md; no references/ or scripts/) and read both sides.
Result: DIFFER. Only difference is the Quick Start sentence:
- skills/: "...and list each with its line number."
- claude-mirror/: "...and list each with its line number, grouped by marker type."
Per SKILL.md: HALT per R19 and ask the Mirror question (Mirror Divergence Halt, four-option Refinement form in references/interview-question-templates.md). Pre-analysis, goal selection, interview, and all later steps have NOT started and do not start until this is resolved.

### AskUserQuestion (Mirror Divergence Halt)
question: "Found this skill at both skills/demo-mirror/ and claude-mirror/skills/demo-mirror/ (.claude/skills/demo-mirror/), but their content differs. Which is authoritative?"
header: "Mirror"
options:
  - "Show me the diff first"
  - "skills/demo-mirror/ is correct"
  - "claude-mirror/skills/demo-mirror/ is correct"
  - "Stop"
Simulated operator answer: "Stop"

## Handling "Stop"
Template semantics: don't touch either copy; end the session so the operator can reconcile.
- No edits made to either copy; no files overwritten, created, or deleted.
- Not run: pre-analysis report, goal selection, interview (BATCH 1/2), steps 2-10.
- No plugin-rulebook or skill-reviewer pass (nothing modified). `<skill-improvement-complete>` is NOT emitted (no refinement happened).

Final message to operator: Stopped. demo-mirror differs between the two copies (Quick Start sentence: the .claude mirror adds ", grouped by marker type"). Neither copy was changed. Reconcile them, then re-run the refinement.
