---
description: >-
  Verify a dev-rules report against current official Claude Code documentation, identify
  gaps between local plugin-devkit rules and the platform, and re-verify every reported gap
  before finalizing a gap report.
argument-hint: --report <path> | --level <plugin|component> --name <name> [--output-dir <dir>]
allowed-tools: Read Write Glob Grep WebFetch WebSearch Bash(mkdir:*) Skill(upstream-sources-registry)
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

**Load prior exclusions:** check whether `{output-dir}/{name}-gaps.md` already exists from a previous run against this same target. If it does, read its **Excluded Candidates** table now and hold it for Step 2 — this is what lets Step 2's "Intentional divergence (carried forward)" case actually find prior decisions on a first pass through this document, rather than only becoming available once Step 3 re-reads it. If no prior gap report exists, proceed with an empty prior-exclusions set (every gap in this run is newly surfaced).

**Provenance marking:** a full run of this command from Setup through Step 5 needs no special marking — the whole report is provenance-clean by construction. But if this pass instead updates an existing gap report by manually following these steps rather than through a fresh top-to-bottom invocation (e.g. a scoped follow-up investigating one new source or a handful of gaps), mark every new or changed Gap row's **Verified** value with a trailing parenthetical recording that, e.g. `CONFIRMED (manually-followed, not a formal /verify-dev-rules invocation)`. This isn't a lesser trust level — Step 1-3's classification and citation requirements still apply in full — it's a provenance record: without it, a later reader can't tell "went through this command's own gates end-to-end" from "was reasoned through inline," and a scoped follow-up that skipped the Pre-flight confirmation and the full Step 1-4 sequence could otherwise be mistaken for a complete re-verification of the whole report.

**Pre-flight:** Before any `WebFetch`/`WebSearch` call, print the resolved report path, the count of rules extracted, and the distinct topic areas found (e.g. "skill frontmatter", "agent/subagent frontmatter", "hooks", "plugin manifest", "commands", "rules/CLAUDE.md", "MCP", "settings"). Use `AskUserQuestion` — question: "Proceed with verification?", options: "Proceed" / "Cancel" — before proceeding; on "Cancel" (or any answer other than an affirmative), print "Cancelled." and stop.

---

## Step 1: Verify Reported Rules Against Official Docs

For each distinct topic area found in the report, invoke `Skill(upstream-sources-registry)` with that topic to check whether a tracked source already covers it:
- If a tracked, enabled source matches, use the registry's returned content (a fresh cached snapshot, or the result of a freshness check it runs itself) as the current official documentation for that topic area.
- If no tracked source matches, fall back to `WebSearch`/`WebFetch` directly to find and read the live docs, same as before.

**Do not answer from training-data memory in either path** — the platform's schemas, valid enum values, and lifecycle behavior evolve across releases, and a rule that was correct when the report was generated may already be stale by the time you verify it (this is the same failure mode `/report-dev-rules` was built to catch across local files — the same discipline applies here against the external source).

For every rule row extracted in Setup, compare it against the documentation content obtained above for its topic area and classify:

| Classification | Meaning |
|---|---|
| `CONFIRMED` | Local rule matches current official docs |
| `OUTDATED` | Official docs have changed since the local rule was written (cite what changed) |
| `MISSING` | Official docs describe a field, value, event, or behavior with no corresponding local rule at all |
| `NOT-OFFICIAL` | Rule is a project-internal convention (naming style, line-count budget, internal field like `title`/`impact`) with no platform-doc equivalent — this is expected and not a defect on its own |
| `UNVERIFIABLE` | No official documentation could be found covering this rule; note this explicitly rather than guessing |

**Authority-tier gate:** when the registry path was used, it returns the source's `authority` tier alongside its content (per `upstream-sources-registry`'s Freshness Check). A `changelog`/`informal`-tier source is corroborating evidence only, never sufficient on its own to classify `OUTDATED`/`MISSING` — if that's the *only* source backing the classification, classify the row `UNVERIFIABLE` instead and note "informal-only, needs spec/guide corroboration" rather than treating it as an actionable gap. Only a `spec`/`guide`-tier source (or training-data-independent direct `WebFetch`/`WebSearch` of a `docs.claude.com` page) is sufficient to classify `OUTDATED`/`MISSING` on its own.

**Before finalizing a `MISSING` classification:** grep the target component's own `references/*.md` files and its `SKILL.md`/agent/command body for the field, value, event, or behavior in question. Official docs describing something with no *local rule row* for it is not the same as the component having *zero coverage* of it — a fact can be fully or partially documented in a reference file or body prose without ever having been extracted into this report's rule tables. If the sweep finds existing coverage, downgrade the finding: it's an `OUTDATED`-in-summary issue (a condensed table or summary line is stale) at most, not a `MISSING` one. This check exists because `plan-dev-rules`'s own Step 2 independent re-verification has repeatedly caught `MISSING` classifications from this step that turned out to be partially or fully covered already — catching it here, before the gap is even written, is more efficient than relying on that downstream safety net every time.

Record, for every non-`CONFIRMED` and non-`NOT-OFFICIAL` row: the doc URL (or the registry source `id` and its `authority` tier if the registry path was used), a short quoted or paraphrased excerpt supporting the classification, and the exact local rule text with its source file.

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

**Exclusion mechanism:** before finalizing a gap, check two things:

1. **Automatic safeguard** — would fixing this gap make local rules *more restrictive* than the official docs (e.g. banning a value the docs list as a supported default, or treating something the docs describe as optional as if it were forbidden)? If so, move it straight to **Excluded Candidates** with case `Automatic safeguard` and a one-line explanation — no user confirmation needed. This class of mistake (proposing a rule that quietly contradicts an official default) has happened before in this exact pipeline and was only caught on a second review pass — do not rely on Step 3 alone to catch it; screen for it here first.
2. **Intentional divergence** — does the local rule deliberately differ from the official docs for a stated policy reason, not a defect? Check the prior-exclusions set loaded in Setup: if it already documents this gap as intentional, carry it forward with case `Intentional divergence (carried forward)` — no need to re-ask. If this is newly surfaced with no prior record, present it to the user (`AskUserQuestion`: conform to match the official docs / keep local as an intentional, recorded divergence) before finalizing — do not silently assume divergence is intentional just because it looks defensible. **If the user answers "conform"**, immediately compile it as a finalized Gap row in this same pass (full ID/Priority/Type/Local rule/Official doc/Recommendation) — do not leave it as a chat-turn commitment to be applied later. An approved-but-unrecorded "conform" decision has no artifact for `/plan-dev-rules` or `/implement-dev-rules` to act on and can sit unimplemented indefinitely, discovered only by accident.

Output both lists (gaps and excluded candidates) — do not silently drop excluded candidates from the report. Every Excluded Candidates row states which of the two cases above it is, so a later run can tell an automatic safeguard from a human-confirmed decision.

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
- [ ] Every Excluded Candidates row states its Case (`Automatic safeguard` or `Intentional divergence (carried forward)`/newly-confirmed) — none left blank.
- [ ] Every gap's Priority is exactly one of P1–P4.
- [ ] Every citation URL in the report was actually fetched during Step 1 or Step 3 in this run (no fabricated or assumed URLs).
- [ ] Every `AskUserQuestion` decision in Step 2 that resolved to "conform" has a corresponding Gap row in the Gaps table — none left as a chat-turn commitment only.
- [ ] Every `MISSING` classification was checked against the target component's own `references/*.md` tree (and body) before being finalized, per Step 1's pre-finalization sweep.
- [ ] If this run updated an existing gap report without a fresh top-to-bottom invocation, every new/changed Gap row's Verified value carries the manually-followed provenance note from Setup — none left ambiguous about which gate it actually went through.

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
| ID | What was considered | Case | Why excluded |
|---|---|---|---|

## Coverage Summary
Rules checked: {n} | Confirmed: {n} | Gaps: {n} (P1: {n}, P2: {n}, P3: {n}, P4: {n}) | Excluded: {n} | Unverifiable: {n}
```

Print:
```
Gap report written: {output-dir}/{name}-gaps.md
Gaps found: {n} ({n} P1, {n} P2, {n} P3, {n} P4) | Excluded candidates: {n}

Next: /plan-dev-rules --gaps {output-dir}/{name}-gaps.md
```
