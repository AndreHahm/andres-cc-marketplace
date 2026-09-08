## Summary
Neither local `.secretlintignore` consumer added for issue #295 verifies the file against a trusted base SHA before reading it, unlike the CI secretlint job's own equivalent check

## Environment
- **Product/Service**: `andres-cc-marketplace` repo tooling — `plugins/git-kit/scripts/scan-staged-files.sh` and `plugins/codex-kit/scripts/lib/secret-filenames.mjs`'s `isExemptedBySecretlintignore` (consumed by `plugins/codex-kit/skills/codex-windows-guardrails/scripts/guarded-dispatch.mjs`)
- **Region/Version**: N/A

## Reproduction Steps
1. Check out an untrusted, unmerged PR branch locally (a normal `codex-kit` use case, e.g. reviewing it via `codex-audit-loop`).
2. Suppose that branch's own `.secretlintignore` has been edited (maliciously or accidentally) to add a new exemption entry for a real credential-bearing file's exact path.
3. Run `git-kit`'s `commit` skill (which calls `scan-staged-files.sh`) or dispatch `guarded-dispatch.mjs` against that checkout.

## Expected Behavior
A local secret-scan consumer should not blindly trust a PR branch's own edits to the file that controls what it exempts from scanning — the same reasoning `.github/workflows/security.yml`'s CI secretlint job already applies to itself.

## Actual Behavior
Both local consumers read the working-tree `.secretlintignore` unconditionally, with no verification against a trusted base SHA. `.github/workflows/security.yml`'s CI job deliberately restores `.secretlintignore` (and `.secretlintrc.json`) from the PR's base SHA before ever reading them, specifically because "a PR could weaken its own secret scan" (see that workflow's own "Restore secretlint config from the trusted base SHA" step) — neither of the two local consumers added in this session has an equivalent check. A crafted PR branch could add its own real secret's exact file path to `.secretlintignore`, and that secret would not be flagged by either local check.

## Impact
**Low-to-Medium** — requires an adversarial or accidentally-misconfigured PR branch actively being reviewed locally; does not affect the CI secretlint job itself (which already has its own base-SHA restore and remains the actual enforced gate). This is a defense-in-depth gap in local tooling, not a bypass of CI.

## Additional Context
Applying the same restore-from-base pattern locally would need a live `gh api` call to fetch the base-SHA content of `.secretlintignore`, which these otherwise-offline-capable local scripts don't currently make. That raises its own design questions worth a dedicated discussion rather than folding into the original fix: a network dependency for a local pre-commit convenience script; how a Windows-only guardrails dispatch script would authenticate to GitHub; whether the fix should live in one shared helper both consumers call rather than being duplicated.

Currently documented only as a code comment in `plugins/codex-kit/scripts/lib/secret-filenames.mjs`'s `isExemptedBySecretlintignore` function header (the comment beginning "Known limitation (security review, issue #295, informational)").

**Ask:** design and implement trusted-base-SHA verification for local `.secretlintignore` consumption — or make and document a deliberate decision not to, if the risk is judged acceptable for local dev-convenience tooling that isn't itself a CI-enforced gate.

Refs: #295 (the issue whose fix introduced these two consumers).
