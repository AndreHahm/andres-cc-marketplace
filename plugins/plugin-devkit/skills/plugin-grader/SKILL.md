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
  are all gradeable target types.
argument-hint: "[target]"
allowed-tools: Read Grep Glob Agent Skill Write Bash(python scripts/compute_score.py:*) Bash(date:*)
---

# Plugin Grader

Orchestrates this plugin's existing reviewer agents into one weighted, gated, 0-10 score with a SWOT summary and prioritized next steps — it does not re-judge quality independently. See `references/rubric.md` for why: nearly every dimension already has a dedicated reviewer, and re-deriving judgments would drift out of sync with them.

## Quick Start

1. **Resolve target and mode** — `$0`, or ask if omitted/ambiguous
2. **Determine target type** — skill/agent/command/hook (component mode) or whole plugin
3. **Dispatch matching reviewers in parallel** — see `references/rubric.md`'s dispatch table
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
- A narrative-only quality review of one skill, agent, command, hook, or rule — findings but no numeric score, SWOT, or hard gates — invoke the type-matched reviewer directly instead: `skill-reviewer`, `subagent-reviewer`, `command-reviewer`, `hook-reviewer`, `rule-reviewer`, or `plugin-validator` (whole-plugin structure/manifest check with no numeric score). This skill dispatches these same agents internally (see `references/rubric.md`'s Type-Matched Reviewer Table) and wraps their findings into the weighted score — invoke one directly when only its plain Critical/Major/Minor findings list is wanted, not the surrounding score/SWOT/next-steps. **Precedence:** if the request contains an explicit scoring/ranking cue ("rate", "score", "grade", "rank", a 1-10 scale) alongside review-style language, this skill wins; a bare "review"/"check quality"/"validate" request with no scoring cue goes to the type-matched reviewer instead (or to `plugin-lifecycle-downstream` if the request also asks to "audit"/"run QA"/combines validate+score in one ask for a whole plugin — that orchestrator dispatches this skill and `plugin-validator` together).
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

### 3. Dispatch Reviewers

Before launching the dispatch, print a status line — e.g. "Dispatching N reviewers in parallel — this
typically takes several minutes..." — since agent dispatches run silently with no built-in progress
streaming; without this, a long dispatch is indistinguishable from a stuck one.

**Component mode** — in a single message, launch in parallel:
- `skilldir-reviewer` (skills with non-`SKILL.md` files only)
- The type-matched `*-reviewer` from `references/rubric.md`
- `completeness-reviewer`
- `activation-reviewer`
- `security-reviewer` — feeds `safety_risk_handling` alongside `plugin-rulebook` R6/R9 (see `references/rubric.md`'s dimension 10 for the axis split that avoids double-counting the same finding)
- `scripts-reviewer` — only if `scripts/` exists for the target
- `hook-reviewer` — only if the target has hooks (a hook component, or a skill/agent declaring `hooks:` frontmatter)
- `Skill(plugin-rulebook)` — invoked via `Skill`, not `Agent`, for Rule Compliance

Also run the Testing static heuristic directly (no dispatch): `Glob` for `evals/`, `evals.json`, `benchmark.json`; `Grep` SKILL.md for a Testing & Validation section.

**Plugin mode** — dispatch the above per component (batched across all components), **plus**, run once across the whole set (not once per component):
- `activation-reviewer` in whole-plugin mode → feeds `activation_critical`
- `consistency-reviewer` across all components → feeds `consistency_critical`
- `plugin-validator` in its default Full-review mode → structural/manifest findings feed each named component's `structure_architecture` dimension alongside `skilldir-reviewer`/the type-matched reviewer (the same "dispatch once, distribute per-component" shape as `activation-reviewer`/`consistency-reviewer` above, not a per-component re-dispatch — `plugin-validator` has no per-component invocation mode of its own outside its Batch mode, which is for splitting a large *sweep*, not for scoping to one target)

**Fast mode** (`--fast` or "quick grade" in the request): skip `scripts-reviewer`, `consistency-reviewer`, and `security-reviewer` dispatches. `robustness` defaults to `is_na: true` (score 10), `maintainability` derives from `skilldir-reviewer`'s duplication axis alone, and `safety_risk_handling` derives from `plugin-rulebook` R6/R9 findings alone. Note the reduced fidelity in `notes.inspection_limits` — never silently present a fast-mode score as equivalent to a full one.

**Reuse pre-supplied findings — don't re-dispatch a check that already ran.** If the caller (typically `plugin-lifecycle-downstream`, reusing its own Phase 1 Validate results) supplies `plugin-rulebook`, `plugin-validator`, and/or `security-reviewer` findings for some or all of the target(s) in scope, use those directly for `rule_compliance`/`structure_architecture`/`safety_risk_handling` scoring instead of dispatching `Skill(plugin-rulebook)`/`plugin-validator`/`security-reviewer` again for the same component. This applies per-component: pre-supplied findings that only cover some components (e.g. from a Scoped Phase 1 run) don't excuse skipping the rest — dispatch fresh for whichever components weren't already covered. A full-mode whole-plugin `security-reviewer` or `plugin-validator` report isn't pre-split by component the way a `plugin-rulebook` batch report is, but every finding in it already cites the specific file(s)/component(s) it applies to — extract per-component findings from that one report rather than treating "not pre-split" as a reason to re-dispatch.

### 4. Score Dimensions and Compute

Map each dispatched reviewer's Critical/Major/Minor (or `plugin-rulebook`'s FAIL/ADVISORY) counts into the `dimensions` object per `references/rubric.md`. Assign `simplicity`, `testing`, `efficiency`, and `actionability` directly against their custom bands (also in `rubric.md`). Set `dimensions.content_quality.contradiction_found: true` if any dispatched reviewer flagged self-contradicting instructions.

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
6. **Fast mode** — confirm `scripts-reviewer`/`consistency-reviewer`/`security-reviewer` are skipped and `notes.inspection_limits` states this
7. **Self-check** — `scripts/smoke_test.py` passes (this skill's own persisted smoke test), re-run after any SKILL.md edit

**Quality gates:**
- [ ] `scripts/compute_score.py` is always invoked for the weighted sum and gate math — never hand-computed
- [ ] Every entry in `gates_applied` has a non-empty `reason`
- [ ] Gate D always emits the literal `"Missing verification."` comment when `testing` scores 0.0 — never a paraphrase
- [ ] Type-matched reviewer dispatch never sends all five `*-reviewer` agents for a single target
- [ ] The written report path is always under `.claude/output/plugin-grader/`
- [ ] The Step 8 `enhancement-suggestor` offer uses `AskUserQuestion` and is never auto-invoked
- [ ] A staging-mirror duplicate (`.claude/` vs `plugins/plugin-devkit/`) is noted, not treated as an error
- [ ] Fast mode is never presented as equivalent-fidelity to a full grade

## Reference Guide

| Resource | Purpose |
|---|---|
| `references/rubric.md` | The 12-dimension scoring table, generic formula, N/A handling, type-matched reviewer dispatch table |
| `references/gates-and-rollup.md` | Exact hard-gate math, stacking rule, and whole-plugin rollup formula |
| `references/output-schema.md` | JSON shapes for the script's input/output and the final written report |
| `references/swot-and-next-steps.md` | Score-driven SWOT derivation and prioritized-next-steps ranking |
| `scripts/compute_score.py` | Deterministic weighted-sum and gate-application script — the only source of truth for this arithmetic |
| `scripts/smoke_test.py` | This skill's own persisted smoke test (frontmatter validity, referenced-file existence, Bash-scope grant consistency) — re-run before packaging or after any SKILL.md edit |
| `assets/example-output.json` | A complete worked example of the final report JSON |
| `plugin-rulebook` skill | Rule Compliance dimension's signal source |
| `enhancement-suggestor` agent | Turns the written report's `prioritized_next_steps` into a full WHAT/WHY/HOW plan (Step 8) |
