# CI Codex review: confirm the 0.170.0 pin on the Linux runner and that the project Codex config stays unapplied

## Summary
Two unverified assumptions behind CI's Codex delta review after PR #792: Codex CLI 0.170.0 has not been run on CI's Linux runner, and CI's Codex is assumed to ignore the repository's `.codex/config.toml` because it never trusts the checkout.

## Environment
- **Product/Service**: `marketplace-ci.yml` Codex delta review job (`run-codex-review`, `codex-review-bridge`)
- **Region/Version**: Codex CLI pin raised from 0.147.0 to 0.170.0 in PR #792 (head `fcafb5e6ed6edee8d89790f44bb5758f6ed17fa6`); local checks ran on Windows 11 with 0.147.0 and 0.170.0
- **Browser/OS**: CI runner `ubuntu-latest`

## Reproduction Steps
1. On a PR that does not touch Tier-1 files (so the Codex delta review dispatches), let the job install `@openai/codex@0.170.0`.
2. Watch the "Allow Codex's bwrap sandbox on the hosted runner" step (`codex sandbox /bin/true`) and the reviewer dispatch.
3. In the job, run `codex features list` from the checkout and compare with the values in `.codex/config.toml` (for example `memories = true`, `fast_mode = false`).

## Expected Behavior
- The bwrap probe and every reviewer dispatch succeed on 0.170.0.
- `codex features list` shows Codex defaults, not the project values, because the checkout is not trusted; `codex exec --sandbox read-only` is what governs the reviewers.

## Actual Behavior
Not yet observed on CI. Locally, with Codex 0.147.0 and an untrusted `CODEX_HOME`, `codex features list` in the checkout showed the defaults (`memories` off, `fast_mode` on); with the project trusted it applied the project values. A deliberately broken `default_permissions` made 0.147.0 exit 1, so a clean load is meaningful. 0.170.0 was not run on Linux, and the untrusted behavior was not checked on 0.170.0 or on Linux.

## Error Details
~~~
None observed.
~~~

## Visual Evidence
None.

## Impact
Medium: if 0.170.0 fails the bwrap step or dispatch on the runner, every CI Codex review fails to start. If CI's Codex did load the project config, the approval and permission profile a PR sets would govern its own reviewers (the concern raised in the PR #792 review thread below).

## Additional Context
- Found in PR #792: https://github.com/AndreHahm/andres-cc-marketplace/pull/792
- Review thread: https://github.com/AndreHahm/andres-cc-marketplace/pull/792#discussion_r4633106151 (Claude delta review, general pass, Major)
- Pin lives in `.github/workflows/marketplace-ci.yml` (npm install line) and `scripts/marketplace_ci/review_contract.py` (`CODEX_CLI_VERSION`); `test_the_cli_pin_matches_the_workflows_npm_install_line` keeps them equal.
- Nothing in the workflow, `scripts/marketplace_ci/review.py` or `plugins/codex-kit/scripts/lib/codex-exec.mjs` writes a `trust_level` or projects entry.
