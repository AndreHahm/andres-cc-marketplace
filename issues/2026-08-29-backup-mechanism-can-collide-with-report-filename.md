## Summary
A backup mechanism that preserves conflicted files by their original relative path can collide with a generated report file written into the same directory — a conflicted file happening to share the report's own filename silently loses its backup.

## Environment
- **Product/Service**: `git-kit` plugin (`resolving-merge-conflicts/scripts/handle-deleted-modified.sh`)
- **Region/Version**: this repo, found during PR #143 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A delete/modify-conflict handler backs up a conflicted file's modified content to `$BACKUP_DIR/<original-relative-path>` before resolving it, as a safety net.
2. The same handler generates a report and writes it to `$BACKUP_DIR/SUMMARY.md`.
3. Cause a conflict on a repository path that is itself named `SUMMARY.md` (e.g. a root-level `SUMMARY.md`).
4. Observe: the file's own backup is first written to `$BACKUP_DIR/SUMMARY.md`, then the report-generation step truncates and overwrites that exact same path — the backup is lost.

## Expected Behavior
A mechanism that backs up files by their original relative path into a directory that also holds generated metadata/report files should reserve a namespace (e.g. a dedicated subdirectory) for one of the two, so no original repository path can ever collide with the metadata filename.

## Actual Behavior
A conflicted file literally named `SUMMARY.md` had its backup silently destroyed by the report-generation step running afterward in the same directory — the exact safety net the backup mechanism exists to provide was lost for that one filename, with the delete-side working-tree change already staged.

## Impact
[Severity: Medium] A real, reproducible data-loss path for one specific (if unusual) filename. Fixed in `git-kit`'s PR #143 (commit `5c6b5c3`) by moving backed-up files into a reserved `files/` subdirectory, structurally separate from the top-level generated `SUMMARY.md` — live-tested with a real conflict on a file literally named `SUMMARY.md`, confirming its backup at `files/SUMMARY.md` now retains the correct content.

## Additional Context
Mined from PR #143's own review history (`chatgpt-codex-connector[bot]`; 24 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #143` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/143#discussion_r3861794704
