## Summary
A review finding that an open GitHub issue already tracks keeps coming back as new and blocking in the
Codex delta review, the local parity review and `cross-model-review`.

## Environment
- **Product/Service**: marketplace CI `Codex delta review`, the local CI-parity review
  (`plugins/git-kit/scripts/git-codex-parity-review.py`), git-kit's `cross-model-review`
- **Region/Version**: issue #808's implementation on PR #822 (heads `bd68b9bb` and `1a7d03ed`)

## Reproduction Steps
1. File an issue for a review finding and leave it open, deferring the fix (here #814: the
   accepted-findings briefing is scoped by rule and path).
2. Push to the PR again, with the PR body's `## Accepted Review Findings` section set to "None".
3. Run the parity review, or let CI run the Codex delta review.

## Expected Behavior
A finding that an open issue already tracks does not block the run again. It is recognized as tracked
(for example through a `deferred #<issue>` line, or because the reviewers are told about the open issue)
and is shown as tracked rather than new.

## Actual Behavior
The finding is reported as a new blocking Major on run after run, and each run has to be declined or
bypassed by hand. On PR #822 the #814 finding blocked local parity runs 1, 5 and 7. In run 7 (head
`1a7d03ed`) it was the only blocking finding: reviewer `plugin-rulebook-checker`, rule
`review-correctness`, `scripts/marketplace_ci/review.py:1722`, wrapper exit 1. `cross-model-review`
round 6 (head `bd68b9bb`) raised it again from both models in several batches.

The only mechanism that clears it today is a waiver line naming the exact rule, path and line
fingerprint. The repeats do not keep to one key: they are reworded, anchored to other lines
(`AGENTS.md:191`, `.github/claude-review/prompt.md:44`, `review.py:1722`) and filed under other rules, so
one waiver line does not cover the next repeat.

## Error Details
~~~
PARITY-WRAPPER-EXIT=1
[Major] plugin-rulebook-checker / review-correctness scripts/marketplace_ci/review.py:1722
~~~

## Visual Evidence
N/A

## Impact
**Medium** - Every repeat costs a manual decline or bypass and another review round. A workaround exists
(decline or bypass each time). Merge safety is not affected: the finding is real and already tracked.

## Additional Context
- Requested by the maintainer. Filed only; the fix is out of scope here.
- A `deferred #814` line in the PR body's `## Accepted Review Findings` section has not been tried. It
  would still name one rule, path and fingerprint, so it would not cover the reworded and re-anchored
  repeats described above.
- `cross-model-review` has no notion of a tracked issue at all: its local list is matched on the same
  key.
- Related: #814 (the finding that repeats), #808 (the accepted-findings design), #525 (blocking scoped to
  the PR's diff).
