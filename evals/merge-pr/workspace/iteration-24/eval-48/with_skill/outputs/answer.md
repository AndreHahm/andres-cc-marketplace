# merge-pr on octo/widgets#952 (no flags): the review-outcomes check

## Answer: the check does not pass

This is step 2's "Review outcomes recorded" check, which is required and blocking. It fails because threads B (5002) and C (5003) have no recorded outcome. The run stops at step 2. Step 3 (merge rights) never runs, and nothing is merged.

## Step by step

1. **Steps 1, 1.5 and 1.6.** The PR resolved and validated. Step 1.5 found nothing and its checkout check passed, so the local ledger part of this check applies. The PR body needed no edit and nothing was pushed, so this is the first pass and step 1's fetch is still current.
2. **Step 2, the other five checks.** Not draft, status checks, no change requests, no conflicts and not behind base all pass.
3. **Is the ledger in use?** `gh api -X GET repos/octo/widgets/contents/.claude/review-outcomes -f ref=<baseRefName>` returns `200`. The repository uses the outcomes ledger, so the check is not a no-op.
4. **Did the PR have review findings?** I would write a fresh `gh-pr-review` marker with `bash "${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review merge-pr` in its own Bash call. I would then run the `reviewThreads` GraphQL query from `references/advisory-disclosures.md` with `-F cursor=null`. It returns one page (`hasNextPage` false) with three threads.
   - The trigger counts resolved threads too, so the PR "had review findings".
   - Every thread has a first comment `databaseId`, so none stops the check as undetermined.
5. **Is the outcomes file part of the PR?** `.claude/review-outcomes/pr-952.json` is in the paginated changed-files list with status `modified`, not `removed`. This condition is met.
6. **What does the head's file record?** I read the file at `ref=<headRefOid>` with the skill's jq filter. It keeps entries with `pr` equal to 952 and a ledger disposition. Both entries qualify (`fixed`), so the recorded finding ids are `["5001", "a0d6cfb2e383a1bb858fc368c8e1760f"]`.
7. **Match each thread's first comment id, as a decimal string:**

| Thread | isResolved | First comment id | Recorded? |
|---|---|---|---|
| A | true | 5001 | yes, matched (`fixed`) |
| B | true | 5002 | **no, missing** |
| C | true | 5003 | **no, missing** |

   - The CI fingerprint entry `a0d6cfb2e383a1bb858fc368c8e1760f` is allowed, but it covers no thread. One entry never covers several threads.
   - Thread B holds no defect (a reviewer's question that was answered). That does not exempt it: a thread with no finding must still be recorded, as `ignored`.
   - Being resolved does not exempt a thread either. Every thread, resolved or not, needs its own disposition.
8. **Local ledger.** `.claude/review-ledger.local.json`, read with `Read`, has no entry with `pr` 952. That condition is met, but it cannot rescue the missing entries.
9. **Result.** Two threads lack an entry, so the check fails and the run stops here.
   - The advisory disclosures (merge-state, unresolved-thread count, coverage tier) only run once all six required checks pass, so they are not reached.
   - Steps 3 to 8 do not run: no merge-rights check, no confirmation prompt, no merge marker, no `gh pr merge`.

## What I report

> **Not ready to merge: the review-outcomes check failed** (step 2, required).
> `.claude/review-outcomes` exists on the base branch, so this repository uses the outcomes ledger. PR #952 has 3 review threads, and every thread, resolved or not, needs its own recorded disposition in `.claude/review-outcomes/pr-952.json` at the PR head.
> - Thread, first comment id **5001**: recorded (`fixed`)
> - Thread, first comment id **5002**: **missing**
> - Thread, first comment id **5003**: **missing**
>
> Two things are fine: `pr-952.json` is among the PR's changed files (modified), and the local ledger holds no unpromoted entry for PR 952. The CI-fingerprint entry `a0d6cfb2e383a1bb858fc368c8e1760f` is allowed but covers no thread.
> Threads 5002 and 5003 have no recorded outcome. Either they were not recorded, or they were not promoted. I stopped before the merge-rights check, and nothing was merged.
> This check confirms that an outcome was recorded for each thread, not that the outcome is true or approved. The file is PR-head content that anyone who can push to the branch can write.

## What the user needs to do

1. Record the two missing outcomes with `handling-review-findings`, through its fix self-review's outcomes ledger:
   - **5002** (thread B, the answered question with no defect): record it as `ignored`.
   - **5003** (thread C): record its real disposition (`accepted`, `fixed`, `declined`, `false_positive` or `ignored`).
   - Use each thread's current first comment id. If a thread's first comment was deleted, its id changes, and the thread is recorded again under the new id.
2. Run the ledger's `promote` before the last push, so the entries land in `.claude/review-outcomes/pr-952.json` and the local ledger is left with no entry for PR 952. Then commit and push through `Skill(commit)`.
3. Re-run `merge-pr` on PR 952. Step 2 re-checks everything against the new head, including waiting for CI on the new push.
