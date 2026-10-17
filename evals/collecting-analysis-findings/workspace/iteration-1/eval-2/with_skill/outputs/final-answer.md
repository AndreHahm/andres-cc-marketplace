# Codacy findings for example-org/example-repo PR 7

**Currency verdict: STALE.** Codacy analysed head `2222222222222222222222222222222222222222`, but GitHub reports the PR head is `3333333333333333333333333333333333333333` (`is_analysing` is false). These findings describe an older commit and are not current counts. Re-run or wait for Codacy's analysis of the new head before acting on them.

The record's `source.pull_request` is 7, which matches the request. The PR status is Open.

Findings on the analysed (older) head: 3 in total, all in `scripts/tool.py`.

| Rule | File | Count |
|---|---|---|
| Bandit_B603 | scripts/tool.py | 2 (lines 10 and 20) |
| Lizard_ccn-medium | scripts/tool.py | 1 (line 30) |

Both Bandit_B603 findings are Warning/Security. The Lizard finding is Warning/Complexity. None is ignored.

Record file: `findings-record.json` (table form: `findings-record.txt`), in the same outputs directory.
