# Codacy findings for example-org/example-repo PR #7

Source: saved Cloud CLI JSON (pr.json). No commands were run against Codacy or GitHub.

PR: #7 "example", Open, feature/x -> main. Analysis is not running (isAnalysing=false). Not up to standards. 3 new issues, 0 fixed.

Freshness: the analysed head commit in the JSON (headCommitSha) is 2222222222222222222222222222222222222222. This matches the head GitHub reports, so the data is current. The 1111... sha on each issue is the commit that introduced it, not the analysed commit.

| # | File:line | Pattern | Category | Severity | Tool | Message | Issue ID |
|---|-----------|---------|----------|----------|------|---------|----------|
| 1 | scripts/tool.py:10 | Bandit_B603 | Security | Warning | Bandit | subprocess call (B603) | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |
| 2 | scripts/tool.py:20 | Bandit_B603 | Security | Warning | Bandit | subprocess call (B603) | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb |
| 3 | scripts/tool.py:30 | Lizard_ccn-medium | Complexity | Warning | Lizard | main has 20 cyclomatic complexity | cccccccccccccccccccccccccccccccc |

All three are deltaType Added, introduced by commit 1111111... (Dev). potentialIssues is empty. The "lineText" in the fixture is a placeholder ("x = 1"), so do not rely on it.

Note: findings 1 and 2 are the same rule (B603) on two lines. Per repo guidance, check that a code change actually lowers Codacy's count before changing code for them.
