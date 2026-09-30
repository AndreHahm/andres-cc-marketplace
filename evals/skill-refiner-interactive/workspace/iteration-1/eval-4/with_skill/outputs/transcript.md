# Transcript: skill-refiner-interactive dry run (eval-4)

Operator request: "Refine the skill in OUTDIR/target so it follows best practices."
Target: OUTDIR/target (copy of fixtures/demo-skill; original untouched).

## Step 0 - Predating context
Predating context exists (the skill path is given in the request). The escape-hatch question would be shown.
Q: "I've reviewed the skill and context you provided. How would you like to proceed?" Options: [Infer from context | Define explicitly].
Simulated answer: "skill already located", so the locate step is not re-asked. Proceeding to Core Workflow: Refinement. The operator's wording ("refine") selects Refine, so the Step 2 Action question is not needed.

## Core Workflow: Refinement

### Step 1 - Locate the skill
Located at OUTDIR/target. It is not gitignored, not in the plugin cache, and has no `.claude/skills/` mirror twin, so the R19 mirror check is N/A. The operator supplied the location, so no ask.

### Step 1 - Pre-analysis (references/pre-analysis-checklist.md)
plugin-rulebook is not present in the fixture's scope, so the fallback flat limits apply (500 lines / 10-line code blocks).

```
Pre-Analysis: demo-skill
Lines: 7 body lines - OK (R13, fallback)
Frontmatter issues: description is single-line (needs >-)
Large sections (>=50 lines): none
Reference files: 2 [clusters: a.md + b.md (TODO marker details)] [oversize >=400 lines: none]
Workflow files: 0 [oversize: none] [workflow->ref chain violations: none]
Reference chain violations (ref->ref): references/a.md -> "Read references/b.md"
Spawn anti-patterns: none
Intake pattern violations: Quick Start - "Ask the user which file to process" with no AskUserQuestion
Argument consistency (R22): none
when_to_use split candidate: no
Tool scoping (R6): undeclared: Grep ("grep the file") / unused declared: none (Read is used)
Dead links: none / Cross-skill references: none
Missing standard sections: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Goal verification: absent - flag as Missing
Deferred goal candidates: missing goal verification; reference cluster; missing standard sections (auto-added)
R13/R18 threshold source: skill-development fallback
```

### Step 1 - Goal derivation and selection (references/goal-derivation.md)
Top 3 by severity: Critical (chain, intake), Major (undeclared tool).
Q (AskUserQuestion, multiSelect): "Which goals should this session pursue?"
Options:
  1. Zero ref->ref chains (verify: chain scan over references/*.md returns 0 matches)
  2. All intake uses AskUserQuestion with options (verify: intake scan returns 0 matches)
  3. Every invoked tool declared in allowed-tools (verify: tool-scoping scan shows no undeclared tools)
  Other
Simulated answer: select all 3 goals.

### Requirements Interview
Goals were selected, so BATCH 1 Question 1 is skipped. Questions 2-4 are asked about the goal areas.
Q2 "What specific problems are you seeing?" [Hard-to-follow instructions | Scattered references | Nested sections | Other]. No answer was given, so the first option is chosen.
Q3 "What would success look like?" [Clearer workflow | Lower token cost | Production-ready | Other]. First option chosen.
Q4 "Any areas to exclude or preserve as-is?" [Keep validation gates | Keep tool scoping | Nothing to exclude | Other]. First option chosen. This does not conflict with the goals: tool scoping is only widened to declare Grep (goal 3), and validation gates are not touched.

BATCH 2 (conditional on findings whose goals were selected):
- Content extraction: no large sections, skipped.
- Intake pattern question: "Section 'Quick Start' collects user input without AskUserQuestion. Convert?" [Yes | No]. First option chosen: Yes.
- Consolidation: its goal was not selected, so skipped here. Step 3 asks it.
- R22: none. when_to_use split: none.
- Production checks: "Which production checks should I run?" [Security scan | Error handling | Tool scoping | None needed], multiSelect. First option chosen: Security scan. No credentials or `${VAR}` substitutions were found in SKILL.md.
Approved scope documented.

### Step 2 - Load workflow reference
Read references/refinement-workflow.md (Preservation Gates section and decision flow).

### Step 3 - Identify consolidation opportunities
references/: a.md (5 lines), b.md (4 lines). Same topic (TODO marker details). Flagged for merge into one file.
Q: "Should we consolidate these files? Saves N lines, improves clarity." [Consolidate | Leave as-is].
Simulated answer: Consolidate. Merge plan: references/a.md + references/b.md -> references/marker-details.md.

### Step 4 - Preservation gates
1. GATE 1 - Content Audit: all content in a.md (heading, summary-format sentence, pointer to b.md) and b.md (heading, two marker formats) is listed. All of it is supplementary (<20% usage). The a.md->b.md pointer becomes redundant once merged.
2. GATE 2 - Capability Assessment: merging does not impair execution. All substantive content migrates, and only the redundant pointer line is dropped. The deletion of a.md/b.md is permitted because every line is migrated.
3. GATE 3 - Migration Verification: destination references/marker-details.md does not yet exist. The plan is to CREATE it first with the full content of both files, and verify completeness before any DELETE.
4. GATE 4 - Operator Confirmation: deletions require approval.
   Q: "Approve deleting references/a.md and references/b.md (content migrated to references/marker-details.md)?" [Approve | Reject].
   Simulated answer: Approve.

### Step 5 - Plan-only exit
Q: "Apply the approved scope?" [Apply changes | Plan only (write changes.md, no edits) | Stop].
Simulated answer: Apply changes. Proceeding to step 6.

### Step 6 - Make changes (CREATE -> LINK -> DELETE)
5. CREATE: references/marker-details.md (merged content of a.md and b.md).
6. LINK: SKILL.md updated. The pointer `references/a.md` became `references/marker-details.md`, verified by Grep that no remaining references to a.md/b.md exist in SKILL.md.
7. DELETE: references/a.md (only after the link was verified).
8. DELETE: references/b.md (only after the link was verified).

Other edits in step 6:
- Frontmatter: description converted to `>-` block (text unchanged); allowed-tools `Read` -> `Read Grep` (goal 3).
- Quick Start free-form intake replaced with an AskUserQuestion block (goal 2, BATCH 2 "Yes").
- Standard sections auto-added: When to Use, When NOT to Use, Testing & Validation, Reference Guide.

### Step 7 - Validate result (7 phases)
- P1 inventory: before SKILL.md + a.md + b.md; after SKILL.md + marker-details.md.
- P2 read all: no content gaps.
- P3 frontmatter: name and description present; `>-` form.
- P4 body: about 55 lines, OK. Workflow pattern OK. No spawn anti-patterns.
- P5 references: 1 linked file, exists, one level deep, no ref->ref chain.
- P6 tools: Read/Grep declared; AskUserQuestion exempt; no unused tools.
- P7 testing: activation phrases are covered by the new Testing & Validation section.

### Step 8 - Measure goals
See goal-measurement.md. All 3 goals PASS.

### Step 9 - Trigger regression check
The description and when_to_use text is unchanged, only reformatted to `>-`. Skipped: no trigger wording changed.

### Step 10 - Compliance and reviewer passes
Skill(plugin-rulebook) and skill-reviewer cannot be dispatched in this dry run. Recorded as not executed. Change summary:
```
Lines: 7 -> 55
Frontmatter: description to >-; allowed-tools += Grep
Sections added: When to Use, When NOT to Use, Testing & Validation, Reference Guide
Files created: references/marker-details.md
Files deleted: references/a.md, references/b.md
plugin-rulebook: not run (dry-run)
```
`<skill-improvement-complete>` is withheld because the step-10 gates were not executed.
