# Codacy findings: example-org/example-repo PR #7

**Currency: CURRENT.** The record's head commit (`2222222222222222222222222222222222222222`) matches the PR head GitHub reports in the request. The analysis is not running (`is_analysing: false`). The PR is Open. These counts describe the current head.

Note: the PR head came from the request text. No `gh` command was run, as the sandbox rules require, so the currency check compares against that stated value and not a live read.

## Counts

Total: 3 findings. Each rule's count below is per file; all three findings are in `scripts/tool.py`.

| Rule | File | Count | Category |
|---|---|---|---|
| Bandit_B603 | scripts/tool.py | 2 | Security |
| Lizard_ccn-medium | scripts/tool.py | 1 | Complexity |

By category: Security 2, Complexity 1.

Findings (all state `new`, delta `Added`, not ignored):
- Bandit_B603 (Warning) at line 10 and line 20: "subprocess call (B603)"
- Lizard_ccn-medium (Warning) at line 30: "main has 20 cyclomatic complexity"

The two Bandit findings are one rule, so there is one rule to act on, not two.

## Record file

`<repo>/evals/collecting-analysis-findings/workspace/iteration-2/eval-1/with_skill/outputs/findings-record.json`

Produced by `collect_codacy.py --kind pr --input <fixtures/pr.json> --format json`, exit 0. Input was the saved fixture, not a live Cloud CLI call.
