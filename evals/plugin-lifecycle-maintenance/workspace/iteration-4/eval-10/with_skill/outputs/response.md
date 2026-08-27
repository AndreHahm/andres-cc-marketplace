# Task

improve-a-plugin's Step 2 (Human Decides) just returned 3 approved suggestions from a session-analysis
report. How many times does Step 3 invoke plugin-conception, and with what input each time? Separately: if
one of those 3 suggestions is a narrow, already-known Repair with an already-accepted finding, what happens
differently for that one?

# Answer

## How many times Step 3 invokes `plugin-conception`, and with what input

Step 3 (Conceive) invokes `plugin-conception` (via `Skill`) **exactly once per approved suggestion from
Step 2 — 3 times total** (one call per suggestion, since Step 2 returned 3 approved suggestions). It is
explicitly *not* a single call with a list: "`plugin-conception` classifies and briefs exactly one
candidate per invocation; a multi-candidate pick from Step 2 is a sequence of separate invocations, not a
single call with a list."

Each of the 3 invocations receives one input: that suggestion passed as **Entry Route B evidence
(source: `analyzing-sessions`)**.

Source: `plugins/plugin-devkit/skills/plugin-lifecycle-maintenance/workflows/improve-a-plugin.md`, Step 3:

> Invoke `plugin-conception` (via `Skill`) **once per approved suggestion from Step 2**, never once for
> the whole batch — `plugin-conception` classifies and briefs exactly one candidate per invocation; a
> multi-candidate pick from Step 2 is a sequence of separate invocations, not a single call with a list.
> This runs immediately after the pick and before Step 4's hand-off, never before the pick (classifying
> every unselected candidate suggestion would be wasted work). Pass each approved suggestion as Entry
> Route B evidence (source: `analyzing-sessions`).

## What happens differently for the narrow, already-known Repair with an already-accepted finding

For that one suggestion (out of the 3), `plugin-conception` takes its own **bypass path** — Step 2 of
`plugin-conception`, described as "Bypass for narrow repairs" — straight through **without producing the
full Conception Brief**. This is called out as "the common case for a small, well-understood retro fix."

By contrast, the other classifications (Enhance/Consolidate/Reposition, or a Repair that isn't narrowly
scoped) get the full treatment: `plugin-conception` produces a full Conception Brief (baseline contract,
implementation plan, risks), and that brief gets its own written artifact-link line
(`📄 Conception Brief written: ...`).

Two things stay the same regardless of bypass vs. full brief:
- Step 7 brief-content approval (approve/revise/merge/defer/reject) still runs per candidate even for the
  bypassed one.
- Step 7's **hand-off invocation** never fires from inside `plugin-conception` for any candidate —
  `improve-a-plugin`'s own Step 4 (not `plugin-conception`) owns routing each classified candidate to its
  next destination.

At Step 3's exit criteria, the bypassed candidate is recorded as "a recorded bypass (Repair, narrow,
already-known fix)" rather than "a written Conception Brief" — the two are treated as parallel, equally
valid completions of Step 3 for that candidate.

Source: same file, Step 3 body and Exit criteria:

> For each suggestion, `plugin-conception` classifies it and, for a narrow, already-known Repair with an
> already-accepted finding, takes its own bypass path (Step 2's "Bypass for narrow repairs") straight
> through without producing the full brief — this is the common case for a small, well-understood retro
> fix. For an Enhance/Consolidate/Reposition suggestion, or a Repair that isn't narrowly scoped, it
> produces the full Conception Brief (baseline contract, implementation plan, risks). Its own Step 7
> brief-content approval (approve/revise/merge/defer/reject) still runs per candidate — but its Step 7
> **hand-off invocation** does not: this workflow, not `plugin-conception`, owns deciding where each
> classified candidate goes next (Step 4 below), so do not let `plugin-conception` separately ask or
> invoke a hand-off target from inside this workflow.
>
> **Exit criteria:** Every approved suggestion has either a recorded bypass (Repair, narrow, already-known
> fix) or a written Conception Brief, each carrying its own classification.

# Files consulted

- `C:\Dev\Repos\andres-cc-marketplace\.claude\worktrees\plugin-conception\plugins\plugin-devkit\skills\plugin-lifecycle-maintenance\SKILL.md`
- `C:\Dev\Repos\andres-cc-marketplace\.claude\worktrees\plugin-conception\plugins\plugin-devkit\skills\plugin-lifecycle-maintenance\workflows\improve-a-plugin.md`
