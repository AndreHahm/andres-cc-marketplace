# Simulated run: skill-refiner-interactive on demo-skill (eval 4)

Operator: "Refine the skill in OUTDIR/target so it follows best practices."
Skill files read from the worktree copy. Target = OUTDIR/target (copy of fixture). AskUserQuestion calls are simulated with the given answers.

## Step 0 - Predating context
No skill content or problem description was supplied, only a path. No predating context, so no escape-hatch question. Continue to Step 1.

## Step 1 - Locate (Quick Start Step 1 / Core Workflow step 1)
Operator answer given: skill already located (OUTDIR/target). No plain-text question asked. Not a gitignored path; no mirror pair (only one copy); not user-space or cache.

## Quick Start Step 2 - Action ask (simulated)
Q: "What would you like to do with this skill?" Options: Refine / Validate. Answer: Refine (request wording matches). Route: Core Workflow: Refinement.

## Pre-analysis (references/pre-analysis-checklist.md)
R13/R18 thresholds from plugin-rulebook settings; SKILL.md has 13 lines: OK.
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: description is single-line (needs >-)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md] [oversize >=400: none]
Workflow files: 0
Reference chain violations (ref->ref): references/a.md line 5 -> references/b.md
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep ("grep the file") / unused declared: none
Dead links: none / Cross-skill references: none (b.md only linked from a.md, not SKILL.md)
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: missing goal verification, reference cluster, frontmatter issue
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

## Goal derivation and selection (goal-derivation.md)
Priority 1: ref chain, intake. Priority 2: undeclared tool. Cap 3 goals.
ASK (multiSelect): "Which goals for this session?" Options: G1 Zero reference->reference chains (verify: chain scan -> 0) / G2 All intake uses AskUserQuestion with options (verify: intake scan -> 0) / G3 Every invoked tool declared in allowed-tools (verify: tool scan -> none undeclared).
Simulated answer: select all three. Recorded.

## Requirements Interview
BATCH 1 (Question 1 skipped since goals selected):
1. Q2 "What specific problems are you seeing?" options: Hard-to-follow instructions / Scattered references / Nested sections -> answer: first option, Hard-to-follow instructions.
2. Q3 "What would success look like?" options: Clearer workflow / Lower token cost / Production-ready -> answer: Clearer workflow.
3. Q4 "Any areas to exclude or preserve as-is?" options: Keep validation gates / Keep tool scoping / Nothing to exclude -> answer: Keep validation gates.
BATCH 2 (only triggered questions):
4. Intake Pattern: "Section 'Quick Start' collects user input without AskUserQuestion. Convert it?" Yes / No -> Yes (first option).
5. Production Checks (always asked): Security scan / Error handling / Tool scoping / None needed -> Security scan. (Nothing found: no credentials or ${VAR} in target.)
No other BATCH 2 question triggered (no large section, no R22 mismatch, no when_to_use split). No cluster question here; step 3 is the single consolidation ask.

## Step 2 - Load workflow reference
Read references/refinement-workflow.md.

## Step 3 - Consolidation
Files: references/a.md (5 lines), references/b.md (4 lines). Same topic (TODO markers): merge candidate.
ASK: "Should we consolidate these files? Saves N lines, improves clarity." Options: Consolidate / Leave as-is. Simulated answer: Consolidate. This is the only consolidation ask.

## Step 4 - Preservation gates
1. Gate 1 - Content Audit: SKILL.md 13 lines (Quick Start, core). references/a.md 5 lines (summary format; supplementary, linked). references/b.md 4 lines (marker formats; supplementary, only reachable via a.md). No scripts/assets.
2. Gate 2 - Capability Assessment: consolidating a.md + b.md into one file loses no content and does not impair execution; replacing free-form intake with AskUserQuestion and adding Grep to allowed-tools does not impair execution. Decision: safe. Deletion of a.md/b.md only after migration (Gate 3) and approval (Gate 4).
(Gates 3 and 4 need the destination to exist and a deletion to be proposed, so they run inside step 6 between CREATE and DELETE, still in gate order.)

## Step 5 - Plan-only exit
ASK: "Apply the approved scope?" Options: Apply changes / Plan only (write changes.md, no edits) / Stop. Simulated answer: Apply changes. Continue to step 6 (no changes.md written).

## Step 6 - Make changes, in exact order
1. CREATE references/marker-details.md (merged content of a.md + b.md; the "Read references/b.md" directive dropped because the content is now in one file).
2. Gate 3 - Migration Verification: destination exists; contains all of a.md ("Details") and b.md ("Marker Formats"); no orphaned content. APPROVED. Migration itself is auto-approved.
3. LINK SKILL.md pointer "See references/a.md for details." -> "See references/marker-details.md for details."; no other SKILL.md reference to a.md or b.md remained (grep verified).
4. Gate 4 - Operator Confirmation for deleting references/a.md (source of consolidation). ASK: "Okay to delete references/a.md? Its content now lives in references/marker-details.md." Options: Delete / Keep. Simulated answer: Delete.
5. DELETE references/a.md.
6. Gate 4 - Operator Confirmation for deleting references/b.md. ASK: "Okay to delete references/b.md? Its content now lives in references/marker-details.md." Options: Delete / Keep. Simulated answer: Delete.
7. DELETE references/b.md.
Then the non-move edits to SKILL.md (no deletion of files, no gate needed):
- Converted Quick Start intake to an AskUserQuestion block (G2).
- Added Grep to allowed-tools (G3).
- Auto-added standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide.
Orphan-warning note: between step 1 and step 3 marker-details.md was temporarily unlinked (expected interim state).

## Step 7 - Validation (seven phases)
1. Inventory: before SKILL.md + references/{a,b}.md (22 lines); after SKILL.md (53 lines) + references/marker-details.md (10 lines).
2. Read all: both files complete, no gaps.
3. Frontmatter: name and description present; single-line description still unflagged-fixed (deferred, out of selected scope); allowed-tools `Read Grep`.
4. Body: 53 lines, R13 OK; all 5 standard sections present; no spawn anti-patterns.
5. References: marker-details.md exists, linked, one level deep, no ref->ref chain.
6. Tools: no undeclared tool; Read declared but not explicitly invoked (Minor, kept).
7. Testing: activation phrases listed in Testing & Validation.

## Step 8 - Measure goals
G1 PASS, G2 PASS, G3 PASS. Details in goal-measurement.md. No FAIL, no ask needed.

## Step 9 - Trigger regression
Skipped: description and when_to_use unchanged.

## Step 10 - Compliance and reviewers
Skill(plugin-rulebook) and skill-reviewer cannot be dispatched in the simulation; recorded as not run. Change summary:
```
Lines: 13 -> 53
Frontmatter: allowed-tools += Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: references/marker-details.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: not run (simulation)
```
<skill-improvement-complete> withheld because plugin-rulebook and skill-reviewer passes did not run; goals G1-G3 all PASS.
