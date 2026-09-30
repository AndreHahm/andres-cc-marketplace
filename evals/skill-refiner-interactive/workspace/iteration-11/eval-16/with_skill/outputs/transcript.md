# Transcript: skill-refiner-interactive dry run (iteration-11 / eval-16)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Setup: fixture `evals/skill-refiner-interactive/fixtures/demo-skill/` copied to `OUTDIR/target/`. Only that copy was edited.
Note: the Grep tool is not available in this session, so scans ran through Bash `grep`. Bash here is unscoped, unlike the skill's own `Bash(wc:*)` grant, which is a simulation limitation only.

## Quick Start
- A. Predating-context check: none. The request only names the skill and the action. No escape-hatch question asked.
- B. Skipped: the request already names the skill (simulated: "skill is already located").
- C. Skipped: the request already says refine.
- D. Routed to Core Workflow: Refinement.

## Step 1: Locate the skill (MANDATORY)
- Target is the given path `OUTDIR/target/` (simulated as located). It is a plain copy outside any `skills/<name>/` or `.claude/skills/` layout, so no gitignored-draft exclusion or R19 mirror pair applies (mirror-pair check: no second copy, nothing to compare). Not user-space, not cache.

### Step 1, pre-analysis (pre-analysis-checklist.md)
Resolved thresholds: plugin-rulebook `assets/settings.json` found at `plugins/plugin-devkit/skills/plugin-rulebook/`. R13: weak 100 / soft 300 / warning 490 / critical 500. R18: 10 / 20 / 30. R21: description min 80 (critical below 20), when_to_use max 512, combined min 80 / max 1536.

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: description is single-line, 22 chars (fine for R8, which only needs >- above 80 chars); no non-standard fields; allowed-tools "Read" only
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary details / marker formats), ambiguous -> asked at step 3] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md for the full list of marker formats."
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" (plain-text intake, no AskUserQuestion)
Argument consistency (R22): none (no $ARGUMENTS / $N / $name in body, no argument-hint/arguments)
when_to_use split candidate: no (no embedded "Use when" clause, description 22 chars)
Description size (R21): description 22 chars, below the 80 floor (warning tier, above the 20 critical line); combined 22
Tool scoping (R6): undeclared: Grep (Quick Start says to grep the file) / unused declared: none (Read is the file read)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: R21 description size; missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

### Step 1, goal derivation and selection (goal-derivation.md)
Findings by priority: (1) ref->ref chain, intake violation; (2) undeclared tool Grep; (3) missing goal verification. The R21 description finding has a goal row but no slot in the priority list, so it is deferred behind the 3 highest-priority goals (cap of 3).

QUESTION (AskUserQuestion, multiSelect: true, header "Goals"): "Which goals should this refinement session measure?"
Options:
1. "Zero reference chains": Zero reference->reference chains. Verification: re-run the chain scan over references/*.md -> 0 matches. (source: ref->ref chain in a.md)
2. "Intake via AskUserQuestion": Every intake section the operator agrees to convert uses AskUserQuestion with options. Verification: re-run the intake scan -> 0 matches outside sections kept free-form. (source: Quick Start intake)
3. "Declare all tools": Every invoked tool is declared in allowed-tools. Verification: re-run the tool-scoping scan -> no undeclared tools. (source: Grep undeclared)
(Other: custom goal, needs a verification check.)
SIMULATED ANSWER: select all three. Recorded goals G1, G2, G3.

## Requirements Interview
BATCH 1: goals were selected, so Question 1 is skipped. Questions 2-4 asked one at a time. No simulated answers given for them, so the first option was chosen.

QUESTION (Q2, multiSelect, header "Key Issues"): "What specific problems are you seeing?" Options: "Hard-to-follow instructions" / "Scattered references" / "Nested sections". ANSWER (first option): Hard-to-follow instructions.
QUESTION (Q3, header "Success"): "What would success look like?" Options: "Clearer workflow" / "Lower token cost" / "Production-ready". ANSWER (first option): Clearer workflow.
QUESTION (Q4, multiSelect, header "Scope Limits"): "Any areas to exclude or preserve as-is?" Options: "Keep validation gates" / "Keep tool scoping". ANSWER (first option): Keep validation gates. Consequence: the target's Testing & Validation area stays untouched, so step 6 does NOT auto-add `## Testing & Validation` (the skill says Q4 exclusions bind auto-added sections). Tool scoping is not excluded, so G3 may edit allowed-tools.
Approved scope documented: fix the 3 goals, auto-add the standard sections that were not excluded, leave Testing & Validation out.

BATCH 2: no escape-hatch choice was made, so the full interview ran. Triggers detected: Intake yes; Extraction no (no >=50-line section); Arguments no; Desc split no. Prod checks is asked every session.

QUESTION (header "Intake"): "Section 'Quick Start' collects user input without AskUserQuestion (plain-text 'Ask the user which file to process'). Convert it?" Options: "Yes" (replace free-form intake with an AskUserQuestion block) / "No" (keep free-form; this section intentionally takes open-ended input). SIMULATED ANSWER: No. Intake stays as-is.
QUESTION (header "Prod checks", multiSelect): "Which production checks should I run?" Options: "Security scan" / "Error handling" / "Tool scoping" / "None needed". ANSWER (first option, none simulated): Security scan. Scan of SKILL.md, references/: no credentials, keys, tokens or ${VAR} substitutions found. Nothing to fix.
Standard sections are auto-added in step 6, not asked.

## Step 2: Load workflow reference
Read `references/refinement-workflow.md` (gates, validation phases, rollback, evidence-gated editing, which does not apply: no observed failures).

## Step 3: Consolidation
references/: a.md (5 lines), b.md (4 lines). Possible single-topic merge (TODO summaries + marker formats, 9 lines total, saves about 2 lines).
QUESTION (header "Consolidate"): "Should we consolidate these files? Saves about 2 lines, improves clarity." Options: "Consolidate" / "Leave as-is". SIMULATED ANSWER: Leave as-is. No consolidation, so no consolidation-source deletion ask in Gate 4 is needed.

## Step 4: Preservation gates 1 and 2 (3 and 4 at each move/deletion in step 6)
- GATE 1 Content Audit: SKILL.md 13 lines: frontmatter (core), Quick Start (core). a.md 5 lines: how summaries list TODOs (supplementary, <20%). b.md 4 lines: marker formats (supplementary).
- GATE 2 Capability Assessment: (a) remove imperative in a.md line 5 and point to b.md from SKILL.md: does not impair execution, content migrated not dropped -> safe. (b) add Grep to allowed-tools: adds capability only -> safe. (c) add 3 standard sections: additive -> safe. No deletion of unmigrated content is proposed.

## Step 5: Apply or plan only
QUESTION (header "Apply"): "Apply the approved scope?" Options: "Apply changes" / "Plan only" / "Stop". SIMULATED ANSWER: Apply changes. Step 6 runs.

## Step 6: Make changes
- Rollback (per refinement-workflow.md "Rollback"): target is a copy under `OUTDIR/target/`, not committed. Pre-edit state = the original fixture `evals/skill-refiner-interactive/fixtures/demo-skill/` (under version control); restore by recopying it.
- Order CREATE -> LINK -> DELETE applied to the b.md pointer:
  1. CREATE destination first: in SKILL.md Quick Start, extended the pointer line to "See references/a.md for details and references/b.md for the full list of marker formats." (new home for the b.md pointer).
  2. GATE 3 Migration Verification: destination exists (SKILL.md line), complete (same sentence content), link target `references/b.md` exists -> approved.
  3. GATE 4 Operator Confirmation: the a.md line is not deleted outright; its content was migrated to SKILL.md (migrations auto-approved), so no Delete/Keep ask. No file was deleted.
  4. LINK/remove: a.md line 5 "Read references/b.md for the full list of marker formats." removed (in-place Edit of an Edit-able line, content migrated).
- Frontmatter: `allowed-tools: Read` -> `allowed-tools: Read Grep` (G3).
- Standard sections auto-added to SKILL.md: `## When to Use`, `## When NOT to Use`, `## Reference Guide` (table of a.md, b.md). `## Testing & Validation` NOT added because BATCH 1 Question 4 excluded it.
- Intake left as-is per the operator's "No". No description change (R21 finding deferred, not in approved scope).

## Step 7: Validate result (seven phases)
- Phase 1 File Inventory: before: SKILL.md, references/a.md, references/b.md. After: same 3 files, no files created or deleted.
- Phase 2 Read All: re-read all three; no gaps.
- Phase 3 Frontmatter: name, description present; description single-line 22 chars (R8 fine, R21 below floor, deferred).
- Phase 4 Body: 28 lines, OK under R13; no workflow pattern, no spawn anti-patterns.
- Phase 5 References: a.md and b.md exist and are linked from SKILL.md; one level deep; no reference->reference chains.
- Phase 6 Tools: Grep used and now declared; Read declared and used; no Bash-for-dedicated-tool misuse.
- Phase 7 Testing: activation trigger phrases, e.g. "summarize the TODOs in this file", match description "Helps with demo tasks." only weakly (known, deferred R21 item).

## Step 8: Measure goals
See goal-measurement.md: G1 PASS, G2 PASS, G3 PASS. No failure, so the "Accept with reason / Continue refining" question was never asked.

## Step 9: Trigger regression check
Skipped: neither `description` nor `when_to_use` text changed this session.

## Step 10: Compliance and reviewer passes
- Not executed in this dry run: `Skill(plugin-rulebook)` and the `skill-reviewer` agent were not called (no dispatch in simulation). Reported as NOT RUN, so the completion marker is NOT emitted.
- Expected findings if run: R29 (missing Testing & Validation) would be a REQUIRED FAIL, a direct consequence of the simulated Q4 "Keep validation gates" answer; R21 description under the 80-char floor.
Change summary:
```
Lines: 13 -> 28
Frontmatter: allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Reference Guide (Testing & Validation excluded by operator scope)
Files created: none
Files deleted: none
plugin-rulebook: NOT RUN
```
(a.md: 5 -> 3 lines, the chain directive removed; b.md unchanged.)
`<skill-improvement-complete>` not emitted because step 10's two checks were not run.
