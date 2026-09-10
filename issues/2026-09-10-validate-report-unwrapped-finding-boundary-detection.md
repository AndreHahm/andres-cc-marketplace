## Summary
`validate_report.py`'s evidence-metadata check cannot detect a substantive finding that was never wrapped in `<!-- finding:start -->`/`<!-- finding:end -->` markers AND never had any metadata fields attempted at all — even though each report-producing skill's own finding format (a SWOT quadrant row, a candidate-pattern entry) actually provides a usable per-skill boundary that could catch this case.

## Environment
- **Product/Service**: `analysis-kit` plugin, `scripts/validate_report.py`
- **Region/Version**: `plugins/analysis-kit/scripts/validate_report.py`, as of PR #302

## Reproduction Steps
1. Write a report with one fully-annotated `<!-- finding:start -->`/`<!-- finding:end -->` block.
2. Add a second, completely unwrapped finding with no markers and no metadata fields at all (e.g. `[S02] a completely unwrapped finding with no markers at all`).
3. Run `validate_report.py` against it.

## Expected Behavior
Per the report-evidence-convention, every substantive finding needs its own metadata block. A second finding with none at all arguably should be caught.

## Actual Behavior
`check_evidence_metadata` returns `valid: true` — this exact case is a documented, pinned-by-test, structural-only limitation (`plugins/analysis-kit/tests/test_validate_report.py::test_unwrapped_finding_with_no_metadata_attempt_is_a_documented_residual_gap`, and the module's own docstring: "Structural checks only -- this never attempts to judge whether a finding's content is actually correct"). The validator has no knowledge of any individual skill's own finding format (a SWOT row's `### SWOT: <name>` heading, a suggestion entry's `[S##]` prefix, etc.), so it can't currently tell a genuine unwrapped finding apart from ordinary prose.

## Error Details
~~~
N/A -- not an error, a documented scope gap in check_evidence_metadata (plugins/analysis-kit/scripts/validate_report.py)
~~~

## Impact
Major (per reviewer's own label; this is a real coverage gap in a mechanical validator meant to catch exactly this class of mistake, but it requires teaching the validator each individual skill's own finding-format boundaries -- a genuine architecture change, not a small patch). Not a regression from this PR's own fixes -- it is a pre-existing, already-documented-and-accepted design boundary that a review finding has now proposed narrowing.

## Additional Context
This was raised as part of a larger review comment that also flagged a real, small, independently-confirmed bug (the stray-label check using a truthy test instead of `is not None`, so a blank-valued stray label was silently missed) -- that smaller part was already fixed and verified in PR #302 itself (commit adding `is not None` to the `stray_labels` list-comprehension in `check_evidence_metadata`). This issue tracks only the remaining, larger suggestion: using each validator caller's (i.e. each report-producing skill's) own finding-format boundary to detect an unwrapped finding with zero metadata attempt.

Any fix here needs to:
- Decide whether `validate_report.py` should gain per-skill format knowledge at all (a deliberate expansion of its current "structural checks only" scope, stated explicitly in its own module docstring) or whether this is better solved a different way (e.g. each skill's own Testing & Validation checklist gets a sharper prose reminder instead of a mechanical check).
- If per-skill format awareness is added, design how `report-contracts.json` would declare each skill's own finding-boundary pattern without hardcoding skill-specific regexes into the shared validator.
- Update `test_unwrapped_finding_with_no_metadata_attempt_is_a_documented_residual_gap` (and its own comment, and the module docstring) once the gap is actually closed -- that test currently pins the OLD, accepted behavior and will need to flip to asserting the NEW detection instead.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/302
- **Head SHA finding was raised against**: `341bcc7f2155c5675dece683e24556922135ac33`
- **Review thread/comment**: https://github.com/AndreHahm/andres-cc-marketplace/pull/302#discussion_r3979114425 (comment id `3979114425`)
- **Reviewer**: `coderabbitai[bot]`
- **Stated severity**: Major (CodeRabbit's own label: "🟠 Major", tagged "🏗️ Heavy lift")
