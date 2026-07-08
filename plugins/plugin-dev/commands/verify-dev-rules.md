---
description: >-
  Verify a dev-rules report against current official Claude Code documentation, identify
  gaps between local plugin-dev rules and the platform, and re-verify every reported gap
  before finalizing a gap report.
argument-hint: --report <path> | --level <plugin|component> --name <name> [--output-dir <dir>]
allowed-tools: Read Write Glob Grep WebFetch WebSearch Bash(mkdir:*)
model: opus
---

Verify a rules report produced by `/report-dev-rules` against current official Claude Code documentation, and produce a verified gap report: $ARGUMENTS

> **Invocation:** Run as `/verify-dev-rules --report ...` or `/verify-dev-rules --level ... --name ...` in the Claude Code prompt.

> **Pipeline:** Step 2 of 4. Reads a report from `/report-dev-rules`, writes a gap report consumed by `/plan-dev-rules`.

---

## Setup: Parse Arguments and Locate Report

| Argument | Required | Default | Notes |
|---|---|---|---|
| `--report` | One of `--report` or `--level`+`--name` required | — | Direct path to a `*-rules.md` file from `/report-dev-rules` |
| `--level` | — | — | `plugin` or `component` (not `marketplace` — verify one report at a time) |
| `--name` | Required if `--level` given | — | Used to locate `{output-dir}/{name}-rules.md` |
| `--output-dir` | No | `.claude/output/rules` | Must match the directory the input report was written to |

If neither `--report` nor `--level`+`--name` resolves to an existing file, stop and print:
```
Usage: /verify-dev-rules --report <path-to-rules-report> [--output-dir <dir>]
   or: /verify-dev-rules --level <plugin|component> --name <name> [--output-dir <dir>]

No rules report found. Run /report-dev-rules first.
```

Read the resolved report file fully. Extract every rule row from every section (see the "Standard table format" in `/report-dev-rules` — `Rule | Severity | Source | Detail`, plus CLAUDE.md rows and any existing Conflict/Consistency rows).

**Pre-flight:** Before any `WebFetch`/`WebSearch` call, print the resolved report path, the count of rules extracted, and the distinct topic areas found (e.g. "skill frontmatter", "agent/subagent frontmatter", "hooks", "plugin manifest", "commands", "rules/CLAUDE.md", "MCP", "settings"). Wait for confirmation ("yes"/"y"/"proceed"/"ok") before proceeding; on any other answer, print "Cancelled." and stop.

---

## Step 1: Verify Reported Rules Against Official Docs

For each distinct topic area found in the report, locate the current official Claude Code documentation for that area. Use `WebSearch`/`WebFetch` to find and read the live docs — **do not answer from training-data memory**; the platform's schemas, valid enum values, and lifecycle behavior evolve across releases, and a rule that was correct when the report was generated may already be stale by the time you verify it (this is the same failure mode `/report-dev-rules` was built to catch across local files — the same discipline applies here against the external source).

For every rule row extracted in Setup, compare it against the official documentation for its topic area and classify:

| Classification | Meaning |
|---|---|
| `CONFIRMED` | Local rule matches current official docs |
| `OUTDATED` | Official docs have changed since the local rule was written (cite what changed) |
| `MISSING` | Official docs describe a field, value, event, or behavior with no corresponding local rule at all |
| `NOT-OFFICIAL` | Rule is a project-internal convention (naming style, line-count budget, internal field like `title`/`impact`) with no platform-doc equivalent — this is expected and not a defect on its own |
| `UNVERIFIABLE` | No official documentation could be found covering this rule; note this explicitly rather than guessing |

Record, for every non-`CONFIRMED` and non-`NOT-OFFICIAL` row: the doc URL, a short quoted or paraphrased excerpt supporting the classification, and the exact local rule text with its source file.

---

## Step 2: Identify and Report Gaps Between Local Rules and Official Docs

From every `OUTDATED`, `MISSING`, and `UNVERIFIABLE` classification in Step 1, compile a gap finding. Assign each:

| Field | Values |
|---|---|
| **ID** | Sequential: `G1`, `G2`, ... |
| **Priority** | `P1` schema drift (field/type/value lists out of date) · `P2` lifecycle/runtime behavior (missing behavioral rules) · `P3` safety/enforcement · `P4` legacy cleanup / internal convention |
| **Type** | `OUTDATED` / `MISSING` / `UNVERIFIABLE` |
| **Local rule** | Quoted text + source file(s) from the input report |
| **Official doc** | URL + quoted/paraphrased excerpt from Step 1 |
| **Recommendation** | The specific corrected wording or addition |

**Exclusion safeguard:** Before finalizing a gap, check whether it would make local rules *more restrictive* than the official docs — e.g. banning a value the docs list as a supported default, or treating something the docs describe as optional as if it were forbidden. If so, do not add it as a gap to fix; instead list it under a separate **Excluded Candidates** section with a one-line reason. This class of mistake (proposing a rule that quietly contradicts an official default) has happened before in this exact pipeline and was only caught on a second review pass — do not rely on Step 3 alone to catch it; screen for it here first.

Output both lists (gaps and excluded candidates) — do not silently drop excluded candidates from the report.

---

## Step 3: Verify All Reported Gaps Against Official Docs

Re-open every gap from Step 2 with fresh scrutiny — do not trust your own Step 2 citation from memory. For each:

- Re-confirm the cited official-doc excerpt actually supports the gap's classification and recommendation. If it doesn't hold up, downgrade the gap to `UNVERIFIABLE` or drop it, and record why.
- Check for contradictions between gaps in the same report — two gaps should never recommend incompatible changes to the same rule.
- Check that no finalized gap effectively restates something listed in **Excluded Candidates**. If one does, remove it and add a note under Excluded Candidates cross-referencing the duplicate.
- Check that no gap's recommendation reintroduces a pattern already excluded in a *previous* run of this pipeline, if a prior gap report or implementation plan for the same target is available in `{output-dir}` — read it if present and treat its exclusions as still binding unless the user's arguments say otherwise.

Update the Step 2 gap list in place with the outcome of this pass. For each gap, add a **Verified** column: `CONFIRMED` (citation holds, recommendation stands), `PATCHED` (recommendation text corrected during this pass — show old vs. new), or `DROPPED` (removed, with reason moved to Excluded Candidates).

---

## Step 4: Quality- and Completeness-Check

Before writing the report, verify:

- [ ] Every rule row from the input report received a Step 1 classification — none silently skipped.
- [ ] Every gap has all six Step 2 fields populated (ID, Priority, Type, Local rule, Official doc, Recommendation) plus a Step 3 **Verified** value.
- [ ] No finalized gap duplicates or contradicts an entry in Excluded Candidates.
- [ ] Every gap's Priority is exactly one of P1–P4.
- [ ] Every citation URL in the report was actually fetched during Step 1 or Step 3 in this run (no fabricated or assumed URLs).

If any check fails, fix it before writing. Do not write a report with unresolved checklist items.

---

## Step 5: Write Gap Report and Confirm Output

Write `{output-dir}/{name}-gaps.md`:

```markdown
# {Name} Dev-Rules Gap Report

Verifies `{input report path}` against official Claude Code documentation.
**Generated:** {YYYY-MM-DD} | **Input report:** {path} | **Rules checked:** {n}

## Gaps
| ID | Priority | Type | Local Rule | Official Doc | Recommendation | Verified |
|---|---|---|---|---|---|---|

## Excluded Candidates
| ID | What was considered | Why excluded |
|---|---|---|

## Coverage Summary
Rules checked: {n} | Confirmed: {n} | Gaps: {n} (P1: {n}, P2: {n}, P3: {n}, P4: {n}) | Excluded: {n} | Unverifiable: {n}
```

Print:
```
Gap report written: {output-dir}/{name}-gaps.md
Gaps found: {n} ({n} P1, {n} P2, {n} P3, {n} P4) | Excluded candidates: {n}

Next: /plan-dev-rules --gaps {output-dir}/{name}-gaps.md
```
