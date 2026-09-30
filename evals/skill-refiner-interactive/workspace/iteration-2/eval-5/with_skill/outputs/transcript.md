# Dry-run transcript: skill-refiner-interactive on demo-skill copy

Operator: "Refine the skill in OUTDIR/target so it follows best practices."

## Quick Start Step 0 (predating context)
The operator's message names a skill path but supplies no skill file contents, problem description, or ongoing discussion. No predating context -> no escape hatch, continue to Step 1.

## Step 1 (what skill?)
Skipped: simulated answer "skill already located" (path given in request: OUTDIR/target).

## Step 2 (Action question)
ASK: "What would you like to do with this skill?" header "Action"; options: Refine / Validate.
Answer: the request says refine -> "Refine".

## Step 3 (route)
Refine -> Core Workflow: Refinement.

## Refinement step 1 (locate)
Target: OUTDIR/target (copy of fixture). Not gitignored, not in plugin cache. Mirror-pair check: only one copy, n/a. Already located per operator answer.

### Pre-analysis (pre-analysis-checklist.md) report
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: description is single-line (needs `>-`); allowed-tools `Read` fine
Large sections (>=50 lines): none
Reference files: 2 [clusters: none (a.md = summary detail, b.md = marker formats; distinct topics) | oversize: none]
Workflow files: 0
Reference chain violations (ref->ref): references/a.md:5 "Read references/b.md ..."
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" with no AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: frontmatter issue, missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json (SKILL.md at 13 lines is OK at any tier)
```

### Goal derivation and selection
ASK (AskUserQuestion, multiSelect, up to 3): goals with verification checks shown:
 - "Zero reference->reference chains": verify chain scan -> 0 matches
 - "All intake uses AskUserQuestion with options": verify intake scan -> 0 matches
 - "Every invoked tool declared in allowed-tools": verify tool-scoping scan -> none undeclared
 (Other: custom goal)
Answer: select all goals. Recorded G1-G3. Deferred: frontmatter, goal verification.

## Requirements Interview
### BATCH 1 (Question 1 skipped because goals were selected)
Q2 "What specific problems are you seeing?" (Key Issues): Hard-to-follow instructions / Scattered references / Nested sections. Simulated (first option): Hard-to-follow instructions.
Q3 "What would success look like?" (Success Metric): Clearer workflow / Lower token cost / Production-ready. Simulated: Clearer workflow.
Q4 "Any areas to exclude or preserve as-is?" (Scope Limits): Keep validation gates / Keep tool scoping / Nothing to exclude. Simulated first option: "Keep validation gates" (irrelevant; target has none) - tool scoping not excluded, so G3 stays in scope.
Approved scope documented: G1-G3.
### BATCH 2
Escape-hatch route: "Define explicitly" not chosen but no predating context -> normal flow. Triggers: no large section, intake violation IS detected but its goal (G2) was selected, so ask:
ASK "Section 'Quick Start' collects user input without AskUserQuestion (...). Convert it?" header "Intake Pattern"; Yes / No. Simulated first option: Yes.
R22: none; Description Split: none.
ASK "Which production checks should I run?" header "Production Checks" multiSelect; Security scan / Error handling / Tool scoping / None needed. Simulated first option: Security scan (no credentials found: only a 13-line skill with none).

## Step 2 (load refinement-workflow.md)
Loaded for preservation gates.

## Step 3 (consolidation)
Listed references/: a.md 5 lines, b.md 4 lines. Judged distinct topics, no merge candidate -> no consolidation ask.

## Step 4 (preservation gates)
Gate 1 audit: all content is core. Gate 2: changes do not impair execution. Gate 3: no content moved. Gate 4: no deletions planned (only a one-line directive removal, see round 2 below, treated as an edit, not a file deletion).

## Step 5 (plan-only exit)
ASK "Apply the approved scope?" options: Apply changes / Plan only (write changes.md, no edits) / Stop.
Answer (operator): Apply changes. Continue to step 6.

## Step 6 (make changes) - pass 1
Edited OUTDIR/target/SKILL.md: `description` converted to `>-`; allowed-tools `Read` -> `Read Grep`; Quick Start intake converted to an AskUserQuestion block; auto-added When to Use, When NOT to Use, Testing & Validation, Reference Guide. (Per simulation control, this first round did NOT touch references/a.md.) CREATE->LINK->DELETE: no file moves.

## Step 7 (validate, seven phases)
P1 inventory: SKILL.md, references/a.md, b.md. P2 read all: ok. P3 frontmatter: name+description ok. P4 body: short, ok. P5 references: links exist; a.md chains to b.md -> not yet caught here in the simulation (caught by measurement next). P6 tools: Read, Grep declared. P7 activation: trigger phrases unchanged in meaning.

## Step 8 (measure goals) - MEASUREMENT PASS 1
G1 FAIL (a.md line 5 still says "Read references/b.md"), G2 PASS, G3 PASS. Details in goal-measurement.md.
ASK "Goal 'Zero reference->reference chains' did not pass. Verification: chain scan -> 0 matches. Actual: references/a.md:5 still has a directive. Accept with a recorded reason, or continue refining?" Options: Accept with reason / Continue refining.
Answer: Continue refining.

## RETURN TO STEP 6 (loop 1, focus: G1)
Edited references/a.md: removed the "Read references/b.md" line. Edited SKILL.md: Quick Start now says "See references/a.md for details and references/b.md for the full list of marker formats" (b.md stays reachable one level deep, LINK before removing the chain). No file deleted.

## Step 7 re-run (validate) 
Phase 5 references: a.md has no further references, b.md reachable from SKILL.md; no chains. Other phases unchanged.

## Step 8 (measure goals) - MEASUREMENT PASS 2
G1 PASS, G2 PASS, G3 PASS. No failed goals; nothing to accept. Details in goal-measurement.md.

## Step 9 (trigger regression)
`description` changed (format only: wording identical, now `>-`). ASK Trigger Regression Check: Run trigger-eval check / Quick size check only / Skip. Simulated first option: "Run trigger-eval check" -> would invoke Skill(skill-development); not dispatchable in this dry run, so NOT EXECUTED. (Note: only the YAML scalar style changed, wording identical, so regression risk is nil.)

## Step 10 (compliance + reviewers)
Would call Skill(plugin-rulebook) and the skill-reviewer agent (structured mode); NOT DISPATCHED (dry run). Simulated as no FAIL/Critical/Major findings; real rounds not run.
Change summary:
```
Lines: 13 -> 41
Frontmatter: description converted to >-; allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: none
plugin-rulebook: not run (dry-run simulation; would be PASS pending real dispatch)
```
Completion marker gate: all goals PASS; plugin-rulebook/skill-reviewer were not actually executed, so the marker would only be valid after those real runs. Simulated emit: <skill-improvement-complete>

Final file listing: see final-tree.txt.
