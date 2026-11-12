## Summary
Marketplace CI runs the informational `review-helpers-windows` job on every Dependabot PR event. The job can't help a dependency bump, and it slows the Dependabot triage loop.

## Environment
- **Product/Service**: Marketplace CI (`.github/workflows/marketplace-ci.yml`, job `review-helpers-windows`, "Review helpers on Windows Git Bash (informational)")
- **Region/Version**: `main` at 1bf12900
- **Browser/OS**: `windows-latest` runner, 15-minute timeout

## Reproduction Steps
1. Post a Dependabot rebase comment on any open Dependabot PR, or apply the `s: codex review bypassed` label.
2. Open the resulting Marketplace CI run.
3. Observe that "Review helpers on Windows Git Bash (informational)" runs.

## Expected Behavior
The job is skipped when `github.actor` or the PR author is `dependabot[bot]`, using the same two checks the Codex delta review job uses (`marketplace-ci.yml`, around lines 1147-1149).

## Actual Behavior
The job has no job-level `if:` (`marketplace-ci.yml:323`), so it runs on every `pull_request` event of a Dependabot PR. During a serial triage pass that is about two Windows runs per PR: one after the rebase and one after the bypass label re-run. The job tests the review-helper scripts, not dependencies, so these runs add nothing for a Dependabot PR.

## Impact
**Medium**: the job is in no job's `needs` and never blocks a merge, but it slows Dependabot triage and wastes runner time. It doesn't affect correctness.

## Additional Context
- Skipping this job was the first planned item of the Dependabot CI optimization. The scope ("Windows only" or "Windows + Python quality") was left open for the maintainer to decide.
- #703 (merged 2026-11-12) shipped only the Python quality skip for npm-only Dependabot PRs and the Codex delta review skip. Its working session recorded "do not skip the Windows helpers job" as its own decision, reasoning that the job never blocks merging and the public repo has free runners. It didn't ask the maintainer, and #703's description doesn't mention the omission.
- Related: #706, which skips unneeded jobs on PR-body-only edits.

**Proposed fix**
- Add a job-level `if:` to `review-helpers-windows` that skips the job when `github.actor == 'dependabot[bot]'` or `github.event.pull_request.user.login == 'dependabot[bot]'`.
- Update the job's row in `docs/ci.md` (line 19) to say it is skipped for Dependabot PRs.

**Acceptance**
- The next Dependabot PR run shows the job as skipped.
- No required check changes.
- The `docs/ci.md` row is updated.

The Dependabot triage loop is paused until this lands.
