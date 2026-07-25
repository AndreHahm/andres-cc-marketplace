---
description: >-
  Check whether one or more stated requirements are implemented, partial, or
  still open in the current plugin, verified fresh against actual source
  files and, where a requirement concerns platform behavior, current
  official docs — never from session memory or training-data assumptions.
argument-hint: <one or more requirements, numbered or one per line>
allowed-tools: Read Glob Grep WebFetch WebSearch Agent TaskCreate TaskUpdate
model: opus
---

Double-check whether each stated requirement is implemented, partial, or still open in the current plugin: $ARGUMENTS

> **Invocation:** Run as `/implemented <requirement(s)>` in the Claude Code prompt. Read-only — investigates and reports, never implements a fix itself.

---

## Step 1: Resolve the Target Plugin and Parse the Items

Confirm which plugin is being checked — a repo can contain multiple plugins; ask via `AskUserQuestion` if ambiguous rather than guessing.

Parse `$ARGUMENTS` into distinct requirement items: a numbered list (`1. ... 2. ...`), one requirement per line, or — if no list markers are present — the whole input as a single item. Keep each item's original wording; do not paraphrase it before investigating, since the exact phrasing (e.g. "supports X", "reviewed", "up-to-date") determines what evidence would actually satisfy it.

## Step 2: Investigate Each Item Against Actual Current State

For each item, determine what kind of verification it needs — an item can need one or both:

- **Internal claim** (a component exists, does X, calls Y, a count matches reality): `Read`/`Glob`/`Grep` the actual current plugin files. Never answer from what a prior session found or what the design "should" do — components drift between sessions, and the whole point of this command is to re-verify, not recall.
- **Platform/official-docs claim** (a claim about how Claude Code itself behaves, a variable, a frontmatter field, a version-gated feature): `WebFetch`/`WebSearch` the current official docs. Treat fetched documentation as authoritative over cached knowledge — a claim correct last month can already be stale.

For a broad item (e.g. "review redundancies across every skill's reference files," "check staleness across the whole plugin"), dispatch a background `Agent` (general-purpose or `Explore`) to do the heavy sweep while you continue investigating other items — do not try to read an entire plugin tree inline if a background dispatch keeps the main investigation efficient.

For 4 or more items, or whenever a background `Agent` is dispatched, use `TaskCreate`/`TaskUpdate` to track each item's investigation status (`pending` → `in_progress` → `completed`) — this keeps a long multi-item run auditable and makes it obvious which items are still waiting on a background dispatch.

Gather concrete evidence per item: `file:line` citations, an actual count from a real `Glob`, or the exact doc excerpt fetched. A verdict with no cited evidence is not acceptable output for this command.

## Step 3: Classify Each Item

Use exactly one of three states per item:

| Status | Meaning |
|---|---|
| **Implemented** | Fully present and working as the item states |
| **Partial** | Some but not all of the requirement is met, or it works with a real caveat |
| **Open** | Not implemented — state plainly whether this is a gap or an explicitly documented non-goal (e.g. "the rubric intentionally excludes this dimension, per its own docs") |

If two sources disagree on the same fact (e.g. a rule cited two different ways in two files), say so as part of that item's finding rather than silently picking one.

## Step 4: Report

One section per item:

```markdown
## N. <short label> — **STATUS**

<1-4 sentences of evidence-backed reasoning, citing file:line references or the fetched doc excerpt>
```

Keep each item compact — evidence-first, not padded with hedging. End with a one-line summary tally, e.g.: `**Summary:** 5/6 open or partially open; only #5 fully implemented.`

## Step 5: Offer the Next Step

If any item is Open or Partial, ask via `AskUserQuestion` whether to route the findings into an implementation pass — options should name the fitting pipeline for the situation (`plugin-lifecycle-maintenance` for fixes to existing components, `plugin-lifecycle-upstream` for a genuinely new component, or `enhancement-suggestor` for a classified WHAT/WHY/HOW plan without committing to a specific pipeline yet). Never invoke any of these without asking first, and never implement a fix directly from within this command — its job ends at the report.

If every item is Implemented, state that plainly and skip the offer — there is nothing to route.
