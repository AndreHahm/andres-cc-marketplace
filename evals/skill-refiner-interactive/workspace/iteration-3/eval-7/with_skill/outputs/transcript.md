# Dry-run transcript: skill-refiner-interactive (eval 7, declined deletion)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Fixture copied to OUTDIR/target (3 files: SKILL.md, references/a.md, references/b.md).

## Step 0 (Quick Start escape hatch)
Predating context: none beyond the request itself (no skill file pasted, no problem described). Escape hatch NOT offered; continue.

## Quick Start Step 1
Skill location was given by the operator (simulated: "skill already located").

## Quick Start Step 2 - ASK
Q: "What would you like to do with this skill?" header "Action". Options: Refine / Validate.
Simulated answer: Refine (request says "refine"/first option).

## Step 3 of Quick Start: route to Core Workflow: Refinement.

## Refinement step 1: Locate the skill
Located at OUTDIR/target (project path, not gitignored, not cache, not user-space). Mirror-pair check: no `.claude/skills/` twin, so not applicable.

### Pre-analysis (references/pre-analysis-checklist.md)
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13; tiers from fallback, plugin-rulebook settings not consulted in dry-run, 13 is far below any tier)
Frontmatter issues: description is single-line (needs >-)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details)] [oversize >=400: none]
Workflow files: 0
Reference chain violations (ref->ref): references/a.md "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep ("grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: frontmatter single-line description; missing goal verification; reference cluster
R13/R18 threshold source: skill-development fallback
```

### Goal derivation (references/goal-derivation.md)
Findings exceed 3; priority order gives 3 goals:
1. Zero reference->reference chains (verify: chain scan -> 0 matches) [first tier]
2. All intake uses AskUserQuestion with options (verify: intake scan -> 0 matches) [first tier]
3. Every invoked tool declared in allowed-tools (verify: tool-scoping scan -> none undeclared) [second tier, first of the second tier]
Deferred: frontmatter issue, missing goal verification, cluster.

ASK (multiSelect, up to 3): "Which goals should this session measure?" Options: the 3 goals above, each description showing its verification check; "Other" for custom.
Simulated answer: select all three. Custom goal: none.

### Requirements Interview (interview-question-templates.md)
BATCH 1 (goals selected, so Question 1 skipped; one question at a time):
- Q2 "What specific problems are you seeing?" options: Hard-to-follow instructions / Scattered references / Nested sections. Answer (first option): Hard-to-follow instructions.
- Q3 "What would success look like?" options: Clearer workflow / Lower token cost / Production-ready. Answer: Clearer workflow.
- Q4 "Any areas to exclude or preserve as-is?" options: Keep validation gates / Keep tool scoping / Nothing to exclude. Answer: Keep validation gates. (No conflict: goal 3 adds a declaration to allowed-tools, it does not remove or narrow scoping; noted for disclosure.)
Scope documented: the 3 goals + standard sections.

BATCH 2 (only questions whose trigger was detected, plus Production Checks):
- Intake Pattern (triggered): "Section 'Quick Start' collects user input without AskUserQuestion (...). Convert it?" Options Yes / No. Answer Yes.
- Content Extraction: not triggered. Argument Consistency: not triggered. Description Split: not triggered.
- Production Checks (always asked): options Security scan / Error handling / Tool scoping / None needed. Answer (first option): Security scan. Grep of target for credentials/keys/tokens/${VAR}: none found.
- Reference clusters are not asked here (step 3 owns it).

## Refinement step 2: Load workflow reference
Reviewed references/refinement-workflow.md conceptually (gates and validation phases) - no new asks.

## Refinement step 3: Consolidation
Files in references/: a.md (5 lines), b.md (4 lines). Same topic (TODO markers) -> flagged as a merge candidate (2 files -> 1, saves roughly 4 lines of overhead).
ASK: "Should we consolidate these files? Saves N lines, improves clarity." Options: Consolidate / Leave as-is.
Simulated answer: Consolidate (operator instruction for step 3).
Proceeding under approval; the source-file deletion is gated in step 4 / Gate 4.

## Refinement step 4: Preservation gates
- Gate 1 (Content Audit): SKILL.md - Quick Start (core); a.md "summaries list each TODO with line number" (core); b.md marker formats TODO:/FIXME: (core). All content classified core.
- Gate 2 (Capability Assessment): deleting a.md/b.md without a migrated destination would impair execution -> only migrate.
- Gate 3 (Migration Verification): applied at each move in step 6 (consolidation destination would need to exist and be complete first).
- Gate 4 (Operator Confirmation): consolidation requires deleting the source files a.md and b.md.
  ASK: "Delete references/a.md and references/b.md after merging into a single file?" Options: Approve deletion / Keep every existing file.
  Simulated answer: operator DECLINES deletion (Keep every existing file).
  Per SKILL.md Gate 4 rule: since the source-file deletion was declined, the consolidation is NOT performed (merging without deleting would only duplicate content). Reported as declined. No merged file created, no file deleted.

## Refinement step 5: Plan-only exit?
Request did not use plan-only wording. ASK: "Apply the approved scope?" Options: Apply changes / Plan only (write changes.md, no edits) / Stop.
Simulated answer: Apply changes. Continue to step 6.

## Refinement step 6: Make changes (CREATE -> LINK -> DELETE)
Nothing deleted anywhere.
1. Goal 1 (ref chain) without consolidation: references/b.md already exists (destination exists - Gate 3 OK). CREATE/LINK: SKILL.md now points directly to references/b.md and includes a Reference Guide table listing both files. Then edited a.md's directive "Read references/b.md for the full list of marker formats." into a non-directive pointer to SKILL.md's Reference Guide. This rewrites one sentence in place; content (the pointer to marker formats) is retained, nothing removed, so no Gate 4 deletion was involved.
2. Goal 2 (intake): Quick Start now asks via an AskUserQuestion block with options "Current file" / "Specify a path".
3. Goal 3 (tools): allowed-tools changed from `Read` to `Read Grep`.
4. Standard sections auto-added (no approval needed): When to Use, When NOT to Use, Testing & Validation (activation phrase + quality gates), Reference Guide. Quick Start already present.
5. Frontmatter: description reflowed to `>-` folded form with identical text (single-line description flagged in pre-analysis; not a selected goal, text unchanged).

## Refinement step 7: Validate (seven phases)
1 Inventory: before 3 files / after 3 files (same set). 2 Read all: no gaps, all original instructions preserved. 3 Frontmatter: name, description present, `>-`. 4 Body: 48 lines, well under R13 tiers; workflow pattern simple; no spawn anti-patterns. 5 References: a.md and b.md exist, one level deep, no ref->ref chains. 6 Tools: Read, Grep declared; both used (Read implied for file reading, Grep for marker search); no Bash. 7 Testing: activation phrase "summarize the TODOs in this file" matches description "Helps with demo tasks." only weakly - noted as observation, description wording not changed this session (out of selected scope).

## Refinement step 8: Measure goals
See goal-measurement.md: goals 1, 2, 3 all PASS. No failed-goal ask.

## Refinement step 9: Trigger regression check
description text unchanged (formatting only), when_to_use absent. Treated as "neither field changed" -> step skipped, stated explicitly here rather than silently. (Formatting-only reflow; length tiers unchanged.)

## Refinement step 10: Compliance and reviewer passes
Cannot dispatch Skill(plugin-rulebook) or the skill-reviewer agent in this dry run. Recorded as NOT RUN (simulation limit), not as PASS. In a real run this is where they would run, with up to 3 fix rounds.

Change summary:
```
Lines: 13 -> 48 (SKILL.md)
Frontmatter: description reflowed to >-, allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide; Quick Start gained an AskUserQuestion block
Files created: none
Files deleted: none
Consolidation of references/a.md + b.md: declined at Gate 4 (deletion declined)
plugin-rulebook: not run (dry-run cannot dispatch)
```
Completion marker: NOT emitted as a verified state, because the step-10 plugin-rulebook and skill-reviewer passes could not run in this simulation (goals all PASS).
