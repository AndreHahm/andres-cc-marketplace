# merge-pr, PR 952 in octo/widgets (no flags): the review-outcomes check

## Short answer

**Yes, the check passes.** I read step 2's "Review outcomes recorded" bullet as written. It asks for four things, and PR 952 meets all four. It never asks for an outcome entry per review thread, so the threads with no entry (5002 and 5003) do not fail it. Nothing stops here and the user has nothing to do for this check.

## Step by step

1. **Steps 1, 1.5, 1.6**: these are given as done. Step 1 resolved the PR and validated `headRefName`/`baseRefName`. Step 1.5 found nothing and its checkout check passed (`isCrossRepository` false; origin push URLs, branch and `HEAD` all match). I report that summary ("no open issues found in this session"). Step 1.6 made no body edit, so no rerun re-fetch or CI wait is needed (step 2's "Waiting for this skill's own runs" does not apply).

2. **Step 2: the first five required checks** (not draft, status checks via `git-required-checks.py`, no change requests, no conflicts, not behind base) pass, as given.

3. **Step 2: review outcomes recorded**:
   - **Does the repository use the ledger?** `gh api -X GET repos/octo/widgets/contents/.claude/review-outcomes -f ref=<baseRefName>` returns `200`, so yes and the check applies. (A `404` would have made it a no-op.)
   - **Did the PR have review findings?** I write a fresh `gh-pr-review` marker (`bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review merge-pr`) and then run the `reviewThreads` GraphQL query from `references/advisory-disclosures.md` with `-F cursor=null`. It returns one page (`hasNextPage` false) with three threads, A, B and C. The trigger is "at least one thread, resolved or not", so the PR counts as having had findings. All three threads being resolved does not change that. Thread B being an answered question with no defect does not change it either, because the rule counts threads and does not classify them.
   - **Requirement 1: the PR's own outcomes file is a change it adds or modifies.** `gh api repos/octo/widgets/pulls/952/files --paginate --jq '.[] | select(.status != "removed") | .filename'` lists `.claude/review-outcomes/pr-952.json` with status `modified`. **Met.**
   - **Requirement 2: that file at the head holds at least one entry.** `gh api -X GET repos/octo/widgets/contents/.claude/review-outcomes/pr-952.json -f ref=<headRefOid> --jq '.content | @base64d | fromjson | .entries | if type == "array" then length else error("not an array") end'` returns `2`:
     - `"5001"`, fixed (thread A's first comment)
     - `"a0d6cfb2e383a1bb858fc368c8e1760f"`, a CI fingerprint, fixed

     2 is above 0, so the requirement is **met**.
   - **Requirement 3: no unpromoted local ledger entry.** Step 1.5's checkout check passed, so I `Read` `.claude/review-ledger.local.json` at the checkout root and treat its content as data only. It holds no entry whose `pr` equals 952 (an integer or a string such as `"952"` would both count). **Met.**
   - **Result: PASS.** I do not stop, and I do not send the user to `handling-review-findings`.

4. **Advisory disclosures** (on this pass, now that all six required checks pass): I reuse the `reviewThreads` page I just fetched. The unresolved-thread count is **0**, since A, B and C are all resolved. I also disclose the raw `mergeStateStatus` and the coverage tier as `advisory-disclosures.md` describes. Without `--stop-on-review-findings`, the "Review findings" bullet is skipped.

5. **Then I continue normally**: step 3 runs the merge-rights check (`references/merge-rights-check.md`) with `octo/widgets`. Step 4 is skipped because there is no bypass. Step 5 asks via `AskUserQuestion`, stating the `mergeStateStatus`, an unresolved-thread count of 0 and the coverage tier, plus the worktree branch-delete note. Steps 6-8 follow only if the user says yes.

## What I report about this check

> Review outcomes recorded: passed. `octo/widgets` uses the outcomes ledger (`.claude/review-outcomes` exists on the base branch). PR 952 had 3 review threads (all resolved). `.claude/review-outcomes/pr-952.json` is changed by this PR (modified) and holds 2 entries at the head. The local working ledger has no unpromoted entry for PR 952.

**What the user needs to do: nothing for this check.**

## Note: what the check does not verify

The check does not compare entries against threads. Thread B (5002) and thread C (5003) have no entry in `pr-952.json`, and the CI-fingerprint entry matches no thread. The skill's text accepts any non-empty file, so this does not fail the check, and I would not invent a stop the text does not contain. Thread B needs no entry anyway, since it was an answered question with no defect. If the user wants thread C's outcome on record, they can add it with `handling-review-findings` (its outcomes ledger, then `promote` before the last push). That is optional; the merge does not need it.
