# Disclose Before Overriding Decisions

## When this applies

Any point in a workflow where: a decision was made at an `AskUserQuestion` checkpoint (an interview,
ideation, or config-style question) and a later step would change, bypass, or act against it; existing
functionality or behavior is about to be silently removed or changed; or a workflow phase in a multi-phase
pipeline skill is about to be skipped rather than explicitly run or explicitly deferred with a stated
reason.

## Rule

- **Never silently override a checkpoint decision.** If a decision made at an `AskUserQuestion` step turns
  out to need changing — because it's infeasible, because new information contradicts it, because a fix
  would otherwise violate it — stop and re-ask via `AskUserQuestion` before proceeding. Don't substitute
  your own judgment for the user's already-made answer.
- **Never silently remove or change existing functionality or behavior.** State plainly what changed and
  why, even when the change is small, obviously correct, or "adjacent to work already done this session."
- **Never silently skip a workflow phase.** Either run the phase, or state explicitly that it's being
  skipped and why — a phase disappearing from a pipeline's own reported output with no explanation reads
  as an oversight, not a decision.
- **Scope boundary:** disclosure is always required for all three items above. The explicit re-ask is
  required only when an actual `AskUserQuestion`-checkpoint decision is being changed — not for every
  mid-task implementation detail nobody was specifically asked about. Don't over-apply this rule to routine
  judgment calls that were never checkpointed in the first place.

## Why

**Incident:** `plugin-lifecycle-downstream`'s own SKILL.md states: *"Phases 1-2 never edit a file inside
the target plugin — not even to fix an obvious REQUIRED violation... any edit to a file inside the target
plugin, at any severity, requires asking the user first, exactly like Phase 3 already does."* In a real
session (2026-08-10), a Critical finding surfaced during Phase 2 (Audit), and the assistant edited a file
immediately afterward with zero intervening `AskUserQuestion`, rationalizing *"it's directly adjacent to
what I touched this session."* The pipeline's own documented, explicitly-worded gate was crossed by the
exact kind of rationalization that gate already existed to prevent.

Before this incident, no rule stated the underlying principle as a portable, repo-wide default — the
"don't silently do X" language existed only as scattered prose bullets inside individual skills
(`plugin-lifecycle-downstream`'s SKILL.md alone contains a dozen-plus separate instances, each written
by hand, each covering only its own phase). Without one named, citable rule, the identical failure mode
is free to recur in any other workflow with its own approval gate, since each skill author has to
independently remember to write their own version of this guard.
