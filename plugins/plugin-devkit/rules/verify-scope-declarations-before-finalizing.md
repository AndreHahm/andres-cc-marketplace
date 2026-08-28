# Verify Scope Declarations Before Finalizing

## When this applies

Three related situations where a change touches something that *declares* what it covers — a filtered
diff/file list, a skill's own "When NOT to Use" exclusion clause, or a component's own tool-grant list —
and that declaration needs to stay consistent with everything else that depends on or must agree with it.

## Rule

- **Filtered lists reused across purposes.** If a diff/file list is filtered for one purpose (e.g. what
  to review), check whether any other check that also needs "what changed" (a trust/security check, a
  mirror-sync check, an eval-staleness check) reuses that same filtered list — it needs its own
  correctly, independently-scoped pass instead.
- **Exclusion clauses vs. worked examples.** After writing a "When NOT to Use"/exclusion clause, check
  it doesn't contradict any of the same skill's own worked examples or stated primary use case.
- **New tool grants.** Every new `Bash(...)`/`Skill(...)` call added to a component's instructions needs
  its exact matching grant already present in `allowed-tools` — check this in the same edit that adds
  the call, not a later pass.

## Why

Each of these traces to a specific, real, individually-cited finding in
`.claude/THIRD_PARTY_REVIEW_LEARNINGS.md`'s Master pre-push checklist (Scope & completeness section):
PR #52 (`cross-model-review`) round 2 for both the filtered-list-reuse item (a `SCOPE`-narrowed review
diff was also reused by a separate dispatcher-trust check, hiding a dispatcher-script change from its
own mandatory trust disclosure) and the exclusion-clause item (an unconditional "reviewing an open PR"
exclusion silently contradicted the same skill's own worked example, since a draft PR is technically an
open PR); PR #54 Pattern 4 for the grant-completeness item (a tool grant added mid-edit went unchecked
until a later review round). Individually low-frequency (one occurrence each so far), which is why
they're bundled into one rule rather than three separate one-clause files — but each is a real,
independently-confirmed gap, not a hypothetical.
