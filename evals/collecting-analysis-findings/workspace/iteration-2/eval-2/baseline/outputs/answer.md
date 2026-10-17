# Codacy findings for example-org/example-repo PR #7

Source: `plugins/quality-kit/skills/collecting-analysis-findings/scripts/fixtures/pr.json` (saved Cloud CLI output; the CLI itself was not run).

**Warning: the fixture is stale.** Its `pullRequest.headCommitSha` is `2222222222222222222222222222222222222222`, but GitHub reports the current head as `3333333333333333333333333333333333333333`. The findings below describe the fixture's head (2222...), not the current head. Re-pull the PR analysis from the Cloud CLI before acting on them.

## Summary

- Status: Open, `feature/x` into `main`
- Analysing: no. Up to standards: no.
- New issues: 3. Fixed issues: 0.
- Potential issues: none. Files: none listed.

## New issues

| # | Tool | Rule | Category | Severity | File | Line | Message |
|---|------|------|----------|----------|------|------|---------|
| 1 | Bandit | Bandit_B603 | Security | Warning | scripts/tool.py | 10 | subprocess call (B603) |
| 2 | Bandit | Bandit_B603 | Security | Warning | scripts/tool.py | 20 | subprocess call (B603) |
| 3 | Lizard | Lizard_ccn-medium | Complexity | Warning | scripts/tool.py | 30 | main has 20 cyclomatic complexity |

All three have the same commit SHA `1111111111111111111111111111111111111111` (author Dev, dev@example.invalid), and `falsePositiveThreshold` 80.

Issue IDs: `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa` (#1), `bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb` (#2), `cccccccccccccccccccccccccccccccc` (#3).

Note: every issue's `lineText` is `x = 1`, which does not match the messages for lines 10, 20 and 30. The fixture may be synthetic or the snippet field may be unreliable, so check the actual lines before fixing.
