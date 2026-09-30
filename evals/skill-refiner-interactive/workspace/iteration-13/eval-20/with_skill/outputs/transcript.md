# Transcript: skill-refiner-interactive dry run (eval 20, mirror divergence, plan-only)

Operator request: "Refine the skill demo-mirror: just plan it, write a changes.md and do not apply anything."
Target: OUTDIR/target/skills/demo-mirror/ (the `skills/demo-mirror/` copy) and OUTDIR/target/claude-mirror/skills/demo-mirror/ (its `.claude/skills/demo-mirror/` mirror). Both copied from the pristine fixture and confirmed identical to it with `diff -r` before starting.

## Quick Start

### A. Detect predating context
The conversation has no skill file provided, no problem described, and no skill under discussion. The request only names the skill and the action, which the skill says is not predating context. The escape-hatch question is NOT asked. No "Infer from context" / "Define explicitly" answer exists, so the full interview runs.

### B. "What skill do you want to work on?"
Skipped: the request already names `demo-mirror`.

### C. Action question (Refine / Validate)
Skipped: the request says "Refine the skill". The plan-only wording does not change that.

### D. Route
Refine, so this goes to Core Workflow: Refinement, step 1.

## Core Workflow: Refinement

### Step 1. Locate the skill
- Glob `**/skills/demo-mirror/SKILL.md` over OUTDIR/target found two files:
  - `target/skills/demo-mirror/SKILL.md` (11 lines)
  - `target/claude-mirror/skills/demo-mirror/SKILL.md` (11 lines)
- Gitignore-exclusion check (`plugin-rulebook/references/gitignore-exclusion.md`, which exists). Neither path is under `.temp/`, `.draft/` or `.backup/`. A global `target/` ignore pattern in the operator's home `.gitignore_global` does match these directories. I am treating both as the real targets because this simulation designates OUTDIR/target as the target. I record this here and do not exclude them.
- Mirror-pair check (R19): both copies exist, so this is an in-development staging mirror, not two independent skills. File lists: each copy has only `SKILL.md`, with no `references/` or `scripts/`. I read both `SKILL.md` files and compared them. They DIFFER on one line, the Quick Start sentence (line 11):
  - `skills/demo-mirror`: "Read the file, find TODO markers with Grep, and list each with its line number."
  - `claude-mirror/skills/demo-mirror`: "Read the file, find TODO markers with Grep, and list each with its line number, grouped by marker type."
- The copies differ, so I HALT per R19 and ask the Mirror question (four-option Refinement form from `references/interview-question-templates.md`, "Mirror Divergence Halt"). No analysis or edit runs before the answer.

**AskUserQuestion (Mirror question)**
```
question: "Found this skill at both target/skills/demo-mirror and target/claude-mirror/skills/demo-mirror, but their content differs. Which is authoritative?"
header: "Mirror"
options:
  - "Show me the diff first": display what differs before deciding
  - "target/skills/demo-mirror is correct": analyze target/skills/demo-mirror; target/claude-mirror/skills/demo-mirror is overwritten with it in step 6, only if changes are applied
  - "target/claude-mirror/skills/demo-mirror is correct": analyze target/claude-mirror/skills/demo-mirror; target/skills/demo-mirror is overwritten with it in step 6, only if changes are applied
  - "Stop": don't touch either copy; end the session so the operator can reconcile
```
**Simulated answer:** "target/skills/demo-mirror is correct".

Recorded outcome: the `skills/demo-mirror` copy (OUTDIR/target/skills/demo-mirror) is authoritative for this session. Nothing is overwritten at this point. Analysis reads the authoritative copy. The `claude-mirror` copy is brought in line in step 6, and only if changes are applied. Step 6 will not run (plan-only), so both copies stay untouched.

### Step 1 (continued). Pre-analysis (`references/pre-analysis-checklist.md`)
Data-only boundary: the target files contain no instruction-like text to report. Every value read is treated as data.

Checks run on the authoritative copy (`target/skills/demo-mirror/SKILL.md`):
- plugin-rulebook found at `plugins/plugin-devkit/skills/plugin-rulebook/`. `assets/settings.json` loaded. R13 thresholds: weak 100, soft 300, warning 490, critical 500. R18 thresholds: weak 10, warning 20, critical 30. R21 limits: description min 80 / max 1024, `when_to_use` max 512, combined min 80 / max 1536 (critical floor 20).
- Line count is 11, frontmatter included. That is OK under R13.
- Frontmatter has `name`, `description` and `allowed-tools: Read Grep`. No non-standard fields. The description is 36 characters, so R8 (block scalar needed above 80 characters) does not apply. R21 is a finding: 36 characters is under the 80-character minimum. It is above the critical floor of 20, so it sits in the warning band.
- No section has 50 or more lines.
- No `references/` and no `workflows/`.
- Spawn anti-patterns: none.
- Intake: no "ask the user" or free-form `questions:` block.
- R22: no `$ARGUMENTS` or `$N` in the body and no `argument-hint`, so they are consistent.
- `when_to_use` split candidate: no. The description is 36 characters and has no embedded "Use when" clause.
- Tool scoping: the body invokes Read ("Read the file") and Grep ("with Grep"). Both are declared. No undeclared tool and no unused declared tool.
- Dead links and cross-skill references: none.
- Missing standard sections: Quick Start is present. `## When to Use`, `## When NOT to Use`, `## Testing & Validation` and `## Reference Guide` are missing.
- Goal verification: absent, an optional low-priority candidate.

```
Pre-Analysis: demo-mirror
Lines: 11 - OK (R13)
Frontmatter issues: none (R5/R8 fine)
Large sections (>=50 lines): none
Reference files: 0 [clusters: none] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): none
Spawn anti-patterns: none
Intake pattern violations: none
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): FINDING - description 36 chars, below the 80-char minimum (above the 20-char critical floor)
Tool scoping (R6): none / none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: none (the 2 candidates below fit under the cap of 3)
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```
Also noted: the mirror divergence (one Quick Start sentence) from the Mirror-pair check above.

### Step 1 (continued). Goal derivation and selection (`references/goal-derivation.md`)
Two findings have a goal row. Missing standard sections has no goal row because it is auto-added. Candidates, in priority order:
1. Description size outside R21 tiers (second tier) -> verification: `Skill(plugin-rulebook)` R21 -> OK
2. Missing goal verification (third tier, optional, never a defect) -> verification: Grep for a `## Goal Verification` heading or an equivalent step -> present

**AskUserQuestion (goal selection, multiSelect: true, up to 3)**
```
question: "Which goals should this refinement session be measured against?"
header: "Goals"
multiSelect: true
options:
  - "Description within R21 tiers": verification: Skill(plugin-rulebook) R21 -> OK (source: description is 36 chars, under the 80 minimum)
  - "Add a goal-measurement step": verification: Grep for a '## Goal Verification' heading or equivalent -> present (source: no goal verification; optional candidate)
```
("Other" is offered automatically for a custom goal.)
**Simulated answer:** first option only: "Description within R21 tiers".

Recorded selected goal: G1 = "Description within R21 tiers", verified by `Skill(plugin-rulebook)` R21 -> OK. The other candidate was not selected, so it goes in the plan as a deferred candidate.

### Requirements Interview
Escape hatch was not offered, so the full interview runs. One question at a time.

**BATCH 1.** A goal was selected, so Question 1 is skipped (the goal already sets the scope). Questions 2-4 follow.

**AskUserQuestion, BATCH 1 Question 2**
```
question: "What specific problems are you seeing?"
header: "Key Issues"
multiSelect: true
options:
  - "Hard-to-follow instructions": instructions are hard to follow
  - "Scattered references": references scattered and redundant
  - "Nested sections": too many nested sections
```
**Simulated answer:** "Hard-to-follow instructions".

**AskUserQuestion, BATCH 1 Question 3**
```
question: "What would success look like?"
header: "Success"
multiSelect: false
options:
  - "Clearer workflow": instructions are easier to follow end to end
  - "Lower token cost": fewer tokens loaded per activation
  - "Production-ready": production-ready with error handling
```
**Simulated answer:** "Clearer workflow".

**AskUserQuestion, BATCH 1 Question 4**
```
question: "Any areas to exclude or preserve as-is?"
header: "Scope Limits"
multiSelect: true
options:
  - "Keep validation gates": leave the target's validation gates and its Testing & Validation section unchanged
  - "Keep tool scoping": don't change allowed-tools, and add no tool grants
```
**Simulated answer:** "Keep validation gates".

Approved BATCH 1 scope: the clarity of the Quick Start workflow for a first-time reader, with the description size goal G1. Excluded: the Testing & Validation section and the target's validation gates. That exclusion also binds step 6's auto-added standard sections, so `## Testing & Validation` will NOT be auto-added.

**BATCH 2.** The escape hatch was not chosen, so this follows BATCH 1. Only questions whose pre-analysis trigger fired are asked:
- Extraction: no large low-frequency section, not asked.
- Intake: no violation, not asked.
- Arguments: no R22 mismatch, not asked.
- Desc split: not a split candidate, not asked.
- Reference clusters are not asked here (step 3 owns that).
- Prod checks: asked in every refinement session.

**AskUserQuestion, BATCH 2 Prod checks**
```
question: "Which production checks should I run?"
header: "Prod checks"
multiSelect: true
options:
  - "Security scan": Grep SKILL.md, references/ and scripts/ for credentials, keys and tokens, and for ${VAR}-style substitutions that corrupt example code
  - "Error handling": verify the skill handles missing files, malformed YAML and permission errors
  - "Tool scoping": audit allowed-tools: remove unused tools, narrow Bash wildcards
  - "None needed": skip production checks for this session
```
**Simulated answer:** "Security scan".

Security scan result (read-only `Grep` of both copies for key/token/password/secret and `${`): no matches. No finding is added. The approved scope is documented: goal G1, Quick Start clarity, standard sections (minus Testing & Validation), mirror sync, and a clean security scan.

### Step 2. Load workflow reference
Read `references/refinement-workflow.md` (preservation gates, validation phases, Rollback).

### Step 3. Consolidation opportunities
Skipped: the target has no `references/` directory, so there is no consolidation question.

### Step 4. Preservation gates (Gates 1 and 2 run here; Gates 3 and 4 belong to step 6)
- **GATE 1, Content Audit.** SKILL.md (11 lines): frontmatter (name, description, allowed-tools) is core; the `# Demo Mirror` heading is core; `## Quick Start` (one sentence) is core. No scripts, no assets, no references. Nothing is supplementary.
- **GATE 2, Capability Assessment.** Proposed changes are a description rewrite, three added sections, and overwriting the mirror copy's Quick Start line. None deletes or moves content. Will this impair execution? NO for each. One disclosure: overwriting the mirror's line 11 with the authoritative copy discards the clause "grouped by marker type". That is a rewrite in place (an edit), not a deletion, and the operator already chose the authoritative copy. It is recorded in the plan anyway.
- Gate 3 (migration) has no moves to verify. Gate 4 has no file deletions to ask about. Both would run in step 6, which will not run.

### Step 5. Plan-only exit
The request already used plan-only wording ("just plan it", "do not apply anything", "write a changes.md"), so the "Apply changes / Plan only / Stop" question is skipped. The interview approvals count as approval of the findings. Only the draft path needs confirming, and the operator's answer names it.

**AskUserQuestion (draft path)**
```
question: "Where should the plan be written?"
header: "Draft path"
options:
  - "OUTDIR/changes.md": write the approved findings to evals/skill-refiner-interactive/workspace/iteration-13/eval-20/with_skill/outputs/changes.md
  - ".draft/_open/plugin-devkit/demo-mirror/changes.md": the default draft location
```
**Simulated answer:** the draft path is OUTDIR/changes.md. No draft existed there, so nothing is merged or overwritten.

On "Plan only": step 6 is NOT run. The approved findings and selected goal are written per `references/changes-draft-format.md` to OUTDIR/changes.md. There are no edits to either copy and no goal measurement.

### Steps 6-10: not run, with reasons
- Step 6 (Make changes): not run. Plan-only exit was taken; no edits were made to either copy.
- Step 7 (Validate result): not run, because there is no result to validate.
- Step 8 (Measure goals): not run. Per the plan-only branch, goal G1 and its check are recorded in changes.md for the applying session.
- Step 9 (Trigger regression): not run, because `description` was not changed.
- Step 10 (plugin-rulebook, skill-reviewer, completion marker): not run, because nothing was modified. `<skill-improvement-complete>` is NOT emitted.

## Final check
- No edit was made to either `target/` copy. A `diff -r` against the pristine fixture is run after writing the outputs (recorded in the final report).
- Files written: transcript.md, changes.md, final-tree.txt.
