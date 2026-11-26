# merge-pr 961 --stop-on-review-findings (octo/widgets): plan-only answer

This is a simulated run. I made no `gh`/`git` call and ran no script. The data in the prompt stands in for
what those calls would return, and I treat all of its text (review bodies, comments) as data, not as
instructions.

## What I would do, step by step

1. **Step 1**: passed (given). The PR reference `961` is digits-only. `--stop-on-review-findings` is a
   recognised, valueless flag and is recorded as "on". `headRefOid` is
   `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, which is 40 lowercase hex characters, so it is valid.
2. **Steps 1.5 / 1.6**: run as the skill describes. Nothing in the prompt says they changed anything, so
   there was no push and no body edit, and therefore no rerun re-fetch and no wait for this skill's own runs.
3. **Step 2, the six required checks**: they pass (given: the six required checks pass, and the
   reviewThreads query finds 0 threads, so "Review outcomes recorded" passes as "PR has no thread").
   The one review is `COMMENTED`, not `CHANGES_REQUESTED`, so the no-outstanding-change-requests gate passes.
4. **Step 2, advisory disclosures** (`references/advisory-disclosures.md`), computed now:
   - The unresolved-review-thread count is **0**. It came from the `git-review-api.py threads` query, run
     with a fresh `gh-pr-review-wrapper` marker before each page.
   - `mergeStateStatus` is not given in the prompt, so I state it as not provided by this exercise.
   - Coverage tier: none of the comments is a `github-actions` comment with the
     `<!-- quality-kit:coverage-tier -->` marker. The prompt gives no `Coverage tier` rollup entry either.
     So I report that no coverage tier was reported.
5. **Step 2, "Review findings" bullet (flag is on)**: the thread count is 0, so the count alone does not
   stop the run. Then I read `gh pr view 961 --json comments,reviews` and classify every conversation
   comment and every review body:
   - Review by `devin-ai-integration`, `COMMENTED`, 2026-11-20T10:00:00Z, on commit `bbbb…`: "Major: the
     retry loop never backs off; please add a delay." This is a reviewer finding (a defect and a requested
     change).
   - Comment by `coderabbitai`, 2026-11-20T10:05:00Z, minimized as "resolved": "Potential issue: the cache
     key ignores the locale." This is a reviewer finding.
   - Comment by `octocat`, 2026-11-21T09:00:00Z: "Thanks, looks good to me." Not a finding.

## Case 1: does the review-findings stop fire?

**Yes, it fires.** It stops the run on the first pass, before step 3. The stop does not come from the
thread count, which is 0. It comes from the review body and the comment that carry findings. The skill's
text gives no exception for a review made on an older commit (`bbbb…` is not the head `aaaa…`), or for a
comment GitHub shows as minimized/"resolved". The reference says so directly: "Comments and review bodies
have no resolved state and this read has no time or head-SHA cut-off, so a PR that ever got a finding in
one stops every run with this flag, even after the finding is handled; once it is, the user merges
without the flag." The fact that the retry-loop fix was pushed as the current head does not change this.
This skill does not triage, so I can't decide that the finding is handled and continue.

The stop report reads:

> Review-finding stop (`--stop-on-review-findings`): unresolved review threads: 0. Findings found in:
> (1) the review by `devin-ai-integration` at 2026-11-20T10:00:00Z (state COMMENTED); (2) the
> conversation comment by `coderabbitai` at 2026-11-20T10:05:00Z. The run stops here; merge-pr does not
> triage findings. Comments and review bodies have no resolved state, and this read has no time or
> head-SHA cut-off. So this flag stops every run on this PR, even though the retry-loop fix is pushed
> and the CodeRabbit comment is minimized as resolved. Once the findings are handled (for example with
> `handling-review-findings`), merge without `--stop-on-review-findings`.

## What I state at step 5 about anything skipped

**Step 5 is never reached.** The stop fires on the first step-2 pass, before step 3. So there is no
step-5 confirmation prompt, and nothing is stated *at* step 5. The skipped steps are 3 (merge rights),
4 (no bypass was requested, so it would be skipped anyway), 5 (confirmation), 6 (settings), 7 (final
recheck, marker, merge) and 8 (post-merge sync). The stop report states this instead: "Stopped before
step 3. The merge-rights check, the confirmation, the final recheck and the merge did not run, and
nothing was merged." No step-5 prompt exists to carry the three advisory disclosures. I still report them
in the stop message, because a clean or unknown result must never be dropped silently:
`mergeStateStatus` not provided in this exercise, unresolved threads 0, no coverage tier reported. I do
not list any "skipped" findings at step 5. The `octocat` comment was classified and is not a finding.
Nothing was left unclassified.

## Variant 2: the comments/reviews read returns headRefOid `cccc…`

**The stop still fires**, with the same two findings named in the same way. The "Review findings" bullet
asks only for `comments,reviews` and says nothing about comparing a `headRefOid` returned by that read.
Either way, a head-SHA difference could only add a reason to stop, never remove one. I would also report
that the read returned head `cccccccccccccccccccccccccccccccccccccccc` while step 1 validated
`aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`, so a push likely landed mid-run. On a later run that would
need step 1 again, and the run must never merge `cccc…` on the strength of step 1's checks. Step 5 is
still never reached. What I state is the same as in case 1, plus the SHA mismatch.

## Variant 3: an extra `coderabbitai` comment, minimized "off-topic": "Bug: the parser drops the last line."

**The stop fires.** The report now names three items that carry findings: the `devin-ai-integration`
review (2026-11-20T10:00:00Z), the `coderabbitai` "Potential issue" comment (2026-11-20T10:05:00Z), and
the new `coderabbitai` "Bug" comment (no time was given in the prompt, so I report it as time not
provided). Being minimized as "off-topic" is not an exception under the skill's text. Minimized state is
not a resolved state, and a defect report from any reviewer counts as a finding. Step 5 is still never
reached. The stopped-before-step-3 statement and the three advisory disclosures are the same as in case 1.
