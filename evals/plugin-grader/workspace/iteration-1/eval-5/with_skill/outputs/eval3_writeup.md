# legacy-plugin — Whole-Plugin Rollup (Zero Scorable Components for Security)

## Scenario

`legacy-plugin` has 2 components, both of a type `plugin-grader` cannot grade at all (e.g. an
`mcp-server` entry — no `safety_risk_handling` dimension is available for this type, per
`references/rubric.md`'s Type-Matched Reviewer Table / `plugin-auditor`'s dispatch rules).
Component-mode **quality** scores are available:

| Component      | `final_score` |
|----------------|---------------|
| mcp-server-a   | 8.0           |
| mcp-server-b   | 7.5           |

Neither component has a `dimensions.safety_risk_handling.score` to report.

## What was run

```bash
python scripts/compute_score.py --rollup rollup_input.json
```

from `plugins/plugin-devkit/skills/plugin-grader/`. The arithmetic was never hand-computed — the
script is the source of truth per `SKILL.md`'s Step 4 instruction and `references/gates-and-rollup.md`.

### Input (`rollup_input.json`)

```json
{
  "component_scores": {
    "mcp-server-a": 8.0,
    "mcp-server-b": 7.5
  },
  "activation_critical": false,
  "consistency_critical": false
}
```

`component_security_scores` was **omitted entirely** — per `references/output-schema.md`: *"Omit
it, or pass `{}`, when no component in the plugin has a security-scorable dimension (e.g. every
component is a type `plugin-grader` cannot grade at all) — the script then reports
`plugin_security_score: null` rather than fabricating a mean from nothing."* That is exactly this
scenario: both components are of an ungradeable type for this dimension, so there is nothing to
average.

### Raw script output (`rollup_output.json`)

```json
{
  "plugin_score_raw": 7.75,
  "weakest_component": {"name": "mcp-server-b", "final_score": 7.5},
  "strongest_component": {"name": "mcp-server-a", "final_score": 8.0},
  "plugin_gates_applied": [],
  "plugin_final_score": 7.8,
  "component_count": 2,
  "plugin_security_score": null,
  "plugin_security_gates_applied": []
}
```

## Answer: what `plugin_security_score` should be, and why

**`plugin_security_score` should be `null`** (not `0`, not `10`, not a fabricated average).

Reasoning, per `references/gates-and-rollup.md` ("Whole-Plugin Security Rollup" section) and
`references/output-schema.md`:

- `plugin_security_score` is computed as the simple unweighted mean of every graded component's
  `dimensions.safety_risk_handling.score` — the exact analog of `plugin_score_raw` for
  `final_score`.
- That computation requires at least one component to actually carry a `safety_risk_handling`
  score. Here, neither component's type has that dimension at all (not even an `is_na: true`
  resolved-to-10 value — `is_na` still requires the dimension to exist and be resolved by the
  caller before rollup; these components never had it to begin with because their type isn't
  security-gradeable in the first place).
- With zero components contributing a security-scorable value, there is no signal to average.
  `output-schema.md` is explicit that this must produce `plugin_security_score: null` with
  `plugin_security_gates_applied: []` — never a fabricated score derived from `component_scores`
  (the quality mean) or any other field. The script's own `compute_rollup()` implements exactly
  this: `component_security_scores` resolves to an empty dict, so it skips the security-mean/Gate
  P4 branch and sets `result["plugin_security_score"] = None`.
- This is independent of `plugin_final_score`: the quality rollup still legitimately computes
  `plugin_score_raw = 7.75` → `plugin_final_score = 7.8` (no gates fired — both components scored
  well above every plugin-level gate's threshold: P1/P2 require a Critical activation/consistency
  finding — false here — and P3 requires some component `final_score < 3.0` — neither is). Gate P4
  (security) never applies to `plugin_final_score` in any scenario, and here it also can't apply to
  `plugin_security_score` itself since there's nothing to gate.

### Required `notes.security_score_unavailable_reason`

Per `output-schema.md`: *"`plugin_security_score` is `null`... In that case
`notes.security_score_unavailable_reason` (a string, e.g. `"No gradeable component types present in
this plugin."`) must be populated so the gap is explicit rather than silently absent."*

For this final written report, that field should read:

```json
"notes": {
  "security_score_unavailable_reason": "No gradeable component types present in this plugin — both components (mcp-server-a, mcp-server-b) are of a type plugin-grader has no safety_risk_handling dimension for, so there is no per-component security score to average."
}
```

## Testing & Validation cross-reference

This exercise matches `SKILL.md`'s own Testing & Validation scenario 12 ("All components N/A") —
note the distinction that scenario is actually testing: scenario 11 covers *every component's
`safety_risk_handling` is `is_na: true`* (dimension exists, resolved to 10, mean = 10.0), while
scenario 12 — this one — covers *zero components have the dimension at all* (nothing to resolve,
mean is undefined → `null`). The two are deliberately different cases in the skill's own test list,
and this worked example exercises scenario 12, not 11.
