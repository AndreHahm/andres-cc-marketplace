# Handoff Template

Use this template structure when creating handoff documents. The smart scaffold script pre-fills the
frontmatter and the Unpushed Changes table; complete the remaining sections based on session context.
Older handoffs (no frontmatter, a Session Metadata section) stay readable: every script and the load
step fall back to their body lines.

## Table of Contents

- [Frontmatter](#frontmatter)
- [Resume Card](#resume-card)
- [Current State Summary](#current-state-summary)
- [Codebase Understanding](#codebase-understanding)
  - [Critical Files](#critical-files)
- [Work Completed](#work-completed)
  - [Work Not Visible in Git](#work-not-visible-in-git)
  - [Unpushed Changes](#unpushed-changes)
  - [Decisions Made](#decisions-made)
- [Pending Work](#pending-work)
  - [Immediate Next Steps](#immediate-next-steps)
  - [Blockers/Open Questions](#blockersopen-questions)
  - [Deferred Items](#deferred-items)
- [Context for Resuming Agent](#context-for-resuming-agent)
  - [Important Context](#important-context)
  - [Assumptions Made](#assumptions-made)
  - [Potential Gotchas & Key Patterns](#potential-gotchas--key-patterns)
- [Related Resources](#related-resources)
- [Template Usage Notes](#template-usage-notes)

---

## Frontmatter

Flat `key: value` lines between `---` markers at the very top of the file, no nesting:

```
---
created: [ISO 8601 UTC, e.g. 2026-11-20T09:15:00Z]
project: [PROJECT_PATH]
branch: [GIT_BRANCH]
head: [commit SHA of HEAD]
pr: [PR number, or none]
platform: [linux | windows | macos]
continues_from: [previous handoff filename, or none]
state: [implementing | pr-draft | in-review | ready-to-merge | ready-to-publish | blocked | done]
context_mode: [none | review | ship | admin - derived from state, see SKILL.md CREATE Step 2 item 5]
---
```

`head` replaces the old Recent Commits list, and `continues_from` the old Handoff Chain section.
`project` is data only: no script ever uses it as a working directory.

```
# Handoff: [TASK_TITLE]
```

## Resume Card

Right after the title, at most 15 lines. A summary for the first read on load; the full sections stay
required. Its labels must not be bare `Branch:`, `Created:` or `Project:`, which older handoffs use.
`validate_handoff.py` requires each of the five lines below to carry a value.

```
- State: [state value, in a few words of context]
- Next step: [Immediate Next Steps item 1, verbatim]
- Branch and PR: [branch], [PR number or none]
- Blockers: [none, or each blocker in one line]
- User constraints: [the user's standing instructions in one line each, or none]
```

## Current State Summary

[One paragraph: What was being worked on, current status, and where things left off]

## Codebase Understanding

### Critical Files

| File | Role | Why it matters |
|------|------|----------------|
| path/to/file | What this file does and where it sits in the system | Why it matters for this task |

The role column carries the architecture (the old Architecture Overview section). The staleness check
reads its file paths.

## Work Completed

### Work Not Visible in Git

- [Issues filed, comments posted, runs left pending; or none]

### Unpushed Changes

Optional: only files that are uncommitted or committed but not pushed. The staleness check reads its
file paths when present.

| File | Change |
|------|--------|
| path/to/file | What changed and why |

### Decisions Made

| Decision | Options Considered | Rationale | Decided by |
|----------|-------------------|-----------|------------|
| Chose X over Y | X, Y, Z | Why X was chosen | user |

A decision the user made is not overridden without asking them again.

## Pending Work

### Immediate Next Steps

1. [Most critical next action - what to do first]
2. [Second priority]
3. [Third priority]

### Blockers/Open Questions

- [ ] Blocker: [description] - Needs: [what's required to unblock]
- [ ] Question: [unclear aspect] - Suggested: [potential resolution]

### Deferred Items

- Item 1 (deferred because: [reason, e.g., out of scope, needs user input])

## Context for Resuming Agent

### Important Context

[Critical information the next agent MUST know to continue effectively - this is the most important
section for handoff]

#### User Constraints

- [The user's standing instructions for this work, verbatim]

#### Learnings

- [Process and tool behavior found this session, e.g. a guard that rejects a chained marker-and-commit
  call]

### Assumptions Made

- Assumption 1: [what was assumed to be true]

### Potential Gotchas & Key Patterns

- [Codebase facts and conventions, e.g. a generated mirror that must not be edited by hand]

Learnings and Gotchas & Key Patterns are split by subject: process and tool behavior go in Learnings,
codebase facts and conventions here.

Environment: [optional: running processes and required env var NAMES only, never values; or none]

## Related Resources

- [Only links not findable from the PR or Critical Files; or none]

---

## Template Usage Notes

When filling this template:
1. Be specific and concrete - vague descriptions don't help the next agent
2. Include file paths with line numbers where relevant (e.g., `src/auth.ts:142`)
3. Prioritize the Resume Card, "Important Context" and "Immediate Next Steps"
4. Don't include sensitive data (API keys, passwords, tokens)
5. Focus on WHAT and WHY, not just WHAT - rationale is crucial for handoffs
6. Leave out what git or the PR already records (commit lists, merged file lists)
