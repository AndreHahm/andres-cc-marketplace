## Summary
A frontmatter validator's substring match (`"name:" in fm`, `"description:" in fm`) accepted unrelated keys sharing the same text fragment (`skill-name:`, `long-description:`) — the check could pass even when the actually-required `name`/`description` key was entirely absent. The identical defect recurred in a second, independent smoke test in a sibling skill.

## Environment
- **Product/Service**: `git-kit` and `analysis-kit` plugins — `github-issue-lifecycle`'s and `mining-review-learnings`'s `scripts/smoke_test.py` (`check_frontmatter`)
- **Region/Version**: this repo, found during PR #172 and PR #179 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Construct a synthetic SKILL.md whose frontmatter contains only `skill-name:` and `long-description:` (no bare `name:`/`description:` key).
2. Run `check_frontmatter`'s substring check: `"name:" in fm`.
3. Observe it returns `True`, since `skill-name:` contains the substring `name:` — the check passes even though the actually-required `name` key is absent.

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| `"name:" in fm` reliably detects a `name:` frontmatter key | It also matches any key merely containing that text as a substring (`skill-name:`, `id-name:`, etc.), producing a false pass |

## Expected Behavior
A frontmatter/YAML key-presence check should match anchored, non-comment key lines (e.g. `^name:\s`/`^description:\s` with `re.MULTILINE`), never a bare substring search.

## Actual Behavior
Two independent occurrences: `github-issue-lifecycle`'s smoke test (PR #172, found by CodeRabbit) and `mining-review-learnings`'s smoke test (PR #179, found by CodeRabbit) — the same defect shape, in two unrelated skills' own copy-pasted-or-independently-written smoke test logic.

## Impact
[Severity: Medium] A structural smoke test that can silently pass on genuinely malformed frontmatter defeats its own purpose across every skill using this checker shape. Fixed in `git-kit`'s PR #172 (commit `2c12b9f`) and `analysis-kit`'s PR #179 (commit `3a7a5b5`): both switched to anchored, non-comment YAML key-line regex matches, verified live against both the real SKILL.md (still passes) and a synthetic `skill-name:`/`long-description:`-only fixture (now correctly fails).

## Additional Context
Mined from PR #172's and PR #179's own review history (`coderabbitai[bot]`; 11 and 25 review rounds respectively) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (an addition to the existing `## PR #172` section, and the new `## PR #179` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. The recurrence across two independently-authored smoke tests suggests this checker shape may be worth auditing across every `smoke_test.py` in the repo that validates frontmatter this way.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/172#discussion_r3882146217, https://github.com/AndreHahm/andres-cc-marketplace/pull/179#discussion_r3885947297
