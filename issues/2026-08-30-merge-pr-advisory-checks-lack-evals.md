## Summary

`merge-pr`'s two new advisory readiness disclosures (out-of-sync-with-base, unresolved-review-thread
count) have no `skill-tester` eval coverage — the existing 9 scenarios in `evals.json` all predate
them, and the pagination/accumulation/unknown-result-handling behavior these checks add is only
covered by `scripts/smoke_test.py`'s structural (text-presence) checks, not by a blind agent-based
eval that actually exercises the behavior.

## Environment

- **Product/Service**: `git-kit` plugin, `merge-pr` skill's `evals/merge-pr/evals.json`
- **Region/Version**: N/A
- **Browser/OS**: N/A

## Reproduction Steps

1. Read `evals/merge-pr/evals.json` — 9 scenarios, all covering pre-existing step 2/5/7 behavior
   (four-state CI classification, worktree branch-delete note, headRefName validation, rebase/squash
   logic).
2. Read `plugins/git-kit/skills/merge-pr/scripts/smoke_test.py` — `check_step2_out_of_sync_disclosure`
   and `check_step2_unresolved_threads_disclosure` only assert that specific phrases/substrings are
   present in SKILL.md's own text (e.g. `"hasNextPage" in step2`), not that an agent following the
   skill actually paginates correctly, accumulates the unresolved count correctly across pages, or
   reports "could not be determined" (rather than a false `0`) when a call fails.

## Expected Behavior

New eval scenarios (or an equivalent blind-comparison mechanism) exist that give an agent following
`merge-pr` a multi-page `reviewThreads` result (or a simulated compare-endpoint failure) and verify it
actually sums across pages correctly, and correctly reports an unknown/failed result rather than a
false `0`.

## Actual Behavior

No such coverage exists. The two new checks' correctness under pagination, accumulation, and failure
handling has only been verified by (a) direct SKILL.md text presence checks, and (b) one-shot live API
calls against real PRs during development — never a scenario where an agent following the skill's own
instructions is actually tested against multi-page or failure-mode input.

## Error Details

~~~
N/A -- a test-coverage gap, not a runtime error.
~~~

## Visual Evidence

N/A

## Impact

**Low** — the underlying `gh api` calls themselves were live-verified to work correctly during
development, and `smoke_test.py`'s structural checks do confirm the *documented* behavior includes
pagination/failure-handling language. The gap is specifically in *behavioral* eval coverage (does an
agent actually execute the documented behavior correctly when given multi-page/failure input), not in
whether the behavior is documented at all.

## Additional Context

Found by Devin's automated review of PR #245, flagging that "the new smoke checks only detect
phrases, leaving pagination, accumulation, and unknown-result behavior untested." Already disclosed as
a known, non-blocking limitation in PR #245's own body ("Open Items" section) before this issue was
filed — this issue exists to give it a trackable follow-up rather than letting it live only as a PR
description note. Authoring proper eval scenarios for this requires a real `skill-tester` Quick
Workflow or Full Pipeline run (LLM dispatch cost), which is why it wasn't done as part of PR #245
itself.

## Review Finding Source

- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/245
- **Head SHA at time of finding**: `36b4739a1d4d0b053a195367fbf3bb73b75939da`
- **Thread**: https://github.com/AndreHahm/andres-cc-marketplace/pull/245#discussion_r3888815544
- **Reviewer**: Devin (`devin-ai-integration[bot]`)
- **Stated severity**: informational/"analysis" kind (no explicit Critical/Major/Minor label given)
