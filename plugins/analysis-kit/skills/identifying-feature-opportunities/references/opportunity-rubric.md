# Opportunity Rubric

The evidence threshold Phase 3 gates on, and the reach/expected-value/confidence/effort scoring bands
Phase 4 uses for anything that passes it.

## Evidence Threshold

A candidate signal proceeds to scoring only if **at least one** of these holds:

- **Repeated evidence** -- the same underlying unmet need was observed 2 or more times in scope, whether
  across multiple sessions or multiple instances within one session. "The same need" means the same
  underlying gap, not necessarily identical wording each time.
- **Single high-consequence instance** -- one occurrence, but with a stated severe cost or risk if left
  unaddressed (a manual step with real error or security risk, a workaround that silently corrupts data
  under some condition, a gap that blocks an entire class of work). Tedium alone, however strongly felt,
  does not meet this bar on a single instance.

Anything that meets neither condition is `insufficient-evidence` -- state which condition was checked and
why it wasn't met, rather than a bare "not enough evidence."

## Worked Examples

**Qualifies (repeated evidence):** every time `mining-recurring-patterns` runs, its own Phase 2
action-token abstraction step has to be rebuilt by hand from conversation context, because no shared
script exists to do it deterministically -- `sequence_miner.py` mines the token list once it exists, but
producing that list is still, by that skill's own documented admission (see its Gotchas: "Action-sequence
extraction is still an LLM judgment call"), unautomated. Each invocation is an independent instance of
the same underlying gap; enough of them meet the repeated-evidence bar and this proceeds to scoring.

**Does not qualify (insufficient evidence):** a single session where the user notices and fixes one typo
in a reference file. One instance, no stated severe consequence from leaving it unaddressed --
`insufficient-evidence`, not a candidate.

## Scoring Bands

Each is a qualitative band, not a measured number -- state the band and a one-clause reason, never invent
a numeric score the underlying evidence doesn't actually support.

| Dimension | Low | Medium | High |
|---|---|---|---|
| **Reach** | Affects one user/session pattern rarely encountered | Affects a recurring pattern for some users/projects | Affects most users/sessions of this plugin/skill |
| **Expected value** | Marginal convenience | Meaningfully reduces manual effort or a real (non-critical) risk | Closes a significant capability gap or removes a real error/security risk |
| **Confidence** | Evidence is thin or the proposed capability is speculative | Evidence is solid but the proposed capability's exact shape is still uncertain | Evidence and the proposed capability's shape are both well-supported by what was actually observed |
| **Effort** | A small, self-contained change | A moderate change touching a few components | A large change spanning many components or requiring new infrastructure |

**Effort is inversely weighted against the others when prioritizing** -- a High-reach/High-value/
Low-effort candidate is the strongest case; note this explicitly in the report rather than leaving the
prioritization implicit in four separate bands a reader has to combine themselves.
