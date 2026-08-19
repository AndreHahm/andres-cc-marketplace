# Phase 3 Consolidation Walkthrough: Reports A, B, C

## Step 1 — Deduplicate by subject

Reports A and B make the **identical claim**: `merge-pr` runs `gh pr merge` without first checking
whether the PR is actually mergeable/ready. Report A frames it as a component weakness (SWOT-style,
P2), Report B frames the same defect as a governance/rule-conformance gap (Major conflict category).
Same underlying issue, two analytical angles — this is exactly the case Phase 3 names explicitly (a
component weakness and a governance conflict about the same rule violation). **A and B merge into one
entry**, citing both reports.

Report C makes a **different kind of claim**: the user asked about merge readiness twice in the
session. That's a discoverability/recall-gap observation about session behavior, not an assertion that
`merge-pr` itself lacks a check. It's plausibly *explained by* the same underlying gap A/B found, but
per Phase 3's explicit instruction, "consistent with" is not the same as "makes the same claim" — merging
it into the A/B entry would bury C's own independent evidence (a recurring-question pattern) inside a
citation nobody would see without opening the merged entry's fine print. **C stays its own entry.**

Result: 2 entries from 3 reports.

## Step 2 — Classify severity

- **A/B merged entry**: A's native term is P2 (`analyzing-plugin-components`), which
  `severity-vocabulary.md`'s mapping table maps P2 -> **Major**. B's native term is a conflict category
  (`analyzing-governance-and-conflicts`), which the same table maps to **Major by default** (Critical
  only if it crosses a safety/governance boundary — a missing pre-merge check degrades quality/process
  but doesn't itself corrupt state or bypass a hard boundary, so default applies). Both source terms
  land on **Major** independently — no conflict to resolve.

- **C entry**: `mining-recurring-patterns` is one of the two eligible source skills with no native
  severity term. Per the file's own fallback ("use the tier definitions above directly"), a
  repeated-question pattern is a session-behavior observation, not itself a defect — it doesn't
  independently require a fix to close (the fix, if any, lives in the merge-pr gap already captured
  above). That matches the **Informational** tier definition ("a useful observation, a pattern worth
  tracking, a note for context") rather than Minor (which requires the item itself to be "a real...
  issue" needing eventual resolution). Classified **Informational**.

## Step 3 — Tag target plugin/component on the finding itself

Both entries are tagged inline as `git-kit`'s `merge-pr` — not left as a bare "see report #N" citation.

---

## Persisted Report (excerpt)

### Source Reports

| # | Skill | Scope |
|---|---|---|
| 1 | analyzing-plugin-components | Report A |
| 2 | analyzing-governance-and-conflicts | Report B |
| 3 | mining-recurring-patterns | Report C |

### P2 — Major

#### M1. `merge-pr` runs `gh pr merge` without a pre-merge readiness/mergeability check — git-kit's merge-pr

**Reported in:** #1, #2
**Status:** OPEN. `merge-pr` needs to verify PR mergeability (checks passing, no blocking reviews,
not in conflict) before invoking `gh pr merge` — surfaced independently as a component-level weakness
(P2) and as a governance/rule-conformance gap (Major conflict category); both source reports describe
the same underlying defect in the same component.

### No Action Needed (Informational)

#### I1. User asked about merge readiness twice in the session — git-kit's merge-pr

**Reported in:** #3
**Status:** INFORMATIONAL. No native severity term from `mining-recurring-patterns`; classified via
severity-vocabulary.md's tier definitions directly (an observation/pattern, not itself a defect
requiring its own fix). Consistent with, but not merged into, M1 above — this is independent evidence
of a discoverability/recall gap (the user had to ask because the tool gave no answer), not a
restatement of M1's own claim. Retained as its own entry so this corroborating evidence stays visible
rather than buried inside M1's citation list. No separate fix required beyond resolving M1.
