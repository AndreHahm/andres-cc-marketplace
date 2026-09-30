# Changes Draft Format

The format for the `changes.md` a plan-only run writes. The draft is a plan only — applying it is a separate refinement session, `skill-improver-loop`, or the operator directly.

## Table of Contents
1. [Draft Location](#draft-location)
2. [Approval Before Writing](#approval-before-writing)
3. [Draft Structure](#draft-structure)
4. [Finding IDs](#finding-ids)
5. [Implementation Order Rules](#implementation-order-rules)
6. [Worked Example](#worked-example)

## Draft Location

Confirm the path with the operator via `AskUserQuestion` before writing, unless the operator already named one. Default: `.draft/_open/<plugin>/<skill>/changes.md`, where `<plugin>` is the plugin name and `<skill>` the skill name. Never hardcode a different path; an operator may keep drafts elsewhere.

If a draft already exists at the confirmed path, read it first and add the new findings to it — never overwrite approved findings already there.

## Approval Before Writing

The findings were approved during the interview and the step-3 consolidation ask, so the plan-only exit needs no second round of approval; only the draft path needs confirming. Deletions are the exception: Gate 4 runs when the plan is applied, so the draft marks every DELETE as pending Gate 4. Write only approved findings, in their approved form:

- Group related findings into one entry (e.g. all tool-scope fixes)
- Drop a rejected finding; incorporate a modification made via "Other"

## Draft Structure

The draft has a header, then one section per finding, then a closing verification list.

**Header sections:**

```markdown
# Approved Changes for <skill-name>

All changes below were discussed and approved, except that every DELETE
still needs Gate 4 confirmation when applied. Implementation follows
CREATE → LINK → DELETE wherever a file is removed.

## Selected Goals

[Each selected goal with its verification check]

## Pre-Analysis Report (complete)

[The pre-analysis report]

## Implementation Order

1. **F1** — [short description]
2. **O1** — [short description]
```

**One section per finding:**

```markdown
## F1: [Finding title]

**Problem:** [What's wrong, where, why it matters — 2-4 sentences,
with line numbers and paths]

### Files affected

| Action | Path |
|--------|------|
| UPDATE | [path] |
| MIRROR | [mirror path, if applicable] |
| DELETE | [path, if a file is removed] — pending Gate 4 |

### Exact edits

[Before/after excerpts, at most ~20 lines each, changed lines only]

### Verification

- [How to confirm the change landed]
```

**Closing section:**

```markdown
## Post-Implementation Verification

1. `Skill(plugin-rulebook)` reports no FAIL findings
2. `skill-reviewer` reports no Critical or Major issues
3. Each selected goal's verification passes
```

## Finding IDs

| Prefix | Category | Meaning |
|--------|----------|---------|
| F1, F2, ... | Fix | Correctness defects |
| O1, O2, ... | Optimization | Improvements that aren't defects |
| M1, M2, ... | Missing | Capabilities the skill should have but lacks |

## Implementation Order Rules

- List findings in dependency order; state a dependency explicitly ("F2 depends on F1")
- Group related findings together
- Fixes before optimizations before missing capabilities

## Worked Example

```markdown
## F1: Tool used but not declared in allowed-tools

**Problem:** SKILL.md tells the operator to run `Grep` in step 4, but
`allowed-tools` lists only `Read Edit Write`, so the call is not
pre-approved and prompts on every use.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `plugins/<plugin>/skills/<skill>/SKILL.md` — `allowed-tools` |

### Exact edits

Before: `allowed-tools: Read Edit Write`
After: `allowed-tools: Read Edit Write Grep`

### Verification

- The frontmatter `allowed-tools` line includes `Grep`
```
