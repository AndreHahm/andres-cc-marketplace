## Summary
reviewer_eval: the A/B report counts one defect reported at several lines as disagreement and as several findings

## Environment
- **Product/Service**: `scripts/reviewer_eval/ab.py` (`_finding_key`, and `sets` in `_arm_summary`)
- **Region/Version**: `main` at `46fb706a`
- **Browser/OS**: any

## Reproduction Steps
1. Run `uv run python -m scripts.reviewer_eval.ab report reviewer-eval/ab/severity-policy-pr-579 --markdown` (records added by the PR for branch `test/reviewer-ab-pilot-labels`).
2. Look at `security-reviewer`, old arm.
3. Read the three runs' blocking findings in `old/run*.json`.

## Expected Behavior
A reader can tell "the runs found the same defect" from "the runs found different defects".

## Actual Behavior
- The key is the rule, path and exact line; agreement uses the path and line.
- All three old-arm runs of `security-reviewer` block on the same defect (the trust of `origin/HEAD` in `git-verify-fix-diff.py`), at lines 106, 100 and 157.
- The report says 1 of 3 runs agree and lists three findings.

## Error Details
~~~
None.
~~~

## Visual Evidence
None.

## Impact
**Medium** - agreement reads as instability when the runs found the same defect, and corpus labels miss findings whose line or rule differs. The workaround is reading the findings by hand.

## Additional Context
A blanket line tolerance would merge distinct defects that sit close together: in the other record, one rule at one line (`simple-commands.md:478`) already covers two different defects. Options to weigh:
- Match on the labelled known issue (`known_issue`) where a label exists, and keep the line otherwise.
- Report both figures, exact-line and per-known-issue, side by side.
- State the limit in `reviewer-eval/README.md` and leave the metric as is.

Found while reading the two comparison runs for #862.
