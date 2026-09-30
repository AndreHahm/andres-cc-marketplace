# Transcript: skill-refiner-interactive dry run (eval 5, failed-goal loop)

Operator: "Refine the skill in OUTDIR/target so it follows best practices."
Target: copy of `evals/skill-refiner-interactive/fixtures/demo-skill/` at `OUTDIR/target/`.

## Quick Start

- A. Predating context: none (request only names the skill and the action). No escape-hatch question.
- B. Skill named in request: skipped the "What skill?" question.
- C. Action: request says "refine": skipped the Action question.
- D. Route: Refinement.

## Core Workflow: Refinement

### Step 1: Locate the skill
- Skill already located (simulated operator answer). Path is outside `~/.claude/plugins/cache/` and not gitignored. No mirror pair (no `.claude/skills/demo-skill/` counterpart), so R19 check is N/A. No user-space warning needed.

### Step 1b: Pre-analysis (pre-analysis-checklist.md)

```
Pre-Analysis: demo-skill
Lines: 13 — OK (R13)
Frontmatter issues: single-line description (`Helps with demo tasks.`, no `>-`); no forbidden `version` field
Large sections (>=50 lines): none
Reference files: 2 [clusters: none (a.md = summary format, b.md = marker formats; distinct topics)] [oversize >=400 lines: none]
Workflow files: 0 [oversize >=300 lines: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md:5 "Read references/b.md ..."
Spawn anti-patterns: none
Intake pattern violations: Quick Start — "Ask the user which file to process" without AskUserQuestion
Argument consistency (R22): none (no argument use in body, none declared)
when_to_use split candidate: no
Description size (R21): description is 22 characters, very short; not measured against tiers (candidate, deferred)
Tool scoping (R6): Grep (body says "grep the file") undeclared / Read declared and used (references link), no unused declared tools
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent — optional low-priority candidate
Deferred goal candidates: frontmatter (single-line description), description size (R21), missing goal verification
R13/R18 threshold source: skill-development fallback (500 / 30 lines; size irrelevant at 13 lines)
```

### Step 1c: Goal derivation and selection (goal-derivation.md)
Priority order: first tier has 2 findings (ref chain, intake); second tier has undeclared tool, frontmatter, description size. Top 3 offered:

ASK (AskUserQuestion, multiSelect: true):
- "Zero reference chains" — verify: re-run ref->ref scan over references/*.md -> 0 matches (source: ref->ref chain finding)
- "Intake via AskUserQuestion" — verify: re-run intake scan -> 0 matches (source: intake violation)
- "All invoked tools declared" — verify: re-run tool-scoping scan -> no undeclared tools (source: Grep undeclared)

Simulated answer: all three selected. Goals recorded: G1, G2, G3. Others listed as deferred candidates in the report above.

### Requirements Interview
Goals selected, so BATCH 1 Question 1 is skipped. (Questions asked one at a time; no operator answer supplied, so first option chosen.)

BATCH 1
- Q2 (multiSelect) "What specific problems are you seeing?" options: Hard-to-follow instructions / Scattered references / Nested sections -> first option: "Hard-to-follow instructions".
- Q3 "What would success look like?" options: Clearer workflow / Lower token cost / Production-ready -> first: "Clearer workflow".
- Q4 (multiSelect) "Any areas to exclude or preserve as-is?" options: Keep validation gates / Keep tool scoping -> first: "Keep validation gates" (the fixture has no validation gates; nothing excluded in practice; standard sections are still auto-added).
- Approved scope documented: G1-G3 plus auto-added standard sections.

BATCH 2 (Escape hatch not used, so runs after BATCH 1; asking only the questions whose trigger fired)
- Extraction: not triggered (no large section).
- Intake: triggered (maps to selected G2). "Section 'Quick Start' collects user input without AskUserQuestion ([reason]). Convert it?" options Yes / No -> first: "Yes".
- Arguments (R22): not triggered.
- Desc split: not triggered.
- Prod checks (always asked), multiSelect, options: Security scan / Error handling / Tool scoping / None needed -> first: "Security scan". Grep over SKILL.md and references/ for credentials, keys, tokens and `${VAR}` substitutions: none found.
- Approved scope documented; proceed.

### Step 2: Load workflow reference
Read `references/refinement-workflow.md` (preservation gates, validation phases).

### Step 3: Consolidation
Target has a `references/` directory: a.md (5 lines), b.md (4 lines). Grouped by topic: summary format vs marker formats, distinct topics, so no merge candidate. The consolidation AskUserQuestion was not asked (nothing to consolidate). Nothing proceeds here.

### Step 4: Preservation gates
- Gate 1 Content Audit: SKILL.md (13 lines, all core Quick Start); a.md 5 lines supplementary; b.md 4 lines supplementary.
- Gate 2 Capability Assessment: intake conversion, allowed-tools addition and added sections do not impair execution. No deletion proposed.
- Gates 3 and 4: apply at move/delete time in step 6. No moves or deletions are planned, so Gate 4 asks nothing.

### Step 5: Plan-only exit
Request does not use plan-only wording, so ask.
ASK: "Apply the approved scope?" options: "Apply changes" / "Plan only" / "Stop".
Simulated answer: "Apply changes". Continue to step 6.

### Step 6: Make changes — pass 1
Rollback: target is an untracked copy, the fixture original remains as the restore point. Edits to `OUTDIR/target/SKILL.md` only:
- Quick Start: free-form "Ask the user" replaced with an AskUserQuestion block (2 options); "grep the file" now says "use Grep".
- `allowed-tools: Read` -> `Read Grep`.
- Auto-added standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (table listing a.md and b.md).
- SIMULATION CONTROL: this first round of edits missed the reference-chain fix. `references/a.md` untouched (line 5 still "Read references/b.md ...").
- No deletions, no moves. `description` and `when_to_use` unchanged.

### Step 7: Validate result (pass 1)
1 inventory: SKILL.md, references/a.md, references/b.md (no files added or removed). 2 read all: complete. 3 frontmatter: name and description present, single-line description (deferred). 4 body: 13 -> ~45 lines, OK vs R13. 5 references: links resolve; ref->ref chain still present at a.md:5 (noted, handled by goal measurement). 6 tools: Read and Grep declared and used. 7 testing: activation phrase "summarize the TODOs" matches description only loosely (short description, deferred).

### Step 8: Measure goals — MEASUREMENT PASS 1
See `goal-measurement.md`, round 1. G1 FAIL (a.md:5 still says "Read references/b.md"), G2 PASS, G3 PASS.
ASK (AskUserQuestion): "Goal 'Zero reference chains' did not pass. Verification: re-run chain scan -> 0 matches. Actual: references/a.md line 5 still says 'Read references/b.md'. Accept with a recorded reason, or continue refining?" Options: "Accept with reason" / "Continue refining".
Simulated answer: "Continue refining".

### RETURN to step 6 (focus: G1)
### Step 6: Make changes — pass 2
Edited `references/a.md` line 5: "Read references/b.md for the full list of marker formats." -> "The supported marker formats are listed in SKILL.md's Reference Guide." b.md stays reachable through SKILL.md's Reference Guide (one level deep). No deletions.

### Step 7 (re-run, abbreviated): only phase 5 and 6 affected
Phase 5 references: all links exist, one level deep, no ref->ref directives. Phase 6 tools unchanged, OK.

### Step 8: Measure goals — MEASUREMENT PASS 2
See `goal-measurement.md`, round 2. G1 PASS, G2 PASS, G3 PASS. No FAIL so no ask. Gate on `<skill-improvement-complete>` for goals is satisfied.

### Step 9: Trigger regression check
Neither `description` nor `when_to_use` changed: step skipped, no Trigger eval question.

### Step 10: Compliance and reviewer passes
Dry-run limitation: `Skill(plugin-rulebook)` and the `skill-reviewer` agent cannot be dispatched. Simulated as run with no REQUIRED-rule FAILs and no Critical/Major findings (an assumption, not a measured result; real run would verify, including deferred frontmatter/R21 candidates that could surface as findings). Round 1 of max 3; no fix rounds needed, so the round-cap question is not asked.

Change summary:
```
Lines: 13 -> 45 (SKILL.md)
Frontmatter: allowed-tools Read -> Read Grep; description unchanged
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: none
Files deleted: none
plugin-rulebook: not dispatched in dry run (simulated PASS)
```
Goals: G1 PASS, G2 PASS, G3 PASS (after a second measurement pass).

```
<skill-improvement-complete>
```
(Emitted on the simulation assumption stated in step 10.)

## Files
Only files under OUTDIR were changed: `target/SKILL.md`, `target/references/a.md`, plus `goal-measurement.md`, `final-tree.txt`, `transcript.md`. `target/references/b.md` unchanged. Original fixture untouched.
