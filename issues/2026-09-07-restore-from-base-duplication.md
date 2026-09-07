## Summary
The trust-boundary `restore_from_base()` bash function is duplicated byte-for-byte 7 times across two GitHub Actions workflows, creating a drift risk for security-relevant restore logic.

## Locations
- `.github/workflows/marketplace-ci.yml` — 6 separate job definitions (currently around lines 95, 171, 247, 331, 407, 501)
- `.github/workflows/await-codex-review.yml` — 1 more occurrence (currently around line 34)

Each copy defines the same `restore_from_base()` function and calls it identically to restore `.github/actions/workflow-killswitch/action.yml`, `.github/actions/track-rerun/action.yml`, and `.github/WORKFLOW_KILLSWITCH` from the PR's trusted base SHA (via the GitHub Contents API) before those composite actions are invoked — so a same-repo PR can't tamper with them ahead of the kill-switch/rerun-tracking check.

## Current State
This restore step is trust-boundary-critical: it's what prevents a same-repo `pull_request` (not `pull_request_target`) run from executing the kill-switch/track-rerun composite actions against a PR-tampered copy. It runs as inline bash, not a shared composite action, because the composite-action resolution mechanism (`uses: ./.github/actions/...`) itself reads from the current (possibly PR-controlled) checkout — the restore step has to run before anything else establishes trust.

## Risk
A future fix to this restore logic (base-SHA verification order, the 404-vs-error branch, `on_absent` semantics, etc.) has to be applied identically in all 7 places. Missing even one copy would silently leave that job's kill-switch/track-rerun composite actions trusting unverified, PR-controlled content while the other 6 stay protected — an easy-to-introduce, hard-to-notice partial security regression, since a diff touching only 6 of 7 copies looks like an intentional partial change rather than a missed spot.

## Impact
**Medium** — no active vulnerability today (all 7 copies are currently identical and correct), but a maintainability/security-hygiene gap that raises the odds of a future partial fix leaving one job unprotected.

## Additional Context
Surfaced by a local `cross-model-review` pass on `feat/ci-pipeline-foundation` (PR #289) on 2026-09-07. An initial proposed fix — extracting `restore_from_base()` into a shared composite action (e.g. `.github/actions/restore-trusted-ci-files`) — was raised and then explicitly refuted by an independent Codex pass in the same review: GitHub Actions resolves `uses: ./.github/actions/...` from the current checkout, which for a same-repo `pull_request` trigger is the PR's own potentially-tampered content. Wrapping `restore_from_base()` in a composite action would just move the untrusted-content problem one level down, since that new action file itself would need trusting before it could safely run — the inline-bash approach exists specifically to avoid that circularity. That refutation was independently verified and is agreed with.

**This issue is deliberately not prescribing a fix.** A trust-boundary-safe de-duplication approach — for example, a single script file restored via the same Contents-API mechanism used today and then `source`d by each job, though that itself needs its own trust analysis — has not been designed yet. Whoever picks this up should design and validate the approach against the same trust boundary before implementing it, not default to the already-refuted composite-action extraction.

Related to PR #289 (`feat/ci-pipeline-foundation`) for context — the duplication was introduced there, but fixing it is not planned as part of that PR.
