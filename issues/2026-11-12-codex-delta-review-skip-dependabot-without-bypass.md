## Summary
`Codex delta review` should skip Dependabot PRs without needing the bypass attestation, the way `Claude delta review` does.

## Environment
- **Product/Service**: `.github/workflows/marketplace-ci.yml` (`codex-review` and `publish` jobs)
- **Region/Version**: as of PR #703, head `1bb83a25`
- **Browser/OS**: n/a

## Reproduction Steps
1. Dependabot opens a PR (author `dependabot[bot]`) whose diff is not `bypass_eligible`.
2. `codex-review` is skipped (its `if:` excludes `github.actor` and the PR author `dependabot[bot]`, since Dependabot runs get no secrets).
3. `Publish Codex policy result` sees a skip that is not `bypass_eligible` and fails closed.

## Expected Behavior
A PR created by Dependabot does not run the Codex delta review, and its check does not block the PR or require a bypass attestation, the same as `Claude delta review` (`docs/ci.md`: "A fork PR and a Dependabot PR skip the whole workflow without failing").

## Actual Behavior
The Codex check fails closed on every non-bypass-eligible Dependabot PR, so each one needs the SHA-bound bypass attestation (comment plus label) before it can merge.

## Error Details
~~~
No error message captured. The behavior is documented in docs/ci.md's "Codex delta review" row:
"publish then fails closed on the non-bypass-eligible skip, and the PR needs the SHA-bound bypass
attestation as before."
~~~

## Visual Evidence
n/a

## Impact
Medium: every Dependabot PR outside the bypass-eligible set needs a manual attestation step, which `triaging-dependabot-prs` currently works around with its path A/B bypass.

## Additional Context
- Found in PR #703 (https://github.com/AndreHahm/andres-cc-marketplace/pull/703), head `13723a22b777093cd2b782ac755b8902e44fe097`, while triaging the Claude delta review's security-pass finding (Major) at `.github/workflows/marketplace-ci.yml:1149`: https://github.com/AndreHahm/andres-cc-marketplace/pull/703#discussion_r4544431092
- Reviewer: Claude delta review (github-actions[bot]), severity Major. The owner declined that finding: the PR-author check is a user requirement and stays in both workflows. This issue records the follow-up the owner asked for instead.
- Keep the PR-author and actor checks (`github.actor` and `github.event.pull_request.user.login` both not `dependabot[bot]`). What should change is how `publish` treats that skip: it should pass, not fail closed, while keeping the existing trust checks (for example the verified-Dependabot-commits check `check-pr` already uses for its merge-privilege exemption), so a human-edited Dependabot branch is not waved through.
- Requirements and implementation docs to update: `docs/ci-codex-review-user-requirements.md`, `docs/ci.md` ("Codex delta review" row and the bypass section), `tests/marketplace_ci/test_ci_review_delta.py`.
