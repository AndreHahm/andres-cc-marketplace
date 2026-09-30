# Transcript: skill-refiner-interactive dry run (eval-5)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Setup: copied the fixture `evals/skill-refiner-interactive/fixtures/demo-skill/` into `OUTDIR/target/`; only that copy is edited. Dry run: AskUserQuestion and other skills/agents cannot be called, so each ask is written out and answered by the simulated operator (first option when no answer was given).

## Quick Start
- A (predating context): none. The request only names the skill and the action, which is not predating context. Escape-hatch question not asked.
- B ("What skill?"): skipped, the request names the skill.
- C (Refine/Validate): skipped, the request says "refine" ("follows best practices" = refine).
- D: route to Core Workflow: Refinement.

## Step 1: Locate the skill
- Simulated operator answer: skill already located (OUTDIR/target). Not a cache path, not user-space, no gitignore exclusion applies.
- Mirror-pair check (R19): no `<repo root>/.claude/skills/demo-skill/` copy exists for the target; single skill, no Mirror question.
- Pre-analysis (references/pre-analysis-checklist.md), report:

```
Pre-Analysis: demo-skill
Lines: 13 - OK (R13; tiers 100/300/490/500 from plugin-rulebook settings.json)
Frontmatter issues: single-line description (needs >-, R8)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details)] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md:5 "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: "Ask the user which file to process" - input is an unbounded file path, exempt per Pattern 4 (plain text correct), not flagged
Argument consistency (R22): none
when_to_use split candidate: no
Description size (R21): 22 characters, under the 80-character floor
Tool scoping (R6): [Grep: "grep the file for TODO markers" invoked, not declared (Major)] / [unused declared tools: none]
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - optional low-priority candidate
Deferred goal candidates: cluster (a.md+b.md), missing goal verification, description size (R21; also addressed by the G3 rewrite)
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```

- Goal derivation (goal-derivation.md), priority order, cap 3:
  1. reference chain (first tier), 2. undeclared tool (second tier), 3. frontmatter issue (second tier).
- ASK (AskUserQuestion, multiSelect: true, "Select the goals for this refinement"):
  - "Zero reference-to-reference chains" - verify: chain scan over references/*.md -> 0 matches
  - "Every invoked tool is declared in allowed-tools" - verify: tool-scoping scan -> no undeclared tools
  - "Frontmatter passes R5 and R8" - verify: Skill(plugin-rulebook) R5 and R8 -> OK
  - (automatic "Other")
  - Simulated answer: all three selected. Goals recorded G1, G2, G3.

## Requirements Interview
- BATCH 1: goals selected, so Question 1 skipped. Asked Questions 2-4 one at a time (no simulated answer given, first option chosen):
  - Q2 "What specific problems are you seeing?" (header "Key Issues", multiSelect) options: Hard-to-follow instructions / Scattered references / Nested sections -> "Hard-to-follow instructions"
  - Q3 "What would success look like?" (header "Success") options: Clearer workflow / Lower token cost / Production-ready -> "Clearer workflow"
  - Q4 "Any areas to exclude or preserve as-is?" (header "Scope Limits", multiSelect) options: Keep validation gates / Keep tool scoping -> "Keep validation gates"
  - Approved scope documented: fix chain, tool grant, frontmatter; testing/validation section excluded by Q4 (binds step 6's auto-added standard sections, so Testing & Validation is NOT auto-added). Tool scoping is not excluded.
- BATCH 2: escape hatch not used, so runs after BATCH 1. Only the always-asked question applies (no large section, intake exempt, no R22 mismatch, no `when_to_use` split):
  - "Which production checks should I run?" (header "Prod checks", multiSelect) options: Security scan / Error handling / Tool scoping / None needed -> "Security scan" (first option)
  - Security scan result: grep for credentials, keys, tokens, `${VAR}` substitutions in SKILL.md and references/: none found.

## Step 2: Load workflow reference
Read references/refinement-workflow.md (gates, validation phases, consolidation, rollback).

## Step 3: Consolidation
- a.md (5 lines) and b.md (4 lines) cover the same topic (TODO marker details) and a.md points at b.md.
- ASK: "Should we consolidate these files? Saves about 2 lines, improves clarity." options: Consolidate / Leave as-is -> "Consolidate" (first option, no answer given).

## Step 4: Preservation gates 1-2
- Gate 1 (Content Audit): SKILL.md 13 lines core; references/a.md 5 lines (supplementary detail), references/b.md 4 lines (supplementary).
- Gate 2 (Capability Assessment): merging b.md into a.md and adding the standard sections will not impair execution; nothing core is deleted. Safe.
- Gates 3 and 4 are applied in step 6.

## Step 5: Plan-only exit question
- ASK: "Apply the approved scope?" options: Apply changes / Plan only / Stop. Simulated answer: "Apply changes". Step 6 runs (no plan-only exit).
- Early Gate 4 ask (the documented exception to gate order), for the consolidation's source file:
  ASK: "Okay to delete references/b.md once its content is in references/a.md?" options: Delete / Keep -> "Delete" (first option).

## Step 6: Make changes (round 1)
- Rollback: target is a copy under OUTDIR; the pre-edit state is the untouched fixture at evals/skill-refiner-interactive/fixtures/demo-skill/ (restore by re-copying). No mirror, so no overwrite edit.
- CREATE: appended "## Marker Formats" (b.md's two bullets) to references/a.md. (Gate 3: destination exists and contains all of b.md's content; SKILL.md pointer to a.md valid.)
- LINK/EDIT SKILL.md: description rewritten as a `>-` block (what + when, 160+ chars); `allowed-tools: Read Grep` (G2); added `## When to Use`, `## When NOT to Use`, `## Reference Guide` (auto-added standard sections). `## Testing & Validation` NOT added: excluded at BATCH 1 Question 4 ("Keep validation gates").
- DELETE: references/b.md removed (Gate 4 approval cited: "Delete" above; Gate 3 had verified the destination). `rm` ran as a Bash command.
- SIMULATION CONTROL: this first round of edits missed the reference-chain fix: references/a.md line 5 still said "Read references/b.md".

## Step 7: Validate result (pass 1)
1 File inventory: SKILL.md + references/a.md (b.md deleted). 2 Read all: complete. 3 Frontmatter: name, `>-` description, allowed-tools valid; no non-standard fields. 4 Body: 31 lines, OK tier; Quick Start actionable. 5 References: SKILL.md link resolves; the chain check was not re-run in this pass (missed). 6 Tools: Grep and Read declared and used. 7 Testing: activation phrase "list the TODOs in this file" matches the description.

## Step 8: Measure goals - MEASUREMENT PASS 1
See goal-measurement.md. G1 FAIL (a.md line 5 still says "Read references/b.md"), G2 PASS, G3 PASS.
- ASK on FAIL: "Goal '...' did not pass. Verification: ... Actual: ... Accept with a recorded reason, or continue refining?" options: Accept with reason / Continue refining -> "Continue refining".

## RETURN to step 6 (focus: G1)
- Removed the stale line 5 ("Read references/b.md ...") from references/a.md; the marker formats now live in the same file under "## Marker Formats". Gate 3/4: pure in-place edit of a line whose target no longer exists, no further file deletion.

## Step 7 (re-run of the touched phase)
Phase 5 (References): references/a.md has no reference directive; no dead link; a.md is linked from SKILL.md; one level deep. PASS.

## Step 8: Measure goals - MEASUREMENT PASS 2
G1 PASS (0 chain matches), G2 PASS, G3 PASS. All selected goals PASS.

## Step 9: Trigger regression
`description` text changed (new text, not just reformatting), so the ask applies.
- ASK: "The description changed. Verify trigger accuracy didn't regress before finalizing?" (header "Trigger eval") options: Run trigger-eval check / Quick size check only / Skip -> "Run trigger-eval check" (first option).
- Not executable in this dry run: it needs Skill(skill-development). Not run; no before/after trigger accuracy is claimed. Quick size check done by hand for the record: description 160+ characters, above R21's 80 floor and far below the limits; no `when_to_use`.

## Step 10: Compliance and reviewer passes
- Skill(plugin-rulebook) and the skill-reviewer agent cannot be invoked in this dry run, so both are NOT RUN. Per the skill, the marker is therefore not emitted.
- Known open item a real run would surface: missing `## Testing & Validation` (excluded at Question 4; fixing it would need the "Expand scope for this fix" / "Keep the exclusion" ask).
- Change summary:
```
Lines: 13 -> 31 (SKILL.md)
Frontmatter: description moved to a >-block and rewritten (what + when); allowed-tools Read -> Read Grep
Sections added: When to Use, When NOT to Use, Reference Guide
Files created: none
Files deleted: references/b.md (content merged into references/a.md)
plugin-rulebook: NOT RUN
```
- `<skill-improvement-complete>` NOT emitted (checks not run).

Final files: see ../final-tree.txt (outputs/final-tree.txt).
