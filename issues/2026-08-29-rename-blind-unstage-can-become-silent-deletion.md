## Summary
A staged-file scan/restore built on rename-blind `git diff --cached --name-only` can silently turn a rejected rename into a real deletion — restoring only the visible destination path of a flagged rename leaves the source-side deletion still staged.

## Environment
- **Product/Service**: `git-kit` plugin (source instance: `scan-staged-files.sh`/`unstage-flagged-files.sh`)
- **Region/Version**: this repo, found during PR #121 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A sensitive-file scanner uses `git diff --cached --name-only` to list staged paths, and flags any path matching a sensitive-directory pattern.
2. Stage a rename of a tracked file into a flagged directory (e.g. `config/plain.txt` → `config/secrets/plain.txt`).
3. `git diff --cached --name-only` reports only the destination path (`config/secrets/plain.txt`) — rename detection is off by default for this form.
4. The scanner "protectively" unstages the flagged destination path (`git restore --staged config/secrets/plain.txt`).
5. Observe: the rename's source-side deletion (of `config/plain.txt`) is still staged — a re-scan finds nothing to flag, and committing now silently records a bare deletion of the original file.

## Expected Behavior
A staged-file scan/restore should use rename-aware `git diff --cached --name-status -M`, and when a flagged path is one side of a detected rename, restore *both* sides — never just the visible destination.

## Actual Behavior
The scanner only ever saw and restored the destination path, silently converting a rejected rename into an unintended deletion of the original file.

## Impact
[Severity: High] Real data-loss path: a legitimate rename gets silently converted into a deletion, with the sensitive-file scanner's own "protective" action being the direct cause. The specific instance was already fixed in `git-kit`'s PR #121 (commit `643fa00`), live-reproduced (confirmed a real rename left a bare staged deletion before the fix) and re-verified clean after switching to `--name-status -M` with both-sides restoration. No `.claude/rules/*.md` file currently states "a staged-file scan/restore must be rename-aware and restore both sides of a flagged rename" — any other staged-file scanner in this repo (or elsewhere) built on `--name-only` could reproduce the same silent-deletion risk.

## Additional Context
Mined from PR #121's own review history (`chatgpt-codex-connector[bot]`; 17 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #121` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/121#discussion_r3845824890
