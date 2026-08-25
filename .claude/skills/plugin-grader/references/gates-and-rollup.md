# Hard Gates and Whole-Plugin Rollup

## Order of Operations (Component Mode)

1. Score all 12 dimensions: 8 (structure_architecture, content_quality, rule_compliance, completeness,
   maintainability, robustness, uniqueness, safety_risk_handling) from reviewer Critical/Major/Minor
   counts via the generic finding-count formula, and 4 (simplicity, testing, efficiency, actionability)
   scored directly against custom bands — see `rubric.md` for the full weight table and band definitions.
2. Apply the Content Quality contradiction cap *before* the weighted sum: if the target contains
   self-contradicting guidance (one section states a rule, another violates it), set
   `dimensions.content_quality.contradiction_found: true` in the script input — this caps Content
   Quality at 4 regardless of what the generic formula would otherwise produce (`rubric.md`'s
   "Dimension-Level Cap" section has the full rationale).
3. `weighted_total = sum(dimension_score_i * weight_i)` — naturally in [0, 10] since weights sum to 1.0 and every dimension is 0-10. Do not treat this as needing a separate "conversion to 1-10" step.
4. Evaluate hard gates against the already-capped dimension scores (boundaries are strict `<` — exactly the threshold value does NOT trigger):

| Gate | Condition | Cap |
|---|---|---|
| A | `rule_compliance` score < 5.0 | 6.0 |
| B | `completeness` score < 4.0 | 5.0 |
| C | `safety_risk_handling` score < 4.0 (a Critical security finding — destructive action with no guard, or `Bash(*)`) | 4.0 |
| D | `testing` score == 0.0 | 8.0, and the output must include the literal comment `"Missing verification."` |

5. `final_score = weighted_total` if no gate triggered; otherwise `final_score = min(weighted_total, min(caps of all triggered gates))`.
6. Round to 1 decimal.
7. **No artificial floor at 1.** A component with multiple gates active can legitimately show as low as the lowest of the triggered caps intersected with the weighted total — including a value near 0.0 if the underlying dimensions are also near 0. Do not clamp a genuinely broken component to look better than it is.

Gate caps are deliberately ordered `C(4) < B(5) < A(6) < D(8)` — taking the minimum when multiple gates fire means "the plugin can do real, unguarded harm" always outranks "missing core functionality," which always outranks "non-compliant," which always outranks "unverified." Gate C sits below Gate B (Gate C was added after Gates A/B already existed, but ranked worse despite arriving later) on the reasoning that a Critical security finding is not just a quality gap the plugin can be used despite — it's a live risk the plugin actively carries, whereas an incomplete plugin is merely less useful. This is exactly what `scripts/compute_score.py`'s `min(caps)` implements — do not hand-compute this arithmetic; run the script.

**Why Gate C exists:** added after this exact gap surfaced twice in this repo's history, in a different plugin (`analysis-kit`, not `plugin-devkit` itself) — a Phase 1 audit found `safety_risk_handling` scores of 0/10 and 2/10 from `Bash(python:*)`/`Bash(git:*)`-class findings, neither of which capped `final_score` the way a completeness Critical already did, so the weighted average alone understated how broken those two components actually were. `safety_risk_handling`'s 5% weight is too small on its own to reflect a Critical finding proportionally — a gate is what makes it visible in the final number, not the weight.

**Every triggered gate must appear in `gates_applied`** with its `reason` — a capped score with no visible reason defeats the "explain reasoning briefly" requirement. Never silently apply a gate.

## Whole-Plugin Rollup

Grading a whole plugin does **not** mean re-deriving a different weighted formula across components — it means:

1. Grade every individual component (skill/agent/command/hook) using the component-mode process above, in parallel where possible.
2. Read `activation_critical`/`consistency_critical` from `plugin-auditor`'s own returned evidence
   bundle (its plugin-mode dispatch already runs `activation-reviewer` and `consistency-reviewer`
   once across the whole set — see `plugin-auditor/references/dispatch-table.md`'s Plugin Mode
   section) — this step never dispatches either reviewer itself, per `SKILL.md`'s own quality gate
   that standalone mode never dispatches a reviewer agent directly.
3. Run `scripts/compute_score.py --rollup <input.json>` with:
   ```json
   {
     "component_scores": {"<name>": <final_score>, ...},
     "activation_critical": <bool>,
     "consistency_critical": <bool>,
     "component_security_scores": {"<name>": <dimensions.safety_risk_handling.score>, ...}
   }
   ```
4. The script computes:
   - `plugin_score_raw` = simple unweighted mean of all component `final_score`s (not weighted by component size/complexity — the simplest, most auditable choice)
   - Plugin-level gates (parallel structure to component gates, same "take the minimum of triggered caps" rule):

| Gate | Condition | Cap |
|---|---|---|
| P1 | `activation-reviewer` found >=1 Critical (exact-phrase collision) | 6.0 |
| P2 | `consistency-reviewer` found >=1 Critical (hard behavioral contradiction or broken cross-component contract) | 6.0 |
| P3 | Any single component's `final_score` < 3.0 | 7.0 |
| P4 | Any single component's `dimensions.safety_risk_handling.score` < 4.0 | 4.0 (applies to `plugin_security_score` only, not `plugin_final_score`) |

   - `plugin_final_score` = `min(plugin_score_raw, min(triggered caps of P1-P3))`, same shape as component-level gating.
5. **Always report `weakest_component` and `strongest_component` alongside the mean** — a mean alone can hide one severely broken component inside an otherwise-healthy plugin. Gate P3 exists specifically to make that case visible in the score itself, not just in a footnote.

## Whole-Plugin Security Rollup

`plugin_security_score` is a second, independent rollup computed alongside `plugin_final_score` in the
same `--rollup` invocation — it is **not** part of the `plugin_final_score` calculation, and Gate P4
never caps `plugin_final_score`.

- **Computation:** simple unweighted mean of every graded component's `dimensions.safety_risk_handling.score`
  — the exact analog of how `plugin_score_raw` is the unweighted mean of `final_score`. There is no
  independent whole-plugin-scope security evidence to aggregate differently: `security-reviewer` (the
  primary evidence source for `safety_risk_handling`) only ever runs in Component Mode, never dispatched
  once across a whole plugin the way `activation-reviewer`/`consistency-reviewer` are (see
  `plugin-auditor/references/dispatch-table.md`'s Plugin Mode "run once across the whole set" list, which
  does not include `security-reviewer`) — component-level scores are the only signal that exists.
- **Gate P4:** any single component's `dimensions.safety_risk_handling.score` < 4.0 caps
  `plugin_security_score` at 4.0 — the same reasoning Gate C already uses at component level (a Critical
  security finding is a live risk the plugin actively carries, not just a quality gap), applied here so a
  mean alone can't hide one severely-insecure component inside an otherwise-healthy plugin's average,
  exactly as Gate P3 already exists to prevent for `final_score`.
- **N/A behavior:** a component whose `safety_risk_handling` is `is_na: true` still contributes its
  (already-resolved) score of 10 to the mean — no special-casing beyond what already exists for the
  underlying dimension at component level.
- **Zero scorable components:** if no component in the plugin has a security-scorable dimension,
  `plugin_security_score` is `null` (see `output-schema.md`'s rollup output and `notes.security_score_unavailable_reason`)
  rather than a fabricated score.
- **All-or-nothing, never partial:** when `component_security_scores` is non-empty, it must have exactly
  one entry per `component_scores` key — `compute_score.py --rollup` raises rather than silently
  computing the mean/Gate P4 over an incomplete subset, since a missing entry could hide an omitted
  component's low security score from the rollup entirely.
- **Valid range:** `[0, 10]`, rounded to 1 decimal, same as every other score in this system.
- **Tie-break:** when multiple components tie for the lowest security score, `weakest_security_name`
  breaks the tie by component name (alphabetical), not by JSON key/dict-iteration order — the gate's
  `reason` text is deterministic regardless of input key order.

## Why These Defaults

- **0-10 scale, not floored at 1**: a component scoring near 0 should read as broken, not "quite bad."
- **Simple mean for rollup, not size-weighted**: easiest to audit; a size-weighting scheme can be added later if means prove misleading in practice, but don't build it speculatively now.
- **N/A dimensions default to 10 + `is_na` flag**, never renormalized weights — keeps the 12 fixed weights identical across every single output, so scores are comparable across different targets.
