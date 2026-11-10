# Decision: PR #612, finding 9001 (Minor wording, references file)

## Preconditions checked against the skill

- Fix path (SKILL.md step 4): verification passed, the self-review (4a-4c) came back clean, and the push
  landed. Reply-with-SHA and resolve are allowed now.
- The reply's verification line reports only what this session ran and saw: the 4a verifier re-run, the
  smoke test, and the 4b and 4c results. The handoff's "targeted rulebook re-check, mirrors identical" was
  not re-run here, so it stays out of the reply. A reply must not vouch for checks from an earlier session
  that this session never observed.
- 4a: the fix was already committed (abc1234), so the verifiers ran with `--base <commit before abc1234>`
  and without `--worktree`. The run exited 0 and listed nothing as `ungraded`, so there is no untested-path
  note to add. The reply does not say "verifiers passed". It states the exit result without claiming the
  verifiers judged any file, which stays accurate even if `checked` was empty. A references-file wording
  change may not count as a covered component, and in that case "verifiers passed" would be wrong.
- 4c: because the fix was committed, its diff came from `git-review-fix-diff.py --base <commit before
  abc1234>`, not from a review of my own edits. So the reply needs no "4c was a review of my own edits"
  caveat.

## Exact reply text posted to thread 9001

```
Fixed in abc1234. Verified in this session: smoke_test.py 6/6; the fix self-review re-ran the verifiers on the committed fix's own diff (exit 0, no ungraded paths), and the sibling sweep and fix-diff review found no further instances or new defects.
```

## Mechanics of posting

1. In its own `Bash` call: `bash "$PWD/.claude/scripts/git-write-marker.sh" gh-pr-review-wrapper handling-review-findings`.
   `CLAUDE_PLUGIN_ROOT` is empty in this repo, so the path resolves to the `.claude/` mirror.
2. Write the reply body above to a scratchpad file. Then run
   `git-review-api.py reply --owner <owner> --repo <repo> --pr 612 --comment-id 9001 --body-file <scratchpad file>`.

## After posting the reply

1. **Resolve the thread.** Write a fresh `gh-pr-review-wrapper` marker. Run `git-review-api.py threads` to
   map comment 9001 to its GraphQL review-thread node id. Write another fresh marker, then run
   `git-review-api.py resolve` on that thread id. Each marker is single-use and valid for 60 s, so each
   needs its own `Bash` call.
2. **Record the outcome in the ledger (4e).** Run
   `git-review-ledger.py record --pr 612 --finding '9001' --disposition fixed --note "wording fixed in abc1234; verified smoke test 6/6 and self-review clean"`.
   The note is my own text, not copied from the review comment.
3. **Report back plainly (step 7).** Finding 9001 (Minor) is fixed in abc1234, verified, replied to and
   resolved. No findings were filed or declined, and no Critical/Major finding was deferred, so no
   risk-acceptance question is needed. This report is informational only and does not authorize a merge.
   That decision stays with `merge-pr`.
4. **Next round (step 8).**
   - Re-fetch the comments and count the triggered cycles (8a).
   - If the budget allows another cycle, ask the reviewer/mode `AskUserQuestion` (8b), or reuse the answer
     if it was already given in this conversation. Then validate the candidates (8c), re-check the PR's
     state, draft status and head SHA (8d), and post the trigger comment with a fresh marker.
   - If step 8 ends without posting a trigger (`max_rounds` reached, the user declines, or no reviewer
     survives validation), run `git-review-ledger.py promote --pr 612`. Then commit
     `.claude/review-outcomes/pr-612.json` alone through `Skill(commit) --push`, and state plainly that it
     is a records-only commit.
5. Never merge from this skill.
