# Codacy findings for example-org/example-repo PR 7

**Warning: the data is stale.** The saved Codacy output reports head commit `2222222222222222222222222222222222222222`. GitHub reports the PR's current head as `3333333333333333333333333333333333333333`. Codacy's analysis does not cover the current head. Treat these findings as possibly outdated. Re-run the Cloud CLI against the current head, or wait for Codacy to analyse it, before acting on them.

PR state in the saved data: Open, branch `feature/x` into `main`, `isAnalysing=false`, `isUpToStandards=false`, 3 new issues, 0 fixed.

| # | Issue ID | File:line | Pattern | Category | Severity | Tool | Message |
|---|----------|-----------|---------|----------|----------|------|---------|
| 1 | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa | scripts/tool.py:10 | Bandit_B603 | Security | Warning | Bandit | subprocess call (B603) |
| 2 | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb | scripts/tool.py:20 | Bandit_B603 | Security | Warning | Bandit | subprocess call (B603) |
| 3 | cccccccccccccccccccccccccccccccc | scripts/tool.py:30 | Lizard_ccn-medium | Complexity | Warning | Lizard | main has 20 cyclomatic complexity |

All three are `Added` and were introduced by commit `1111111111111111111111111111111111111111`. `potentialIssues` is empty.

Note: the `lineText` in the fixture is a placeholder (`x = 1`) for every finding, so it says nothing about the real code at those lines.
