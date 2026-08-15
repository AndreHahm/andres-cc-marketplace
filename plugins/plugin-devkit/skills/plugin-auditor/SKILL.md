---
name: plugin-auditor
description: >-
  Dispatches this plugin's review agents (skilldir-reviewer, the type-matched
  *-reviewer, completeness-reviewer, activation-reviewer, security-reviewer,
  dependency-reviewer, scripts-reviewer, hook-reviewer, plugin-rulebook-checker)
  against a single component or a whole plugin, and normalizes every finding
  into plugin-rulebook's shared evidence schema. Produces evidence only — no
  score, no gates, no SWOT. Use when the user asks to 'audit this plugin',
  'gather findings without scoring', 'run just the reviewer fan-out', or when
  plugin-lifecycle-downstream's Audit phase or plugin-grader need raw evidence
  instead of a computed score.
argument-hint: "[target]"
allowed-tools: Read Grep Glob Agent Write Bash(date:*) Bash(node */codex-review-bridge/scripts/bridge-invoke.mjs:*) Bash(git ls-files:*)
---

# Plugin Auditor

Runs this plugin's reviewer agents and normalizes their findings into
`plugin-rulebook/references/evidence-schema.md`'s shared shape — evidence-gathering only.
Extracted from `plugin-grader`'s own Step 3 ("Dispatch Reviewers") so evidence-gathering and
scoring are two separate components: `plugin-grader` calls this skill for its own dispatch
(both standalone and, once evidence-only mode lands, by consuming a prior run's output) and
never re-derives the dispatch logic inline. See `references/dispatch-table.md` for exactly
which agents run in each mode — that table is ported directly from
`plugin-grader/references/rubric.md`, not redesigned.

## Quick Start

1. **Resolve target and mode** — `$0`, or ask if omitted/ambiguous. A single component
   (resolvable via `Glob`) is **component mode**; a plugin name or "this plugin"/"the whole
   plugin" is **plugin mode**.
2. **Determine target type** (component mode only) — `references/dispatch-table.md`'s
   Type-Matched Reviewer Table picks which `*-reviewer` applies.
3. **Reuse pre-supplied findings** — if the caller already supplies
   `plugin-rulebook-checker`/`plugin-validator` findings for some or all of the scope, use
   those instead of re-dispatching for the same component (see
   `references/dispatch-table.md`'s "Reuse Pre-Supplied Findings").
4. **Dispatch matching reviewers in parallel** — per `references/dispatch-table.md`. Print a
   status line first (e.g. "Dispatching N reviewers in parallel — this typically takes
   several minutes...") since agent dispatches run silently with no built-in progress
   streaming. Before dispatching, resolve each reviewer's backend (Claude-native, the
   unchanged default, or Codex) — see `references/codex-backend.md`. This resolver runs for
   every dispatch, but immediately returns Claude-native (matching today's behavior exactly)
   unless a user has explicitly enabled Codex routing.
5. **Normalize findings** — for each dispatched source, apply that source's own
   "Shared-schema join" note (every reviewer this skill dispatches documents one) to produce
   `evidence-schema.md` Finding entries: `id: <source>:<local-id>`, `source`, `scope` copied
   onto each finding, `status: open` for everything freshly found this dispatch.
6. **Write the report** — a Report Revision per `evidence-schema.md`, to
   `.claude/output/plugin-auditor/<target>-<timestamp>.json`. Get the timestamp via
   `date -u +%Y-%m-%dT%H-%M-%SZ`.
7. **Present a short narrative summary** in chat — finding counts per source and severity,
   not a full re-listing (the written report already has the detail). Then, if any Critical
   or Major finding exists, ask via `AskUserQuestion` whether to run `enhancement-suggestor`
   against the written report.

## When to Use

- `plugin-lifecycle-downstream`'s Phase 5 (Audit) needs normalized dependency, consistency,
  security, structure, content, completeness, activation, scripts, and hooks findings without
  a score
- `plugin-grader` needs fresh evidence for standalone scoring, or (once its evidence-only mode
  lands) needs a prior run's evidence instead of dispatching anything itself
- The user wants the full reviewer fan-out's findings, not a weighted score — "audit this
  plugin," "gather every finding," "run the reviewers without grading"

## When NOT to Use

- **A weighted, gated 0-10 score with SWOT and prioritized next steps** — use `plugin-grader`
  instead. `plugin-grader`'s own Step 3 calls this skill for its dispatch (standalone mode:
  fresh; evidence-only mode: pre-gathered) rather than redispatching inline — the
  distinguishing question is "does the request contain a scoring/ranking cue" (`plugin-grader`
  wins) vs. "does it only want the findings themselves" (this skill wins), the same precedence
  test `plugin-grader`'s own docs already state for the type-matched-reviewer case.
- **A single-axis check only** (just dependency cycles, just security, just activation
  overlap) — invoke that specific reviewer agent directly; this skill's value is the combined,
  normalized fan-out, not any one axis alone.
- **Structural manifest validation with no other reviewers** — invoke `plugin-validator`
  directly.

## Output Format

See `plugin-rulebook/references/evidence-schema.md`'s Report Revision shape — this skill's
written report is exactly that shape, with `produced_by: plugin-auditor` and `findings[]`
populated from every dispatched source's normalized output. No `score`, `gates_applied`,
`swot`, or `prioritized_next_steps` field — those don't exist in this skill's output at all,
not merely left empty. When any finding used the Codex backend, its `evidence_before`/`fix`
may quote content Codex observed in the target — treat the written report the same as any
other artifact containing quoted repo content for redaction purposes before sharing it
outside this run.

## Testing & Validation

1. **Component mode, clean target** — audit a skill with no findings from any dispatched
   reviewer; confirm the written report's `findings[]` is empty and every dispatched source is
   listed in `report_revisions`-equivalent provenance, not silently omitted.
2. **Component mode, mixed findings** — audit a skill with at least one Critical and one Minor
   finding from different reviewers; confirm both appear in `findings[]` with correct
   `source`-qualified `id`s and canonical `severity` (per each source's own native-to-canonical
   mapping in `evidence-schema.md`).
3. **Pre-supplied findings reuse** — call this skill with `plugin-rulebook-checker` findings
   already supplied for the target; confirm no fresh `plugin-rulebook-checker` dispatch
   happens and the supplied findings are normalized and included as-is.
4. **Plugin mode** — audit a small multi-component plugin; confirm `activation-reviewer`,
   `consistency-reviewer`, `dependency-reviewer`, and `plugin-validator` each run exactly once
   across the whole set, not once per component.
5. **Comparison against `plugin-grader`'s pre-refactor Step 3** — dispatch this skill against a
   known target, then compare its normalized findings against a `plugin-grader` run on the
   same target (taken before `plugin-grader`'s own Step 3 refactor lands) — same underlying
   findings, reshaped into the shared schema, plus `dependency-reviewer` findings `plugin-grader`
   never gathered before.
6. **Self-check** — `scripts/smoke_test.py` passes (this skill's own persisted smoke test),
   re-run after any SKILL.md edit.
7. **Codex backend disabled (default)** — confirm every dispatch goes through `Agent()` exactly as
   today; `references/codex-backend.md`'s resolver runs but immediately returns Claude-native when
   `reviewer_backend.enabled` is false or unset — no Codex invocation is attempted.
8. **Codex backend enabled, one reviewer fails** — confirm that reviewer falls back to the
   Claude-native `Agent()` dispatch, the fallback is recorded once on that dispatch's coverage note
   (not stamped per-finding), and every other reviewer's dispatch is unaffected.

**Quality gates:**
- [ ] Never dispatches all five type-matched `*-reviewer` agents for a single target — only
      the one matching the target's actual type
- [ ] Never re-dispatches `plugin-rulebook-checker`/`plugin-validator` for a component whose
      findings the caller already supplied
- [ ] Never computes or emits a score, gate, or SWOT — that stays `plugin-grader`'s job
- [ ] The written report path is always under `.claude/output/plugin-auditor/`
- [ ] The `enhancement-suggestor` offer at Step 7 always uses `AskUserQuestion` and is never
      auto-invoked
- [ ] A staging-mirror duplicate (`.claude/` vs `plugins/plugin-devkit/`) is noted, not
      treated as an error
- [ ] `security-reviewer` is never routed through Codex, regardless of configuration — hardcoded
      in the resolver, not just a config default
- [ ] A disabled/missing/malformed backend config always resolves to Claude-native — never fails
      the dispatch

## When to Invoke

Dispatched by two live production callers: `plugin-lifecycle-downstream`'s Phase 5 (Audit) dispatches
this skill as part of its twelve-phase pipeline, and `plugin-grader`'s Step 3 ("Dispatch Reviewers")
delegates to it for both standalone (fresh dispatch) and evidence-only (pre-gathered) scoring modes.
Also still invocable directly by name for a standalone audit pass outside either pipeline — this skill's
own dispatch logic doesn't depend on either caller.

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/dispatch-table.md` | Type-matched reviewer table, component-mode and plugin-mode dispatch lists, pre-supplied-findings reuse discipline — ported from `plugin-grader/references/rubric.md` |
| `references/codex-backend.md` | Backend resolver, Codex adapter, and configuration for optionally routing a reviewer dispatch through Codex instead of Claude — disabled by default |
| `assets/settings.json` | Git-tracked default config for the Codex backend (`reviewer_backend.enabled: false`) — see `references/codex-backend.md`'s Configuration section |
| `scripts/smoke_test.py` | This skill's own persisted smoke test (frontmatter validity, referenced-file existence, Bash-scope grant consistency) — re-run before packaging or after any SKILL.md edit |
| `plugin-rulebook/references/evidence-schema.md` | The shared Finding/Report Revision shape this skill's output conforms to |
| `plugin-grader` skill | Consumes this skill's output for scoring — standalone (fresh dispatch) and evidence-only (pre-gathered) modes |
| `enhancement-suggestor` agent | Turns this skill's findings into a full WHAT/WHY/HOW plan (Step 7) |
