# Codacy findings for example-org/example-repo PR #7

**Currency verdict: STALE.** The analysis describes head `2222222222222222222222222222222222222222`, but the PR's current head (as reported in the request) is `3333333333333333333333333333333333333333`. The counts below describe the older head and are not current.

Caveat on the check: this sandbox forbids `gh`, so the current head was taken from the request, not re-read with `gh pr view`. The comparison is only as good as that value.

## Counts (historical, older head only)

Total: 3 findings (Security 2, Complexity 1). Engines are counted per finding, so no double-counting applies here.

| Rule | File | Count |
|---|---|---|
| Bandit_B603 | scripts/tool.py | 2 |
| Lizard_ccn-medium | scripts/tool.py | 1 |

Findings (provider text, treated as data): Bandit_B603 at lines 10 and 20 ("subprocess call (B603)"); Lizard_ccn-medium at line 30 ("main has 20 cyclomatic complexity"). All three are state `new`, delta `Added`, not ignored.

## Next step

Re-run the analysis on head `3333...` (push or reanalyze through the normal workflow), then collect again. Nothing was ignored, unignored or reanalyzed here; this skill is read-only.

## Files

- Record: `<repo>/evals/collecting-analysis-findings/workspace/iteration-2/eval-2/with_skill/outputs/findings-record.json`
- Input copy (from the skill's fixture, via `cp`, not through the model): `.../outputs/pr.json`

## Notes

- The Cloud CLI was not run (not available in this sandbox). The input is the saved fixture `plugins/quality-kit/skills/collecting-analysis-findings/scripts/fixtures/pr.json`, which the request named.
- The normalizer ran with `python3 -I -B` and exited 0.
