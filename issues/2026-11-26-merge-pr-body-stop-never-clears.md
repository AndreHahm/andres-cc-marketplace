# merge-pr: a review-body finding stops every later `--stop-on-review-findings` run, even after it is handled

## Summary
With `--stop-on-review-findings`, a reviewer finding in a conversation comment or a review body stops every later merge-pr run on that PR. It keeps stopping after the finding is handled, so the user has to merge without the flag.

## Environment
- **Product/Service**: git-kit `merge-pr`, the "Review findings" advisory bullet (`plugins/git-kit/skills/merge-pr/references/advisory-disclosures.md`; on `main` it is in `plugins/git-kit/skills/merge-pr/SKILL.md`, around lines 266-268)
- **Region/Version**: added in #732 (d9cff13c); moved unchanged into the reference file by PR #909

## Reproduction Steps
1. A reviewer leaves a finding in a PR conversation comment or a review body (not an inline thread).
2. The finding gets fixed and the fix is pushed.
3. Run `merge-pr --stop-on-review-findings` (directly, or through `triaging-dependabot-prs`).

## Expected Behavior
A finding that has been handled, or one tied to an earlier head, no longer stops the run. A new or still-open finding still does.

## Actual Behavior
Comments and review bodies have no resolved state, and the read has no time or head-SHA cut-off. Any finding ever posted in one stops every run that uses the flag. The skill text discloses this ("once it is, the user merges without the flag"). Dropping the flag also drops the stop for new findings.

## Error Details
~~~
skill-reviewer, Major, workflow-correctness: plugins/git-kit/skills/merge-pr/references/advisory-disclosures.md:123
fingerprint f29fca888eb82e5075def7b7a6a6973c
~~~

## Visual Evidence
None.

## Impact
Medium: the stop can never clear on a PR that ever got a body or comment finding. The only way out is to drop the flag, which loses its protection against new findings for that run.

## Additional Context
- Found in PR #909: https://github.com/AndreHahm/andres-cc-marketplace/pull/909
- Head SHA: 003300bddb6aec9294d28d8c6cf81428dd51e4c9
- Reviewer: CI Codex delta review (skill-reviewer), Marketplace CI run 45799263967. It was reported in the job log, with no inline thread.
- Severity: Major (blocking in CI). Deferred as out of PR #909's scope: that PR only moved the text.
- Suggested direction (from the reviewer): stop on body findings only when they are tied to the current head or still unresolved. Add a scenario where a handled finding from an earlier head does not block a later run but a new finding does.
