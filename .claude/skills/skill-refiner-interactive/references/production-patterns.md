# Production Patterns

Essential patterns for production-ready skills used in team environments or with production data.

## Table of Contents
1. [Error Handling](#error-handling)
2. [Logging & Change Documentation](#logging--change-documentation)
3. [Security Considerations](#security-considerations)
4. [Example: Production-Ready Validation Report](#example-production-ready-validation-report)

## Error Handling

Production skills must handle errors gracefully, providing helpful feedback instead of failing silently.

### File Operations

**Missing files:** locating the target skill follows SKILL.md's step 1 (project first, then user-space with a warning, cache refused, otherwise ask the operator). Never silently fail or assume a path exists.

**Malformed content:**

```
When reading SKILL.md:
1. Attempt to parse YAML frontmatter
2. If parsing fails → Report the specific error
   Example: "Frontmatter syntax error on line 3: missing colon after 'name'"
3. Continue with graceful degradation if possible
4. Ask the operator for help if content is corrupt
```

**Permission issues:**

```
When editing files:
1. Verify the file is writable before attempting an edit
2. If not writable → Report clearly
   Example: "Cannot edit /path/file.md: permission denied"
3. Suggest: "Check file permissions or move to a project-scoped location"
4. Don't attempt workarounds; inform the operator
```

## Logging & Change Documentation

### Changes Made Summary

Always provide a clear before/after summary:

```
Refinement completed:

CHANGES MADE:
- Moved "Deployment Notes" section to references/deployment-notes.md
  (150 lines removed from SKILL.md; pointer added)
- Consolidated 3 files into 1: error-handling.md (124), team-patterns.md (189)
  and edge-cases.md (156) = 469 lines → production-patterns.md (380), saving 89 lines
- 4 SKILL.md pointers updated; all links verified working

METRICS:
Before: 620 lines (SKILL.md) + 469 lines (references) = 1,089 total
After:  470 lines (SKILL.md) + 530 lines (references: 380 + 150) = 1,000 total
R13 tier: Critical (620) → Soft Warning (470)

VALIDATION: phases 1-7 passed
```

### Validation Logging

Document what was validated and the results:

| Phase | Check | Result |
|-------|-------|--------|
| 1 File Inventory | SKILL.md, 3 references, 1 script | pass |
| 2 Read All | frontmatter valid, body loads, all links resolve | pass |
| 3 Frontmatter | name and description valid, trigger phrases present, no non-standard fields | pass |
| 4 Body Content | 470 lines (within the R13 tiers), 80% rule applied, Quick Start present | pass |
| 5 References | all files exist, no orphans, one level deep | pass |
| 6 Tool Scoping | Read, Edit, Write, Glob declared and used; Bash limited to `Bash(git:*)` | pass |
| 7 Testing | trigger phrases activate; Quick Start walkthrough clear | pass |

## Security Considerations

### File Access Scope

```
ALLOWED (project-scoped skills):
✓ Read, Edit, Write: files in the current project (skills/, .claude/skills/)
✓ Glob: file discovery in the project

CONDITIONAL (user-space skills):
⚠ Read, Edit, Write: ~/.claude/skills/ (affects all projects - requires confirmation)

FORBIDDEN (never access):
✗ ~/.claude/plugins/cache/* (installed plugins - read-only)
✗ /etc/, /private/, /System/, or other system paths
✗ Any other path outside the user's project directories (the confirmed user-space skill above is the only exception)
✗ Sensitive files (.env, .git/config with credentials, etc.)
```

### Tool Scoping

Good and poor `allowed-tools` scoping examples live in `allowed-tools.md`; the validation checks are Phase 6 in `refinement-workflow.md`.

## Example: Production-Ready Validation Report

```
SKILL: example-skill
VALIDATED: <YYYY-MM-DD>
Status: PRODUCTION READY (all validation phases passed)

STRUCTURE: clean (SKILL.md, 4 references, 1 script), one level deep, kebab-case names
ACTIVATION: specific trigger phrases; description matches real requests
CONTENT: SKILL.md 430 lines (Soft Warning tier, no Critical); 80% rule applied;
         examples are concrete
ERROR HANDLING: missing files, malformed YAML and permission issues all handled
TOOL SCOPING: least privilege; Bash limited to git and npm; no broad wildcards
DOCUMENTATION: before/after summaries, validation logging, complete references

RECOMMENDATIONS: none. For team adoption, share the skill as a model for
production patterns and reference its error handling in team guidelines.
```
