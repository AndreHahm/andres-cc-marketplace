## Summary
A Git object-ID validation regex (`^[0-9a-f]{7,40}$`) rejects valid uppercase hex SHAs and 64-character SHA-256-repository object IDs that Git itself accepts — and the identical regex was independently duplicated into two skills plus a third, still-unfixed instance.

## Environment
- **Product/Service**: `analysis-kit` plugin (`analyzing-plugin-components`, `analyzing-sessions`) and `git-kit` (`scripts/remap-handoff-shas.py`)
- **Region/Version**: this repo, found during PR #137 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A guard classifies a string as a "SHA" using `^[0-9a-f]{7,40}$`.
2. Run `git rev-parse --verify` or `git show` against an uppercased current-HEAD SHA — both resolve it correctly (Git accepts uppercase hex object IDs).
3. Run the same guard against that uppercased SHA — it's rejected as malformed.
4. Separately, a SHA-256 repository (`--object-format=sha256`) uses 64-character object IDs, which the `{7,40}` length bound also rejects.

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| A Git object ID is always lowercase hex, 7-40 characters | Git accepts uppercase hex, and a SHA-256 repository's object IDs are 64 characters |

## Expected Behavior
A Git object-ID shape check should accept both hex cases and the repository's actual supported hash length (`^[0-9a-fA-F]{7,64}$`).

## Actual Behavior
The guard rejects a valid uppercase or 64-character object ID and records a false "malformed" finding instead of verifying it.

## Impact
[Severity: Medium] Fixed in `analyzing-plugin-components` and `analyzing-sessions` in PR #137 (commit `17b9dda`), verified live against `git rev-parse --verify`/`git show` before fixing, with a new skill-tester eval covering both a 40-char uppercase SHA and a 64-char SHA-256-length SHA. A third, identical-pattern instance in `plugins/git-kit/scripts/remap-handoff-shas.py` (no `re.IGNORECASE`, no 64-char accommodation) was explicitly disclosed as out-of-scope and left unfixed in that PR.

## Additional Context
Mined from PR #137's own review history (`chatgpt-codex-connector[bot]`; 8 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #137` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/137#discussion_r3850978810

Suggested scope: fix the remaining unfixed instance in `remap-handoff-shas.py`, and grep for any other Git-object-ID regex in this repo sharing the same `[0-9a-f]{7,40}` shape.
