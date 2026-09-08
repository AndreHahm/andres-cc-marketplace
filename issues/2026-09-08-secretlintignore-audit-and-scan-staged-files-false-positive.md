## Summary
Audit `.secretlintignore`'s contents, and make `scan-staged-files.sh` (and similar filename-pattern secret checks) consult it to avoid false positives on legitimately-named config files

## Environment
- **Product/Service**: `andres-cc-marketplace` repo tooling — `.secretlintignore` (introduced by PR #294's `security.yml` workflow) and `plugins/git-kit/scripts/scan-staged-files.sh`
- **Region/Version**: N/A

## Reproduction Steps
1. Stage an edit to `.secretlintignore` itself (e.g. removing an ignore pattern).
2. Run `git-kit`'s `commit` skill (or `scan-staged-files.sh` directly) against the staged changes.
3. Observe `.secretlintignore` gets flagged as a sensitive file.

## Expected Behavior
A legitimate, non-credential config file like `.secretlintignore` should not be flagged as a suspected secret just because its filename contains the substring "secret".

## Actual Behavior
`scan-staged-files.sh`'s `*secret*` glob pattern (line 29) matches `.secretlintignore` by filename alone, flagging it for unstaging even though it holds no credentials — it's the ignore-pattern list for the secret scanner itself.

## Error Details
~~~
scan-staged-files.sh flagged: .secretlintignore
(matched via the `*secret*` pattern in the sensitive-filename check)
~~~

## Visual Evidence
N/A

## Impact
**Low** — false positive only, no security exposure. Workaround exists (manually confirm and proceed past the flag), but it adds friction to every future commit that touches `.secretlintignore`, and risks someone reflexively unstaging a legitimate change.

## Additional Context
Two related, separable follow-ups surfaced together:

1. **Audit `.secretlintignore`'s own contents.** It currently mirrors a large chunk of `.gitignore` verbatim (see PR #294's own round-2 fix, which had to remove `.env`/`.env.*` from this mirrored list since it let a force-added, tracked `.env` file bypass the secret scan entirely). Worth a fresh pass to check for other overbroad or stale entries in that mirrored block, not just the one already caught.
2. **Make `scan-staged-files.sh`-style filename checks `.secretlintignore`-aware.** Rather than hardcoding a fixed `*secret*`/`*credential*`/etc. pattern list with no way to declare an intentional exception, consider having this (and any similar local pre-commit/CI filename-pattern check) read `.secretlintignore`'s own patterns and treat a match there as a signal to skip the flag — the same file already exists specifically to declare "this path is not a secret-scanning concern," so reusing it here avoids a second, independently-maintained exception list.

Found live during PR #294 (`feat/pr-ci-governance`) while committing a legitimate edit to `.secretlintignore` itself.
