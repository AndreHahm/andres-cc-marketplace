---
description: >-
  Turn a verified dev-rules gap report into a file-by-file implementation plan, verify the
  plan's file coverage against the actual codebase, and quality-check before implementation.
argument-hint: --gaps <path> [--output-dir <dir>] [--exclude <id,id,...>]
allowed-tools: Read Write Glob Grep Bash(mkdir:*)
model: opus
---

Turn a verified gap report into an implementation plan: $ARGUMENTS

> **Invocation:** Run as `/plan-dev-rules --gaps ...` in the Claude Code prompt.

> **Pipeline:** Step 3 of 4. Reads a gap report from `/verify-dev-rules`, writes a plan consumed by `/implement-dev-rules`.

---

## Setup: Parse Arguments and Load Gaps

| Argument | Required | Default | Notes |
|---|---|---|---|
| `--gaps` | Yes | — | Path to a `*-gaps.md` file from `/verify-dev-rules` |
| `--output-dir` | No | Same directory as `--gaps` | Where to write the plan |
| `--exclude` | No | — | Comma-separated gap IDs to exclude beyond what the gap report already excludes |

If `--gaps` is missing or doesn't exist, stop and print:
```
Usage: /plan-dev-rules --gaps <path-to-gaps-report> [--output-dir <dir>] [--exclude <id,id,...>]

No gap report found. Run /verify-dev-rules first.
```

Read the gaps file fully. Build the working gap set: every row from its **Gaps** table where **Verified** is `CONFIRMED` or `PATCHED`, minus any gap ID passed via `--exclude`. Carry the **Excluded Candidates** table forward unchanged, plus any `--exclude` IDs added with reason "excluded by user at plan time."

**Pre-flight:** Print the working gap count by priority tier and the excluded count. Use `AskUserQuestion` — question: "Proceed with planning?", options: "Proceed" / "Cancel" — before proceeding.

---

## Step 1: Create an Implementation Plan for All Reported and Verified Gaps

For each gap in the working set, determine which file(s) currently assert the fact the gap corrects. Use `Grep`/`Glob` to find them directly — search for the field name, the specific stale value, or the surrounding phrase quoted in the gap's **Local Rule** column. Do not assume only the file named in the gap's original **Local Rule** source needs to change; a fact is frequently duplicated in sibling files (a component's own quick-reference table, a `references/*.md` schema doc, a validation checklist, an example template, and an executable validator script have all been found, in practice, to carry independent copies of the same enum or threshold that drift out of sync with each other).

Group findings into numbered sections, one per target file, each with a table:

```markdown
## {N}. `{file path}`

{One-sentence description of the file's role.}

| Gap | Priority | Change |
|---|---|---|
| G3 | P1 | {specific corrected wording/value, taken from the gap's Recommendation} |
```

Mark any file that does not yet exist as `## {N}. \`{file path}\` *(NEW FILE)*` and describe what it should contain.

Maintain an explicit exclusion list at the top of the plan (gap IDs from Excluded Candidates plus `--exclude`), each with its one-line reason, so the plan is self-documenting about what was deliberately left out and why — this list must be checked again in Step 2 and must never silently disappear.

---

## Step 2: Verify the Plan Against Current Codebase and Gaps

For every gap in the working set, run an independent completeness search across the whole codebase (not limited to files the plan already lists) for the fact it concerns — grep for the field name, the old value, and the new value. For every file the search turns up that is **not** already in the plan's file list:

- Add it as a new numbered section (or a new row in an existing section for that file) with the same gap ID and appropriate change description.
- Do not treat "the gap's original source file already covers it" as sufficient — sibling files carrying the same fact independently need their own plan entry, or they will silently stay stale after implementation even though the plan looks complete.

Also verify:
- **File existence** — every non-`NEW FILE` path in the plan actually exists (`Glob`/`Read` check).
- **No re-exclusion drift** — no plan row's Change contradicts or restates an entry in the exclusion list from Step 1.
- **Size budget sanity** — for any target that is a `SKILL.md` (or other file with a known line-count convention in this codebase, e.g. a rulebook-enforced limit), read its current line count and flag in the plan if the planned additions look likely to push it past its applicable soft/hard threshold, so `/implement-dev-rules` knows to move content to a reference file instead of inlining it.
- **Coverage** — every gap in the working set appears in at least one file section; none silently dropped.

Update the plan in place with anything Step 2 found. Add a short **Validation Notes** subsection under each affected file section only where Step 2 added or corrected something, so the diff from Step 1's first draft is visible.

---

## Step 3: Quality- and Completeness-Check

Before writing the final plan, verify:

- [ ] Every gap ID in the working set appears in at least one file section's table.
- [ ] Every file section has a one-sentence role description and a properly formatted table.
- [ ] Every exclusion (from the gap report and from `--exclude`) is listed with a reason and does not appear as a planned change anywhere.
- [ ] Every plan row's Priority matches its source gap's Priority.
- [ ] Every referenced file path was actually checked for existence in Step 2 (no unchecked assumptions).

If any check fails, fix it before writing.

---

## Step 4: Write Plan and Confirm Output

Write `{output-dir}/{name}-plan.md` (derive `{name}` from the gaps filename, stripping `-gaps.md`):

```markdown
# {Name} Dev-Rules Implementation Plan

**Source:** `{gaps file path}`
**Excluded (Do Not Adopt):** {gap IDs with one-line reasons, or "none"}
**Priority tiers:** P1 schema drift · P2 lifecycle/runtime · P3 safety/enforcement · P4 legacy cleanup

## 1. `{file path}`
{...as produced in Step 1-2...}

## Summary by Priority
| Priority | Gap Count |
|---|---|

## Files Requiring New Content Creation
| File | Rationale |
|---|---|
```

Print:
```
Plan written: {output-dir}/{name}-plan.md
Files affected: {n} ({n} new) | Gaps planned: {n} (P1: {n}, P2: {n}, P3: {n}, P4: {n}) | Excluded: {n}

Next: /implement-dev-rules --plan {output-dir}/{name}-plan.md
```
