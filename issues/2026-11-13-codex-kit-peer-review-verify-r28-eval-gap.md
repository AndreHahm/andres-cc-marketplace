## Summary
codex-peer-review and codex-verify each have 1 eval scenario, below plugin-rulebook R28's minimum of 3, and neither covers the routing distinction added in PR #726.

## Environment
- **Product/Service**: codex-kit `codex-peer-review` and `codex-verify`; `evals/codex-peer-review/evals.json`, `evals/codex-verify/evals.json`
- **Region/Version**: found in PR #726 at head `17f785738fb9bb40b549b2cdf03db3f323c58f2a`

## Reproduction Steps
1. Count the scenarios in `evals/codex-peer-review/evals.json` and `evals/codex-verify/evals.json` (1 each).
2. Compare with plugin-rulebook R28's `min_eval_scenarios` (3).
3. Note the routing PR #726 added: codex-peer-review's "When NOT to Use" route for one critical, security-relevant or uncertain action Claude is about to execute (line 46), and codex-verify's split between a user-requested plan-step verification and Claude's own unrequested check (line 54).

## Expected Behavior
Each skill has at least 3 eval scenarios with run evidence, including one that exercises the new routing distinction.

## Actual Behavior
One scenario each, covering neither routing distinction. The routing was checked in PR #726 only by `evals/consulting-decision-model/routing-evals.json`, from the consulting-decision-model side.

## Error Details
~~~
CI Codex delta review, run 43492881351 (PR #726):
- plugin-rulebook-checker, Minor, plugin-rulebook/R28, plugins/codex-kit/skills/codex-peer-review/SKILL.md:46 (notice)
- plugin-rulebook-checker, Minor, plugin-rulebook/R28, plugins/codex-kit/skills/codex-verify/SKILL.md:54 (notice)
~~~

## Visual Evidence
N/A

## Impact
Low: a test-coverage gap that predates PR #726. No behavior is wrong; the new routing has no eval from these two skills' own side.

## Additional Context
- Found in PR #726, during round 2 of its review; deferred to this issue at the PR author's direction.
- Thread/finding: CI run https://github.com/AndreHahm/andres-cc-marketplace/actions/runs/43492881351 (no inline thread).
- Reviewer: marketplace CI Codex delta review (plugin-rulebook-checker).
- Severity: Minor (non-blocking notice).
- Related: #695 (the same R28 gap for two context-kit skills).
- Suggested fix: add two routing scenarios per skill (one routed here, one routed to consulting-decision-model or codex-verify respectively) and run them with skill-tester, recording the run evidence.
