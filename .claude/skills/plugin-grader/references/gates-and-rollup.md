# Hard Gates and Whole-Plugin Rollup

## Order of Operations (Component Mode)

1. Score all 12 dimensions per `rubric.md`.
2. Apply the Content Quality contradiction cap (see `rubric.md`) *before* the weighted sum.
3. `weighted_total = sum(dimension_score_i * weight_i)` — naturally in [0, 10] since weights sum to 1.0 and every dimension is 0-10. Do not treat this as needing a separate "conversion to 1-10" step.
4. Evaluate hard gates against the already-capped dimension scores (boundaries are strict `<` — exactly the threshold value does NOT trigger):

| Gate | Condition | Cap |
|---|---|---|
| A | `rule_compliance` score < 5.0 | 6.0 |
| B | `completeness` score < 4.0 | 5.0 |
| D | `testing` score == 0.0 | 8.0, and the output must include the literal comment `"Missing verification."` |

5. `final_score = weighted_total` if no gate triggered; otherwise `final_score = min(weighted_total, min(caps of all triggered gates))`.
6. Round to 1 decimal.
7. **No artificial floor at 1.** A component with Gates A and B both active can legitimately show as low as the lower of the two caps intersected with the weighted total — including a value near 0.0 if the underlying dimensions are also near 0. Do not clamp a genuinely broken component to look better than it is.

Gate caps are deliberately ordered `B(5) < A(6) < D(8)` — taking the minimum when multiple gates fire means "missing core functionality" always outranks "non-compliant," which always outranks "unverified." This is exactly what `scripts/compute_score.py`'s `min(caps)` implements — do not hand-compute this arithmetic; run the script.

**Every triggered gate must appear in `gates_applied`** with its `reason` — a capped score with no visible reason defeats the "explain reasoning briefly" requirement. Never silently apply a gate.

## Whole-Plugin Rollup

Grading a whole plugin does **not** mean re-deriving a different weighted formula across components — it means:

1. Grade every individual component (skill/agent/command/hook) using the component-mode process above, in parallel where possible.
2. Run the two whole-plugin-only reviewers **once** across the entire set (not once per component — that's quadratic waste):
   - `activation-reviewer` in whole-plugin mode → feeds `activation_critical`
   - `consistency-reviewer` across all components → feeds `consistency_critical`
3. Run `scripts/compute_score.py --rollup <input.json>` with:
   ```json
   {
     "component_scores": {"<name>": <final_score>, ...},
     "activation_critical": <bool>,
     "consistency_critical": <bool>
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

   - `plugin_final_score` = `min(plugin_score_raw, min(triggered caps))`, same shape as component-level gating.
5. **Always report `weakest_component` and `strongest_component` alongside the mean** — a mean alone can hide one severely broken component inside an otherwise-healthy plugin. Gate P3 exists specifically to make that case visible in the score itself, not just in a footnote.

## Why These Defaults

- **0-10 scale, not floored at 1**: a component scoring near 0 should read as broken, not "quite bad."
- **Simple mean for rollup, not size-weighted**: easiest to audit; a size-weighting scheme can be added later if means prove misleading in practice, but don't build it speculatively now.
- **N/A dimensions default to 10 + `is_na` flag**, never renormalized weights — keeps the 12 fixed weights identical across every single output, so scores are comparable across different targets.
