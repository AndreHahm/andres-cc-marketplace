# Codacy findings for example-org/example-repo PR #7

Source: `plugins/quality-kit/skills/collecting-analysis-findings/scripts/fixtures/pr.json` (saved Cloud CLI output; no live `codacy` call made).

PR: "example" (`feature/x` -> `main`), status Open.
Head commit: `2222222222222222222222222222222222222222`, which matches the head GitHub reports, so the fixture is current for this head.

Summary: 3 new issues, 0 fixed. `isUpToStandards` is false. No potential issues and no per-file entries.

## New issues (3)

| # | File | Line | Tool | Rule | Category | Severity | Message | Issue ID |
|---|------|------|------|------|----------|----------|---------|----------|
| 1 | scripts/tool.py | 10 | Bandit | Bandit_B603 | Security | Warning | subprocess call (B603) | aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa |
| 2 | scripts/tool.py | 20 | Bandit | Bandit_B603 | Security | Warning | subprocess call (B603) | bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb |
| 3 | scripts/tool.py | 30 | Lizard | Lizard_ccn-medium | Complexity | Warning | main has 20 cyclomatic complexity | cccccccccccccccccccccccccccccccc |

All three are `deltaType: Added` and were introduced in commit `1111111111111111111111111111111111111111` (dev@example.invalid, Dev, 2026-01-01T00:00:00Z).

## Notes

- The fixture's `lineText` is `x = 1` for all three issues, which does not match the code the findings point at. This may be a placeholder in the saved fixture, so I did not rely on it.
- The two Bandit B603 findings share a rule and file. They are separate issues on different lines, so they should be counted as two.
