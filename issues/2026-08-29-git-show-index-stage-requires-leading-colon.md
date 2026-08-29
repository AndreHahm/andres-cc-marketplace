## Summary
`git show N:file` (no leading colon) is parsed by Git as a request for a revision literally named `N`, not an index stage — index-stage syntax requires the leading colon (`:N:file`).

## Environment
- **Product/Service**: `git-kit` plugin (`resolving-merge-conflicts/scripts/show-stage.sh`)
- **Region/Version**: this repo, found during PR #143 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. During a regular (`UU`) merge conflict, request either side's full content via `git show 2:<file>` or `git show 3:<file>`.
2. Observe Git exits 128 with `fatal: invalid object name '2'` — it parsed `2` as a revision name, not an index-stage number.
3. Run `git show :2:<file>` (leading colon) instead — this correctly resolves index stage 2's content.

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| `git show <stage-number>:<file>` addresses an index stage | Git parses this as a revision name; index-stage syntax requires a leading colon (`:<stage-number>:<file>`) |

## Expected Behavior
A helper that inspects a merge conflict's index-stage content via `git show` should use the leading-colon `:<stage>:<file>` form.

## Actual Behavior
The bare `<stage>:<file>` form failed with a plausible-looking but misleading "invalid object name" error, blocking the skill's ability to inspect either side of a real conflict.

## Impact
[Severity: High] This broke the core workflow of the skill being introduced (planning a conflict resolution requires inspecting both sides). Fixed in `git-kit`'s PR #143 (commit `0bb9d72`) — changed to `git show ":${stage}:${file}"`, live-tested against a real `UU` conflict confirming both stage 2 and stage 3 now resolve correctly.

## Additional Context
Mined from PR #143's own review history (`chatgpt-codex-connector[bot]`; 24 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #143` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. This extends the repo-wide "verify tool/API/language behavior before instructing" theme already tracked in `.claude/rules/verify-tool-behavior-before-instructing.md` with a new concrete Git-syntax instance.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/143#discussion_r3861476777
