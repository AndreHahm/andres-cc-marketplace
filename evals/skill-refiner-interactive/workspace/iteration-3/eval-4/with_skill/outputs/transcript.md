# Dry-run transcript: skill-refiner-interactive on demo-skill (simulated operator)

Target: OUTDIR/target (copy of fixtures/demo-skill: SKILL.md, references/a.md, references/b.md).
Operator request: "Refine the skill in OUTDIR/target so it follows best practices."

## Step 0 - Predating context escape hatch
Conversation has no pre-provided skill file/problem beyond the request. Escape hatch not offered; continue to Step 1.

## Step 1 - Ask which skill
Plain-text question "What skill do you want to work on?" Simulated answer: skill already located (OUTDIR/target).

## Step 2 - AskUserQuestion (Action)
Question: "What would you like to do with this skill?" Options: Refine / Validate.
Simulated answer (no answer given: first option): Refine.

## Step 3 - Route
Refine -> Core Workflow: Refinement.

## Refinement step 1 - Locate skill
Skill located at OUTDIR/target (not gitignored, not user-space, not plugin cache). No mirror pair exists, so R19 check is N/A.

### Pre-analysis (references/pre-analysis-checklist.md)
plugin-rulebook settings not loaded in this simulation; fallback flat limits (500 lines SKILL.md, 30 lines code block).

Pre-Analysis: demo-skill
Lines: 13 - OK (R13, fallback limit)
Frontmatter issues: none (description single-line but short; no forbidden fields)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (same topic, TODO summary details/marker formats)] [oversize >=400: none]
Workflow files: 0
Reference chain violations (ref->ref): references/a.md -> "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: Read is used only for reference reading (not flagged)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: missing standard sections (auto-added in step 6), missing goal verification, reference cluster (handled at step 3)
R13/R18 threshold source: skill-development fallback

### Goal derivation and selection
Question (AskUserQuestion, multiSelect, up to 3 goals):
 1. "Zero reference->reference chains" (verify: chain scan over references/*.md -> 0 matches)
 2. "All intake uses AskUserQuestion with options" (verify: intake scan -> 0 matches)
 3. "Every invoked tool is declared in allowed-tools" (verify: tool-scoping scan -> no undeclared tools)
Simulated answer: select all goals (1, 2, 3). Recorded.

### Requirements Interview
Goals selected, so Question 1 of BATCH 1 skipped.
BATCH 1 Q2 "What specific problems are you seeing?" options: Hard-to-follow instructions / Scattered references / Nested sections. Simulated (first option): Hard-to-follow instructions.
BATCH 1 Q3 "What would success look like?" options: Clearer workflow / Lower token cost / Production-ready. Simulated: Clearer workflow.
BATCH 1 Q4 "Any areas to exclude or preserve as-is?" options: Keep validation gates / Keep tool scoping / Nothing to exclude. Simulated: Keep validation gates (skill has none to change).
Scope documented; proceed to BATCH 2.
BATCH 2: Intake Pattern triggered (goal 2 selected). Question: "Section 'Quick Start' collects user input without AskUserQuestion (free-form ask). Convert it?" options Yes / No. Simulated: Yes.
Other triggers (large section, R22, description split) not detected: not asked. Reference clusters not asked here (step 3).
BATCH 2: Production Checks (asked every session). Options: Security scan / Error handling / Tool scoping / None needed. Simulated (first option): Security scan. Result: no credentials, keys, tokens or ${VAR} substitutions in SKILL.md or references/.

## Refinement step 2 - Load workflow reference
references/refinement-workflow.md reviewed (preservation gates, validation phases).

## Refinement step 3 - Consolidation opportunities
references/: a.md (5 lines), b.md (4 lines). Same topic (TODO summary details and marker formats) -> merge 2 files into 1.
Question: "Should we consolidate these files? Saves N lines, improves clarity." Options: Consolidate / Leave as-is. Simulated: Consolidate. Proceeding.

## Refinement step 4 / step 5
Step 4 (gates) numbered below, Gates 1-2 run here, 3-4 at step 6.
Step 5: Question "Apply the approved scope?" Options: Apply changes / Plan only (write changes.md, no edits) / Stop. Simulated: Apply changes. Step 6 runs.

## Ordered action log (steps 4 and 6)
1. GATE 1 (Content Audit): SKILL.md = core (Quick Start, frontmatter). references/a.md (summary format + pointer to b.md) and references/b.md (marker formats) = supplementary (<20% usage). All content listed.
2. GATE 2 (Capability Assessment): consolidating a.md+b.md and converting intake does not impair execution; all content is migrated, nothing dropped. OK.
3. CREATE: references/details.md (merged content of a.md and b.md; the ref->ref "Read references/b.md" pointer removed as the content is now inline, under "## Marker Formats").
4. GATE 3 (Migration Verification): destination references/details.md exists, read back, contains all summary-format text and both marker formats from a.md/b.md. Complete.
5. LINK: SKILL.md pointer changed from references/a.md to references/details.md; Quick Start intake converted to an AskUserQuestion block with options; Grep added to allowed-tools; auto-added standard sections (When to Use, When NOT to Use, Testing & Validation, Reference Guide table listing details.md). Verified SKILL.md no longer mentions a.md or b.md.
6. GATE 4 (Operator Confirmation) for deleting references/a.md (source of consolidation). Question: "Delete references/a.md (content migrated to references/details.md)?" Options: Approve deletion / Decline. Simulated: Approve deletion.
7. DELETE: references/a.md.
8. GATE 4 (Operator Confirmation) for deleting references/b.md (source of consolidation). Question: "Delete references/b.md (content migrated to references/details.md)?" Options: Approve deletion / Decline. Simulated: Approve deletion.
9. DELETE: references/b.md.

## Refinement step 7 - Validate (seven phases)
P1 inventory: before SKILL.md + references/a.md + references/b.md; after SKILL.md + references/details.md.
P2 read all: complete, no gaps. P3 frontmatter: name + description present (description kept as short single line; no forbidden fields).
P4 body: 46 lines, OK; standard sections present. P5 references: details.md exists, one level deep, no ref->ref chains.
P6 tools: Grep and Read declared; no undeclared tools. P7 activation: "summarize the TODOs in this file" fires; "fix the TODOs" does not.

## Refinement step 8 - Measure goals
- Goal 1 zero ref->ref chains: scan of references/*.md for "references/" -> 0 matches. PASS
- Goal 2 intake uses AskUserQuestion with options: scan for "ask the user"/"prompt the user" in SKILL.md -> 0 matches; AskUserQuestion block has options. PASS
- Goal 3 every invoked tool declared: Grep now in allowed-tools -> no undeclared tools. PASS
No FAIL, so no accept/continue question.

## Refinement step 9 - Trigger regression
description and when_to_use unchanged -> step skipped.

## Refinement step 10 - Compliance and reviewer passes
Skill(plugin-rulebook) and the skill-reviewer agent cannot be dispatched in this dry run, so neither was executed and no PASS is claimed. Because the completion gate requires both to have been run, <skill-improvement-complete> is NOT emitted.
Change summary:
Lines: 13 -> 46 (SKILL.md)
Frontmatter: allowed-tools: Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: references/details.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: not run (simulation)
