# Transcript: skill-refiner-interactive dry run (iteration-11, eval-12)

Simulated operator context: earlier the operator pasted the skill's SKILL.md (treated as target/SKILL.md) and said "the intake is sloppy and a tool isn't declared". The operator now says: "Refine it."
Target: OUTDIR/target (copy of fixtures/demo-skill). The original fixture was not touched. No edits were made to target.

## Quick Start A: detect predating context

Check: a skill file was already provided, and a problem was already described ("intake is sloppy", "a tool isn't declared"). That is predating context (not merely a skill name plus an action). Offering the escape hatch.

QUESTION (AskUserQuestion)
- question: "I've reviewed the context you provided. How would you like to proceed?"
- header: "Interview"
- options: "Infer from context" (infer refinement needs from what you shared, skip the detailed interview (faster)) / "Define explicitly" (define improvement areas and goals explicitly (full interview))
- SIMULATED ANSWER: "Infer from context"

Effect: this sets the interview style only. BATCH 1 will be skipped when the interview starts. Not an interview question for step 1's pre-analysis ordering. Continue to B.

## Quick Start B

Skipped. The request ("Refine it", on the pasted skill already located at OUTDIR/target) already names the skill, so the plain-text "What skill do you want to work on?" is not asked.

## Quick Start C

Skipped. The request already says refine ("Refine it"), so the Action question is not asked.

## Quick Start D: route

Action = Refine. Go to Core Workflow: Refinement, step 1.

## Core Workflow: Refinement, Step 1 (Locate the skill, MANDATORY first step)

- Skill location: OUTDIR/target (given by the operator). Glob `**/skills/<name>/SKILL.md` not needed because the operator supplied the location.
- Gitignore-exclusion check (per plugin-rulebook references/gitignore-exclusion.md): I ran `git check-ignore -v` on target/SKILL.md. It matches a global ignore rule `target/` (from ~/.gitignore_global). The skill text says a draft in a gitignored directory is not the real target. Disclosure: the simulated operator instruction says this location IS the target, so I proceed with it under the operator's explicit direction. The interpretation is recorded here, not silently overridden.
- Mirror-pair check (R19): `<repo root>/.claude/skills/demo-skill/` does not exist, so there is no mirror pair. Treated as one logical skill. No Mirror question asked.
- Not in user-space or in the plugin cache. No user-space WARN, no cache REFUSE. "Not found anywhere" question not needed.

### Step 1: pre-analysis (before any interview; the escape-hatch question was routing, not an interview question)

Loaded references/pre-analysis-checklist.md and ran every check.

Resolved tiers (plugin-rulebook found at plugins/plugin-devkit/skills/plugin-rulebook/assets/settings.json):
- R13 (SKILL.md total lines): weak_warning 100, soft_warning 300, warning 490, critical 500
- R18 (inline code block lines): weak_warning 10, warning 20, critical 30
- R21: description min 80 / max 1024; when_to_use max 512; combined min 80 / max 1536
- R8: descriptions over 80 chars need `>-`

Evidence gathered:
- SKILL.md: 13 lines (frontmatter included). references/a.md 5 lines, references/b.md 4 lines.
- description = "Helps with demo tasks." (22 characters). No `when_to_use`. allowed-tools = `Read`. No non-standard fields (no `version`).
- Body: `## Quick Start` only. Text: "Ask the user which file to process. Then grep the file for TODO markers and summarize them. See references/a.md for details."
- a.md: "Read references/b.md for the full list of marker formats." (imperative directive to read another references file)
- No workflows/, no scripts/, no `$ARGUMENTS`, no `argument-hint`.

Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: none under R5/R8 (description is 22 chars, under the 80-char `>-` threshold). Size issue is reported under R21 below.
Large sections (≥50 lines): none
Reference files: 2 [clusters: a.md + b.md (both cover how TODO/FIXME markers are summarized; topic overlap is plausible but not certain, so they go into the step-3 ask and the operator decides) | oversize ≥400 lines: none]
Workflow files: 0 [oversize ≥300 lines: none] [workflow→ref chain violations: none]
Reference chain violations (ref→ref): references/a.md line 3 "Read references/b.md for the full list of marker formats."
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" collects input as free text without AskUserQuestion (matches the `ask the user` scan). Note: a file path is close to unbounded, so this is a borderline case under Pattern 4 of ask-user-question-patterns.md; it is flagged because the operator's own context called the intake sloppy, and the operator decides at the Intake question.
Argument consistency (R22): none (no `$ARGUMENTS`, `$0`/`$1`, or declared arguments in the body or frontmatter)
when_to_use split candidate: no (no `Use when` clause embedded in a description; description is far under 400 characters)
Description size (R21): description 22 chars is below the 80-char floor; combined length 22 is below the combined 80-char floor. (Finding.)
Tool scoping (R6): undeclared tools: Grep (Quick Start says "grep the file"; `allowed-tools` declares only Read) — Major / unused declared tools: none (Read is implied by "process the file"; it is not named as an explicit invocation, so it is not flagged)
Dead links: none (references/a.md and references/b.md exist) / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present; 4 of 5 missing; Minor; auto-added in step 6, so not a goal)
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: R21 description size (below the floor); reference cluster a.md + b.md (covered by the step-3 consolidation ask); missing goal verification section (optional)
R13/R18 threshold source: plugin-rulebook/assets/settings.json

### Step 1: derive and select goals (after the report, before the interview)

Loaded references/goal-derivation.md. Findings mapped by selection priority (max 3):
1. First: reference chains (ref→ref), intake violation
2. Second: undeclared tool (Grep)
3. Third / not in the ordering: cluster, missing goal verification, R21 description size (deferred)

Three goals, each with a verification and a source finding:
- G1 "Zero reference→reference chains" — verification: re-run the checklist's chain scan over references/*.md → 0 matches — source: ref→ref chain in a.md
- G2 "Intake section uses AskUserQuestion with options (or the operator keeps it free-form at the Intake question)" — verification: re-run the checklist's intake scan → 0 matches outside sections the operator kept free-form — source: intake violation in Quick Start
- G3 "Every invoked tool is declared in allowed-tools" — verification: re-run the checklist's tool-scoping scan → no undeclared tools — source: Grep undeclared

QUESTION (AskUserQuestion, multiSelect: true)
- question: "Which goals should this refinement session aim for? (up to 3)"
- header: "Goals"
- options:
  - "Zero reference chains": no reference→reference chains; verify: chain scan over references/*.md returns 0 matches
  - "Intake via AskUserQuestion": intake sections use AskUserQuestion with options; verify: intake scan returns 0 matches outside sections kept free-form
  - "Declare every tool": every invoked tool is in allowed-tools; verify: tool-scoping scan finds no undeclared tools
  - ("Other" is offered automatically for a custom goal, which would need a verification check)
- SIMULATED ANSWER: all three goals selected. No custom goal, so no follow-up verification-check question.

Recorded goals: G1, G2, G3. The deferred candidates stay listed in the pre-analysis report. The interview is scoped to these goals, and step 8 would measure them (the checklist is reloaded there).

## Requirements Interview

### BATCH 1: Refinement Focus — SKIPPED

Reason: the escape-hatch answer was "Infer from context", which skips BATCH 1 (this matches the BATCH 2 routing bullet "skip BATCH 1 and come straight here"). Also, since goals were selected, Question 1 would have been skipped anyway. Nothing was asked, so there are no BATCH 1 answers and no exclusions recorded (Question 4 was not asked; no area is excluded).

### BATCH 2: Implementation Details (one question at a time)

Routing: "Infer from context" → come straight here. Ask only the questions whose trigger pre-analysis detected:
- Extraction (large low-frequency section ≥50 lines): not triggered (no section ≥50 lines) → not asked
- Intake (intake pattern violation): TRIGGERED, and its goal (G2) was selected → asked
- Arguments (R22 mismatch): not triggered → not asked
- Desc split (when_to_use split candidate): not triggered → not asked
- Prod checks: asked in every refinement session → asked
- Reference clusters are not asked here; step 3 is the single consolidation ask.

QUESTION BATCH2-Intake (AskUserQuestion)
- question: "Section 'Quick Start' collects user input without AskUserQuestion (it says 'Ask the user which file to process', free-text intake). Convert it?"
- header: "Intake"
- options: "Yes" (replace free-form intake with an AskUserQuestion block; derive options from observed inputs) / "No" (keep free-form; this section intentionally takes open-ended input)
- SIMULATED ANSWER: "Yes"

QUESTION BATCH2-Prod checks (AskUserQuestion, multiSelect: true)
- question: "Which production checks should I run?"
- header: "Prod checks"
- options: "Security scan" / "Error handling" / "Tool scoping" / "None needed"
- SIMULATED ANSWER: the operator rule says to choose "Yes" for any BATCH 2 question, but this question has no "Yes" option. Disclosed deviation: I read "Yes" as "run the checks" and selected the three substantive options (Security scan, Error handling, Tool scoping) and not "None needed".

Approved scope (documented): convert the Quick Start intake to AskUserQuestion (Yes); run Security scan, Error handling and Tool scoping checks; goals G1-G3. Standard sections are auto-added in step 6 with no question needed.

## Step 2: Load workflow reference

Read references/refinement-workflow.md (preservation gates, validation phases, consolidation procedure, Rollback).

## Step 3: Identify consolidation opportunities (BEFORE changes)

The target has a references/ directory, so this step applies.
- Files with line counts: references/a.md — 5 lines ("Details": how summaries list each TODO with its line number; contains the "Read references/b.md" directive); references/b.md — 4 lines ("Marker Formats": TODO:/FIXME: formats).
- Grouping by topic: both describe how TODO/FIXME markers are summarized (a.md: summary output; b.md: marker formats), and a.md already points at b.md. Flagged as a potential merge (2 files, same domain). I am not certain they share one topic, so per the step, they are included in the ask and the operator decides.
- Merging would also remove the a.md→b.md chain (goal G1).

QUESTION (AskUserQuestion) — the single consolidation ask
- question: "Should we consolidate these files (references/a.md + references/b.md)? Saves about 2 lines (9 → about 7, the duplicate heading and blank lines), improves clarity, and removes the reference→reference chain."
- header: "Consolidate"
- options: "Consolidate" / "Leave as-is"
- SIMULATED ANSWER: no answer was given for this question, so the first option: "Consolidate"

Operator approved consolidation, so proceed. Note that this only records the approval to merge; nothing is merged because step 6 never runs (see step 5).

## Step 4: Apply preservation gates (four gates, in order; Gates 1 and 2 run here)

GATE 1: Content Audit (list ALL content; classify core 80%+ or supplementary <20%)
- SKILL.md (13 lines): frontmatter (name, description, allowed-tools) — core; `## Quick Start` (intake sentence + grep-and-summarize instruction + pointer to references/a.md) — core, used in every activation
- references/a.md (5 lines): summary output format (TODO plus line number) and the directive to read b.md — core for summarizing output (used whenever the skill runs)
- references/b.md (4 lines): marker formats (TODO:, FIXME:) — supplementary to core, needed when deciding what counts as a marker; keep the content
- No scripts/ or assets/.
Gate 1 check: full audit complete → proceed to Gate 2.

GATE 2: Capability Assessment (for each proposed change: will it impair execution?)
- Convert intake to AskUserQuestion: an edit in place, execution path unchanged → NO impairment → safe
- Add `Grep` to allowed-tools: adds a capability, impairs nothing → safe
- Consolidate a.md + b.md: consolidated file keeps all content (summary format plus both marker formats); the skill still works → NO impairment → safe to consolidate; deleting the two originals is only possible after Gate 3 and Gate 4
- Auto-add 4 standard sections: additive → safe
Gate 2 check: all pass. No change needs to be downgraded to migrate-only.

GATES 3 and 4: not run in this session. Per step 4 they apply at each move and each deletion in step 6. Step 6 does not run (see step 5). The early Gate 4 ask about the consolidation's source files is collected only "once they have chosen to apply changes (step 5)" — the operator did not choose to apply, so that ask was NOT made (this is not a silent skip; it is conditional on the step-5 answer).

## Step 5: Plan-only exit

The request did not use plan-only wording ("just plan it", "don't apply", "write a changes.md"), so the ask is required.

QUESTION (AskUserQuestion)
- question: "Apply the approved scope to demo-skill, or exit without edits?"
- header: "Apply"
- options: "Apply changes" / "Plan only" (write changes.md, no edits) / "Stop"
- SIMULATED ANSWER: "Stop"

"Stop" selected: the session ends here. Consequences, stated explicitly:
- Step 6 (Make changes) — NOT run: no CREATE/LINK/DELETE, no standard sections added, no Rollback settling needed (no edit happens).
- Step 7 (Validate result), step 8 (Measure goals), step 9 (trigger regression: neither description nor when_to_use changed) and step 10 (plugin-rulebook and skill-reviewer passes) — NOT run, because no edits were made.
- No changes.md written (that is only the "Plan only" branch).
- `<skill-improvement-complete>` is NOT emitted: the three conditions (plugin-rulebook FAILs fixed, skill-reviewer Critical/Major fixed, every selected goal passed) were not established, since goals G1-G3 were never measured and no compliance run happened.
- Consolidation approved at step 3 was not performed.

## Final state

Edits made to target: none. target/ is byte-identical to fixtures/demo-skill (files: SKILL.md, references/a.md, references/b.md). The fixture original was not modified. final-tree.txt lists the files.

Session summary
- Approved scope (not applied): convert intake (Yes); prod checks Security scan, Error handling, Tool scoping; goals G1 zero ref chains, G2 intake via AskUserQuestion, G3 declare every tool; consolidate a.md + b.md.
- Findings: ref→ref chain (a.md→b.md), free-text intake in Quick Start, undeclared Grep, description below R21 floor, 4 missing standard sections, cluster a.md + b.md.
