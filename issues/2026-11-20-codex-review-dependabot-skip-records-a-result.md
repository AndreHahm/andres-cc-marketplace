# fix(ci): a verified Dependabot PR records a codex-review-skip result, R15 says it records none

## Summary
For a verified Dependabot PR, R15 says the skipped Codex review "records no review result", but `compute-scope` still uploads a `codex-review-skip` record that later runs can take as their anchor. A workflow comment also misstates what the bypass records.

## Environment
- **Product/Service**: `marketplace-ci.yml`, jobs `compute-scope` and `publish`
- **Region/Version**: `main` as of 2026-11-20
- **Browser/OS**: GitHub-hosted `ubuntu-latest`

## Reproduction Steps
1. Dependabot opens a PR that changes only root `package.json` / `pnpm-lock.yaml`.
2. `compute-scope` scores it `mode: light`, so `bypass_eligible: true`.
3. Its skip-record step uploads the `codex-review-skip` artifact for that head.
4. A later run on the PR can take that record as its anchor (R5).

## Expected Behavior
Per `docs/ci-codex-review-user-requirements.md` R15: "The pass is never presented as a clean review and records no review result."

## Actual Behavior
A `codex-review-skip` record is written for the Dependabot head. The same record is written for any `light`-scope PR, so the practical effect is small, but the behavior and R15's wording disagree.

Separately, the comment above the Dependabot branch of `publish` (`.github/workflows/marketplace-ci.yml`, "Like the bypass above, it records no review result") is wrong about the bypass: a valid bypass records `codex-review-bypass` (R12).

## Error Details
~~~
None.
~~~

## Visual Evidence
None.

## Impact
**Low** - no merge gate is weakened; a later run anchoring on the record reviews only what changed after it, which for these PRs is still Dependabot-only content.

## Additional Context
- Found by an R1-R15 audit of the Codex delta review during issue #793's work (2026-11-20).
- Direction: either skip the record for a Dependabot skip (`hygiene`'s `skip_codex_review=true`), or amend R15 to allow it. Fix the comment either way.
