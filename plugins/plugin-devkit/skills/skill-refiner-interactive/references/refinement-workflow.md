# Refinement Workflow

Complete, unified workflow for improving Claude Code skills while preserving functionality and following established patterns. This is the authoritative reference for all refinement operations.

## Table of Contents
1. [Content Distribution (80% Rule)](#content-distribution-80-rule)
2. [Preservation Gates](#preservation-gates)
3. [Validation Phases](#validation-phases)
4. [Movement Pattern](#movement-pattern)
5. [Consolidation Strategy](#consolidation-strategy)
6. [Content Extraction](#content-extraction)
7. [Quality Decision Trees](#quality-decision-trees)

## Content Distribution (80% Rule)

See `80-percent-rule.md` for the full decision framework, core-vs-supplementary examples, and worked consolidation example — not restated here to avoid drift.

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

**Example Audit:**
```
SKILL.md:
  - Quick Start (35 lines) → Core
  - Core Workflow: Refinement (220 lines) → Core
  - Core Workflow: Validation (180 lines) → Core
  - Key Rules (120 lines) → Core
  - Reference Files Guide (80 lines) → Supplementary
  - Pro Tips (45 lines) → Supplementary
  - Common Scenarios (130 lines) → Core
  - Notes (30 lines) → Supplementary

references/refinement-workflow.md (298 lines) → Core
references/validation-checklist.md (156 lines) → Supplementary
references/production-patterns.md (214 lines) → Supplementary (advanced only)
references/preservation-rules.md (89 lines) → Core (protects refinement)

Total: ~1,751 lines
Core content: ~1,065 lines
Supplementary: ~686 lines
```

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
Proposed: Delete "Reference Files" section (80 lines of descriptive text)
Question: Will losing this hurt execution?
Answer: NO—it's descriptive. Core reference guide (Gate 3) lists what files exist.
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
✓ Links correct: SKILL.md updated to "See references/production-patterns.md"
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
   - Just verify with operator: "I've moved X to references/. Working as expected?"
3. **For CONSOLIDATIONS** → Auto-approved (improves efficiency):
   - No separate approval needed
   - Just report: "Consolidated N files into M. Clearer organization."

**Example Gate 4 Exchange:**
```
Claude: "I found 3 related files on error handling (298 lines total).
         Can consolidate into 1 file, save 78 lines, improve clarity.
         Approve consolidation?"
Operator: "Yes, consolidate them."
→ APPROVED: Proceed to consolidation

Claude: "The 'Reference Files Guide' section (80 lines) is supplementary.
         Should I delete it or move it to an appendix?"
Operator: "Delete it—we don't need that reference list anymore."
→ APPROVED: Proceed to deletion

Claude: "Moving 'Advanced Patterns' to references/ now."
(Later) "Done. All links updated. Can you verify it still works?"
→ Auto-approved migration
```

**Gate 4 Check:** All deletions must have explicit approval. Migrations and consolidations are auto-approved.

## Validation Phases

Seven systematic phases to validate skills after refinement. Run in order.

### Phase 1: File Inventory

**Action:** List complete skill structure before and after refinement.

**Report:**

**R18 exception (recorded):** intentionally exceeds the 30-line threshold — a single coherent before/after comparison; splitting it would break the comparison it's illustrating.

```
BEFORE REFINEMENT:
├── SKILL.md (1,200 lines)
├── references/
│   ├── workflow.md (298 lines)
│   ├── checklist.md (156 lines)
│   └── patterns.md (214 lines)
├── scripts/
│   └── validate.py (87 lines)
└── assets/ (empty)

AFTER REFINEMENT:
├── SKILL.md (950 lines) ← 250 lines removed
├── references/
│   ├── workflow.md (298 lines)
│   ├── checklist.md (156 lines)
│   └── production-patterns.md (285 lines) ← Consolidated
├── scripts/
│   └── validate.py (87 lines)
└── assets/ (empty)

Changes: 1 file merged, SKILL.md reduced, references consolidated
```

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
- [ ] `name` field present (lowercase, hyphen-separated, ≤64 chars)
- [ ] `description` field present (80–1024 chars; `when_to_use` if present ≤512 chars; combined ≤1536; includes trigger phrases, uses `>-` multiline)
- [ ] `allowed-tools` field correct (space-separated preferred; comma-separated and YAML list are also valid; principle of least privilege)
- [ ] YAML syntax valid (triple dashes, proper indentation)

**Non-standard fields — remove if present:**
- `version` — non-standard for skills (command-only field)

**Harmless, not a violation:** `AskUserQuestion` in `allowed-tools` — a no-op (every tool remains callable regardless of `allowed-tools`, per current Claude Code docs), not something to remove.

**Example:**
```yaml
---
name: skill-refiner                        ✓ Correct
description: >-
  Improve and validate Claude Code skills... ✓ Multiline >-; includes trigger phrases
allowed-tools: Read Edit Write Glob        ✓ Space-separated, principle of least privilege
---
```

**Pass Condition:** Required fields present and correctly formatted; no non-standard fields; syntax valid.

### Phase 4: Body Content

**Action:** Verify SKILL.md body follows quality standards.

**Checks:**
- [ ] **Line count:** <500 lines (non-negotiable for token efficiency)
- [ ] **80% rule applied:** Essential content in body, supplementary in references
- [ ] **Quick Start section:** Present and actionable (not theory)
- [ ] **Clarity:** Procedural instructions, not abstract explanations
- [ ] **Examples:** Code-first examples before abstract explanations
- [ ] **Structure:** Clear sections (Quick Start → Workflows → Key Rules → References)
- [ ] **Activation:** Trigger phrases present and clear (will Claude recognize requests?)
- [ ] **Workflow pattern:** Load `skill-development/references/design-patterns.md`; identify which named pattern applies (Sequential Workflow Orchestration, Multi-MCP Coordination, Iterative Refinement, Context-aware Tool Selection, Domain-specific Intelligence); verify load-bearing key techniques are present — missing ones are Major
- [ ] **Spawn anti-patterns:** No Cartesian product spawning (O(N×M) subagent spawns across independent lists), no unbounded agent spawning (loop spawn with no explicit count cap on a user-controlled list), no vague subagent prompts (dispatch with no file paths, goal, or output spec)

**Example Check:**
```
Before refinement:
- SKILL.md: 1,200 lines (too long)
- "Reference Files" section (80 lines of descriptive text about what files exist)
- "Theory of Refinement" section (120 lines of abstract concepts)
→ Issues: Too long, contains supplementary content

After refinement:
- SKILL.md: 950 lines (✓ under 500 range, acceptable)
- Removed descriptive text → files are self-evident
- Moved theory to references/80-percent-rule.md
→ Pass: Better token efficiency, core content preserved
```

**Pass Condition:** <500 lines, 80% rule applied, clear procedural content.

### Phase 5: References

**Action:** Verify reference files are complete, organized, and properly linked.

**Checks:**
- [ ] All files referenced in SKILL.md exist
- [ ] No orphaned files (all reference files are linked)
- [ ] One level deep only (no nested chains: `references/` → files, not `references/subdir/file`)
- [ ] **No reference→reference chains:** scan each `references/*.md` for imperative directives to read another `references/` file (e.g., `Read references/bar.md`, `see references/bar.md`) — flag each as Major
- [ ] File naming consistent (lowercase, hyphens: `refinement-workflow.md`)
- [ ] Each file has clear purpose (title, table of contents if >100 lines)
- [ ] Links from SKILL.md are accurate (correct filenames)

**Example Check:**
```
SKILL.md references:
  - "See references/refinement-workflow.md" → ✓ File exists
  - "See references/validation-checklist.md" → ✓ File exists
  - "See references/production-patterns.md" → ✓ File exists (merged)

Orphaned files (referenced nowhere):
  - None ✓

Directory structure:
  references/
  ├── refinement-workflow.md      ✓ One level deep
  ├── validation-checklist.md     ✓ One level deep
  └── production-patterns.md      ✓ One level deep
  (No nested directories) ✓
```

**Pass Condition:** All referenced files exist, no orphans, one level deep only.

### Phase 6: Tool Scoping

**Action:** Verify `allowed-tools` field matches actual tool usage and applies principle of least privilege.

**Check:**
- [ ] **Undeclared tools:** All tools called in SKILL.md and all `references/*.md` files are listed in `allowed-tools` — absence causes runtime block (Major)
- [ ] **Unused declared tools:** No tools in `allowed-tools` that are never referenced in SKILL.md or any reference file — principle of least privilege (Minor)
- [ ] **Bash-for-dedicated-tool misuse:** No `Bash(grep:*)`, `Bash(find:*)`, `Bash(cat:*)` where Grep, Glob, Read would serve the same purpose (Minor)
- [ ] Wildcards used appropriately (`Bash(git:*)` for git-only, `Task(*)` for all agents)
- [ ] Tool scoping is explicit and documented

**Example:**
```
Skill uses: Read, Edit, Write, Bash (git operations), Glob, Task (explore agent)
Current allowed-tools: Read,Edit,Write,Bash(*),Glob,Task(*)
Issues: (1) Bash(*) too broad; (2) Task(*) too broad — comma-separated format itself is valid, not an issue

Fix: scope Bash and Task to the specific operations used

Updated: allowed-tools: Read,Edit,Write,Bash(git:*),Glob,Task(Explore)
```

**Pass Condition:** Tool scoping is explicit, principle of least privilege applied.

### Phase 7: Testing

**Action:** Verify skill activates correctly and executes as intended.

**Checks:**
- [ ] **Activation:** Describe skill. Does it include trigger phrases users will recognize?
  - Test: "Refine my skill" → Should trigger skill-refiner? ✓
  - Test: "Validate this for production" → Should trigger? ✓
  - Test: "Make this clearer" → Should trigger? ✓
- [ ] **Execution:** Run through Quick Start mentally. Are procedures clear?
- [ ] **Links:** Follow a reference link. Does it work? Is content complete?
- [ ] **Workflows:** Trace main workflow. Are steps in correct order?
- [ ] **Examples:** Run through an example. Does it work end-to-end?

**Example Testing:**
```
Test 1: "Refine the plugin-creator skill"
→ Skill description includes "refine existing skills"? ✓ Should trigger
→ Quick Start covers this? ✓ Procedure clear
→ Can find plugin-creator? ✓ Locate workflow works

Test 2: "Validate that my skill is production-ready"
→ Description includes "validate"? ✓ Should trigger
→ Core Workflow: Validation delegates to skill-reviewer + Skill(plugin-rulebook)? ✓ Correctly routes instead of reimplementing checks
→ Report renders skill-reviewer's verdict + plugin-rulebook FAILs? ✓ Presentation works

Pass: Activation and execution verified
```

**Pass Condition:** Skill activates correctly, procedures are clear, examples work end-to-end.

## Movement Pattern

See `movement-pattern.md` for the full CREATE→LINK→DELETE sequence, why the order matters, and a worked step-by-step example — not restated here to avoid drift.

## Consolidation Strategy

Consolidate related reference files to improve organization and reduce complexity.

### When to Consolidate

- **2-4 files** on same topic (e.g., error-handling.md + team-patterns.md + advanced-patterns.md)
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

   ## Error Handling
   [Content from error-handling.md]

   ## Team Patterns
   [Content from team-patterns.md]

   ## Advanced Patterns
   [Content from advanced-patterns.md]

   ## Table of Contents (at top)
   Links to each section
   ```

2. **Link from SKILL.md** (point to sections of consolidated file)
   ```markdown
   For error handling: see references/production-patterns.md#error-handling
   For team patterns: see references/production-patterns.md#team-patterns
   ```

3. **Delete old files** (error-handling.md, team-patterns.md, advanced-patterns.md)
   - Only after (1) and (2) verified
   - Test links before deleting

### Consolidation Report

See `production-patterns.md`'s "Changes Made Summary" for a worked example of this exact 3-file consolidation report format — not restated here to avoid drift.

## Content Extraction

Extract large low-frequency SKILL.md sections into new reference files to reduce body length while preserving content.

### When to Extract

- Section is ≥80 lines with estimated usage <20% of activations (apply 80% rule)
- SKILL.md is over 500 lines and the section is identifiably supplementary
- A natural "read more" boundary exists: the section is self-contained

### When NOT to Extract

- Section is used in 80%+ of activations → keep inline
- Section is already brief (<80 lines) → indirection is not worth it
- Content is genuinely core to the skill's primary workflow → must stay inline

### Extraction Procedure (always CREATE → LINK → DELETE)

1. **CREATE** `references/<topic>.md` with the full extracted content
2. **LINK**: Replace the inline section in SKILL.md with a concise pointer:
   ```markdown
   ## Section Name
   See `references/<topic>.md` for [description of what's there].
   ```
3. **DELETE** the inline body content (the pointer is now the only thing inline)

### Extraction Report

```
Extracted: "Compaction Mode" section (147 lines, <20% usage)
From: SKILL.md (694 lines → 547 lines after extraction)
To: references/compaction-orchestration.md (new file, 147 lines)
Pointer: "See references/compaction-orchestration.md for CP1–CP5 orchestration steps"
```

## Quality Decision Trees

Quick reference for common refinement decisions.

### Should This Content Move to References?

```
Is this content executed in 80%+ of skill activations?
├─ YES → Keep in SKILL.md (core procedural)
├─ NO → Can move to references/ (supplementary)
└─ UNCERTAIN → Keep in SKILL.md by default (preserve functionality)

Example: "Error handling for missing files"
├─ Happens in <20% of activations? → Move to references/
├─ Happens in 80%+ of activations? → Keep in SKILL.md
└─ Unsure? → Ask operator, keep in SKILL.md by default
```

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

Example: Deleting "Reference Files Guide" (80 lines, supplementary)
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
2. If deletion: Run Gate 4 (get operator approval)
3. If migration: Run Gate 3 (verify destination complete)
4. Make change using Movement Pattern (CREATE → LINK → DELETE)
5. Run validation Phase 5 (References) and Phase 7 (Testing)

Only if all gates/phases pass: Change is safe
```
