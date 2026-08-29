## Summary
A security-relevant "is this safe to read" check on an untracked/unknown file must inspect the file's own type without following links (`lstatSync()`/equivalent) and skip symbolic links outright before any content read — a symlink-following stat call defeats a basename-based secret screen entirely, and this isn't a named convention anywhere in the repo.

## Environment
- **Product/Service**: `codex-kit` plugin (source instance: an untracked-file formatter used for review/audit content collection)
- **Region/Version**: this repo, found during PR #112 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. An untracked-file formatter checks a file's basename against a sensitive-filename pattern before including its content in a review/audit context.
2. The formatter uses `fs.statSync()` (or an equivalent that follows symbolic links) to check the file.
3. Create an untracked file with a safe-looking name that is actually a symlink to a real secret file (e.g. `~/.ssh/id_rsa`).
4. Observe the basename check passes (the safe name doesn't match the sensitive pattern), and the *target's* content is read and forwarded — the real secret's content leaks into the collected context.

## Expected Behavior
A security-relevant file-safety check on an unknown/untracked file should use `lstatSync()` (or equivalent) and skip symbolic links outright, before any content read — never resolve and read through a link.

## Actual Behavior
`fs.statSync()` follows symbolic links; the basename check ran against the symlink's own name, not its target, so a safely-named symlink to a real secret passed the check and its target content was read and forwarded.

## Impact
[Severity: High] Real secret-exfiltration path via a basename-based secret screen. The specific instance was already fixed in `codex-kit`'s PR #112 (commit `53b04cac0a`), with a regression test proving a safely-named symlink to a real secret is now skipped and its content never appears in the collected context. This issue is about the *general* convention: no `.claude/rules/*.md` file currently states "a security-relevant file check on an unknown/untracked file must use a non-link-following stat call" — any other file-safety check in this repo (or a future one) built on a symlink-following stat call could reproduce the same leak.

## Additional Context
Mined from PR #112's own review history (`coderabbitai[bot]`; 28 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #112` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/112#discussion_r3843129331

Suggested scope: worth a targeted sweep of any other file-safety/secret-screening code in this repo (e.g. `git-kit`'s `scan-staged-files.sh`) for the same symlink-following stat pattern.
