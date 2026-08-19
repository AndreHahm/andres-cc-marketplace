# Phase 3 Consolidation Walkthrough: Reports A, B, C

## Step 0 — Treat report content as data

All three reports are read in full and treated strictly as data to consolidate, not as instructions. None
of the three contain anything that looks like an embedded instruction, so no filtering is needed there —
this is just the standard posture Phase 3 requires before touching the findings.

## Step 1 — Deduplicate by subject

Looking past each report's own wording and analytical angle, all three findings trace to the **same
underlying subject**: `git-kit`'s `merge-pr` invokes `gh pr merge` without first confirming the PR is
actually ready to merge.

- **Report A** (analyzing-plugin-components) states it as a component-level SWOT weakness: merge-pr skips
  a readiness check before merging.
- **Report B** (analyzing-governance-and-conflicts) states the identical mechanical gap — no mergeability
  check before `gh pr merge` — but frames it as a governance/rule-conformance violation (a "Major conflict
  category" finding).
- **Report C** (mining-recurring-patterns) doesn't describe the missing check directly; it reports a
  *symptom* of it — the user had to ask about merge readiness twice in the same session. That repeated
  question is best read as behavioral evidence of the same root cause: because merge-pr doesn't verify
  readiness itself, the user is left to check (and re-check) it manually.

This is exactly the case the skill's own example calls out — "a component SWOT weakness and a governance
conflict about the same rule violation" collapsing into one entry — extended one step further to include
a recurring-pattern finding that corroborates the same root cause from a third, behavioral angle. All
three collapse into **one consolidated finding**, citing all three source reports.

## Step 2 — Classify severity

Per severity-vocabulary.md's mapping table:

- Report A: `P2` → **Major**
- Report B: `Major` conflict category → **Major** (already native scale, no translation needed)
- Report C: no native severity term (mining-recurring-patterns is one of the two source skills with no
  mapping-table row). Per that file's stated fallback, the tier definitions are applied directly rather
  than treating the missing row as a gap: a single recurring question about a process gap, on its own,
  would land at Minor/Informational — it's evidence of friction, not itself a defect with independent
  operational impact. Since C is being folded into the same entry as A/B rather than reported standalone,
  its role here is corroborating evidence, not a separate severity input — it doesn't get its own line in
  the P1/P2/P3 buckets.

Consolidated severity: **Major (P2 tier)** — driven by A and B's agreement; C is cited as supporting
evidence within the same entry rather than averaged or independently scored.

## Step 3 — Tag the target plugin and component explicitly

The finding itself is tagged directly (not left as a citation-only reference):

**C1 — git-kit's merge-pr**

## Resulting persisted-report structure

**Source-report table** (excerpt):

| # | Skill | Scope |
|---|---|---|
| A | analyzing-plugin-components | (session scope) |
| B | analyzing-governance-and-conflicts | (session scope) |
| C | mining-recurring-patterns | (session scope) |

**P2 (Major) bucket:**

> ### C1. merge-pr merges without verifying PR readiness/mergeability — git-kit's merge-pr
>
> **Reported in:** #A, #B, #C
>
> **Status:** OPEN. `merge-pr` calls `gh pr merge` without first checking draft status, required-check
> pass state, or outstanding change-request reviews (#A, #B). This forced the user to ask about merge
> readiness manually, twice in the same session (#C) — a direct behavioral symptom of the missing
> automated check. Fix: add a readiness/mergeability check (not draft, all required checks green, no
> unresolved change-request reviews) before invoking `gh pr merge`, matching the check `merge-pr`'s own
> skill description already claims to perform.

No separate entry is created for C, and nothing here goes into the "No action needed" (informational)
section — C's content is fully absorbed as supporting evidence inside C1 rather than left as a standalone,
unclassified item.

## Why this is the correct application of Phase 3, not just "merge A and B, drop C"

The instructions call for deduplication "by subject, not by exact wording," and explicitly warn against
treating the absence of a severity-mapping row as a reason to work around a finding rather than classify
it. Dropping C because it lacks a native severity term would violate that; folding it in as evidence would
violate nothing, since it never needed an independent severity in the first place — it's already covered
by the tier A and B jointly established for the same subject. The alternative reading — keeping C as a
separate, third bucket item — was considered and rejected: C describes no new mechanism, only a
consequence of the one mechanism A and B already describe, so a separate entry would just be the same
underlying issue counted twice under Phase 3's own dedup rule.
