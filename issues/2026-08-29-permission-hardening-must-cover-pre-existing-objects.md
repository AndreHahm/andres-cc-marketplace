## Summary
A permission-hardening fix must explicitly re-narrow objects that could already exist on disk before the code path runs, not rely solely on the object's own creation-call mode flag — that flag only ever governs objects the current run itself creates.

## Environment
- **Product/Service**: `codex-kit` plugin (source instance: a broker's state directory and job log file)
- **Region/Version**: this repo, found during PR #112 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A state directory and a log file are narrowed to safe permissions (e.g. `0o700`/`0o600`) only via the mode flags passed to their own creation calls (`mkdirSync(path, {mode: 0o700})`, file-open mode).
2. An older code path (or a prior run) already created the same directory/file on disk with looser permissions (e.g. `0o755`).
3. Run the current code against that pre-existing directory/file — the creation call is skipped (the object already exists), so the narrower mode is never applied.
4. The directory/file keeps its original, looser permissions indefinitely.

## Expected Behavior
A permission-hardening fix should explicitly re-narrow an object that could already exist (e.g. an unconditional `chmodSync`/`fchmodSync` call after open/mkdir, independent of whether the object was just created), not rely solely on the creation call's own mode flag.

## Actual Behavior
The state directory and log file were only narrowed via their creation-call mode flags — an already-existing, looser-permissioned directory or file created under an older code path was never re-narrowed.

## Impact
[Severity: Medium] A security-relevant permission gap that could silently persist across an upgrade (old on-disk state stays loosely permissioned even after the fix ships). The specific instance was already fixed in `codex-kit`'s PR #112 (commit `53b04cac0a`), with explicit `chmodSync(0o700)`/`fchmodSync(0o600)` calls plus a POSIX regression test proving a pre-existing `0o755` directory is narrowed on save. This issue is about the *general* convention: no `.claude/rules/*.md` file currently states "a permission-hardening fix must explicitly re-narrow pre-existing objects, not rely on the creation call's mode flag alone" — any other permission-hardening fix in this repo could reproduce the same gap for objects that predate it.

## Additional Context
Mined from PR #112's own review history (`coderabbitai[bot]`; 28 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #112` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/112#discussion_r3843302938
