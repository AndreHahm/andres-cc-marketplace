# Output Schema

## `scripts/compute_score.py` Input (Component Mode)

```json
{
  "dimensions": {
    "structure_architecture": {"counts": {"critical": 0, "major": 0, "minor": 1}},
    "content_quality": {"counts": {"critical": 0, "major": 1, "minor": 0}, "contradiction_found": false},
    "rule_compliance": {"counts": {"critical": 0, "major": 0, "minor": 2}},
    "completeness": {"counts": {"critical": 0, "major": 0, "minor": 0}},
    "maintainability": {"counts": {"critical": 0, "major": 0, "minor": 0}},
    "robustness": {"score": 10, "is_na": true},
    "simplicity": {"score": 8},
    "testing": {"score": 4},
    "uniqueness": {"counts": {"critical": 0, "major": 0, "minor": 0}},
    "safety_risk_handling": {"counts": {"critical": 0, "major": 0, "minor": 0}},
    "efficiency": {"score": 9},
    "actionability": {"score": 10}
  }
}
```

Each of the 12 keys under `dimensions` takes **either** `counts` (Critical/Major/Minor — scored via the generic formula) **or** a precomputed `score` (0-10, for the four custom-band dimensions: `simplicity`, `testing`, `efficiency`, `actionability`). Never both. `is_na: true` is informational only — the script still needs a `score` (always 10 for N/A) to compute the weighted sum.

## `scripts/compute_score.py` Output (Component Mode)

```json
{
  "dimension_scores": {"structure_architecture": 9.5, "...": "..."},
  "weighted_total": 7.8,
  "gates_applied": [
    {"gate": "A_rule_compliance", "reason": "Rule Compliance scored 2 (< 5)", "cap": 6.0}
  ],
  "final_score": 6.0
}
```

## Rollup Input / Output

`scripts/compute_score.py --rollup <input.json>` input:

```json
{
  "component_scores": {"<name>": <final_score>, "...": "..."},
  "activation_critical": false,
  "consistency_critical": false,
  "component_security_scores": {"<name>": <dimensions.safety_risk_handling.score>, "...": "..."}
}
```

`component_security_scores` is optional. Omit it, or pass `{}`, when no component in the plugin has a
security-scorable dimension (e.g. every component is a type `plugin-grader` cannot grade at all) — the
script then reports `plugin_security_score: null` rather than fabricating a mean from nothing. When
present, its values are each component's already-resolved `dimensions.safety_risk_handling.score`
(including the N/A-defaults-to-10 value for an `is_na: true` component — resolved by the caller before
this input is built, exactly like `component_scores` already works for `final_score`).

Output:

```json
{
  "plugin_score_raw": 7.1,
  "weakest_component": {"name": "skill-b", "final_score": 4.2},
  "strongest_component": {"name": "skill-c", "final_score": 9.1},
  "plugin_gates_applied": [],
  "plugin_final_score": 7.1,
  "component_count": 5,
  "plugin_security_score": 8.5,
  "plugin_security_gates_applied": []
}
```

With no gates applied, `plugin_final_score` always equals `plugin_score_raw` exactly (`plugin_final = min(raw, min(caps)) if caps else raw` in `compute_score.py` -- an empty `caps` list means `plugin_final_score` is never anything other than `plugin_score_raw` unchanged). See the Component Mode output example above for what a *capped* result looks like: a non-empty `gates_applied` paired with a `final_score` lower than `weighted_total`.

`plugin_score_raw` is a simple unweighted mean of every component's `final_score`. See
`gates-and-rollup.md`'s Whole-Plugin Rollup section for the P1/P2/P3 gate conditions/caps and where
`activation_critical`/`consistency_critical` come from.

`plugin_security_score` is the same shape of computation applied to `component_security_scores` instead:
a simple unweighted mean, gated by the new Gate P4 (see `gates-and-rollup.md`). It is `null`, with
`plugin_security_gates_applied: []`, exactly when `component_security_scores` was omitted or empty —
never derived from `component_scores` or any other field. The report-writing step (not this script)
is responsible for adding `notes.security_score_unavailable_reason` when this happens; the script
itself only ever reports the numeric result or `null`.

## Schema Versioning

Every report (component mode and plugin mode alike) carries a top-level `grader_schema_version` field,
introduced from scratch as of `"1.1.0"` — no report ever literally stored `"1.0.0"` as a value; a
report written before this field existed simply has no `grader_schema_version` key at all, and that
**absence** (not a stale value) is what a consumer reads as "pre-1.1.0." Versioning policy going
forward: bump the minor segment for any additive, backward-compatible change (a new optional key, a
new `notes` sub-field); bump the major segment only for a change that alters the meaning of an
existing field or removes one. This matches the bump policy used elsewhere for other `schema_version`
fields this report format feeds (e.g. `plugin-inventory`'s own inventory schemas) — one consistent
convention rather than several independently-invented ones.

## Final Report JSON (Written to `.claude/output/plugin-grader/`)

The script's output is **not** the final artifact — it's inlined into a larger report that adds the narrative pieces the script doesn't (and shouldn't) compute: SWOT, prioritized next steps, and per-dimension findings summaries.

**Component mode** (`<target>-<timestamp>.json`):

Top-level fields (each `dimensions` entry is shown separately below, since its own nested shape is the part worth seeing in full):

```json
{
  "grader_schema_version": "1.1.0",
  "target": "skill-tester",
  "target_type": "skill",
  "graded_at": "2026-07-11T14:32:00Z",
  "dimensions": { "<dimension_name>": "... see the per-dimension shape below ..." },
  "weighted_total": 7.8,
  "gates_applied": [{"gate": "...", "reason": "...", "cap": 6.0}],
  "final_score": 7.8,
  "swot": {"strengths": ["..."], "weaknesses": ["..."], "opportunities": ["..."], "threats": ["..."]},
  "prioritized_next_steps": [{"rank": 1, "action": "...", "dimension": "...", "points_gain_estimate": 0.9, "lifts_gate": null}],
  "reasoning_summary": "2-4 sentence brief explanation of the final score.",
  "notes": {"inspection_limits": "...", "na_dimensions": ["robustness"], "backend_mix": {"claude_only": true, "mixed": false, "codex_reviewers": []}}
}
```

Each `dimensions` entry's own nested shape:

```json
"structure_architecture": {
  "score": 9.5, "weight": 0.15, "is_na": false,
  "source": "skilldir-reviewer, skill-reviewer",
  "findings_summary": "1 Minor: generic reference filename."
}
```

`notes.backend_mix` is additive — present whenever the underlying evidence came from a
`plugin-auditor` dispatch: in standalone mode, whenever the resolver in
`plugin-auditor/references/codex-backend.md` ran at all during this scoring pass; in evidence-only
mode, whenever the supplied evidence bundle's own dispatch/coverage records show the resolver ran
at any point in that evidence's history (no dispatch happens in evidence-only mode itself — this
field is derived from the bundle, not from a fresh dispatch this step performs).

**`claude_only`/`mixed` are derived from the dispatch record, never from `findings[]`.** A Codex-
backed reviewer that returns zero findings has nothing to stamp `backend: codex` on, so deriving
these fields from finding-level `backend` values would report `claude_only: true` for a run that
genuinely sent repo content to Codex. Instead: `claude_only: true` only when `codex_reviewers` is
empty (no reviewer type in this run's dispatch record used the Codex backend); `mixed: true` only
when `codex_reviewers` is non-empty **and** at least one dispatched reviewer in this run used
Claude-native. `codex_reviewers` itself lists which reviewer types **actually ran** through Codex
for this report, populated from the caller's own resolved reviewer list — not echoed from a Codex
envelope's own self-reported fields — so two runs of the same target aren't presented as trivially
comparable when their backend mix differs.

`dimensions` in the *final report* carries the full per-dimension object (`score`/`weight`/`is_na`/`source`/`findings_summary`) — richer than the script's input/output, which only needs `counts`/`score` to compute. Do not conflate the two shapes when writing the report: run the script first with the terse input, then build the rich report around its output.

**Plugin mode** (`<plugin-name>-<timestamp>.json`) adds:

```json
{
  "target_type": "plugin",
  "components": {"skill-a": { "...component report shape above...": "..." }},
  "plugin_score_raw": 7.1,
  "weakest_component": {"name": "skill-b", "final_score": 4.2},
  "strongest_component": {"name": "skill-c", "final_score": 9.1},
  "plugin_gates_applied": [],
  "plugin_final_score": 6.8,
  "plugin_security_score": 8.5,
  "plugin_security_gates_applied": []
}
```

`plugin_security_score` is `null`, with `plugin_security_gates_applied: []`, when the plugin has zero
components with a security-scorable dimension — in that case `notes.security_score_unavailable_reason`
(a string, e.g. `"No gradeable component types present in this plugin."`) must be populated so the gap
is explicit rather than silently absent. This mirrors `component_scores`'/`plugin_score_raw`'s existing
exclusion of ungradeable component types from the mean — not new behavior, the same exclusion extended
to this field.

See `assets/example-output.json` for a complete component-mode worked example, and
`assets/example-output-plugin.json` for a complete plugin-mode worked example (including the two new
security fields and `grader_schema_version`).

## Evidence-Only Mode: Additional Fields and Refusal Shape

Both component-mode and plugin-mode reports always carry a `mode` field; they additionally carry
`report_revisions` when produced in evidence-only mode:

```json
{
  "mode": "standalone",
  "report_revisions": [
    {"report_id": "phase5-plugin-auditor", "revision": 1, "path": ".claude/output/plugin-auditor/skill-tester-2026-08-13T10-00-00Z.json"}
  ]
}
```

`mode` is `"standalone"` or `"evidence_only"` — present on every report from either path, per M3's
requirement that the two never be confused. `report_revisions` is required in evidence-only mode
(every report/revision actually used, `{report_id, revision, path}` per each entry, shown in the
JSON example above) and optional/informational in standalone mode. `plugin-rulebook/references/
evidence-schema.md` remains the canonical owner of this shape for provenance purposes — this file
restates it rather than redefining it.

**Refusal** — when evidence-only mode cannot score because required evidence is missing, stale, or
the wrong schema version, return this shape instead of a scored report:

```json
{
  "mode": "evidence_only",
  "status": "refused",
  "target": "skill-tester",
  "reason": "component 'skill-b' has no corresponding report in the supplied evidence bundle",
  "missing_or_stale": ["skill-b"],
  "report_revisions": []
}
```

A **qualified** score (evidence present but partially stale/unverifiable) uses the normal scored
report shape above, with `status: "qualified"` added and `notes.inspection_limits` stating exactly
what wasn't verifiable — never silent about the gap.
