# Refinement Workflow

Complete, unified workflow for improving Claude Code skills while preserving functionality and following established patterns. It covers the preservation gates, validation phases, consolidation and extraction; the pre-analysis, goal and plan-only steps live in SKILL.md and the references it names.

## Table of Contents
1. [Content Distribution (80% Rule)](#content-distribution-80-rule)
2. [Preservation Gates](#preservation-gates)
3. [Validation Phases](#validation-phases)
4. [Movement Pattern](#movement-pattern)
5. [Consolidation Strategy](#consolidation-strategy)
6. [Content Extraction](#content-extraction)
7. [Quality Decision Trees](#quality-decision-trees)
8. [Evidence-Gated Editing (Optional Rigor)](#evidence-gated-editing-optional-rigor)
9. [Rollback](#rollback)

## Content Distribution (80% Rule)

Content used in 80%+ of activations stays in SKILL.md (core). Content used in under 20% (supplementary) can move to `references/`. When unsure, keep it inline — preserving functionality outranks saving lines.

## Preservation Gates

Four mandatory gates that protect skill functionality. Apply **in order**. Do not skip gates.

### Gate 1: Content Audit

**Purpose:** Baseline what exists before any changes.

**Action:**
1. List ALL content in skill: SKILL.md (by section), references/ (by file), scripts/, assets/
2. Include line counts and topic summaries
3. Classify each piece:
   - **Core (80%+):** Essential to execution, Claude needs it always
   - **Supplementary (<20%):** Nice-to-have, edge cases, theory

**Gate 1 Check:** Proceed to Gate 2 only after completing full audit.

### Gate 2: Capability Assessment

**Purpose:** Verify proposed changes won't impair execution.

**Action:**
1. Review proposed changes (deletions, moves, consolidations)
2. For EACH change, ask: "Will this impair Claude's ability to execute the skill?"
3. If YES to any change → That change CANNOT be deleted, only migrated to references
4. If NO → Change is safe to delete or modify
5. Document assessment

**Example Assessment:**
```
Proposed: Delete "Historical Notes" section (80 lines of descriptive text)
Question: Will losing this hurt execution?
Answer: NO—nothing in the execution path uses it.
Decision: SAFE to delete OR move to appendix

Proposed: Consolidate 3 production-related files into 1
Question: Will this impair execution?
Answer: NO—consolidated file covers all scenarios, skill still works
Decision: SAFE to consolidate (improves efficiency)

Proposed: Move "Key Rules" section to references
Question: Will this impair execution?
Answer: YES—these rules are core constraints Claude must know always
Decision: CANNOT move; MUST stay in SKILL.md
```

**Gate 2 Check:** All changes must pass this assessment. If any fails, adjust the change (migrate instead of delete, split consolidation, etc.).

### Gate 3: Migration Verification

**Purpose:** Ensure moved content is complete before removing from source.

**Action:**
1. For each content move (NOT deletion), verify:
   - **Destination exists** - file/section created and accessible
   - **Content is complete** - all related information moved, no gaps
   - **Links are correct** - SKILL.md pointers updated and tested
   - **No orphans** - every moved element has a home
2. Test the link: Can Claude follow SKILL.md → references/ → complete information?

**Example Verification:**
```
Moving: "Advanced error handling" (currently in SKILL.md)
Destination: references/production-patterns.md (new section: "Error Handling")

Checks:
✓ File exists: references/production-patterns.md
✓ Content complete: All error scenarios present in new location
✓ Links correct: SKILL.md pointer now targets references/production-patterns.md
✓ No orphans: All related content (examples, tables) moved together

APPROVED: Safe to remove from SKILL.md
```

**Gate 3 Check:** Only after all migrations verified, proceed to Gate 4.

### Gate 4: Operator Confirmation

**Purpose:** Explicit approval for deletions and sensitive changes.

**Action:**
1. **For DELETIONS** → Require explicit operator approval:
   - Show what's being deleted and why
   - Use `AskUserQuestion` — question: "Okay to delete this?", options: "Delete" / "Keep"
   - Wait for the answer before removing anything
2. **For MIGRATIONS** → Auto-approved (content preserved, just moved):
   - No separate approval needed
   - Report what moved and where (informational, no question)
3. **For CONSOLIDATIONS** → Approved once, at the consolidation question (SKILL.md step 3):
   - That approval covers merging the content; the source files it leaves empty still need the explicit "Delete" / "Keep" answer from point 1 before they are removed
   - If the operator declines deleting the source files, do not perform the consolidation: merging without deleting only duplicates content. Report it as declined
   - Afterwards report: "Consolidated N files into M. Clearer organization."

**Example Gate 4 Exchange:**

```
AskUserQuestion (step 3): "Consolidate these 3 related files on error handling
  (298 lines, saves 78)?"  options: Consolidate / Leave as-is   → Consolidate
AskUserQuestion (Gate 4): "Okay to delete the 3 originals once their content is in
  the new file?"  options: Delete / Keep                        → Delete (approved)
AskUserQuestion (Gate 4): "Delete the 'Historical Notes' section (80 lines,
  supplementary)?"  options: Delete / Keep                      → Delete (approved)
Migration (no question): "Moved 'Advanced Patterns' to references/edge-cases.md;
  links updated."
```

**Gate 4 Check:** All deletions, including the source files of a consolidation, must have explicit approval. Migrations are auto-approved.

## Validation Phases

Seven systematic phases to validate skills after refinement. Run in order.

### Phase 1: File Inventory

**Action:** List complete skill structure before and after refinement.

**Report:** a before/after file tree (SKILL.md line count, each `references/` file, `scripts/`, `assets/`) with a one-line summary of what changed.

**Pass Condition:** File structure is complete and accounts for all changes.

### Phase 2: Read All

**Action:** Load complete skill content. Verify nothing was accidentally deleted or left incomplete.

**Check:**
- [ ] SKILL.md loads completely (no truncation)
- [ ] All frontmatter present (name, description; no non-standard fields)
- [ ] All references/ files accessible and complete
- [ ] All script files intact
- [ ] No broken links (SKILL.md → references all resolve)

**Pass Condition:** Complete skill content loads without gaps or errors.

### Phase 3: Frontmatter Check

**Action:** Verify required metadata present and correct.

**Check:**
- [ ] `name` field present (lowercase, hyphen-separated, within R4's length limit, no "anthropic" or "claude")
- [ ] `description` field present and within plugin-rulebook's R21 limits (also `when_to_use` if present, and the combined length); includes trigger phrases, uses `>-` multiline
- [ ] `allowed-tools` field correct (space-separated preferred; comma-separated and YAML list are also valid; principle of least privilege)
- [ ] YAML syntax valid (triple dashes, proper indentation)

**Non-standard fields — remove if present:** per `plugin-rulebook`'s R5 (the source of truth for this check — trace back to its current text rather than restating the list here). As of R5's current text, the only forbidden field is `version` (command-only field); `AskUserQuestion` in `allowed-tools` is explicitly *not* a violation — a harmless no-op, since every tool remains callable regardless of `allowed-tools`.

**Pass Condition:** Required fields present and correctly formatted; no non-standard fields; syntax valid.

### Phase 4: Body Content

**Action:** Verify SKILL.md body follows quality standards.

**Checks:**
- [ ] **Line count:** total SKILL.md lines (including frontmatter) within the resolved R13 tiers; above the Critical threshold (500) blocks
- [ ] **80% rule applied:** Essential content in body, supplementary in references
- [ ] **Quick Start section:** Present and actionable (not theory)
- [ ] **Clarity:** Procedural instructions, not abstract explanations
- [ ] **Examples:** Code-first examples before abstract explanations
- [ ] **Structure:** Clear sections (Quick Start → Workflows → Key Rules → References)
- [ ] **Activation:** Trigger phrases present and clear (will Claude recognize requests?)
- [ ] **Workflow pattern:** Load `${CLAUDE_PLUGIN_ROOT}/skills/skill-development/references/design-patterns.md`; identify which named pattern applies (Sequential Workflow Orchestration, Multi-MCP Coordination, Iterative Refinement, Context-aware Tool Selection, Domain-specific Intelligence); verify load-bearing key techniques are present — missing ones are Major
- [ ] **Spawn anti-patterns:** No Cartesian product spawning (O(N×M) subagent spawns across independent lists), no unbounded agent spawning (loop spawn with no explicit count cap on a user-controlled list), no vague subagent prompts (dispatch with no file paths, goal, or output spec)

**Pass Condition:** within the R13 tiers with no Critical, 80% rule applied, clear procedural content.

### Phase 5: References

**Action:** Verify reference files are complete, organized, and properly linked.

**Checks:**
- [ ] All files referenced in SKILL.md exist
- [ ] No orphaned files (all reference files are linked)
- [ ] One level deep only (no nested chains: `references/` → files, not `references/subdir/file`)
- [ ] **No reference→reference chains:** scan each `references/*.md` for imperative directives to read another `references/` file — flag each as Major
- [ ] File naming consistent (lowercase, hyphens: `refinement-workflow.md`)
- [ ] Each file has clear purpose (title, table of contents if >100 lines)
- [ ] Links from SKILL.md are accurate (correct filenames)

**Pass Condition:** All referenced files exist, no orphans, one level deep only.

### Phase 6: Tool Scoping

**Action:** Verify `allowed-tools` field matches actual tool usage and applies principle of least privilege.

**Check:**
- [ ] **Undeclared tools:** All tools called in SKILL.md and all `references/*.md` files are listed in `allowed-tools` — an undeclared tool is not pre-approved and remains subject to the active permission settings (R6 tool-completeness; Major)
- [ ] **Unused declared tools:** No tools in `allowed-tools` that are never referenced in SKILL.md or any reference file — principle of least privilege (Minor)
- [ ] **Bash-for-dedicated-tool misuse:** No `Bash(grep:*)`, `Bash(find:*)`, `Bash(cat:*)` where Grep, Glob, Read would serve the same purpose (Minor)
- [ ] Wildcards used appropriately (`Bash(git:*)` for git-only; bare `Agent` pre-approves any agent type, so narrow it to `Agent(<type>)` only where the current Claude Code docs confirm that form for `allowed-tools`)
- [ ] Tool scoping is explicit and documented

**Pass Condition:** Tool scoping is explicit, principle of least privilege applied.

### Phase 7: Testing

**Action:** Verify skill activates correctly and executes as intended.

**Checks:**
- [ ] **Activation:** Describe skill. Does it include trigger phrases users will recognize?
  - Test: "Refine my skill" → Should trigger skill-refiner-interactive?
  - Test: "Validate this for production" → Should trigger?
  - Test: "Make this clearer" → Should trigger?
- [ ] **Execution:** Run through Quick Start mentally. Are procedures clear?
- [ ] **Links:** Follow a reference link. Does it work? Is content complete?
- [ ] **Workflows:** Trace main workflow. Are steps in correct order?
- [ ] **Examples:** Run through an example. Does it work end-to-end?

**Pass Condition:** Skill activates correctly, procedures are clear, examples work end-to-end.

## Movement Pattern

Every content move follows CREATE → LINK → DELETE: create or update the destination first, update the SKILL.md pointers second, and delete the source only after the links are verified. Never delete first.

## Consolidation Strategy

Consolidate related reference files to improve organization and reduce complexity.

### When to Consolidate

- **2-4 files** on same topic (e.g., error-handling.md + team-patterns.md + edge-cases.md)
- **Related content** (all addressing one domain: production patterns, validation, preservation)
- **Cross-references** between files (file A links to file B, they should merge)
- **Reducing noise** (3 separate files vs. 1 organized file with sections)

### When NOT to Consolidate

- **Single large file already** (>400 lines, consolidation adds little value)
- **Distinct domains** (skill activation logic vs. tool configuration—keep separate)
- **Different audiences** (user-facing reference vs. internal notes—keep separate)

### Consolidation Procedure

Apply movement pattern in this order:

1. **Create consolidated file** with sections for each topic
   ```markdown
   # Production Patterns

   ## Table of Contents
   Links to each section

   ## Error Handling
   [Content from error-handling.md]

   ## Team Patterns
   [Content from team-patterns.md]

   ## Edge Cases
   [Content from edge-cases.md]
   ```

2. **Link from SKILL.md** (point to sections of consolidated file)
   ```markdown
   Error handling: references/production-patterns.md#error-handling
   Team patterns: references/production-patterns.md#team-patterns
   ```

3. **Delete old files** (error-handling.md, team-patterns.md, edge-cases.md)
   - Only after (1) and (2) verified
   - Test links before deleting

### Consolidation Report

```
Consolidated: error-handling.md + team-patterns.md + edge-cases.md (469 lines)
Into: production-patterns.md (380 lines, saves 89)
Links updated: SKILL.md (3 pointers → 1); old files deleted after link check
```

## Content Extraction

Extract large low-frequency SKILL.md sections into new reference files to reduce body length while preserving content.

### When to Extract

- Section is ≥50 lines with estimated usage <20% of activations (apply 80% rule)
- SKILL.md is in an R13 Warning or Critical tier and the section is identifiably supplementary
- A natural "read more" boundary exists: the section is self-contained

### When NOT to Extract

- Section is used in 80%+ of activations → keep inline
- Section is already brief (<50 lines) → indirection is not worth it
- Content is genuinely core to the skill's primary workflow → must stay inline

### Extraction Procedure (always CREATE → LINK → DELETE)

1. **CREATE** `references/<topic>.md` with the full extracted content
2. **LINK**: Replace the inline section in SKILL.md with a concise pointer:
   ```markdown
   ## Section Name
   Details: `references/<topic>.md` ([description of what's there]).
   ```
3. **DELETE** the inline body content (the pointer is now the only thing inline)

### Extraction Report

```
Extracted: "Troubleshooting" section (60 lines, <20% usage)
From: SKILL.md (307 lines → 249 lines after extraction and a 2-line pointer)
To: references/troubleshooting.md (new file, 60 lines)
Pointer: "When a run fails, details are in references/troubleshooting.md"
```

## Quality Decision Trees

Quick reference for common refinement decisions. The core-versus-supplementary test is stated once, under Content Distribution above.

### Should These Files Consolidate?

```
Are 2-4 files addressing related topics?
├─ YES → Consolidation candidate
│  ├─ Create consolidated file
│  ├─ Link from SKILL.md
│  └─ Delete old files (in that order!)
└─ NO → Keep separate

Example: 3 production-related files (error-handling, team-patterns, advanced)
├─ All address production environments? YES
├─ Related content? YES
└─ Consolidate into production-patterns.md
```

### Is This Deletion Safe?

```
Are you deleting content from SKILL.md?
├─ YES → Run Gate 2 (Capability Assessment)
│  ├─ Will deletion impair execution?
│  │  ├─ YES → Cannot delete; migrate instead
│  │  └─ NO → Safe to delete (still need Gate 4 approval)
│  └─ Get Gate 4 operator confirmation
└─ NO → Just updating, no deletion needed

Example: Deleting "Historical Notes" (80 lines, supplementary)
├─ Will losing it impair execution? NO
├─ Operator approved? YES
└─ Safe to delete
```

### Should I Apply This Change?

```
For ANY proposed change (edit, move, delete, consolidate):
1. Run Gate 2: Will it impair execution?
   ├─ YES → Modify approach (migrate instead of delete, etc.)
   └─ NO → Proceed
2. Make the change using the Movement Pattern (CREATE → LINK → DELETE):
   - Run Gate 3 once the destination exists (verify it is complete)
   - Run Gate 4 before any deletion (get operator approval)
3. Run validation Phase 5 (References) and Phase 7 (Testing)

Only if all gates/phases pass: Change is safe
```

## Evidence-Gated Editing (Optional Rigor)

Apply when optimizing a skill with observed failures or measured drift. An edit ships only when it demonstrably beats the version already in use.

Score the current and proposed versions on a fixed held-out check set (3–8 tasks, including the triggering failure). Accept only if the candidate strictly beats the current on the triggering criterion with no regression on others. Cap at ~4 changes per revision; rank by systematic impact.

## Rollback

Refinement edits, deletes and (for a mirror pair) overwrites files, and it can stop part-way: a declined Gate 4, a failed goal the operator abandons, or the 3-round cap. Settle how to undo it before the first edit in SKILL.md step 6:

- **Project skill under version control:** the pre-edit state is the last commit. Note in the plan whether the target's files already have uncommitted changes. If none do, undo by restoring the listed files from version control (both copies of a mirror pair). If any do, a whole-file restore would discard those earlier edits: before the first edit, save a copy of each dirty file (or its `git diff` as a patch) in a scratch location outside the repository, and undo by reversing only this refinement's changes against that copy, never by restoring the file from version control.
- **User-space skill (`~/.claude/skills/`):** no version control is assumed. Before the first edit, ask the operator to copy the skill directory somewhere safe, or accept that there is no undo.
- **After a stop:** the change summary's "Files created" and "Files deleted" lists are the restore list. A consolidation whose source deletion was declined was not performed, so leave the destination file out of that list.
