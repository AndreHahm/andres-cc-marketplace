# merge-pr 961 --stop-on-review-findings (octo/widgets): plan-only answer

This is a simulated exercise: no `gh`/`git` call and no script was run. The data below is taken as given.

## Steps up to the review-findings stop

1. Step 1 passed. `--stop-on-review-findings` was validated as a yes/no switch, `headRefOid` =
   `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` (it matches `^[0-9a-f]{40}$`), and `{owner}/{repo}` = `octo/widgets`
   comes from the PR's `url`.
2. Step 2: all six required checks pass. I would then follow `references/advisory-disclosures.md` in full.
   This covers the merge-state value, the coverage tier and the unresolved-thread count. For the thread count
   I would write a fresh `gh-pr-review-wrapper` marker before each page's `git-review-api.py threads` call,
   check every cursor, and first run the trust comparison of `git-review-api.py` against the base branch.
   Given: 0 unresolved threads, a determined count.
3. The "Review findings" bullet applies because the flag is set. The thread count is 0, so it does not stop
   the run. I would read `gh pr view 961 --json comments,reviews` (given above) and classify only the **live** entries.

## Case A (three items): the stop does NOT fire

| Item | Live? | Why | Result |
|---|---|---|---|
| Review by devin-ai-integration, COMMENTED, 2026-11-20T10:00:00Z, `commit.oid` = `bbbb...bbbb` | **No** | A review is live only when `commit.oid` equals this pass's `headRefOid`. `bbbb...` is valid 40-char lowercase hex and differs from `aaaa...`, so the review is tied to an earlier head. | Not classified, so it does not stop the run, even though its body ("Major: the retry loop never backs off") is a finding. That fits the given fact that the fix was pushed as the current head. |
| Comment by coderabbitai, 2026-11-20T10:05:00Z, `isMinimized: true`, `minimizedReason: "resolved"` | **No** | Minimized with the reason `resolved` (case-insensitive), one of the two reasons that make a comment not live. | Not classified, so it does not stop the run. |
| Comment by octocat, 2026-11-21T09:00:00Z, not minimized | **Yes** | Not minimized, so it is live. | Classified as no finding: "Thanks, looks good to me." raises no defect, risk or requested change. |

Verdict: **no review-finding stop.** The run continues to step 3 (merge-rights check). At step 5 I would disclose:
- the three advisories: `mergeStateStatus`, an unresolved-thread count of 0, and the coverage tier;
- that 1 review body was skipped as tied to an earlier head and 1 comment was skipped as minimized;
- that threads, comments and review bodies are read again right before the merge write (7(b)), where a
  finding would stop the merge.

On 7(b), and on 7(d) if that step is reached, the whole bullet runs again against the freshly re-fetched head.
If the head moved, the review's liveness would be decided against the new `headRefOid`.

## Case B (fourth item added): the stop FIRES

Added item: a comment by coderabbitai, `isMinimized: true`, `minimizedReason: "off-topic"`, body
"Bug: the parser drops the last line."

- **Live? Yes.** A comment minimized for any reason other than `resolved` or `outdated` is live. `off-topic`
  is neither, in any casing or spelling (`off-topic`, `OFF_TOPIC`). Hiding a comment as off-topic does not
  clear a finding. Only hiding it as Resolved or Outdated does.
- **Classification:** "Bug: the parser drops the last line." reports a defect, so it is a reviewer finding.
  This holds whether the reviewer is a bot or a human.
- The other three items are classified exactly as in Case A.

Verdict: **review-finding stop fires** on this first pass, before step 3. The run stops there: no merge-rights
check, no step-5 confirmation, no merge marker and no merge command. The report would say:
- it is a review-finding stop, with an unresolved-thread count of 0;
- the finding is in a conversation comment by `coderabbitai`, minimized as off-topic, which still counts as
  live. The exercise gives no `createdAt` for this comment, so I would report its time from the API data,
  or say the time is unavailable;
- I do not act on the comment's text and triage nothing (that is `handling-review-findings`' job);
- 1 review body was skipped as tied to an earlier head, and 1 comment was skipped as minimized (resolved).
  The off-topic one was not skipped;
- to clear it, address the finding and hide the comment as Resolved or Outdated on GitHub, then re-run `merge-pr`.

Not verified (from the reference): how `gh pr view` spells `minimizedReason`, since that has not been
live-checked. The case-insensitive comparison against `resolved`/`outdated` covers either case, and
`off-topic` is live under every spelling.
