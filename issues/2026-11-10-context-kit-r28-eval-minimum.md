## Summary
context-kit's `context-window-analysis` and `strategic-compact` skills have fewer eval scenarios than the R28 minimum of three.

## Environment
- **Product/Service**: plugins/context-kit (skills `context-window-analysis`, `strategic-compact`)
- **Region/Version**: main at 5a153456, found on PR #694 head 49fbd2c9
- **Browser/OS**: not relevant

## Reproduction Steps
1. Run the plugin-rulebook R28 check on `plugins/context-kit/skills/context-window-analysis/SKILL.md`.
2. Run the same check on `plugins/context-kit/skills/strategic-compact/SKILL.md`.
3. Count the scenarios in each skill's eval set against `config.min_eval_scenarios` (3).

## Expected Behavior
Each skill has at least three eval scenarios with run evidence, or a Testing & Validation section that justifies why full evals are not warranted.

## Actual Behavior
Both skills have two eval scenarios. `context-window-analysis` records only 2 of 5 declared scenarios as covered. `strategic-compact` explains that hook behavior is verified directly by its smoke test rather than by skill-tester evals; R28 still classes the under-count as advisory.

## Error Details
~~~
plugin-rulebook-checker R28 (Minor, notice, non-blocking)
plugins/context-kit/skills/context-window-analysis/SKILL.md:69
plugins/context-kit/skills/strategic-compact/SKILL.md:350
~~~

## Visual Evidence
None.

## Impact
Low. The finding is advisory and did not block the PR. The strategic-compact hooks are covered by a 55-check smoke test; the gap is eval coverage of the skills' guidance.

## Additional Context
- Found in PR #694: https://github.com/AndreHahm/andres-cc-marketplace/pull/694
- Head SHA: 49fbd2c9c18748b2e850cc2d88309ee895e40fca
- Reviewer: CI Codex delta review (plugin-rulebook-checker), severity Minor, gate "notice"
- Deferred rather than fixed in PR #694 by the user's decision, to keep that PR to one change; it is already size XL.
- Options: add a third scenario to each eval set, or extend each skill's justification so R28 is satisfied.
- Related: #690 (the noise fixes PR #694 refs).
