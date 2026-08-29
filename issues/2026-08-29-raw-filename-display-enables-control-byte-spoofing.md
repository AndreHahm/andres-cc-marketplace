## Summary
A `printf '%s'` display of untrusted candidate filenames in a numbered selection list passed newline, tab, and ANSI control bytes through unescaped — a crafted filename can visually corrupt or spoof the numbered list, causing a human to select the wrong index despite reading the display correctly.

## Environment
- **Product/Service**: `git-kit` plugin — `commit` skill's `stage-selected-files.sh` (`--list` display)
- **Region/Version**: this repo, found during PR #159 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Create a file whose name contains embedded control bytes (e.g. a newline or ANSI escape sequence) — possible on a branch checked out from a fetched/contributed PR.
2. Run `stage-selected-files.sh --list`, whose display line used `printf '%s'` to print each candidate's raw filename.
3. Observe the control bytes render directly in the terminal, capable of shifting lines, inserting fake entries, or otherwise making the numbered list misleading.
4. A user selecting an index based on the corrupted display can end up staging a different file than intended.

## Expected Behavior
When displaying an untrusted filename in any numbered/indexed selection UI, escape it for display (e.g. `printf '%q'`) while keeping the raw, unescaped bytes in the actual selection pipeline (a NUL-delimited pathspec, index-based lookup) — display safety and selection correctness need different treatments of the same string.

## Actual Behavior
The display used raw `%s` formatting with no escaping, so a crafted filename could corrupt or spoof the numbered list's visual layout.

## Impact
[Severity: Low, per CodeRabbit's own classification] A display-only spoofing risk, not itself a code-execution path — but it can mislead a human's selection decision, which is the whole point of a numbered confirmation UI. Fixed in `git-kit`'s PR #159 (commit `8d1df09`): the `--list` display line now goes through bash `printf '%q'`; the snapshot file and the actual `git add` pathspec still use raw, unescaped bytes. Verified against the same command-substitution-crafted filename used in this PR's own testing — now shown safely escaped.

## Additional Context
Mined from PR #159's own review history (`coderabbitai[bot]`; 19 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #159` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/159#discussion_r3878624135
