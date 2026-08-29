## Summary
Comparing ISO8601 timestamp strings lexicographically to find the "most recent" entry is not the same as comparing them chronologically when values carry different UTC offsets — the wrong entry can be selected.

## Environment
- **Product/Service**: `plugin-devkit` plugin (`inventory_common/grading.py`)
- **Region/Version**: this repo, found during PR #141 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Persist two grading records with `graded_at` values `2026-08-25T01:00:00Z` and `2026-08-25T10:00:00+10:00`.
2. Note that `+10:00` (UTC+10) makes the second value chronologically *earlier* than the first in real UTC time (`2026-08-25T00:00:00Z` equivalent).
3. Select "the current/most recent" record via `max(records, key=lambda e: e["graded_at"])` (raw string comparison).
4. Observe the second (chronologically earlier) record is selected, because its string sorts lexicographically greater (`...T10:00:00+10:00` > `...T01:00:00Z` as plain strings).

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| Sorting ISO8601 timestamp strings lexicographically gives chronological order | It only does when every value shares the same UTC offset/format — mixed offsets (or a bare non-`Z` format) break it |

## Expected Behavior
Before comparing timestamps for "most recent," every value should be normalized to a common UTC representation (or parsed into a real datetime object) rather than compared as raw strings.

## Actual Behavior
`graded_at` was accepted as any non-empty string and compared lexicographically, so a value with a positive UTC offset could be picked as "current" over a chronologically later `Z`-format value.

## Impact
[Severity: Medium] Fixed in `plugin-devkit`'s PR #141 (commit `7ace291`): `graded_at` must now end in `Z` (the only format `plugin-grader` itself ever emits) and parse via `datetime.fromisoformat`, rejecting offset timestamps, garbage strings, and invalid calendar dates. Live-verified: the exact offset-vs-Z scenario now resolves correctly, and the wrong-score-selected bug is closed for this one field. No sweep was made for other timestamp fields elsewhere in this repo that might do the same raw-string comparison.

## Additional Context
Mined from PR #141's own review history (`chatgpt-codex-connector[bot]`; 25 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #141` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/141#discussion_r3856638731

Suggested scope: grep this repo for other `max(...)`/sort-based "most recent" selection over a raw timestamp string field, to check whether the same class of bug exists elsewhere.
