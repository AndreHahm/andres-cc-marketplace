# Dry-run transcript: skill-refiner-interactive (eval-1, plan-only)

Operator request: "Analyze the skill in OUTDIR/target and just write a changes.md, do not apply anything."
Target: OUTDIR/target (copy of fixtures/demo-skill; original untouched).

## Step 0 (Quick Start): Detect predating context
The request names a path but no skill file content, problem description, or ongoing discussion was provided in the conversation. Treated as NO predating context, so the escape hatch is not offered. Continue to Step 1.

## Step 1 (Quick Start): "What skill do you want to work on?" (plain text)
Simulated answer: skill is already located (OUTDIR/target).

## Step 2 (Quick Start): AskUserQuestion
- Question: "What would you like to do with this skill?" / header "Action"
- Options: "Refine" | "Validate"
- Simulated answer: first option, "Refine" (consistent with the request: write a change plan).

## Step 3 (Quick Start): Route
"Refine" -> Core Workflow: Refinement.

## Refinement step 1: Locate the skill
- Gitignore-exclusion: OUTDIR/target is not in a gitignored draft path; accepted as the real target (operator said it is already located).
- Mirror-pair check (R19): only one copy exists (no `.claude/skills/demo-skill/` sibling). Treated as one logical skill. N/A.
- Not user-space, not plugin cache. No "where should I find this skill" question needed (operator already located it).

## Refinement step 1 (cont.): Pre-analysis (references/pre-analysis-checklist.md)
Checks run:
- plugin-rulebook found; its settings.json holds no explicit R13/R18 tier values that I could resolve quickly. SKILL.md is 13 lines total, so it is OK under any tier. (Threshold source noted below.)
- Frontmatter: `description: Helps with demo tasks.` is 22 chars, under R8's 80-char limit, so single-line is fine. No non-standard fields. `allowed-tools: Read` fine. No issue.
- Sections >=50 lines: none.
- References: 2 files (a.md 5 lines, b.md 4 lines), same domain (TODO summary details / marker formats) -> one cluster. None >=400.
- workflows/: none.
- Ref->ref chain: references/a.md line 5 "Read references/b.md for the full list of marker formats." -> VIOLATION.
- Spawn anti-patterns: none.
- Intake: SKILL.md Quick Start "Ask the user which file to process." is free-form intake with no AskUserQuestion -> VIOLATION.
- R22: body uses no $ARGUMENTS/$0/$name; no argument-hint/arguments declared -> consistent. (Note: no argument is consumed even though the skill asks for a file; not an R22 mismatch.)
- when_to_use split: no embedded "Use when" clause, description short -> no.
- Tool scoping: body says "grep the file for TODO markers" -> Grep invoked but not declared (Major, R6). `Read` is declared; the body tells the operator to read the references and the target file implicitly, so not flagged as unused (judgement call).
- Dead links: references/a.md and references/b.md both exist -> none. Cross-skill references: none.
- Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide missing (Quick Start present) -> Minor, auto-added by step 6 in an apply run.
- Goal verification: absent -> Missing.

### Pre-analysis report
```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: none
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO summary details / marker formats)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md:5 -> references/b.md
Spawn anti-patterns: none
Intake pattern violations: SKILL.md Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): Grep used ("grep the file") but not declared / none unused
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent — flag as Missing
Deferred goal candidates: reference cluster (a.md + b.md), missing goal verification
R13/R18 threshold source: plugin-rulebook/assets/settings.json consulted; no resolvable R13 tiers found, 13 lines is OK regardless
```

## Refinement step 1 (cont.): Derive and select goals (references/goal-derivation.md)
Priority order: (1) ref chain, intake; (2) undeclared tool; (3) cluster, missing goal verification. Three candidates taken from priorities 1-2; rest deferred.

AskUserQuestion (multiSelect: true):
- Question: "Which goals should this refinement session measure?" / header "Goals"
- Options:
  1. "Zero reference->reference chains" — verification: re-run the checklist's chain scan over references/*.md -> 0 matches
  2. "All intake uses AskUserQuestion with options" — verification: re-run the checklist's intake scan -> 0 matches
  3. "Every invoked tool is declared in allowed-tools" — verification: re-run the checklist's tool-scoping scan -> no undeclared tools
  (+ automatic "Other" for a custom goal, which would need a verification check)
- Simulated answer: select all goals offered -> goals 1, 2, 3 selected.

## Requirements Interview
BATCH 1 (goals selected, so Question 1 is skipped; Questions 2-4, first option, one at a time):
- Q2 "What specific problems are you seeing?" (Key Issues, multiSelect) — options: Hard-to-follow instructions | Scattered references | Nested sections. Simulated: first option, "Hard-to-follow instructions".
- Q3 "What would success look like?" (Success Metric) — options: Clearer workflow | Lower token cost | Production-ready. Simulated: "Clearer workflow".
- Q4 "Any areas to exclude or preserve as-is?" (Scope Limits, multiSelect) — options: Keep validation gates | Keep tool scoping | Nothing to exclude. Simulated: first option, "Keep validation gates" (fixture has no validation gates; nothing to preserve). Note: "Keep tool scoping" was NOT chosen, so goal 3 (declare Grep) stays in scope.
Approved scope documented: the three selected goals.

BATCH 2 (only triggered questions):
- Content Extraction: not triggered (no >=50-line section).
- Intake Pattern: triggered. Question: "Section 'Quick Start' collects user input without AskUserQuestion (free-form 'Ask the user which file to process'). Convert it?" / header "Intake Pattern" / options "Yes" | "No". Simulated: "Yes".
- Argument Consistency: not triggered. Description Split: not triggered.
- Production Checks (asked every session): "Which production checks should I run?" / multiSelect / options Security scan | Error handling | Tool scoping | None needed. Simulated: first option, "Security scan". Ran a Grep-style scan over SKILL.md and references/ for credentials/keys/tokens/${VAR} substitutions: none found.
- Reference clusters are not asked here (step 3 owns consolidation).

## Refinement step 2: Load workflow reference
Reviewed the preservation gates and validation phases from references/refinement-workflow.md (by the skill's direction; content applied below).

## Refinement step 3: Consolidation opportunities
- references/: a.md 5 lines, b.md 4 lines. Same topic (TODO marker summary details). Flag merge: 2 files -> 1 (references/details.md, ~8 lines). Also removes the ref->ref chain.
- AskUserQuestion: "Should we consolidate these files? Saves N lines, improves clarity." (N = about 1 line plus one fewer file) / options "Consolidate" | "Leave as-is". Simulated: first option, "Consolidate". Approved.

## Refinement step 4: Preservation gates
- GATE 1 Content audit: SKILL.md Quick Start (core); a.md "Summaries list each TODO with its line number" (core, used every activation); b.md marker formats TODO:/FIXME: (core). All content is small and kept.
- GATE 2 Capability assessment: merging a.md+b.md keeps all content; no capability impaired. Adding Grep to allowed-tools only expands capability. PASS.
- GATE 3 Migration verification: destination references/details.md must contain the marker formats and summary-line rule before the old files are deleted (CREATE -> LINK -> DELETE).
- GATE 4 Operator confirmation: deletion of source files a.md and b.md (consolidation sources) needs approval. AskUserQuestion: "Delete references/a.md and references/b.md after their content is merged into references/details.md?" / options "Approve deletion" | "Keep the old files". Simulated: first option, "Approve deletion". (Plan-only: nothing is deleted now; approval is recorded in the draft.)

## Refinement step 5: Plan-only exit
The request already used plan-only wording ("just write a changes.md, do not apply anything"), so the "Apply changes / Plan only / Stop" ask is SKIPPED. Prior BATCH and Gate 4 approvals count as approval of findings; only the draft path needs confirming. Path ask (per changes-draft-format.md): operator already supplied... simulated operator answer: draft path is OUTDIR/changes.md. No existing draft there, so nothing to merge.
Wrote changes.md per references/changes-draft-format.md. Step 6 NOT run; no edits to OUTDIR/target; no goal measurement (step 8 skipped per plan-only rule); steps 9-10 and `<skill-improvement-complete>` not run/emitted (no edits to validate). Stop.

Verification: OUTDIR/target was left unmodified (copy of the fixture).
