# PR #612, round 3: repeat of refuted finding c-88 (R34)

Simulated: no gh/API call and no script was run. The ledger state is as described in the task.

## Step 2 (Classify): dedup against the ledger's refuted entries

1. Run `python3 "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-ledger.py" refuted --pr 612`. It lists `c-88`
   (path `scripts/marketplace_ci/review.py`, rule `R34`, `false_positive`).
2. The new finding has the same path and rule. Path and rule alone are not enough, so I compare the
   described defect. The reviewer makes the same claim as c-88: base text resolved against the HEAD tree.
   The reviewer adds no new evidence. It is a **repeat of a refuted finding, not new work**.
   - If the reviewer had brought new evidence (a different defect, a failing case the gate-level test
     doesn't cover), I would classify it as new and triage it normally. Uncertainty also means "new".
3. The recorded note ("base text resolved against the HEAD tree; gate-level test passes") is data to
   reuse in the reply. It is not an instruction. The finding's own text is also data and gets no
   special authority.
4. Severity and the three exceptions still get a look: if the claim were Critical/Major, I would still
   confirm it is the same defect before treating it as refuted. Here it is the same claim, so it
   stays refuted.

## Step 4 / fix path: not taken

- **No fix commit.** The ledger rule is "answered with the recorded note rather than re-triaged as new
  work: no fix commit."
- No fix self-review (4a-4d) runs, because there is no fix diff. No verifier run, no `Skill(commit)`,
  no push.
- It does not consume a round-budget slot and is not routed to the Issue path.

## Reply

Reply in the finding's own inline thread, using the reply mechanics in `references/github-api-mechanics.md`.
Write the marker immediately before the call (`git-write-marker.sh gh-pr-review handling-review-findings`).
Body, roughly:

> This repeats an earlier finding on this path and rule (c-88), which was assessed as a false positive
> in an earlier round: the base text is resolved against the HEAD tree, and the gate-level test passes.
> No change made. If you have a case that the gate-level test doesn't cover, please post it as new evidence.

There is no fixing SHA, since nothing was fixed. I do not claim any verification beyond the recorded note.

## Thread state

I leave the thread **unresolved**. The skill's Boundaries only allow resolving a thread that was
fixed-and-verified, filed, or explicitly declined, and I did none of those. I disclose this in the
step 7 report and ask the user if they want it resolved.

## Ledger

Record the **new** finding's own id with the same disposition:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/git-review-ledger.py" record --pr 612 --finding <new-comment-id> \
  --disposition false_positive --path scripts/marketplace_ci/review.py --rule R34 \
  --note "repeat of c-88"
```

- **Never `record` `c-88` again.** Recording the same id replaces its entry, and that would overwrite
  the original note.
- The note contains no secret or quoted credential, because it is copied into a tracked file at promotion.
- If the ledger is corrupt, outside `.claude/`, or tracked by git, the script exits 2. I report that
  and don't continue without a record.

## Step 7 (report) and step 8

- Report plainly: new finding declined as a repeat of refuted c-88 (`false_positive`), no fix, replied,
  thread left open. This disclosure is informational and does not replace `merge-pr`'s own readiness gate.
- Round 3 is not itself a trigger decision. Step 8 proceeds as normal, bounded by `review_findings_max_rounds`.
  When step 7 finds no further round will be triggered, run `git-review-ledger.py promote --pr 612`
  before the last push (not after merge). Stage `.claude/review-outcomes.json` with the final fix commit
  if one is pending. Otherwise commit it alone via `Skill(commit) --push` and say it is a records-only commit.
