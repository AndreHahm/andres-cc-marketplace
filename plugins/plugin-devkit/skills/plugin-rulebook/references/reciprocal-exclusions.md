# Reciprocal Exclusions (R36)

Full detail for R36. `SKILL.md` carries the rule's statement and a pointer here. ADVISORY and
forward-looking, like R28-R30: checked on newly-created or structurally-modified skills and agents.

## What is checked

A skill or agent A names another component B in its `## When NOT to Use` section, or in a
"not for / use B instead" sentence of its `description`. R36 asks whether B names A back, in B's own
`## When NOT to Use` or `description`. If it does not, and the two domains overlap, the finding is
reported against B: B should name A.

The matching convention is the one in `.claude/rules/resolve-activation-overlap-bidirectionally.md`: name the
specific sibling, state the criterion that separates the two, and do it in both directions.

## Only a real overlap is a finding

A one-way pointer is not a defect by itself. Many exclusions are plain delegation: `cross-model-review`
saying "committing is `commit`'s job" does not make `commit` need to name `cross-model-review`, because
nobody asks `commit` for a cross-vendor review. A raw count of every one-way pointer in this repo measured
161 of 512 same-plugin exclusion pointers, so the check would be mostly noise if it fired on all of them.

Report a pair only when a request could plausibly match either component's description:

- **Report** when A and B cover the same or adjacent domain (two review skills, two analysis skills), so
  a request landing on B has nothing telling it to defer to A.
- **Do not report** when B's domain would never attract the requests A excludes (pure delegation to a
  differently-scoped helper).

This is a judgment call, which is why the rule is ADVISORY and never blocking. State the overlap you
judged in the finding, so the maintainer can disagree.

## Scope limits

- Same-plugin pairs first. A cross-plugin pointer is reported only when both components are visible in the
  pass being run.
- A component named only in an Examples or Incorrect block is not an exclusion pointer.
- The rule asks for the name of the other component, not a copy of its criterion: B's half of the
  criterion is B's own.

## Fix

Add to B's `## When NOT to Use` (or `description`) a line that names A and states B's half of the
distinguishing criterion.
