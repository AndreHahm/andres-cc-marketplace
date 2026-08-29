## Summary
Adding a new enumerated classification/type value to a multi-stage pipeline requires threading it through every independent consumer (routing tables, auto-detection branches, schemas, downstream agent input contracts) — a single un-updated consumer silently drops or misroutes the new value, and this can recur in more than one place in the same change.

## Environment
- **Product/Service**: `plugin-devkit` plugin (`plugin-conception`, `plugin-lifecycle-upstream`, `plugin-lifecycle-maintenance`, `plugin-planning`, `build-handoff-writer`)
- **Region/Version**: this repo, found during PR #142 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Introduce a new classification value (`Create`) into a pipeline that already has several established classifications (Enhance/Repair/Consolidate/Reposition/Retain/Reject/Defer), each of which is consumed independently by multiple downstream tables/branches.
2. Enumerate every place that branches on the existing classification set: a routing table in `plugin-lifecycle-maintenance`, an auto-detection branch in `plugin-lifecycle-upstream`, the originating skill's own short-circuit logic (`plugin-conception`), a downstream agent's input/output contract (`build-handoff-writer`), and a validation gate in a consumer skill (`plugin-planning`).
3. Observe that at least five of these independently missed the new value or the classification-validation step entirely — each was fixed only after a separate reviewer comment named that specific location.

## Expected Behavior
When a new enumerated value is introduced, every consumer that branches on the existing enum should be enumerated and updated in the same change — not discovered one reviewer-comment at a time.

## Actual Behavior
Five separate consumers each independently failed to account for the new `Create` classification: a routing table had no disposition for it (candidates silently stranded), an auto-detection branch resumed the wrong phase for non-Create classifications, the originating skill wrote an unnecessary artifact for a should-short-circuit outcome, a handoff-writer agent never consumed the new artifact type, and a planning skill assumed the wrong classification for any supplied brief.

## Impact
[Severity: Medium] All five instances were fixed in the same PR (commits `02a6e91`, `1f569b7`), each confirmed and verified individually. This issue is about the *general* convention: no `.claude/rules/*.md` file currently states "enumerate and update every consumer when adding a new enum/classification value" — the same shape (five independent misses in one PR) demonstrates this is not a one-off oversight but a real, recurring risk whenever a pipeline's enum grows.

## Additional Context
Mined from PR #142's own review history (`chatgpt-codex-connector[bot]`; 19 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #142` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/142#discussion_r3859723730, https://github.com/AndreHahm/andres-cc-marketplace/pull/142#discussion_r3859723734, https://github.com/AndreHahm/andres-cc-marketplace/pull/142#discussion_r3859723739

Suggested scope: consider a checklist item in `plugin-lifecycle-upstream`/`plugin-lifecycle-maintenance`'s own Design phase: "if this change adds a new classification/enum value, list every existing consumer of that enum and confirm each was updated."
