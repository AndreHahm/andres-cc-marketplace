# Overlap Check

How Phase 4 decides between `candidate` and `merge-with-existing` for a candidate that already passed
the evidence threshold.

## Search Surface

Before scoring finishes, search for something that already addresses the proposed capability:

- **This plugin's own skills** -- `Glob` `plugins/analysis-kit/skills/*/SKILL.md` and read each
  `description` for a capability match. A near-miss (a skill that partially covers the need, or could be
  extended to) still counts as overlap for this check, even if it isn't a perfect match.
- **The wider marketplace, when relevant** -- if the proposed capability plausibly belongs outside
  `analysis-kit` (a different plugin's domain), `Glob('plugins/*/skills/*/SKILL.md')` and check for an
  existing match there too. Skip this wider search when the candidate is clearly analysis-kit-scoped and
  the plugin-local search already found no overlap -- don't pad the report with a search that was never
  going to find anything relevant to a narrowly-scoped candidate.

## Deciding the Disposition

- **No meaningful overlap found** -- `candidate`. State what was searched (which directories/`Glob`
  patterns) so the report's own overlap-check claim is verifiable, not just asserted.
- **An existing skill already covers this, or could reasonably be extended to** -- `merge-with-existing`.
  Name the specific skill and describe the gap between what it does today and what the candidate asks
  for -- "extend X's Phase N to also cover Y" is a useful `merge-with-existing` note; "X is kind of
  related" is not specific enough to act on.

## What Counts as Meaningful Overlap

A shared *domain* isn't automatically overlap -- two skills can both touch "session reliability" without
either one addressing the specific unmet need a candidate describes. Meaningful overlap means an existing
skill's actual documented behavior (its Phases, its own stated scope) would already produce the proposed
capability, or come close enough that extending it is clearly cheaper than building a new one. When in
doubt, err toward `merge-with-existing` and name the extension point explicitly -- a wrongly-merged
candidate is easy to re-split later; a wrongly-separate new capability duplicating existing coverage is a
maintainability cost this plugin's own `analyzing-governance-and-conflicts` Phase 5 would later flag as
drift between two overlapping skills.
