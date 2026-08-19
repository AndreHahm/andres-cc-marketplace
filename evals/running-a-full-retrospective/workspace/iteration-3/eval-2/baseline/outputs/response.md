# Consolidating Reports A, B, and C into One Persisted Report

No skill or methodology invoked — this is plain reasoning about how I'd merge three independently-produced
findings that appear to describe the same underlying issue, using only standard judgment.

## Step 1 — Normalize each finding into a common shape

Before comparing anything, I'd pull each report's finding into the same fields so they're actually
comparable instead of eyeballing free text:

| Field | Report A (analyzing-plugin-components) | Report B (analyzing-governance-and-conflicts) | Report C (mining-recurring-patterns) |
|---|---|---|---|
| Component | git-kit / merge-pr | git-kit / merge-pr | (session-level, not component-scoped) |
| Claim | Skips a readiness check before merging | Doesn't verify PR mergeability before `gh pr merge` | User asked about merge readiness twice this session |
| Category | Component gap / improvement suggestion | Governance/rule-conformance conflict | Recurring pattern (no defect claim) |
| Stated severity | P2 | Major | none — pattern-mining doesn't assign severity |
| Evidence type | Direct read of merge-pr's logic/output | Direct read of merge-pr's logic/output, framed against a conformance rule | Session transcript — two user turns asking about merge readiness |

## Step 2 — Decide whether these are the same finding or three different ones

A and B are describing the identical underlying defect (merge-pr proceeds without confirming the PR is
actually mergeable/ready before invoking `gh pr merge`) from two different analytical lenses — one calls
it a component completeness gap, the other calls it a rule-conformance gap. Same component, same code
path, same missing check. These get merged, not just cross-referenced.

C is different in kind: it makes no defect claim on its own. It's a behavioral signal — the user asking
about merge readiness twice suggests they were compensating for the exact gap A and B independently
found. I would *not* list C as a fourth, separate finding. Its value is as corroborating evidence that
raises confidence the A/B gap is real and user-impacting (people are hitting it in practice, not just
theoretically present in the code) — so it gets folded into the merged finding's evidence section, not
kept as its own entry with its own severity.

Before merging, I'd also sanity-check the underlying claim against current repo state rather than trust
two reports simply agreeing with each other — two analyses citing the same wrong premise would still
produce false agreement. A quick read of the actual `merge-pr` skill logic (or the merge-pr skill file in
this repo) to confirm it really does call `gh pr merge` without a preceding readiness/mergeability check
is a cheap way to avoid persisting a merged finding built on a shared misreading.

## Step 3 — Reconcile the two different severity vocabularies

A used "P2" (a priority-tier scale) and B used "Major" (a conflict-severity category). These aren't
directly interchangeable without a stated mapping, and silently picking one over the other would hide the
reasoning. I'd:

1. Write down each scale's meaning as understood from its source skill (P2 = second-highest priority tier
   in a P0–P3 scheme; Major = second-highest severity in a Critical/Major/Minor governance-conflict
   scheme).
2. Note that both independently land in the "second-from-top" band of their own scale — that agreement
   across two different vocabularies is itself informative, not just coincidence to paper over.
3. Resolve to a single output severity for the consolidated report (e.g. **Major/P2**, or whatever the
   persisted report's own shared scale calls its second-highest tier), and state explicitly in the
   consolidated entry that this is a reconciled value drawn from two source scales, with both original
   labels preserved for traceability rather than discarded.
4. Since C provides no native severity, it doesn't get a vote in the severity resolution — it only
   strengthens confidence/priority-to-fix, which I'd note as a separate "corroborating signal" line rather
   than smuggling it into the severity number itself.

## Step 4 — Build the merged entry

```
Finding: merge-pr (git-kit) runs `gh pr merge` without first verifying the PR is actually
ready/mergeable (no readiness or mergeability check precedes the merge call).

Resolved severity: Major / P2 (reconciled from Report A's P2 priority tier and Report B's
Major conflict-severity tier — both independently placed this in their scale's second-highest band).

Source reports:
  - Report A (analyzing-plugin-components): flagged as a component completeness gap, P2.
  - Report B (analyzing-governance-and-conflicts): flagged as a governance/rule-conformance
    conflict, Major — merge-pr's own behavior violates the expectation that a merge is
    preceded by a readiness check.
  - Report C (mining-recurring-patterns): corroborating signal only, no severity — the user
    asked about merge readiness twice in the same session, consistent with working around
    this exact gap manually.

Confidence: raised by cross-source agreement (two independent analytical lenses on the same
code path) plus one behavioral corroboration (C). Not independently re-verified against live
repo state as part of this consolidation pass unless a fresh read of merge-pr's current logic
is done — recommended before acting on this finding.

Recommended action: add an explicit pre-merge readiness/mergeability check (draft status,
required checks, review state) to merge-pr before it calls `gh pr merge`.
```

## Step 5 — Decide the dedup rule going forward (not just for this pair)

The general rule I'd apply while scanning for more overlaps across the three reports: merge two findings
only when component *and* underlying defect match, regardless of which severity vocabulary or analytical
lens produced them. A finding about a different component, or a different aspect of the same component,
stays separate even if the wording sounds similar. A finding with no defect claim of its own (like C) is
never merged as a peer entry — it's either corroborating evidence for an existing merged finding, or (if
nothing else supports it) it stays listed on its own as a "pattern observed, no defect confirmed" item so
it isn't lost, but isn't inflated into something it didn't claim to be.

## Step 6 — Where and how to persist

I'd write one consolidated report file (not three separate ones left as-is), containing:

- A short summary section up top listing the deduplicated finding count vs. raw finding count (3 raw → 1
  consolidated + explicit note that C was folded in as corroboration rather than counted separately).
- The merged finding entry as shown above, in a findings table or list.
- A traceability section mapping each consolidated entry back to its original source report(s) and
  original severity label(s), so nothing is lost by the merge — a reader can always get back to "what did
  Report B originally say, verbatim."
- Since this is a generated retrospective artifact rather than a shippable plugin component, I'd place it
  under a non-component output location (e.g. an `.claude/output/`-style directory for this kind of
  generated report) rather than the repo root, and avoid inventing a new ad hoc location without a reason.

## Caveat about doing this without tooling

Doing this consolidation by hand (as I just did) relies entirely on my own read of three free-text
findings recognizing they're "the same" defect and reconciling two different severity vocabularies by
judgment call. That's exactly the kind of cross-report duplicate/contradiction detection that's easy to
get subtly wrong at scale (more reports, less obviously-matching wording, severity scales that don't line
up as neatly as P2-vs-Major happened to here) — a dedicated structural comparison step across the actual
report files, rather than eyeballing a paraphrase of each one, would be a more reliable way to run this
same process if there were more than three findings or fewer obvious textual overlaps.
