# SWOT and Prioritized Next Steps

## Why This Isn't `analyzing-sessions`'s SWOT

`analyzing-sessions/references/swot-framework.md` frames SWOT around **observed session behavior** ("what did the component do well *in this session*"). plugin-grader is scoring a component's **current static state**, not behavior over a session — reusing that framework verbatim would be a category mismatch. Use the score-driven framing below instead.

## Score-Driven SWOT

Derive every SWOT entry directly from the computed dimension scores and gates — never from free-floating impressions not traceable to a number. This keeps the SWOT auditable against the same data the score came from.

- **Strengths**: every dimension scoring >= 8. State the dimension name and score, e.g. "Rule Compliance (10/10) — all 24 rules PASS."
- **Weaknesses**: every dimension scoring <= 5, plus every triggered gate. State the dimension, score, and the specific finding driving it (from `findings_summary`).
- **Opportunities**: the single highest-leverage fix per weak dimension — what specific change would move the score, not a generic "improve X." Tie each opportunity to a `prioritized_next_steps` entry.
- **Threats**: risks external to the component's current content — a signal source it depends on that could drift (e.g. "relies on plugin-rulebook's R13 threshold; a future threshold change would re-grade this component without any edit to it"), or a dependency on another component's behavior that isn't guaranteed stable.

Do not list a design intent as a Strength if no reviewer actually confirmed it (mirrors `swot-framework.md`'s "Strength-washing" anti-pattern) — every Strength/Weakness must cite the dimension score or finding that produced it.

## Prioritized Next Steps

This is intentionally a **lightweight ranked list**, not a full WHAT/WHY/HOW implementation plan — `enhancement-suggestor` already owns that (offer it as the Suggested Next Step, per SKILL.md).

Rank candidates by:

1. **Gate-lifting fixes first** — any fix that would raise a dimension past a hard-gate threshold (e.g. Rule Compliance from 4.5 to 5.0+, lifting Gate A) ranks above any non-gate fix, regardless of point value. Set `lifts_gate` to the gate ID it would clear.
2. **Then by estimated weighted-point gain** — `(target_score - current_score) * dimension_weight`, using the *nearest realistic anchor* as the target (e.g. moving a Major finding to zero findings targets the dimension's 7-anchor, not blindly 10). Set `points_gain_estimate` to this value, rounded to 2 decimals.
3. Cap the list at 5 entries — beyond that, point the user at `enhancement-suggestor` for the full backlog rather than padding this list.

Each entry: `{rank, action, dimension, points_gain_estimate, lifts_gate}` — `action` must name the specific file/section to change (pull directly from the dispatched reviewer's finding, don't paraphrase into vagueness).
