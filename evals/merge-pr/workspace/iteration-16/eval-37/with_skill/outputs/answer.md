# Eval 37: step 2 wait for this skill's own runs (PR 934, head 2222...)

Source: merge-pr SKILL.md, step 2, "Waiting for this skill's own runs" (lines 162-177).

End condition (both must hold):
(a) every required context whose latest pre-baseline entry is a CheckRun with a non-empty
    workflowName has a COMPLETED entry with startedAt strictly later than the baseline (10:00:00);
(b) on two consecutive polls, the script, run after each poll that meets (a), reports no context
    pending or missing.

Here `Unit tests` is a workflow-reported CheckRun (workflowName `CI`), so (a) applies to it.
`Codacy` has no workflowName, so only (b) applies to it.

## Poll 1: CONTINUE
Unit tests has only its old COMPLETED entry, started 09:50. That is not strictly later than
the 10:00:00 baseline, so (a) is not met. The script's "passing" output reflects the old run,
so it cannot count. The script is not run toward (b) because the poll did not meet (a).

## Poll 2: CONTINUE
The new Unit tests entry is IN_PROGRESS, so it is not COMPLETED and (a) is not met. The
script's "pending" output is not counted toward (b).

## Poll 3: CONTINUE
Unit tests is now COMPLETED, started 10:01, which is after the baseline, so (a) is met. The
script, run after this poll, reports Codacy missing, so (b) fails and the consecutive count
resets to zero. A missing context keeps the wait going; it is not treated as failing yet.

## Poll 4: CONTINUE
(a) still holds on the same rollup. The script reports everything passing, which is the first
clean consecutive poll (count = 1). Two consecutive clean polls are still needed.

## Poll 5: END OF WAIT
(a) holds and the script reports everything passing again. That is the second consecutive
clean poll (count = 2), so the wait ends here. Before using the result, confirm that this
poll's headRefOid is still 2222...; a different head stops the run and reports both SHAs.
(The eval brief does not state headRefOid for each poll, so this check is an assumption to verify.)

## After the wait ends
1. Classify from the last script output (poll 5): every required context passing. Do not
   reuse the poll-1 output.
2. Confirm headRefOid is still 2222... (the head this skill pushed). If not, stop and report both SHAs.
3. Re-run the rest of step 2 on the fresh re-fetch from the rerun: isDraft false, no
   CHANGES_REQUESTED in latest reviews, mergeable MERGEABLE (bounded poll if UNKNOWN), not
   behind base (compare API, or mergeStateStatus for a fork), and review outcomes recorded.
   The step-2 bypass exception is not in play.
4. Collect the advisory disclosures: mergeStateStatus and the unresolved-review-thread count
   (with pagination).
5. Step 3: merge-rights check (references/merge-rights-check.md).
6. Step 5: AskUserQuestion with the readiness summary and the advisory disclosures. Merge only
   on an explicit yes.
