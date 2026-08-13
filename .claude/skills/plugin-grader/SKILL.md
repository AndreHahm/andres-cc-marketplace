---
name: plugin-grader
description: >-
  Grades, rates, ranks, or scores a Claude Code plugin or a single
  skill/agent/command/hook against 12 weighted quality dimensions —
  structure, content quality, rule compliance, completeness,
  maintainability, robustness, simplicity, testing, uniqueness, safety,
  efficiency, and actionability — producing a weighted overall score with
  hard gates for critical issues, dimension-by-dimension reasoning, a SWOT
  summary, and prioritized next steps as structured JSON. Use when the
  user asks to 'grade this plugin', 'rank this skill', 'score this Claude
  Code plugin', 'rate this skill and suggest improvements', 'rank this
  plugin from 1 to 10', or 'grade this rule' — skill/agent/command/hook/rule
  are all gradeable target types. Standalone/direct use dispatches
  `plugin-auditor` for fresh evidence; an internal evidence-only mode for
  `plugin-lifecycle-downstream`'s Grading phase scores pre-gathered evidence
  instead, with no dispatch of its own.
argument-hint: "[target]"
allowed-tools: Read Grep Glob Agent Skill Write Bash(python scripts/compute_score.py:*) Bash(date:*)
---

# Plugin Grader

Orchestrates this plugin's existing reviewer agents into one weighted, gated, 0-10 score with a SWOT summary and prioritized next steps — it does not re-judge quality independently. See `references/rubric.md` for why: nearly every dimension already has a dedicated reviewer, and re-deriving judgments would drift out of sync with them.

## Quick Start

1. **Resolve target and mode** — `$0`, or ask if omitted/ambiguous
2. **Determine target type** — skill/agent/command/hook (component mode) or whole plugin
3. **Gather evidence** — standalone mode: dispatch `plugin-auditor` fresh; evidence-only mode: consume pre-supplied evidence, no dispatch
4. **Score dimensions and compute** — map findings to the rubric, run `scripts/compute_score.py`
5. **Build SWOT + prioritized next steps** — `references/swot-and-next-steps.md`
6. **Write the JSON report** — `.claude/output/plugin-grader/<target>-<timestamp>.json`
7. **Present a narrative summary** in chat, then offer `enhancement-suggestor` as a follow-up

## When to Use

- The user wants one defensible, reproducible numeric score for a plugin, skill, agent, command, or hook — not just a list of findings
- Comparing "how good is X" needs hard gates so a critical issue (broken rule compliance, missing core functionality) can't be averaged away by strong scores elsewhere
- The user wants prioritized next steps tied directly to score impact, not just a findings dump

## When NOT to Use

- Holistic Keep/Improve/Update/Retire/Merge verdicts across a whole skill library, without numeric weighting — use `skill-stocktake` instead (it explicitly uses holistic judgment, not a numeric rubric, even though some dimension names overlap)
- A single-axis check only (just rule compliance, just security, just activation overlap) — invoke that specific reviewer/skill directly (`plugin-rulebook`, `activation-reviewer`, etc.); this skill is for when the *combined weighted* picture is wanted
- A narrative-only quality review of one skill, agent, command, hook, or rule — findings but no numeric score, SWOT, or hard gates — invoke the type-matched reviewer directly instead: `skill-reviewer`, `subagent-reviewer`, `command-reviewer`, `hook-reviewer`, `rule-reviewer`, or `plugin-validator` (whole-plugin structure/manifest check with no numeric score). This skill dispatches `plugin-auditor` for its own evidence (see `references/rubric.md`'s Type-Matched Reviewer Table for which reviewer applies per type — `plugin-auditor` owns the actual dispatch decision now) and wraps the returned findings into the weighted score — invoke a reviewer directly when only its plain Critical/Major/Minor findings list is wanted, not the surrounding score/SWOT/next-steps.
- **The full reviewer fan-out's findings across every axis, with no score at all** — use `plugin-auditor` directly instead of this skill. That's exactly the evidence this skill's own Step 3 dispatches internally (standalone mode) or consumes pre-gathered (evidence-only mode) — invoke `plugin-auditor` when only the normalized findings are wanted, this skill when the weighted score/SWOT/next-steps built on top of them are wanted too.
- **Precedence:** if the request contains an explicit scoring/ranking cue ("rate", "score", "grade", "rank", a 1-10 scale) alongside review-style language, this skill wins; a bare "review"/"check quality"/"validate" request with no scoring cue goes to the type-matched reviewer instead (or to `plugin-lifecycle-downstream` if the request also asks to "audit"/"run QA"/combines validate+score in one ask for a whole plugin — that orchestrator dispatches this skill and `plugin-validator` together).
- A full WHAT/WHY/HOW implementation plan for the findings — use `enhancement-suggestor` (offered automatically as this skill's own Suggested Next Step)
- A retrospective on how a component *behaved this session* — use `analyzing-sessions`; this skill grades static current-state quality, not session behavior
- A side-by-side comparison of two components — use `plugin-comparison`

## Usage

```text
/plugin-grader <target>
```

`target` is a component name/path resolvable via `Glob`, or a plugin name/`"this plugin"` for whole-plugin rollup mode. If omitted or ambiguous, ask via `AskUserQuestion` rather than guessing.

## Processing Flow

### 1. Resolve Target and Mode

Parse `$0` (or the conversation). If it names a single component (a skill/agent/command/hook resolvable via `Glob`), this is **component mode**. If it names a plugin, or the user says "this plugin"/"the whole plugin", this is **plugin mode**. Apply R19-style path discipline: if the target resolves to both a `plugins/plugin-devkit/` copy and a `.claude/` mirror (the intentional staging-mirror pattern), use the `plugins/plugin-devkit/` copy as canonical and note the mirror in `notes`.

### 2. Determine Target Type (component mode)

skill (has `SKILL.md`) / agent (a file in `agents/`) / command (a file in `commands/`) / hook (`hooks.json` or a hook script) / rule (a file in `.claude/rules/`). Use `references/rubric.md`'s Type-Matched Reviewer Table to pick which `*-reviewer` applies — never dispatch all five.

### 3. Gather Evidence

One dispatch path for both modes below — never two. Which mode applies is decided by the caller's
input shape, not a flag the user has to know about: standalone use only ever supplies a target; the
evidence-only shape (scope manifest + evidence bundle) only ever comes from
`plugin-lifecycle-downstream`'s Phase 11.

**Standalone mode** (default — `/plugin-grader <target>` used directly, unaffected by this skill's
own M3 refactor): dispatch the `plugin-auditor` skill (via `Skill`) against the resolved target and
mode (component/plugin from Step 1-2), passing Fast mode through if requested. Print a status line
first — e.g. "Dispatching plugin-auditor for evidence gathering — this typically takes several
minutes..." — since it runs silently with no built-in progress streaming. `plugin-auditor` owns the
actual reviewer fan-out and component-mode/plugin-mode dispatch rules (see
`plugin-auditor/references/dispatch-table.md` — the type-matched `*-reviewer`, `completeness-reviewer`,
`activation-reviewer`, `security-reviewer`, `dependency-reviewer`, `scripts-reviewer`,
`hook-reviewer`, `plugin-rulebook-checker`, plus `consistency-reviewer`/`plugin-validator` in plugin
mode) and returns a normalized evidence bundle per
`plugin-rulebook/references/evidence-schema.md`. If the caller (typically
`plugin-lifecycle-downstream`, reusing its own Phase 3 Validate results) supplies pre-gathered
`plugin-rulebook-checker`/`plugin-validator` findings for some or all of the target(s), pass those
through as pre-supplied findings on the `plugin-auditor` call — its own reuse discipline decides
what to skip re-dispatching; this step does not re-implement that logic.

**Fast mode** (`--fast` or "quick grade" in the request, standalone mode only — evidence-only mode
has no dispatch to speed up): pass the Fast-mode flag through to `plugin-auditor`, which skips
`scripts-reviewer`, `consistency-reviewer`, and `security-reviewer` per its own Fast mode.
`robustness` defaults to `is_na: true` (score 10), `maintainability` derives from
`skilldir-reviewer`'s duplication axis alone, and `safety_risk_handling` derives from
`plugin-rulebook-checker` R6/R9 findings alone. Note the reduced fidelity in
`notes.inspection_limits` — never silently present a fast-mode score as equivalent to a full one.

**Evidence-only mode** (new — for `plugin-lifecycle-downstream`'s Phase 11): accepts the scope
manifest, Phase 5's `plugin-auditor` evidence bundle, validation reports, test report, and final
evidence bundle instead of dispatching anything. In this mode:
- perform no `plugin-auditor`, reviewer-agent, or test dispatch of any kind;
- verify the supplied evidence's freshness (baseline/current commit match), coverage (every
  in-scope component has at least one report), provenance (every finding traces to a real report
  revision), and schema `version` before using it;
- if required evidence is missing, stale, or the wrong schema version, refuse scoring (state
  exactly what's missing/stale, per `references/output-schema.md`'s refusal shape) or return a
  qualified score with `notes.inspection_limits` stating what wasn't verifiable — never score
  silently past a gap;
- mark any optional check that wasn't run as `not_run`, never as a pass;
- record every report/revision actually used (`report_revisions` in the output, per
  `references/output-schema.md`) so the score's provenance is traceable.

Both modes: also run the Testing static heuristic directly (no dispatch — this stays
`plugin-grader`'s own direct check, per `plugin-auditor`'s dispatch table's "Not This Skill's Job"):
`Glob` for `evals/`, `evals.json`, `benchmark.json`; `Grep` SKILL.md for a Testing & Validation
section. In evidence-only mode, prefer the scope manifest's own smoke-test/eval inventory if it
already states this instead of re-deriving it.

### 4. Score Dimensions and Compute

Map each finding's canonical severity (Critical/Major/Minor — already normalized from each source's native scale by `plugin-auditor`'s evidence bundle, in either mode) into the `dimensions` object per `references/rubric.md`. Assign `simplicity`, `testing`, `efficiency`, and `actionability` directly against their custom bands (also in `rubric.md`). Set `dimensions.content_quality.contradiction_found: true` if any finding flagged self-contradicting instructions.

Write this as JSON per `references/output-schema.md`'s input shape, then run:

```bash
python scripts/compute_score.py <input.json>
```

**Never hand-compute the weighted sum or gate application** — the script is the source of truth for this arithmetic (see `references/gates-and-rollup.md` for why: gate stacking and boundary precision are exactly the class of error this plugin has hit before).

For plugin mode, after every component has a `final_score`, build the rollup input and run:

```bash
python scripts/compute_score.py --rollup <rollup_input.json>
```

### 5. Build SWOT and Prioritized Next Steps

Per `references/swot-and-next-steps.md` — every SWOT entry must trace to a specific dimension score or finding; next steps are ranked gate-lifting-first, then by estimated weighted-point gain, capped at 5 entries.

### 6. Write the Report

1. Get a timestamp: `date -u +%Y-%m-%dT%H-%M-%SZ`
2. Write to `.claude/output/plugin-grader/<target>-<timestamp>.json` per `references/output-schema.md`'s Final Report JSON shape
3. Confirm the written path to the user

### 7. Present a Narrative Summary

In chat (not a separate file): a dimension score table, any `gates_applied` with their reasons, the final score, the SWOT, and the prioritized next steps — a readable rendering of the JSON just written, not a re-derivation of it.

### 8. Suggested Next Step

If `prioritized_next_steps` is non-empty, ask with `AskUserQuestion`: "Run `enhancement-suggestor` against this grading report for a full classified WHAT/WHY/HOW action plan?" — options "Yes — run enhancement-suggestor" / "No — skip for now". If yes, invoke the `enhancement-suggestor` agent (via `Agent`) against the written report path. Never invoke it without asking first.

## Output Format

See `references/output-schema.md` for the exact JSON shapes (`compute_score.py` input/output, and the richer final report written to disk).

## Testing & Validation

1. **Single skill, clean** — grade a skill with no findings from any dispatched reviewer; confirm all 12 dimensions score 10 and `final_score` is 10.0 with no gates
2. **Rule compliance gate** — grade a target with a known REQUIRED rule violation; confirm Gate A fires and `final_score` is capped at 6.0
2a. **Safety gate** — grade a target with a Critical `safety_risk_handling` finding (e.g. `Bash(*)`); confirm Gate C fires and `final_score` is capped at 4.0, even when every other dimension scores 10
2b. **Testing gate** — grade a target with `testing == 0.0` (no `evals/`, no Testing & Validation section of its own); confirm Gate D fires, `final_score` is capped at 8.0, and the output includes the literal comment `"Missing verification."` exactly as `gates-and-rollup.md` specifies
3. **Gate stacking** — construct an input triggering both Gate A and Gate B; confirm `final_score` uses the *lower* of the two caps (5.0), not the first one found. Also confirm stacking Gate B and Gate C uses 4.0 (the lower of the two), since Gate C is now the lowest cap of the four
4. **N/A dimension** — grade a component with no `scripts/`; confirm `robustness` scores 10 with `is_na: true`, not excluded from the weighted sum
5. **Plugin rollup with one broken component** — construct component scores where one is < 3; confirm Gate P3 fires and `weakest_component` is reported even though the mean looks acceptable
6. **Fast mode** — confirm the Fast-mode flag reaches `plugin-auditor`, `scripts-reviewer`/`consistency-reviewer`/`security-reviewer` are skipped, and `notes.inspection_limits` states this
7. **Self-check** — `scripts/smoke_test.py` passes (this skill's own persisted smoke test), re-run after any SKILL.md edit
8. **Evidence-only mode, missing evidence → refusal** (new, M3) — invoke evidence-only mode with a scope manifest naming a component that has no corresponding report in the supplied evidence bundle; confirm scoring is refused (not silently skipped or scored as if clean) per `references/output-schema.md`'s refusal shape, and confirm no `plugin-auditor`/reviewer/test dispatch was attempted
8a. **Evidence-only mode, stale evidence → qualified score** — supply evidence whose `current_commit` doesn't match the scope manifest's; confirm the score is returned qualified, with `notes.inspection_limits` stating the staleness, not refused outright and not silently ignored
8b. **Evidence-only mode, complete and fresh → identical scoring** — supply a complete, fresh evidence bundle for a target already graded via standalone mode in scenario 1; confirm the two runs produce the same `final_score`/`gates_applied` (the dispatch mechanism differs, the scoring doesn't)

**Quality gates:**
- [ ] `scripts/compute_score.py` is always invoked for the weighted sum and gate math — never hand-computed
- [ ] Every entry in `gates_applied` has a non-empty `reason`
- [ ] Gate D always emits the literal `"Missing verification."` comment when `testing` scores 0.0 — never a paraphrase
- [ ] Standalone mode never dispatches a reviewer agent directly — always goes through `plugin-auditor`, which itself never sends all five type-matched `*-reviewer` agents for a single target
- [ ] The written report path is always under `.claude/output/plugin-grader/`
- [ ] The Step 8 `enhancement-suggestor` offer uses `AskUserQuestion` and is never auto-invoked
- [ ] A staging-mirror duplicate (`.claude/` vs `plugins/plugin-devkit/`) is noted, not treated as an error
- [ ] Fast mode is never presented as equivalent-fidelity to a full grade
- [ ] Evidence-only mode never dispatches `plugin-auditor`, a reviewer agent, or a test — it only ever reads supplied evidence
- [ ] Evidence-only mode always refuses or qualifies when required evidence is missing/stale/wrong-version — never scores silently past a gap
- [ ] Standalone mode and evidence-only mode never get confused for one another — the input shape alone (a bare target vs. a scope manifest + evidence bundle) determines which mode runs, no separate flag required

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/rubric.md` | The 12-dimension scoring table, generic formula, N/A handling, type-matched reviewer table (informational — `plugin-auditor` owns the actual dispatch decision, see `plugin-auditor/references/dispatch-table.md`) |
| `references/gates-and-rollup.md` | Exact hard-gate math, stacking rule, and whole-plugin rollup formula |
| `references/output-schema.md` | JSON shapes for the script's input/output and the final written report |
| `references/swot-and-next-steps.md` | Score-driven SWOT derivation and prioritized-next-steps ranking |
| `scripts/compute_score.py` | Deterministic weighted-sum and gate-application script — the only source of truth for this arithmetic |
| `scripts/smoke_test.py` | This skill's own persisted smoke test (frontmatter validity, referenced-file existence, Bash-scope grant consistency) — re-run before packaging or after any SKILL.md edit |
| `assets/example-output.json` | A complete worked example of the final report JSON |
| `plugin-auditor` skill | Step 3 — dispatched for fresh evidence in standalone mode, or supplies pre-gathered evidence consumed in evidence-only mode |
| `plugin-rulebook-checker` agent | Rule Compliance dimension's signal source, via `plugin-auditor`'s own dispatch |
| `enhancement-suggestor` agent | Turns the written report's `prioritized_next_steps` into a full WHAT/WHY/HOW plan (Step 8) |
