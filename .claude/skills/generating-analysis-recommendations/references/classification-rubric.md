# Classification Rubric

## Complexity Bands

| Band | Meaning |
|---|---|
| Low | A single-file text/config edit, or a small, self-contained code change with no new abstraction |
| Medium | Touches multiple files, or adds a new script/component, but follows an existing pattern in the codebase |
| High | Requires new architecture, touches a widely-shared component, or has no existing pattern to follow |

## Risk Bands

| Band | Meaning |
|---|---|
| Low | Additive, easily reversible, no behavior change to existing functionality |
| Medium | Changes existing behavior in a bounded, well-understood way |
| High | Changes behavior in a widely-used shared component, or the fix itself needs its own verification before trusting it |

## Benefit Bands

| Band | Meaning |
|---|---|
| Low | Polish; doesn't change session outcomes |
| Medium | Degrades quality or coverage if left unfixed; fix improves a specific dimension |
| High | Prevents a category of failure, unblocks other work, or resolves a finding with outsized downstream effect |

## Priority Buckets

- **Quick Win** — Low complexity, Low-to-Medium risk, Medium-to-High benefit. Do these first.
- **Strategic Investment** — Medium-to-High complexity or risk, High benefit. Worth doing, but plan for it deliberately rather than folding it into an unrelated pass.
- **Nice-to-Have** — Low complexity/risk, Low-to-Medium benefit. Fine to defer.
- **Reconsider** — High risk or complexity with benefit that doesn't clearly justify it. Name this explicitly rather than silently omitting it — a "don't do this" verdict is itself useful information.

## WHAT/WHY/HOW Format

See SKILL.md's Phase 3 for the literal `**WHAT:**`/`**WHY:**`/`**HOW:**` template — not repeated here to
avoid two copies drifting apart.

`WHY` must cite the actual source finding, not a generic justification. `HOW` should name a concrete first step, not just "fix this."
