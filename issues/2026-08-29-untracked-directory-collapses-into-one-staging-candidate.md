## Summary
`git status --porcelain`'s default untracked-files mode groups an entire untracked directory into one candidate line — a numbered file-selection UI built on this output shows one entry for a multi-file untracked directory, and selecting that single index stages every file beneath it, contradicting the UI's own "one candidate = one file" numbering.

## Environment
- **Product/Service**: `git-kit` plugin — `commit` skill's `stage-selected-files.sh` (`--list` mode)
- **Region/Version**: this repo, found during PR #159 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Create an untracked directory containing two or more files.
2. Run `git status --porcelain -z` (no `--untracked-files=all`) against the working tree.
3. Observe the directory appears as a single entry (`?? newdir/`), not one line per file inside it.
4. A numbered selection UI built on this output presents that directory as one candidate; selecting its index stages every file beneath it, even though the UI's own numbering implied a single file.

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| Each numbered candidate from `git status --porcelain` corresponds to exactly one file | An untracked directory collapses to one porcelain entry by default, silently expanding a single selected index into every file inside it |

## Expected Behavior
A file-selection UI built on `git status --porcelain` should pass `--untracked-files=all` to get one line per actual file, so its own "one candidate = one file" numbering holds.

## Actual Behavior
Live-reproduced: a 2-file untracked directory showed as 1 candidate in `--list`'s output; selecting it staged both files.

## Impact
[Severity: Medium] A user selecting what they believe is a single file can unknowingly stage additional, unreviewed files. Fixed in `git-kit`'s PR #159 (commit `8d1df09`): added `--untracked-files=all` to the `git status --porcelain -z` call. Reproduced the exact scenario first, then confirmed the fix lists both files as separate candidates and partial selection works correctly.

## Additional Context
Mined from PR #159's own review history (`chatgpt-codex-connector[bot]`; 19 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #159` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. This extends the repo-wide "verify tool/API/language behavior before instructing" theme already tracked in `.claude/rules/verify-tool-behavior-before-instructing.md` with a new concrete `git status` semantics instance.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/159#discussion_r3878603940
