# Dry-run transcript: skill-refiner-interactive, eval 10 (three compliance rounds, accept at the cap)

Conventions: "Q:" is an AskUserQuestion the skill would fire; "A:" is the simulated operator answer. Target is OUTDIR/target (a copy of fixtures/demo-skill).

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."

## Quick Start (steps A-D)

- A. Predating-context check: the request only names the skill and the action, so this is not predating context. No escape-hatch question. BATCH 1 will run as normal.
- B. Skill already named in the request: skipped.
- C. Request says "refine", so the Action question is skipped. Route: Refine.
- D. Route to Core Workflow: Refinement.

## Core Workflow: Refinement, step 1 (Locate the skill)

Simulated operator answer: skill already located (OUTDIR/target). No Glob search, no user-space/cache handling, no mirror pair (no .claude/ copy), so the R19 halt does not apply.

### Pre-analysis (references/pre-analysis-checklist.md)

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: description is single-line (no >- block scalar; R8). Only name/description/allowed-tools present, none non-standard.
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary details and marker formats) ] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md "Read references/b.md for the full list of marker formats."
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" collects input without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): finding — description is 22 characters, under the R21 floor
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: frontmatter issue (R8/R21), reference cluster, missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Goal selection (references/goal-derivation.md)

Q: "Which goals should this session meet?" header "Goals", multiSelect true, options (each description shows its verification check):
  1. "Zero reference chains" — re-run the ref->ref chain scan over references/*.md -> 0 matches
  2. "Intake uses AskUserQuestion" — re-run the intake scan -> 0 matches
  3. "Every tool declared" — re-run the tool-scoping scan -> no undeclared tools
A (simulated): select all three. Recorded goals G1, G2, G3. Deferred candidates stay in the report only.

## Requirements Interview (BATCH 1)

Goals were selected, so Question 1 is skipped. Questions 2-4 asked one at a time. No answers were given for them, so the first option is taken.

- Q2: "What specific problems are you seeing?" header "Key Issues", multiSelect. Options: Hard-to-follow instructions / Scattered references / Nested sections. A: "Hard-to-follow instructions".
- Q3: "What would success look like?" header "Success", single-select. Options: Clearer workflow / Lower token cost / Production-ready. A: "Clearer workflow".
- Q4: "Any areas to exclude or preserve as-is?" header "Scope Limits", multiSelect. Options: Keep validation gates / Keep tool scoping. A: "Keep validation gates". Consequence: step 6's auto-add of `## Testing & Validation` is excluded; the tool-scoping goal is not limited because "Keep tool scoping" was not chosen.

Approved scope documented: goals G1-G3; hard-to-follow instructions; clearer workflow; Testing & Validation left out.

## BATCH 2 (Implementation Details)

Routing: "Define explicitly"/"Infer" not chosen (no escape hatch), so BATCH 2 follows BATCH 1. Only questions whose trigger was detected (and whose finding maps to a selected goal or has no goal row):

- Extraction: no section >=50 lines. Not asked.
- Intake: detected, maps to selected goal G2. Q: "Section 'Quick Start' collects user input without AskUserQuestion (asks the user free-form for a file). Convert it?" header "Intake". Options: Yes / No. A (first option): Yes.
- Arguments (R22): none detected. Not asked.
- Desc split: no embedded trigger clause. Not asked.
- Prod checks (asked in every session): Q: "Which production checks should I run?" header "Prod checks", multiSelect. Options: Security scan / Error handling / Tool scoping / None needed. A (first option): Security scan. Result: Grep over SKILL.md and references/ for credentials, tokens, `${VAR}` substitutions: none found.

Reference-file clusters are not asked here.

## Step 2 (Load workflow reference)

Read references/refinement-workflow.md for preservation gates, validation phases, Rollback.

## Step 3 (Consolidation)

Target has references/. Listing: a.md (5 lines), b.md (4 lines). Same topic (TODO summary and marker formats), flagged as a merge.
Q: "Should we consolidate these files? Saves 1 file, improves clarity." Options: Consolidate / Leave as-is. A (first option): Consolidate.
Plan: merge b.md into a.md (destination a.md).

## Step 4 (Preservation gates)

- GATE 1 (Content audit): SKILL.md Quick Start is core (80%+). a.md: summary format, core. b.md: marker formats, core for the skill's one task (used every activation), so it must be migrated intact, not dropped.
- GATE 2 (Capability assessment): the merge does not impair execution if all marker formats survive. Migrate only.
- GATE 4 for the consolidation's source file (asked right after the step-3 approval, before step 6): Q: "Delete references/b.md after its content is merged into references/a.md?" Options: Delete / Keep. A (first option): Delete. Consolidation proceeds.
- GATE 3 (Migration verification) runs in step 6 once the destination exists.

## Step 5 (Plan-only exit)

The request did not use plan-only wording, so the ask fires.
Q: "Apply the approved scope?" Options: Apply changes / Plan only / Stop. A (simulated): "Apply changes". Step 6 runs.

## Step 6 (Make changes: CREATE -> LINK -> DELETE)

Rollback settled before the first edit: the pre-edit state is the tracked fixture at evals/skill-refiner-interactive/fixtures/demo-skill/ (unmodified original); restore list is the change summary's Files created/deleted lists.

1. CREATE: references/a.md updated with a "Marker Formats" section holding b.md's two marker lines (the destination, created first). GATE 3: destination exists and contains both formats. The `Read references/b.md` directive is removed (G1).
2. LINK: SKILL.md pointer reads "See references/a.md for details and marker formats."
3. DELETE: references/b.md removed with a Bash `rm` through a normal permission prompt, after Gate 4 approval and link verification.
4. Intake (G2): "Ask the user which file to process" replaced with an AskUserQuestion block (header "File", two options).
5. Tool scoping (G3): "grep the file" now says use Grep; `allowed-tools: Read` -> `Read Grep`.
6. Standard sections auto-added: `## When to Use`, `## When NOT to Use`, `## Reference Guide`. `## Testing & Validation` NOT added (excluded by BATCH 1 Question 4). `## Quick Start` already present.

## Step 7 (Validate result, seven phases)

1. File inventory: before SKILL.md, references/a.md, references/b.md; after SKILL.md, references/a.md.
2. Read all: complete, no gaps; both marker formats preserved.
3. Frontmatter: name and description present. Description still single-line (R8 not addressed at this stage; not a selected goal).
4. Body: 37 lines, OK against R13 tiers; workflow pattern and spawn anti-patterns clean.
5. References: a.md exists, one level deep, no ref->ref chain.
6. Tools: Grep now declared; Read declared and used; no Bash-for-dedicated-tool misuse.
7. Testing: trigger phrases are unchanged words.

## Step 8 (Measure goals)

- G1 zero reference chains: re-ran the chain scan over references/*.md -> 0 matches. PASS.
- G2 intake uses AskUserQuestion: re-ran the intake scan -> 0 matches. PASS.
- G3 every tool declared: re-ran the tool-scoping scan -> no undeclared tools. PASS.
All goals PASS; no failure ask.

## Step 9 (Trigger regression)

description/when_to_use text unchanged so far, so this step is skipped. (See the compliance rounds below: each fix there only reformats the same description words, which does not count as a text change, so step 9 is not re-entered.)

## Step 10 (Compliance and reviewer passes)

### Initial run of both checks (not a round)

- Skill(plugin-rulebook), full check on OUTDIR/target (not a mirror pair): 1 FAIL — R8 (description not in a `>-` block scalar).
- skill-reviewer agent (full, Structured output mode): counts.critical = 0, counts.major = 1 — missing Quick Start example.
- Marker status: rulebook FAIL and a Major open. NO MARKER EMITTED

### Compliance round 1

- Fix pass: R8 — converted description to a `>-` block scalar (same words: format-only, so step 9 not re-entered). Major — added a worked Example to Quick Start (`notes.txt` line 4 TODO).
- Re-run both checks (simulation: fixes do not clear the findings):
  - plugin-rulebook: 1 FAIL (R8)
  - skill-reviewer: counts.critical 0, counts.major 1 (missing Quick Start example)
- Round count 1 of 3 used. Findings remain, so continue. NO MARKER EMITTED

### Compliance round 2

- Fix pass: R8 — re-wrapped the description block (same words, format-only, no step 9). Major — reworked the example into an Input/Output block.
- Re-run both checks (simulation):
  - plugin-rulebook: 1 FAIL (R8)
  - skill-reviewer: counts.critical 0, counts.major 1 (missing Quick Start example)
- Round count 2 of 3 used. NO MARKER EMITTED

### Compliance round 3

- Fix pass: R8 — re-wrapped the description block again (format-only, no step 9). Major — added a FIXME case to the example.
- Re-run both checks (simulation):
  - plugin-rulebook: 1 FAIL (R8)
  - skill-reviewer: counts.critical 0, counts.major 1 (missing Quick Start example)
- Round count 3 of 3 used (the cap). Findings remain after round 3. NO MARKER EMITTED

### Post-round-3 question (the cap)

Q: "Findings remain after 3 compliance rounds (plugin-rulebook R8 FAIL; skill-reviewer Major: missing Quick Start example). How do you want to proceed?" header "Round cap".
Options:
  1. "Continue another round"
  2. "Accept remaining findings with reason"
  3. "Stop"
A (simulated): "Accept remaining findings with reason". Reason given: "cosmetic, tracked separately".
Recorded: R8 FAIL (plugin-rulebook) and the Major (missing Quick Start example, skill-reviewer) accepted with reason "cosmetic, tracked separately".

### Change summary

```
Lines: 13 → 48
Frontmatter: description converted to a >- block scalar (R8 still reported as FAIL, accepted); allowed-tools Read → Read Grep
Sections added: When to Use, When NOT to Use, Reference Guide (Testing & Validation not added: excluded by BATCH 1 Question 4)
Files created: none
Files deleted: references/b.md (merged into references/a.md)
plugin-rulebook: 1 accepted with reason ("cosmetic, tracked separately")
Accepted findings: R8 FAIL; skill-reviewer Major "missing Quick Start example" — reason: "cosmetic, tracked separately"
Goals: G1 PASS, G2 PASS, G3 PASS
```

### Marker gate

Both checks ran. All three conditions hold: every plugin-rulebook FAIL is fixed or accepted with a recorded reason (R8, accepted via the round-cap question); every skill-reviewer Critical/Major is fixed or accepted with a recorded reason (the Major, accepted); every selected goal passed. The marker is emitted once:

```
<skill-improvement-complete>
```

End of run. Marker emissions in this transcript: 1 (above). All earlier points show NO MARKER EMITTED.
