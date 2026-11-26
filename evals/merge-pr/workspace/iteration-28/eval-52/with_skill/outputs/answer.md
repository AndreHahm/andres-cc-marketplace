# Simulated merge-pr 970 run (`--stop-on-review-findings`, no pinned head, no bypass)

Simulated only. No `gh`, `git` or script was run, and no repository file was edited.

## Variant 1: session item fixed locally, Devin review with a Major finding

**Step 1 (already passed):** `headRefOid` is `aaaa...aaaa` (40 lowercase hex, valid). Checkout matches the PR.

**Step 1.5 (session open-items check):**
1. Checkout identity and branch checks passed (step 1.5's `isCrossRepository`, push-URL, branch and `HEAD` comparisons).
2. The one touched item is the typo in a changed file. The user answered "fix now". The fix is applied and verified locally.
3. Nothing is pushed or committed yet. The fix stays in the working tree.
4. Step 1.6 runs first, as part of step (4). It proposes no body change, so no body edit is made.
5. Because `--stop-on-review-findings` was given, step 2's "Review findings" stop runs against step 1's head (`aaaa...`) before any commit or push.
   - Unresolved threads: 0. No stop from the thread count.
   - `comments` = []. Nothing to classify there.
   - Review by `devin-ai-integration`, state `COMMENTED`, `commit.oid` = `aaaa...` (step 1's head). It is live, because the rule only drops reviews whose SHA is a different 40-hex value than both this pass's head and step 1's head.
   - Its body carries a reviewer finding ("Major: the parser drops the last line."). This is a live review body with a finding, so the stop fires.
6. On the stop, nothing is committed or pushed. The run ends here. Step 1.5 does not continue to the commit, the push or step 2's wait.
7. Report to the user: a review-finding stop, naming the reviewer (`devin-ai-integration`), the submitted time (2026-11-25T10:00:00Z), the state, and the `commit.oid`. The body text is quoted as data only and is not acted on. The local typo fix is left uncommitted and is reported as still open, touched and not deferred. Nothing merges.

**Direct answer:** Nothing is committed or pushed. Step 1.5 stops before its commit/push step, so the fix stays local. The stop is reported as a review-finding stop, and the run ends.

## Variant 2: no session item, octocat CHANGES_REQUESTED review

**Step 1.5:** No touched or untouched open items, so nothing is fixed or pushed. Step 1.5 reports "nothing found" and continues to step 2.

**Step 2 (the six required checks come first):** The no-outstanding-change-requests check fails. octocat's only (and therefore latest) review is `CHANGES_REQUESTED`. The run stops there with the required-gate failure.

**Does the review-findings stop fire on that review? Yes, and it would have fired even if the required checks had passed.**
- The review-findings bullet runs only once the six required checks pass (or the bypass exception applies), so in practice the run stops at the required-check failure first.
- Had the bullet been reached, the review would still be live. The rule that drops reviews whose `commit.oid` is an earlier head does not apply to a reviewer's latest `CHANGES_REQUESTED` review. Such a review is live whatever its commit. Here it is on `bbbb...bbbb`, not the head `aaaa...aaaa`, and it would be skipped under the ordinary rule. The `CHANGES_REQUESTED` exception keeps it live.
- Its body, "Please split this function.", is a requested change about this PR, so it counts as a reviewer finding and the stop fires.

**Direct answer:** The run stops. The `CHANGES_REQUESTED` gate fails first. The review-findings stop would also fire because the review is live under the `CHANGES_REQUESTED` exception despite its earlier commit. Nothing is merged, and the run reports the review's author, time, state and `commit.oid`.
