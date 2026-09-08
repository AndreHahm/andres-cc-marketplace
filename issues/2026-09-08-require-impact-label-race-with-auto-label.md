## Summary
`require-impact`'s label check can run and fail before `pr-auto-label.yml`'s size-derived impact label has actually been added, since the two are separate `pull_request_target`-triggered workflows with no ordering guarantee on the same event

## Environment
- **Product/Service**: `andres-cc-marketplace` repo tooling — `.github/workflows/pr-require-impact-label.yml` (`require-impact` job) and `.github/workflows/pr-auto-label.yml` (`label` job)
- **Region/Version**: N/A

## Reproduction Steps
1. Open a new, non-breaking PR via `gh pr create` (not converted from a draft).
2. Both `pr-require-impact-label.yml` and `pr-auto-label.yml` fire independently on the same `pull_request_target: opened` event.
3. `require-impact` fetches live labels via `github.rest.issues.get` and fails with "Missing impact label" if `pr-auto-label.yml`'s "Label PR by Conventional Commit title" step hasn't added the size-derived `i: minor change`/`i: major change` label yet.

## Expected Behavior
`require-impact` should not fail transiently for a PR that will have exactly one impact label moments later through the normal, expected auto-labeling flow.

## Actual Behavior
Observed live on PR #299: `require-impact` checked labels and failed at `2026-09-08T19:16:45.58Z`; `pr-auto-label.yml`'s `label` job added `i: major change` at `2026-09-08T19:16:47.63Z` — about 2 seconds later. `require-impact`'s own code comment ("Fetch live labels to avoid stale payload when labeled/unlabeled events fire concurrently with the autofix workflow") shows the author was aware of a race with `pr-impact-autofix.yml` (which only manages the breaking-change label), but not with `pr-auto-label.yml`, which is the workflow that actually applies the size-derived major/minor label on `opened`. Re-running the `require-impact` job after the label landed made it pass, confirming the check itself is correct — it's a pure timing race, not a logic bug.

## Impact
**Low** — always self-resolves via a manual re-run once the label lands, and doesn't block merging (assuming the required check is re-run or configured to be less strict about the first attempt). Still real friction: every non-breaking PR opened via `gh pr create` (not through the draft→ready path) risks hitting this exact race and needing a manual re-run.

## Additional Context
Candidate fixes to consider (not yet designed in detail):
- Add a short retry/poll loop inside `require-impact` before failing (e.g. wait a few seconds and re-check labels once) to absorb the expected propagation delay.
- Have `require-impact` also trigger on a slight delay, or gate on `pr-auto-label.yml`'s completion somehow (cross-workflow ordering is not natively supported by GitHub Actions `needs:`, so this would need `workflow_run` chaining or similar).
- Reconsider whether `require-impact` needs to run on `opened` at all, given `pr-auto-label.yml` already runs on that same event and is the one actually responsible for setting the label there.

Found live while creating PR #299 (branch `fix/secretlintignore-audit`, closing #295).
