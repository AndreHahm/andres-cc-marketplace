# Dry-run transcript: skill-refiner-interactive on big-skill

Operator: "Refine the skill in OUTDIR/target so it is lighter."
Target: OUTDIR/target (copy of fixtures/big-skill; original untouched).

## Quick Start
- Step 0 (predating context): only a path was given, no skill file contents or described problem -> escape hatch not offered; continue to Step 1. (Judgment call, noted.)
- Step 1 (locate): simulated "skill already located" -> skipped the ask.
- Step 2 Action question: "What would you like to do with this skill?" options: Refine / Validate. Answer: Refine (from operator request).
- Step 3: route to Core Workflow: Refinement.

## Core Workflow: Refinement
### 1. Locate (MANDATORY)
Located at OUTDIR/target. Not in a gitignored path, not user-space, not cache. Mirror-pair check (R19): no `.claude/skills/` counterpart -> single logical skill, no Mirror Divergence question.

### 1. Pre-analysis (pre-analysis-checklist.md)
Report:
```
Pre-Analysis: big-skill
Lines: 307 - Soft Warning (R13)   [tiers from plugin-rulebook settings.json: >100 Weak, >300 Soft, >490 Warning, >500 Critical]
Frontmatter issues: none (description uses >-, no forbidden fields)
Large sections (>=50 lines): Troubleshooting (Edge Cases) - 60 lines, states "consulted only when a run fails" (<20% usage, low-frequency). Workflow Steps 1-7 are 33 lines each (core).
Reference files: 1 [clusters: none] [oversize >=400 lines: none]
Workflow files: 0 [...none]
Reference chain violations (ref->ref): none
Spawn anti-patterns: none
Intake pattern violations: none
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: none / unused declared: Grep, Glob (Minor)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide (Quick Start present)
Goal verification: absent - flag as Missing
Deferred goal candidates: none (R13 tier and large section are separate findings; 3 goals suffice)
R13/R18 threshold source: plugin-rulebook/assets/settings.json
```
**R13 tier logged: Soft Warning (307 lines).**

### 1. Goal derivation and selection (goal-derivation.md)
AskUserQuestion (multiSelect, up to 3). Options (description = verification check):
1. "Extract Troubleshooting section out of SKILL.md" - Re-run large-section scan -> none unapproved
2. "SKILL.md within a lower R13 tier" - `wc -l SKILL.md` -> <=300 (out of Soft Warning)
3. "Add a goal-measurement step" - Grep for `## Goal Verification` -> present
Simulated answer: select all three.

### Requirements Interview
BATCH 1 (goals selected -> Question 1 skipped). Questions asked one at a time, simulated answer = first option (no answer given):
- Q2 "What specific problems are you seeing?" (Key Issues) options: Hard-to-follow instructions / Scattered references / Nested sections -> "Hard-to-follow instructions"
- Q3 "What would success look like?" (Success Metric) options: Clearer workflow / Lower token cost / Production-ready -> "Clearer workflow"
- Q4 "Any areas to exclude or preserve as-is?" (Scope Limits) options: Keep validation gates / Keep tool scoping / Nothing to exclude -> "Keep validation gates" (first option)
Approved scope documented.

BATCH 2 (Define-explicitly path, goals selected; trigger-detected questions only):
- Content Extraction: "Section 'Troubleshooting (Edge Cases)' is 60 lines and appears in <20% of activations. Extract to references/troubleshooting.md?" options Yes / No -> **Yes** (operator answer).
- Intake Pattern / Argument Consistency / Description Split: triggers not detected -> not asked.
- Production Checks (always asked): "Which production checks should I run?" options Security scan / Error handling / Tool scoping / None needed -> first option "Security scan". Grep for credentials/keys/tokens/${VAR} in SKILL.md and references/: 0 matches. (Tool scoping not selected, so unused Grep/Glob left as-is; Minor, reported only.)
- Reference-file clusters: none, and not asked here.

### 2. Load workflow reference
Reviewed refinement-workflow.md conceptually (preservation gates, validation phases). 

### 3. Consolidation
1 reference file (rules.md), no clusters -> no consolidation candidates, so no ask.

### 4. Preservation gates
- GATE 1 Content Audit: Workflow Steps 1-7 + Quick Start = core; Troubleshooting (60 lines) = supplementary (<20%).
- GATE 2 Capability Assessment: migrating (not dropping) Troubleshooting keeps a pointer; execution of the core path not impaired -> OK to migrate.
- GATE 3 Migration Verification: destination references/troubleshooting.md created and diffed identical to source before deletion (see action 1).
- GATE 4 Operator Confirmation: "Delete the inline Troubleshooting body (55 failure-mode lines) from SKILL.md now that it lives in references/troubleshooting.md?" options Approve / Decline -> **Approve** (operator answer).

### 5. Plan-only exit
AskUserQuestion: "Apply the approved scope?" options: Apply changes / Plan only (write changes.md, no edits) / Stop -> **Apply changes**.

### 6. Make changes (CREATE -> LINK -> DELETE)
Actions in order performed:
1. CREATE: target/references/troubleshooting.md (heading + 58 lines of the 55 failure-mode body copied from SKILL.md; 60 lines total; diff against source body = identical).
2. LINK: SKILL.md "Troubleshooting (Edge Cases)" now begins with pointer "When a run fails, see `references/troubleshooting.md` for the 55 failure modes and their fixes." (links verified; inline body still present at this point). Count corrected to 55 (the 53 first typed was wrong, caught by grep).
3. DELETE: removed inline Troubleshooting body (intro sentence + 55 failure-mode bullets) from SKILL.md after link verified; only heading + pointer remain. `Grep "Failure mode" SKILL.md` -> 0.
Standard sections auto-added (no approval needed; not CREATE/LINK/DELETE of existing content): When to Use, When NOT to Use, Testing & Validation, Reference Guide (table listing rules.md and troubleshooting.md). Also added `## Goal Verification` section to back selected goal 3.

### 7. Validate (seven phases)
1. Inventory: before SKILL.md + references/rules.md; after SKILL.md + references/rules.md + references/troubleshooting.md.
2. Read all: no content gaps; troubleshooting content fully present in new file.
3. Frontmatter: name, description present, unchanged.
4. Body: 283 lines -> Weak Warning (R13), improved from Soft Warning; no inline block issues.
5. References: both linked files exist, one level deep, no ref->ref chains.
6. Tools: allowed-tools Read Write Grep Glob; Read/Write used; Grep/Glob unused (Minor, left per operator scope).
7. Testing: trigger phrases "clean this CSV", "dedupe this export" match description.

### 8. Measure goals
See goal-measurement.md: G1 PASS, G2 PASS, G3 PASS. No failure ask.

### 9. Trigger regression
description / when_to_use unchanged -> step skipped.

### 10. Compliance and reviewer passes
Not executable in dry-run (cannot dispatch Skill/agent). Would call Skill(plugin-rulebook) and skill-reviewer; none dispatched here. Expected change summary:
```
Lines: 307 -> 283
Frontmatter: no changes
Sections added: When to Use, When NOT to Use, Testing & Validation, Goal Verification, Reference Guide
Files created: references/troubleshooting.md
Files deleted: none (inline Troubleshooting body removed from SKILL.md)
plugin-rulebook: not run (dry-run)
```
Completion marker withheld since plugin-rulebook/skill-reviewer were not actually run.
