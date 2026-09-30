# Changes Draft Format

The format for the `changes.md` a plan-only run writes. The draft is a plan only — applying it is a separate refinement session, `skill-improver-loop`, or the operator directly.

## Draft Location

Confirm the path with the operator via `AskUserQuestion` before writing. Default: `.draft/_open/<plugin>/<skill>/changes.md`, where `<plugin>` is the plugin name and `<skill>` the skill name. Never hardcode a different path; an operator may keep drafts elsewhere.

If a draft already exists at the confirmed path, read it first and add the new findings to it — never overwrite approved findings already there.

## Approval Before Writing

Write only findings the operator approved, and only the approved form:

- Group related findings into one question (e.g. all tool-scope fixes)
- Use `multiSelect: true` for independent findings and single-select for dependent ones
- Drop a rejected finding; incorporate a modification made via "Other"

## Draft Structure

```markdown
# Approved Changes for <skill-name>

All changes below were discussed and approved. Implementation follows
CREATE → LINK → DELETE wherever a file is removed.

## Selected Goals

[Each selected goal with its verification check — see goal-derivation.md]

## Pre-Analysis Report (complete)

[The pre-analysis report]

## Implementation Order

1. **F1** — [short description]
2. **O1** — [short description]

---

## F1: [Finding title]

**Problem:** [What's wrong, where, why it matters — 2-4 sentences, with line numbers and paths]

### Files affected

| Action | Path |
|--------|------|
| UPDATE | [path] |
| MIRROR | [mirror path, if applicable] |

### Exact edits

[Before/after excerpts, at most ~20 lines each, changed lines only]

### Verification

- [How to confirm the change landed]

---

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
`allowed-tools` lists only `Read Edit Write`, so the call is blocked at runtime.

### Files affected

| Action | Path |
|--------|------|
| UPDATE | `plugins/<plugin>/skills/<skill>/SKILL.md` — frontmatter `allowed-tools` |

### Exact edits

    # Before:
    allowed-tools: Read Edit Write
    # After:
    allowed-tools: Read Edit Write Grep

### Verification

- The frontmatter `allowed-tools` line includes `Grep`
```
