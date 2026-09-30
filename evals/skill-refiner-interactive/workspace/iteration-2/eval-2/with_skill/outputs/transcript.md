# Transcript: skill-refiner-interactive dry run (iteration-2, eval-2)

Operator: "Refine the skill in OUTDIR/target so it follows best practices."
Fixture copied to OUTDIR/target (original untouched).

## Step 0 (Quick Start: predating context)
No skill file, problem description or active discussion predates the request (only a path). Escape hatch not offered; continue to Step 1.

## Step 1 (Quick Start: which skill)
Plain-text question "What skill do you want to work on?" Simulated answer: skill already located (OUTDIR/target).

## Step 2 (Quick Start: Action)
AskUserQuestion "What would you like to do with this skill?" [Refine | Validate]. Simulated answer: Refine (from the request wording).

## Step 3 (Quick Start: route)
Refine -> Core Workflow: Refinement.

## Refinement step 1: Locate the skill
Located at OUTDIR/target (user-provided path; not in cache, not user-space, not gitignored). Mirror-pair check: no mirror, N/A.

### Pre-analysis (pre-analysis-checklist.md)
```
Pre-Analysis: demo-skill
Lines: 12 - OK (R13)
Frontmatter issues: single-line `description` (needs `>-`)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary details / marker formats)] [oversize >=400 lines: none]
Workflow files: 0
Reference chain violations (ref->ref): references/a.md -> references/b.md ("Read references/b.md")
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep ("grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: frontmatter issues, missing goal verification
R13/R18 threshold source: not read in this dry run (12 lines is OK under any tier)
```

### Goal derivation and selection (goal-derivation.md)
Priority picks (max 3): ref chain, intake violation, undeclared tool.
AskUserQuestion (multiSelect, up to 3) options:
1. Zero reference->reference chains - verify: chain scan over references/*.md -> 0 matches
2. All intake uses AskUserQuestion with options - verify: intake scan -> 0 matches
3. Every invoked tool declared in allowed-tools - verify: tool-scoping scan -> no undeclared tools
Simulated answer: all three selected.

### Requirements Interview
Goals selected -> BATCH 1 Question 1 skipped. Questions 2-4 asked one at a time, scoped to selected goals, first option each:
- Q2 "What specific problems are you seeing?" options [Hard-to-follow instructions | Scattered references | Nested sections] -> Hard-to-follow instructions
- Q3 "What would success look like?" [Clearer workflow | Lower token cost | Production-ready] -> Clearer workflow
- Q4 "Any areas to exclude or preserve as-is?" [Keep validation gates | Keep tool scoping | Nothing to exclude]  -> "Keep validation gates" (first option; note: no validation gates exist in the target, no conflict; tool scoping is a selected goal, so not excluded)
Approved scope documented: the 3 goals.
BATCH 2 (only triggered questions):
- Intake Pattern (triggered) "Section 'Quick Start' collects user input without AskUserQuestion. Convert it?" [Yes | No] -> Yes
- Argument Consistency: not triggered. Description Split: not triggered. Content Extraction: not triggered.
- Production Checks (always asked) [Security scan | Error handling | Tool scoping | None needed] -> Security scan. Result: no credentials/keys/tokens or ${VAR} substitutions in SKILL.md/references.

## Refinement step 2: Load workflow reference
refinement-workflow.md conceptually loaded (preservation gates, validation phases).

## Refinement step 3: Consolidation
references/: a.md (5 lines), b.md (5 lines), same topic (TODO marker details). AskUserQuestion "Should we consolidate these files? Saves N lines, improves clarity." [Consolidate | Leave as-is] -> Consolidate (first option). Also removes the ref->ref chain.

## Refinement step 4: Preservation gates
- Gate 1 Content Audit: all content is core (small skill).
- Gate 2 Capability Assessment: merging b.md into a.md loses nothing.
- Gate 3 Migration Verification: destination a.md gets the full "Marker Formats" content before b.md removal.
- Gate 4 Operator Confirmation: AskUserQuestion to delete references/b.md (consolidation source) [Approve | Keep] -> Approve (first option).

## Refinement step 5: Plan-only exit
AskUserQuestion "Apply the approved scope?" ["Apply changes" | "Plan only" | "Stop"] -> Apply changes (simulated).

## Refinement step 6: Make changes (CREATE -> LINK -> DELETE)
- CREATE: references/a.md now holds the Marker Formats section; the "Read references/b.md" directive was removed.
- LINK: SKILL.md pointer to references/a.md updated ("including the supported marker formats"); Reference Guide lists only a.md.
- DELETE: references/b.md removed (after links verified).
- Intake: Quick Start now uses an AskUserQuestion block with options.
- Tools: `Grep` added to allowed-tools (`Read Grep`).
- Standard sections auto-added: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start already present).

## Refinement step 7: Validate (seven phases)
1 inventory: SKILL.md + references/a.md. 2 read all: no gaps. 3 frontmatter: name + description present (single-line description left as-is: a deferred candidate, not a selected goal, and operator scope was the 3 goals). 4 body: 47 lines, OK. 5 references: a.md exists, one level deep, no chains. 6 tools: Read, Grep declared and used; AskUserQuestion exempt. 7 testing: trigger phrase "summarize the TODOs in this file" documented.

## Refinement step 8: Measure goals
See goal-measurement.md: all three PASS. No "Accept with reason" needed (no failures occurred).

## Refinement step 9: Trigger regression check
description/when_to_use unchanged -> step skipped.

## Refinement step 10: Compliance and reviewer passes
Dry-run limitation: Skill(plugin-rulebook) and the skill-reviewer agent were NOT dispatched (simulation confined to OUTDIR; manual checks above stand in). Flagged, not claimed as passed: the target's single-line `description` (R8-style `>-` issue) remains unfixed and would likely appear as a plugin-rulebook finding; 3-round loop not run.
Change summary:
```
Lines: 12 -> 47
Frontmatter: allowed-tools: Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: references/b.md (merged into references/a.md)
plugin-rulebook: not run in dry run
```
Completion marker withheld: plugin-rulebook/skill-reviewer were not actually run, so the gate in step 10 cannot be claimed satisfied. (All 3 selected goals PASS.)
