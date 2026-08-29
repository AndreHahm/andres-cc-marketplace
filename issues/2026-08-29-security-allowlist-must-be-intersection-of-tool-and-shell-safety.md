## Summary
A security allowlist's rule must be verified against both the domain tool's own valid syntax AND the execution context's safety requirements — a reviewer's own suggested "just validate against the tool's real syntax" fix was independently proven unsafe here, since the tool's syntax rules are broader than the shell-safety requirement.

## Environment
- **Product/Service**: `git-kit` plugin (`merge-pr`, `finishing-work`)
- **Region/Version**: this repo, found during PR #137 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. A branch-name guard rejects shell-unsafe characters via an allowlist regex.
2. The regex is too strict: it rejects `feature+api`, `user@topic`, `release=next` — all valid Git branch names (`git check-ref-format --branch` accepts them) that contain no shell metacharacters.
3. A reviewer suggests fixing this by validating against Git's own ref-format rules instead of a hand-picked allowlist.
4. Test that suggestion: `git check-ref-format` also accepts `;`, `&`, `|`, `$`, backticks, parens, `<`, `>`, `!`, quotes, `{`, `}`, `#`, `%` as valid ref-name characters — adopting "Git's own syntax" as the allowlist would readmit every one of these into a value later interpolated into a shell command.

## Expected Behavior
When narrowing or widening a security allowlist, the accepted rule must be the intersection of "valid per the consuming domain tool" and "safe per the execution context the value is used in" — verifying only one side is not sufficient, even when the reviewer proposing the fix is confident in it.

## Actual Behavior
The original guard was too strict (rejected valid, safe characters); the reviewer's own suggested alternative would have been actively unsafe (reopened shell injection) had it been adopted without independent verification.

## Impact
[Severity: Medium — a security-relevant near-miss, not a shipped vulnerability, since the unsafe alternative was verified and rejected before being applied]. Fixed in `git-kit`'s PR #137 (commit `8b01b26`) with a narrower allowlist (`^[A-Za-z0-9._/@+=-]+$`, adding only `@`, `+`, `=`), verified both Git-valid and shell-safe, and mirrored to `finishing-work`. A new eval verifies both the previously-rejected valid names and the original injection-attempt case still behave correctly.

## Additional Context
Mined from PR #137's own review history (`chatgpt-codex-connector[bot]`; 8 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #137` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/137#discussion_r3851373148
