# Dry-run transcript: skill-refiner-interactive on demo-skill (iteration 4, eval 4)

Target: OUTDIR/target (copy of fixture demo-skill). Simulated operator answers applied as given.

## Quick Start
- A. Predating context: the operator supplied a request naming the skill path and "refine"; no separate skill file or problem was pasted. Escape hatch not offered. (Simulated answer "skill already located" covers B.)
- B. "What skill do you want to work on?" skipped: request already names the skill (OUTDIR/target).
- C. Action question skipped: request already says "refine".
- D. Route: Refine -> Core Workflow: Refinement.

## Step 1: Locate the skill
- Path given directly (OUTDIR/target/SKILL.md). Located; not in user-space or cache; no mirror pair (no .claude/skills copy). Gitignore/mirror checks: N/A.
- Pre-analysis (references/pre-analysis-checklist.md). plugin-rulebook settings.json not read in this sim; fallback size limits (500 / 30). Report:
```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13)
Frontmatter issues: single-line description (needs >-)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (same topic, linked by a->b)] [oversize >=400: none]
Workflow files: 0
Reference chain violations (ref->ref): references/a.md "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file" without AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep (body says "grep the file") / unused declared: none
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: missing standard sections, missing goal verification, cluster a/b
R13/R18 threshold source: skill-development fallback
```
- Goal derivation (references/goal-derivation.md).
- **QUESTION (AskUserQuestion, multiSelect, up to 3):** "Which goals should this session pursue?"
  - Options: (1) "Zero reference->reference chains" [verify: re-run chain scan -> 0 matches]; (2) "All intake uses AskUserQuestion with options" [verify: re-run intake scan -> 0 matches]; (3) "Every invoked tool is declared in allowed-tools" [verify: re-run tool-scoping scan -> no undeclared tools]; Other.
  - Simulated answer: all three selected.
- Frontmatter single-line description and cluster are lower-priority findings, not goals; handled via step 3 / step 6 below.

## Requirements Interview
- BATCH 1: goals selected, so Question 1 skipped. Q2-Q4 asked about goal areas; simulated operator: "select all goals" used as scope approval; first options chosen (Hard-to-follow instructions, Clearer workflow, Nothing to exclude). Scope documented.
- BATCH 2: Extraction (no large section): not asked. Intake: its finding maps to selected goal 2 -> asked; first option "Yes". Arguments: none. Desc split: none. Prod checks asked (every session); first option "Security scan" (Grep scan: no secrets, no ${VAR}; clean).

## Step 2: Load workflow reference
- Read references/refinement-workflow.md.

## Step 3: Consolidation
- references/ files: a.md 5 lines, b.md 4 lines. Same topic (TODO marker summaries); a.md links to b.md. Candidate merge: a.md + b.md -> details.md.
- **QUESTION (AskUserQuestion):** "Should we consolidate these files? Saves 0 lines, improves clarity." Options: "Consolidate" / "Leave as-is". Simulated answer: Consolidate.

## Step 4: Preservation gates
1. GATE 1 (Content Audit): SKILL.md core (Quick Start, 13 lines); a.md (5 lines, supplementary), b.md (4 lines, supplementary).
2. GATE 2 (Capability Assessment): consolidating a.md+b.md does not impair execution; merged file carries all content; safe to consolidate. Deleting originals safe once content lives in details.md.

## Step 5: Plan-only exit
- Request has no plan-only wording. **QUESTION (AskUserQuestion):** "Apply the approved scope?" Options: "Apply changes" / "Plan only" / "Stop". Simulated answer: Apply changes. Proceeding to step 6.

## Step 6: Make changes (CREATE -> LINK -> DELETE)
3. CREATE: target/references/details.md (merged content of a.md and b.md; the ref->ref directive dropped since content is now in one file).
4. GATE 3 (Migration Verification): destination exists, contains both a.md and b.md content, no orphans. Approved.
5. LINK: target/SKILL.md updated - pointer now `references/details.md` (old `references/a.md` pointer removed); Reference Guide table points to details.md. Same edit: Quick Start intake converted to AskUserQuestion block (goal 2), `Grep` added to allowed-tools (goal 3), description converted to `>-` multiline, and standard sections auto-added (When to Use, When NOT to Use, Testing & Validation, Reference Guide).
6. Link check: Grep for `references/a.md` / `references/b.md` in target -> 0 matches.
7. GATE 4 (Operator Confirmation) **QUESTION (AskUserQuestion):** "Okay to delete references/a.md and references/b.md (their content is now in references/details.md)?" Options: "Delete" / "Keep". Simulated answer: Delete (approved).
8. DELETE: target/references/a.md.
9. DELETE: target/references/b.md.

## Step 7: Validate (seven phases)
- Phase 1 inventory: before SKILL.md 13 lines, references a.md, b.md; after SKILL.md 49 lines, references/details.md. Phase 2 read all: complete, no gaps. Phase 3 frontmatter: name/description present, `>-`, allowed-tools `Read Grep`, no forbidden fields. Phase 4 body: 49 lines (OK); standard sections present. Phase 5 references: details.md exists and is linked, no orphans, no ref->ref. Phase 6 tools: Grep declared; Read declared and used by the skill; AskUserQuestion excluded. Phase 7 activation: "summarize the TODOs in this file" would trigger.

## Step 8: Measure goals
- Goal 1 (zero ref->ref chains): scan references/*.md for directives to read another references file -> 0 matches. PASS.
- Goal 2 (intake uses AskUserQuestion): scan for "ask the user"/free-form questions: -> 0 matches (Quick Start now an options block). PASS.
- Goal 3 (every invoked tool declared): Grep and Read declared -> no undeclared tools. PASS.

## Step 9: Trigger regression check
- description changed (reformatted to `>-` with trigger sentence). **QUESTION (AskUserQuestion):** Trigger eval. Options: "Run trigger-eval check" / "Quick size check only" / "Skip". No simulated answer -> first option. Not executable in this dry run (cannot dispatch Skill(skill-development)); not run. Size note: description ~100 chars, within R21 tiers.

## Step 10: Compliance and reviewer passes
- Skill(plugin-rulebook) and the skill-reviewer agent cannot be dispatched in this simulation; not run. Change summary:
```
Lines: 13 -> 49
Frontmatter: description converted to >- multiline with trigger sentence; Grep added to allowed-tools
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: references/details.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: not run (simulation)
```
- Completion marker withheld: step 10 checks were not executed in this simulation (goals all PASS).
