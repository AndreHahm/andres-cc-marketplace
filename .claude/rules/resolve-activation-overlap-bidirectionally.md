---
paths:
  - "plugins/*/skills/**/SKILL.md"
  - "plugins/*/agents/*.md"
  - ".claude/skills/**/SKILL.md"
  - ".claude/agents/*.md"
---

# Resolve Activation Overlap Bidirectionally

## When this applies

Two skills (or an agent/skill pair) in the same or different plugins have genuinely overlapping domains —
a request could plausibly match either one's activation description — and a collision has actually
surfaced (a real ambiguous-trigger incident, or an `activation-reviewer` finding), not just a theoretical
risk.

## Rule

Resolve the overlap with an explicit, reciprocal textual exclusion, not a one-sided redirect or a bare
"see also":

1. **Name the specific sibling.** Each skill's own "When to Use"/"When NOT to Use" section (or
   equivalent) names the other skill by its actual identifier — never a generic "or a similar tool."
2. **State the exact distinguishing criterion**, not just "use the other one instead." The criterion is
   the actual axis that separates the two domains (e.g. "counts *that* something happened" vs. "assesses
   *how well* it happened"; "no CODEOWNERS context needed" vs. "reviewer action with CODEOWNERS context") —
   specific enough that a reader can classify a new, unseen request without re-deriving the distinction
   from scratch.
3. **Make it bidirectional.** Both skills must carry the exclusion, each pointing at the other with its
   own half of the criterion. A one-sided redirect (only skill A points away from skill B) leaves the
   un-excluded direction free to misfire — a request landing on B first has nothing telling it to defer to
   A.

## Why

This exact pattern was independently invented twice in this repo before either side knew about the
other: `analysis-kit`'s `analyzing-plugin-components`/`starting-an-analysis` collision (and later
`analyzing-tool-and-framework-use`/`analyzing-actor-behavior`,
`analyzing-governance-and-conflicts`/`mining-recurring-patterns`) were each closed this way, and so was
`git-kit`'s `gh-operations`/`collaborating-on-a-pr` pair — same shape (named sibling, stated criterion,
bidirectional), arrived at separately in two different plugin-fix sessions with no shared reference
between them. Naming the pattern once here means the next occurrence (in either plugin, or a new one)
reuses a documented convention instead of re-deriving the same shape a third time — or, worse, converging
on a subtly different variant that then needs reconciling later.

## How to apply

When `activation-reviewer` (or a real usage incident) surfaces an overlap, apply the three-step rule
above directly. Don't just add a one-line "see also X" — that satisfies neither the criterion requirement
nor the bidirectionality requirement, and is the shape that produces silent misfires in the un-excluded
direction.
