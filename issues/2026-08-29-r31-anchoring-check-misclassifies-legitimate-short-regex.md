## Summary
A content-scan validation heuristic (`check_evals.py`'s new R31 anchoring check) treats every short, unanchored `re.search` branch in a skill's own quality-gate code as a "vacuous SKILL.md assertion," producing a false REQUIRED failure on a legitimate check that is intentionally short and unanchored.

## Environment
- **Product/Service**: `plugin-devkit` plugin — `plugin-grader`'s `check_evals.py` (R31 rule)
- **Region/Version**: this repo, found during PR #147 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. `plugin-grader`'s own quality-gate code contains a `re.search` checking for shell metacharacters (`&&`, pipes, semicolons) anywhere in a command line — intentionally short and unanchored, since the pattern must match those characters at any position in the string.
2. Run `check_evals.py --smoke-test` against `plugin-grader`'s own `SKILL.md` with the new unconditional R31 anchoring check active.
3. Observe: the check flags this legitimate `re.search` as a "vacuous SKILL.md assertion" and reports a REQUIRED failure, even though the code is correct and the pattern's shortness is intentional, not a defect.

## Expected Behavior
A content-scan heuristic that flags "suspiciously short/unanchored" patterns as defects should scope itself to the actual context it's meant to catch (e.g. only assertion-content variables), not apply unconditionally to every short regex in the codebase.

## Actual Behavior
The unconditional check produced a false REQUIRED failure on valid code, which would have blocked `plugin-grader` from passing its own smoke test had it not been caught in review.

## Impact
[Severity: Medium] A validation heuristic producing false positives on legitimate code undermines trust in the check and can block valid work. Fixed in `plugin-devkit`'s PR #147 (commit `fb99f41`) by scoping the anchoring rule to haystacks whose variable name contains "skill," matching a sibling `re.findall` loop's existing guard — live-verified: `check_evals.py --smoke-test` exits 0 post-fix, and `test_check_evals.py`'s 9-fixture suite still passes.

## Additional Context
Mined from PR #147's own review history (`chatgpt-codex-connector[bot]`; 11 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #147` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/147#discussion_r3871838115
