# Transcript: skill-refiner-interactive dry run (eval-7, declined deletion)

Target: OUTDIR/target (copy of fixtures/demo-skill). Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Simulated answers: skill located; all goals; consolidate; Gate 4 declines any deletion; step 5 "Apply changes". Unanswered asks use the first option.

## Step 0 (escape hatch)
No predating context (no skill file pasted, no problem described; only a path). Escape-hatch question NOT asked.

## Step 1 (plain-text: which skill?)
Already answered by the request (path). Skipped.

## Step 2 (AskUserQuestion: Action)
Question: "What would you like to do with this skill?" Options: Refine / Validate. Simulated: first option, Refine (the request also said "refine").

## Step 3 (route) -> Core Workflow: Refinement

## Refinement step 1: Locate the skill
- Path is a project-local directory under OUTDIR, not gitignored-draft, not user-space, not plugin cache. No REFUSE/WARN.
- Mirror-pair (R19) check: no `.claude/skills/demo-skill` counterpart. Not applicable.
- Pre-analysis (references/pre-analysis-checklist.md). plugin-rulebook settings not loaded in this dry run, so R13/R18 use the fallback (500 lines / 30-line blocks).

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: single-line description (needs >-); description has no trigger phrases
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (marker/summary details)] [oversize >=400: none]
Workflow files: 0
Reference chain violations (ref->ref): references/a.md line 5 "Read references/b.md ..."
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" (no AskUserQuestion)
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep ("grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - flag as Missing
Deferred goal candidates: frontmatter issues, missing goal verification, reference cluster (consolidation handled at step 3)
R13/R18 threshold source: skill-development fallback
```

### Goal derivation (references/goal-derivation.md)
AskUserQuestion, multiSelect, max 3 goals (each option shows its verification check; "Other" = custom goal):
1. "Zero reference->reference chains" - check: re-run the chain scan over references/*.md -> 0 matches
2. "All intake uses AskUserQuestion with options" - check: re-run the intake scan -> 0 matches
3. "Every invoked tool is declared in allowed-tools" - check: re-run the tool-scoping scan -> no undeclared tools
Simulated: all three selected. Custom goals: none.

## Requirements Interview
- BATCH 1: goals selected, so Question 1 skipped. Q2 (specific problems), Q3 (success), Q4 (exclude/preserve) asked one at a time; simulated first options: "Hard-to-follow instructions", "Clearer workflow", "Keep validation gates". Scope documented.
- BATCH 2 (only triggered questions):
  - Large low-frequency section: not triggered.
  - Intake Pattern: triggered. Question "Section 'Quick Start' collects user input without AskUserQuestion (...). Convert it?" Options Yes / No. Simulated: Yes.
  - Argument Consistency: not triggered. Description Split: not triggered.
  - Production Checks (always asked): options Security scan / Error handling / Tool scoping / None needed. Simulated: first, Security scan.
  - Reference clusters: not asked here (step 3 is the single consolidation ask).

## Refinement step 2: load references/refinement-workflow.md (gates, validation phases)

## Refinement step 3: Consolidation opportunities
Files: references/a.md (5 lines), references/b.md (4 lines). Same topic (TODO summary and marker formats), a links to b. 
Question: "Should we consolidate these files? Saves N lines, improves clarity." Options: Consolidate / Leave as-is. Simulated: Consolidate.
Plan: merge b.md's content into a.md (a.md is already the file SKILL.md links), replacing a.md's pointer to b.md with the content itself.

## Refinement step 4: Preservation gates
- Gate 1 (Content audit): SKILL.md 13 lines core; a.md 5 lines core-ish detail; b.md 4 lines marker formats (supplementary).
- Gate 2 (Capability): merging b.md into a.md loses nothing; intake conversion preserves the same choice; adding Grep to allowed-tools only widens a needed grant. No change impairs execution. The one deletion candidate (b.md, the consolidation source) was not needed for execution.
- Gate 3 (Migration verification): destination a.md gets all 2 marker bullets (TODO:, FIXME:); link from SKILL.md to a.md unchanged; no orphans while b.md is retained and listed in the Reference Guide.
- Gate 4 (Operator confirmation): deletion of references/b.md (consolidation source). Question "Okay to delete this?" Options Delete / Keep. Simulated: DECLINE -> Keep. b.md is retained byte-for-byte; no file is deleted anywhere. Migrations are auto-approved. CREATE -> LINK happened, the DELETE leg of CREATE -> LINK -> DELETE is skipped by operator decision (disclosed).

## Refinement step 5: Plan-only exit
Wording did not request plan-only. Question: "Apply the approved scope?" Options: Apply changes / Plan only (write changes.md, no edits) / Stop. Simulated: Apply changes.

## Refinement step 6: Make changes (CREATE -> LINK -> DELETE)
Edits, all inside OUTDIR/target:
1. references/a.md: CREATE - appended "## Marker Formats" section with b.md's two bullets; LINK - removed the "Read references/b.md" directive (now redundant). Fixes the ref->ref chain.
2. SKILL.md Quick Start: replaced "Ask the user which file to process" with an AskUserQuestion block (options: file already in context / enter a path via Other); "grep the file" became "use Grep on the chosen file".
3. SKILL.md frontmatter: allowed-tools "Read" -> "Read Grep" (R6 tool completeness).
4. Standard sections auto-added (no approval needed): When to Use, When NOT to Use (no sibling skills exist to name, so the redirections are stated as out-of-scope work, no invented skill names), Testing & Validation, Reference Guide (lists a.md and b.md).
5. DELETE leg: references/b.md NOT deleted (Gate 4 declined).
Not changed (not in approved goals): single-line `description` and lack of trigger phrases (reported below).

## Refinement step 7: Validation phases
1. File inventory: before SKILL.md 13 / a.md 5 / b.md 4 lines. After SKILL.md 51 / a.md 8 / b.md 4. Same 3 files.
2. Read all: all three files load, no gaps.
3. Frontmatter: name ok; description is single-line, short, no trigger phrases (still a finding; out of approved scope, reported); allowed-tools "Read Grep" consistent.
4. Body: 51 lines, OK tier; Quick Start actionable; no spawn anti-patterns. Workflow pattern check (design-patterns.md) not loaded in dry run; trivial single-path skill.
5. References: a.md exists and links resolve; b.md exists and is listed in the Reference Guide (no orphan); one level deep; no ref->ref chain.
6. Tools: Read and Grep declared and used; AskUserQuestion is a no-op exempt; no Bash use.
7. Testing: activation phrases listed in SKILL.md Testing & Validation; Quick Start traced end to end.
Production check (Security scan) run: no credentials, tokens or ${VAR} patterns found (0 matches).

## Refinement step 8: Measure goals
See goal-measurement.md. All 3 goals PASS; no "Accept with reason / Continue refining" ask needed.

## Refinement step 9: Trigger regression
description / when_to_use unchanged -> step skipped (stated, not silent).

## Refinement step 10: Compliance and reviewer passes
- Skill(plugin-rulebook) and the skill-reviewer agent cannot be dispatched in this dry run. NOT RUN, so no PASS is claimed for either.
- Consequence: the `<skill-improvement-complete>` marker is WITHHELD in this simulation (its precondition - plugin-rulebook no FAIL, skill-reviewer no Critical/Major - is unverified).

Change summary:
```
Lines: 13 -> 51 (SKILL.md); references: a.md 5 -> 8, b.md 4 -> 4
Frontmatter: allowed-tools Read -> Read Grep; description unchanged
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: none (operator declined deletion of references/b.md at Gate 4)
plugin-rulebook: not run (dry run cannot dispatch)
```

Open items for the operator: b.md is now a duplicate of content in a.md (kept by choice); `description` is single-line with no trigger phrases; run plugin-rulebook and skill-reviewer for real.
