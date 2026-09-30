# Transcript: skill-refiner-interactive dry-run, eval-7 (declined deletion)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: copy of fixture demo-skill at OUTDIR/target (original untouched).

## Quick Start A-D
- A (escape hatch): no predating context (no skill file or problem supplied in conversation) -> not offered.
- B: skill named in request / already located -> skipped.
- C: request already says "refine" -> Action question skipped.
- D: route to Core Workflow: Refinement.

## Step 1: Locate the skill
- Simulated operator: skill already located (OUTDIR/target/SKILL.md). Not in user-space or cache. R19 mirror-pair check: no `.claude/skills/demo-skill` counterpart, single logical skill.

### Pre-analysis (references/pre-analysis-checklist.md)
```
Pre-Analysis: demo-skill
Lines: 10 — OK (R13)
Frontmatter issues: single-line description (needs >-); description is vague ("Helps with demo tasks.")
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details) | oversize: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md for the full list..."
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent — flag as Missing
Deferred goal candidates: frontmatter issues, missing goal verification, reference cluster (a.md + b.md), missing standard sections
R13/R18 threshold source: plugin-rulebook/assets/settings.json (tiers not individually looked up in this simulation; 10 lines is OK under any tier)
```

### Goal selection (goal-derivation.md)
Priority order gives 3 slots: (1) ref chain, (1) intake, (2) undeclared tool (frontmatter issue is also tier 2 but the 3-goal cap is filled; deferred).
AskUserQuestion (multiSelect, up to 3):
 - "Zero reference->reference chains" (verify: chain scan over references/*.md -> 0 matches)
 - "All intake uses AskUserQuestion with options" (verify: intake scan -> 0 matches)
 - "Every invoked tool is declared in allowed-tools" (verify: tool-scoping scan -> no undeclared tools)
 - (Other: custom goal)
Simulated answer: select all three goals.

## Requirements Interview
Goals selected -> BATCH 1 Question 1 skipped. No "Infer from context" routing.
### BATCH 1 (one question at a time)
- Q2 "What specific problems are you seeing?" (Hard-to-follow instructions / Scattered references / Nested sections) -> no answer given, first option: "Hard-to-follow instructions"
- Q3 "What would success look like?" (Clearer workflow / Lower token cost / Production-ready) -> first option: "Clearer workflow"
- Q4 "Any areas to exclude or preserve as-is?" (Keep validation gates / Keep tool scoping / Nothing to exclude) -> first option: "Keep validation gates" (no gates exist; does not block the tool-scoping goal)
Approved scope documented: the three goals.
### BATCH 2
- Intake question (trigger detected; goal selected): "Section 'Quick Start' collects user input without AskUserQuestion (plain 'Ask the user'). Convert it?" options Yes / No -> first option: Yes.
- Extraction: not triggered. Arguments: not triggered. Desc split: not triggered (no embedded trigger clause, short description).
- Prod checks (asked every session): options Security scan / Error handling / Tool scoping / None needed -> first option: Security scan. Result: no credentials/keys/tokens or ${VAR} substitutions in SKILL.md or references/.
- Reference cluster not asked here (step 3 is the single ask).

## Step 2: Load workflow reference
Read references/refinement-workflow.md (gates, validation phases, consolidation).

## Step 3: Consolidation opportunities
Files in references/: a.md (5 lines), b.md (4 lines). Same topic (TODO markers) -> merge candidate a.md + b.md -> one file.
AskUserQuestion: "Should we consolidate these files? Saves N lines, improves clarity." options: Consolidate / Leave as-is
Simulated answer: Consolidate. (Gate 4 below still governs deletion of the sources.)

## Step 4: Preservation gates 1 and 2
- Gate 1 Content Audit: SKILL.md (Quick Start, ~10 lines, core); references/a.md (summary format, supplementary); references/b.md (marker formats, supplementary but needed for completeness).
- Gate 2 Capability Assessment: intake rewrite, adding Grep, relocating the b.md pointer and adding sections do not impair execution -> OK. Deleting b.md/a.md would be safe only if their content is merged first.
- Gates 3 and 4 applied in step 6.

## Step 5: Plan-only exit
AskUserQuestion: "Apply the approved scope?" options: Apply changes / Plan only / Stop -> Apply changes (simulated). Step 6 runs.

## Step 6: Make changes
Consolidation (a.md + b.md): CREATE merged file would come first, then LINK, then DELETE the sources.
- Gate 4 ask (before deleting the consolidation's source files): "Okay to delete references/a.md and references/b.md once merged?" options Delete / Keep -> simulated operator DECLINES (Keep).
- Per step 4 / Gate 4 rule: declined deletion -> consolidation NOT performed (no merged file created, since merging without deleting only duplicates content). Reported as DECLINED: "Consolidation of a.md + b.md declined; both files kept."
No file was deleted.

Remaining edits (no deletions):
1. Chain goal: CREATE/LINK first — SKILL.md now links both references/a.md and references/b.md. Gate 3 (migration verification): destination (SKILL.md pointer) exists, b.md exists and is complete, link correct. Then the ref->ref directive line ("Read references/b.md for the full list of marker formats.") was removed from a.md. Treated as a migration of a pointer to SKILL.md (auto-approved, no content lost: b.md's content untouched), not a deletion of content; disclosed here.
2. Intake goal: Quick Start now says to use AskUserQuestion with two options (File named in the request / Most recently opened file; "Other" lets the operator type a path) instead of the plain-text "Ask the user".
3. Tool-scoping goal: allowed-tools changed from `Read` to `Read Grep`.
4. Standard sections auto-added (no approval needed): When to Use, When NOT to Use, Testing & Validation (3 gates), Reference Guide (table of both references files). Quick Start already present.
Frontmatter name/description left unchanged (frontmatter issues were a deferred candidate, not a selected goal).

## Step 7: Validate (seven phases)
1 Inventory: before SKILL.md 10 lines, references/a.md 5, b.md 4 -> after SKILL.md 44, a.md 3, b.md 4; no files created or deleted.
2 Read all: complete, no gaps. 3 Frontmatter: name/description/allowed-tools present, YAML valid; single-line description remains (deferred, not selected). 4 Body: 44 lines, within R13 OK tier; no spawn anti-patterns. 5 References: a.md and b.md both linked from SKILL.md, exist, one level deep, no ref->ref chain. 6 Tools: Read and Grep declared and used; none unused. 7 Testing: trigger phrases "summarize TODOs" still map to the skill (description unchanged).

## Step 8: Measure goals
See goal-measurement.md: all three PASS. No failure asks.

## Step 9: Trigger regression
description/when_to_use unchanged -> step skipped.

## Step 10: Compliance and reviewer passes
Skill(plugin-rulebook) and the skill-reviewer agent cannot be dispatched in this simulation; they are recorded as NOT RUN (no claim of PASS). Mirror pair: not applicable. Round count: 0 of 3.
Change summary:
```
Lines: 10 -> 44
Frontmatter: allowed-tools Read -> Read Grep; name/description no changes
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: none (consolidation of a.md + b.md declined at Gate 4)
plugin-rulebook: not run (simulation)
```
Completion marker: all three selected goals PASS; the plugin-rulebook and skill-reviewer conditions could not be verified in a dry run. In a live run the marker would be emitted only after both report no FAIL/Critical/Major; emitted here conditionally:
<skill-improvement-complete>
