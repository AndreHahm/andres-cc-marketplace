## Summary
On a large PR the Claude delta review's security pass hits its 25-turn cap on every run, and since a failed run is never an anchor, every later push reviews the whole PR again and fails the same way

## Environment
- **Product/Service**: marketplace CI, `.github/workflows/claude-review-ci.yml`, `scripts/marketplace_ci/headless_review.py`, `scripts/marketplace_ci/claude_review.py`
- **Region/Version**: PR #822 (heads `f2db9f98`, `8786f3d0`, `0effbb13`, `f750f029`)

## Reproduction Steps
1. Open a PR that changes a Tier-1 path (so the security pass runs) and is large: PR #822 has 26 reviewed paths and a 220 KB `delta.diff`, including `scripts/marketplace_ci/review.py` (over 4,000 lines).
2. Mark it ready. The first Claude delta review has no anchor and reviews the whole PR.
3. Push a small fix and let the review run again.

## Expected Behavior
The security pass can finish a whole-PR review of a PR this size, or a later push is reviewed against the part already covered, so the check reaches `clean` or `findings` at some point.

## Actual Behavior
All four runs since the PR left draft ended `could_not_run` with "the security pass stopped early (error_max_turns)":

- **Turn cap:** `MAX_TURNS = {"general": 50, "security": 25}` (`headless_review.py:36`). The security pass is told to read the whole `delta.diff` first, and every partial read of a large file is a turn. On `8786f3d0` it stopped at 26 turns having spent $0.07 of its $1.00 budget, so the turn cap binds, not the cost cap. The general pass finished in 42 turns of 50.
- **No anchor after a failed run:** only a `clean` or `findings` run becomes an anchor (R3, `claude_review.py` `decide`), so each push after a failure has "Anchor: none (whole PR)" and the same overflowing scope. Nothing ends the loop short of a run that finishes.
- **Inline comments:** `publish` only POSTs new inline comments for the current run's unwaived Critical and Major findings; it never edits, replies to or resolves an earlier inline comment, and Minor findings are never inline. Only the summary comment is updated in place. This matches R6 ("inline Critical/Major findings, one updated summary comment"), so changing it is a requirements decision.

A third cause, that a pass reaching a cap discarded the other pass's finished findings, is fixed in PR #822: they are now recorded as `recorded_findings` and counted in the summary.

## Error Details
~~~
status=could_not_run verdict=None the security pass stopped early (error_max_turns)
{"pass":"security","outcome":"success","result":{"subtype":"error_max_turns","is_error":true,"num_turns":26,"total_cost_usd":0.069710595}}
~~~

## Visual Evidence
None.

## Impact
Medium. The check is advisory and never blocks a merge, but on a large Tier-1 PR it gives no review at all, every run, while still costing money each run (general and security passes together: $0.62 on `f2db9f98`, $0.34 on `8786f3d0`).

Options, each needing a decision:
1. Size the security pass's turn cap to the scope (or raise it toward the general pass's 50), or brief it with only the paths that need a security review instead of the whole delta.
2. Let a pass that finished count as an anchor for that pass (changes R3).
3. Edit or resolve earlier inline comments on a later run (changes R6).

## Additional Context
- Found in PR #822.
- PR: https://github.com/AndreHahm/andres-cc-marketplace/pull/822
- Runs: 44950194661, 44955018442, 44958101602, 44961479592
- Related: #808 (the Claude delta review redesign), #706.
