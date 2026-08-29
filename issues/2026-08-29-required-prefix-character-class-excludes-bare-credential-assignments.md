## Summary
A security-relevant credential-assignment pattern required a leading `[A-Za-z_]` character before the `CREDENTIAL`/`AUTH` alternation — a bare `AUTH=...` or `CREDENTIAL=...` assignment (no prefix at all) doesn't match, because the required leading character class consumes the assignment's own first letter before the alternation is evaluated, silently excluding the exact bare shape the check exists to catch.

## Environment
- **Product/Service**: `codex-kit` plugin — `codex-windows-guardrails`'s `guarded-dispatch.mjs` (`ADDITIONAL_CREDENTIAL_ASSIGNMENT_PATTERN`)
- **Region/Version**: this repo, found during PR #161 review (`AndreHahm/andres-cc-marketplace`)

## Reproduction Steps
1. Construct a documentation file (exempted by the content-aware documentation exemption) containing the line `AUTH=opaque-live-value` or `CREDENTIAL=opaque-live-value` — no prefix before the keyword.
2. Test `ADDITIONAL_CREDENTIAL_ASSIGNMENT_PATTERN` against these lines. Live node-verified: the regex matched `SERVICE_CREDENTIAL=opaque-value` and `DB_AUTH_VALUE=opaque-value` but did **not** match bare `CREDENTIAL=opaque-value`/`AUTH=opaque-value`.
3. `redactSecrets()` also misses both bare forms, so `checkSecretFiles()` exempts the file entirely.
4. A `danger-full-access` Windows dispatch then proceeds despite the file containing exactly the credential-assignment shape the check exists to block.

## Assumed vs. actual

| Assumed | Actual |
|---|---|
| An "optional prefix + required keyword" regex matches both prefixed (`SERVICE_CREDENTIAL=`) and bare (`CREDENTIAL=`) forms | The required leading `[A-Za-z_]` character class consumes the bare keyword's own first letter before the alternation evaluates, so the bare form never matches |

## Expected Behavior
When a security check's regex is built as "optional prefix + required keyword," verify with a direct test (not just a read-through) that the bare, unprefixed form of the keyword still matches.

## Actual Behavior
A documentation file containing a bare `CREDENTIAL=`/`AUTH=` assignment would bypass the secret-file check and reach a `danger-full-access` dispatch on Windows.

## Impact
[Severity: Major, per CodeRabbit's own classification — a concrete security exposure on the exact gate this PR was introducing] Fixed in `codex-kit`'s PR #161 (per the PR's own review reply threads), updating `ADDITIONAL_CREDENTIAL_ASSIGNMENT_PATTERN` in both mirrored `guarded-dispatch.mjs` files to match bare assignments as well as suffixed names, with smoke coverage added in `codex-windows-guardrails-preflight.mjs` for an unprefixed assignment.

## Additional Context
Mined from PR #161's own review history (`coderabbitai[bot]`; 9 review rounds total) via `mining-review-learnings`, and proposed into `.claude/THIRD_PARTY_REVIEW_LEARNINGS.md` (new `## PR #161` section) by `managing-review-learnings`, which found no existing rule covering this subject before filing this issue. This extends the repo-wide "verify tool/API/language behavior before instructing" theme already tracked in `.claude/rules/verify-tool-behavior-before-instructing.md` with a new concrete regex-construction instance.

Evidence: https://github.com/AndreHahm/andres-cc-marketplace/pull/161#discussion_r3879392796
