---
description: >-
  Implement a verified dev-rules plan file-by-file, verify each change actually landed,
  run a staleness check across the whole codebase for sibling copies of the same facts,
  and quality-check (including plugin-rulebook compliance) before finishing.
argument-hint: --plan <path>
allowed-tools: Read Write Edit Glob Grep Bash(mkdir:*) Agent Skill TodoWrite
model: opus
---

Implement a verified plan file-by-file, then check for anything it missed: $ARGUMENTS

> **Invocation:** Run as `/implement-dev-rules --plan ...` in the Claude Code prompt.

> **Pipeline:** Step 4 of 4 (final). Reads a plan from `/plan-dev-rules`, applies it to the codebase, and writes an implementation report.

---

## Setup: Parse Arguments and Load Plan

| Argument | Required | Default | Notes |
|---|---|---|---|
| `--plan` | Yes | — | Path to a `*-plan.md` file from `/plan-dev-rules` |

If `--plan` is missing or doesn't exist, stop and print:
```
Usage: /implement-dev-rules --plan <path-to-plan>

No plan found. Run /plan-dev-rules first.
```

Read the plan fully. Parse its numbered file sections, exclusion list, and priority tiers.

**Group files for implementation:** files within the same skill/component directory are frequently cross-referential (a `SKILL.md` and its own `references/*.md` files often describe the same fact from different angles) — group these together so one implementer handles all of them consistently. Unrelated skills/components can be implemented independently.

**Identify foundational files:** if any planned file is shared configuration that other planned files' changes are described as "matching" (e.g. a `settings.json` other sections reference), implement that file first and synchronously, before dispatching the rest — later groups may need to read its final state to stay consistent.

**Pre-flight:** print the implementation groups (foundational file first, then each batch), the exclusion list, and ask for confirmation before making any changes.

---

## Step 1: Implement the Verified Plan

Implement the foundational file(s) first, directly.

For the remaining groups, implement each file section's rows. Whether done directly or by dispatching parallel `Agent` calls per group, every implementer must be given (not left to assume): the exact plan rows it owns, the full exclusion list (so nothing excluded is reintroduced), and the instruction to make surgical edits only — match existing file style, do not rewrite or reformat unrelated content, do not add anything beyond what the plan row specifies.

For every row, implement the specific corrected wording/value from the plan — do not re-derive or improvise a different fix than what the plan (already verified in the previous pipeline steps) specifies.

For `NEW FILE` sections, create the file, matching the conventions of sibling files in the same directory (heading style, frontmatter presence/absence, tone).

For any file with a known line-count convention in this codebase (e.g. a rulebook-enforced `SKILL.md` limit), check the line count before and after editing — `Read` output is line-numbered, so the last line number read is the count; no separate tool call is needed. If the plan flagged a likely overflow, or if the actual edit pushes past the applicable threshold, move the added content to the most relevant reference file instead of inlining it, and note this deviation from the plan's literal file assignment.

For any executable script touched, no shell-interpreter tool is granted here (unscoped `Bash` and `Bash(bash:*)`/`Bash(sh:*)` are both forbidden by this codebase's own tool-scoping rule) — re-read the diff carefully by inspection instead: balanced quotes/brackets, matching `case`/`esac` or `if`/`fi` blocks, no stray control characters. If a syntax check tool is genuinely required, delegate that specific check to an `Agent` invocation scoped with the narrow permission it needs, rather than broadening this command's own `allowed-tools`.

---

## Step 2: Verify Implementation Against the Plan

Do not trust an implementer's self-reported "done" — re-read every target file and confirm:

- Every plan row's specified value/wording is actually present in the file (grep or read the exact location).
- Every `NEW FILE` was actually created and is non-empty.
- Nothing in the plan's exclusion list appears anywhere in the diff (grep the excluded patterns across all touched files).
- No file was modified outside what the plan specified (spot-check: does the diff for each file correspond only to its planned rows?).

Record any row that did not land correctly and re-implement it before proceeding.

---

## Step 3: Staleness Check

For every distinct fact this plan changed (each enum, threshold, or claim that was corrected — not per-file, per-fact, since one fact may span several plan rows), search the **entire codebase** — not just the plan's own file list, not just the same plugin — for other files that independently assert the same fact and were never covered by the plan. This is the single most common source of incomplete implementation in this pipeline: a fact duplicated across a component's own quick-reference table, a `references/*.md` schema doc, a validation checklist, an example/prompt template, and an executable validator script drifts out of sync one copy at a time, and a plan built from a gap report only ever names the files known at plan time.

Concretely, for each changed fact:
- Grep the whole repository (excluding backup, output, merged, and not-yet-implemented scratch directories) for the **old** (pre-change) value or phrase.
- Any hit in a file outside the plan's list is a stale reference. If the fix is unambiguous (the same fact, same correction applies), fix it directly. If it requires judgment (a different component type, an intentionally different value, an out-of-scope skill), flag it for the user instead of guessing.
- Check for **shadow copies**: does the same component, skill, or command exist at another scope — project-root `.claude/`, user `~/.claude/`, or a different plugin entirely — independent of the copy just changed? Report any such shadow copy explicitly; do not silently edit it without flagging, since a duplicate at a different scope may be deliberately independent rather than simply stale.

Compile a Staleness Findings list: fact → old value → files fixed (with location) → files flagged but not fixed (with reason).

---

## Step 4: Quality- and Completeness-Check

Before finishing:

- [ ] Every plan row is implemented and verified (Step 2 passed with no outstanding re-implementations).
- [ ] The Staleness Check (Step 3) ran for every distinct changed fact, not just a sample.
- [ ] Every staleness finding is either fixed or explicitly flagged with a reason — none silently ignored.
- [ ] No excluded pattern was reintroduced anywhere, including in files found during the staleness check.
- [ ] **Plugin-rulebook compliance:** for every skill, agent, command, or hook file modified or created in this run, invoke the `plugin-rulebook` skill (if present in this codebase) via the `Skill` tool and confirm no REQUIRED-severity FAIL findings remain — this repo's own rule enforcement requires validating any created, modified, or renamed plugin component before finalizing. If `plugin-rulebook` resolves to a different copy than the one actually being modified (a shadow-copy conflict — see Step 3), note this and apply the ruleset manually instead of trusting the tool resolution.

If any check fails, fix it before writing the final report.

---

## Step 5: Write Implementation Report and Confirm Output

Write `{same directory as --plan}/{name}-implementation-report.md` (derive `{name}` from the plan filename, stripping `-plan.md`):

```markdown
# {Name} Dev-Rules Implementation Report

**Source plan:** `{plan file path}`

## Implemented
| Gap | File | Status |
|---|---|---|

## Staleness Findings
| Fact | Old Value | Files Fixed | Files Flagged (Not Fixed) |
|---|---|---|---|

## Plugin-Rulebook Compliance
| File | Result |
|---|---|

## Summary
Rows implemented: {n} | Files changed: {n} ({n} new) | Staleness fixes: {n} | Flagged (unresolved): {n} | Rulebook FAILs remaining: {n}
```

Print:
```
Implementation report written: {report path}
Files changed: {n} ({n} new) | Staleness fixes: {n} | Flagged for review: {n} | Rulebook FAILs: {n}
```

If any item is flagged for review or any rulebook FAIL remains, list them directly in the chat output — do not let them be visible only inside the report file.
