# Validation Checklist

Quick reference checklist for validating Claude Code skills. `skill-reviewer` and `plugin-rulebook` run the authoritative checks (see SKILL.md's Core Workflow: Validation); use this checklist for a quick manual sanity pass before requesting a full validation run. It covers what the validation phases in the refinement workflow do not: frontmatter, body, reference and tool-scoping checks are those phases, so they are not repeated here.

## Table of Contents
1. [File Structure Checklist](#file-structure-checklist)
2. [Scripts/ Checklist (if present)](#scripts-checklist-if-present)
3. [Assets/ Checklist (if present)](#assets-checklist-if-present)
4. [Activation & Recognition Checklist](#activation--recognition-checklist)
5. [Production-Ready Checklist](#production-ready-checklist)
6. [Final Checklist: Ready to Deploy?](#final-checklist-ready-to-deploy)
7. [Quick Reference: Common Issues & Fixes](#quick-reference-common-issues--fixes)
8. [Anti-Patterns Validation](#anti-patterns-validation)

## File Structure Checklist

- [ ] `SKILL.md` exists (required)
- [ ] `references/` directory exists (if references used)
- [ ] `scripts/` directory exists (if scripts used)
- [ ] `assets/` directory exists (if assets used)
- [ ] No nested subdirectories in `references/` (one level deep only)
- [ ] All referenced files exist and are accessible
- [ ] No orphaned files (all files are used or documented)

## Scripts/ Checklist (if present)

- [ ] Scripts are clearly documented in SKILL.md or references/
- [ ] Scripts are executable and start with a shebang (`#!/usr/bin/env python3`, `#!/bin/bash`, etc.)
- [ ] Scripts have clear usage instructions
- [ ] Error handling is present (non-zero exit codes for failures)
- [ ] Scripts validate inputs (don't crash on bad data)
- [ ] Procedures invoke scripts clearly ("Run `scripts/validate.py`", not "use the script somewhere")

## Assets/ Checklist (if present)

- [ ] Assets are referenced in SKILL.md or output documentation
- [ ] File formats are appropriate (not converting unnecessarily)
- [ ] Filenames match references in documentation
- [ ] Assets are user-facing outputs (templates, example outputs, images), not internal build artifacts

## Activation & Recognition Checklist

- [ ] Skill description includes specific trigger phrases
  - [ ] Not vague ("Process things") but specific ("Create and refine skills")
  - [ ] Not generic ("Help with stuff") but specific ("Validate production readiness")
  - [ ] Trigger phrases Claude will recognize in real requests
- [ ] Test activation mentally:
  - [ ] User says: "Refine my skill" → does the description match?
  - [ ] User says: "Validate this is production-ready" → does the description match?
  - [ ] User says: "Make my skill clearer" → does the description match?
- [ ] Scope constraints are clear: the operator knows what the skill will and won't do, and the scope is realistic

## Production-Ready Checklist

For skills used in team environments or with production data:

### Error Handling
- [ ] Handles missing files gracefully
- [ ] Handles malformed input (YAML parsing, etc.)
- [ ] Provides helpful error messages (not cryptic)
- [ ] Doesn't fail silently (reports problems explicitly)

### Logging & Documentation
- [ ] Documents what it's doing (helpful for debugging)
- [ ] Provides change summaries (what was modified)
- [ ] Clear before/after state (helps verify correctness)

### Testing & Validation
- [ ] Validated with the smaller and larger models the skill is expected to run on
- [ ] Tested with real-world example requests
- [ ] Works across different project structures
- [ ] Edge cases considered (missing files, unusual configurations)

### Security
- [ ] Tool scoping applied (principle of least privilege)
- [ ] No hardcoded credentials or secrets
- [ ] Safe file operations (respects user boundaries)

## Final Checklist: Ready to Deploy?

Run through this final checklist before considering skill validation complete:

- [ ] All file structure checks pass
- [ ] All frontmatter checks pass
- [ ] SKILL.md body quality is high
- [ ] All references are present and complete
- [ ] Tool scoping is appropriate
- [ ] Activation will work (trigger phrases clear)
- [ ] Production patterns present (if team/production skill)
- [ ] Examples work end-to-end
- [ ] Documentation is clear and complete

If every box is checked, the skill is ready to deploy. If any check fails, identify the specific issues and address them before deployment.

## Quick Reference: Common Issues & Fixes

| Issue | Symptom | Fix |
|-------|---------|-----|
| **Too long** | SKILL.md in a Warning or Critical R13 tier | Move supplementary content to references/ |
| **Vague activation** | Description has no trigger phrases | Add specific phrases: "refine", "validate", "improve" |
| **Missing files** | SKILL.md links to a non-existent reference | Create the missing file or update the link |
| **Overly broad tools** | `allowed-tools: Bash(*)` | Restrict: `Bash(git:*)`, `Bash(npm:*)`, etc. |
| **Inconsistent structure** | Sections organized randomly | Reorganize: Quick Start → Workflows → Key Rules → References |
| **Nested references** | `references/subdir/file.md` | Move to `references/file.md` (flatten) |
| **Orphaned files** | Reference files not linked from SKILL.md | Link or delete unused files |
| **Unclear trigger phrases** | Skill doesn't activate when needed | Make the description specific: "Use when refining", "when validating for production" |
| **No examples** | All abstract explanations, no concrete cases | Add code examples, walk-throughs, decision trees |
| **Error handling missing** | Skill crashes on unexpected input | Add checks: missing files, malformed YAML, permission errors |

## Anti-Patterns Validation

Check against common skill creation mistakes. Detailed examples live in `${CLAUDE_PLUGIN_ROOT}/skills/skill-development/references/anti-patterns.md`. Structure and tool-scoping mistakes are covered by the validation phases of the refinement workflow; these are the activation and content ones.

### Activation Anti-Patterns

- [ ] **Vague description** - does the description match specific trigger phrases or just generic terms?
  - Bad: "A helpful skill for working with documents"
  - Good: "Extract text from PDF files. Use when analyzing PDFs or scanned documents"
- [ ] **Missing trigger context** - are trigger phrases matched to real user requests?
  - Test mentally: would the user's actual request activate this skill?
  - If not sure, ask in requirements gathering

### Content Anti-Patterns

- [ ] **No Quick Start** - does important content appear before extensive theory?
  - Bad: long explanation before examples
  - Good: example first, explanation second
- [ ] **Unclear reference links** - do link descriptions explain what's inside?
  - Bad: "Details are in `references/docs.md`"
  - Good: "Error handling patterns are in `references/error-handling.md`"
- [ ] **Theory before examples** - are concrete examples presented first?
  - Bad: 3 paragraphs explaining PDF structure, then one example
  - Good: example code first, then a link to the detailed theory
- [ ] **Generic placeholder names** - are examples concrete or generic?
  - Bad: `process_data(your_data)`
  - Good: `extract_names_from_csv(contacts.csv)`
