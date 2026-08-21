## Summary
`handling-review-findings`'s Workflow step 3 requires classifying every finding as Critical/Major or Minor/nit to apply `review_findings_severity_gate` and the Hard Cap exception's merge-risk confirmation, but `references/round-and-dedup-rules.md` only defines severity as "the reviewer's own stated severity" (Codex P1/Critical badges, Devin's equivalent) -- with no fallback for a finding that carries no severity label at all, which is the common case for an ordinary human review comment.

## Environment
- **Product/Service**: `git-kit`'s `handling-review-findings` skill, `references/round-and-dedup-rules.md` (Hard Cap exception section), `SKILL.md` Workflow step 3
- **Region/Version**: this repo, PR #88, found during that PR's own review

## Reproduction Steps
1. A human reviewer leaves an ordinary PR review comment with no severity indicator at all -- e.g. "this looks wrong, please check the null case" -- unlike Codex's P1/P2 badges or Devin's own bug/severity tagging.
2. Workflow step 2 classifies the finding (round, dedup); step 3 must then decide whether it's Critical/Major (subject to the Hard Cap exception -- never silently deferred-and-merged) or Minor/nit (subject to the severity gate's decline path).
3. `references/round-and-dedup-rules.md`'s own definition -- "Severity here means the reviewer's own stated severity... a live re-read of the finding at classification time" -- gives no answer when the reviewer stated no severity at all.
4. The workflow has no documented default: it could guess Minor (risking a real Critical/Major finding silently bypassing the Hard Cap exception's merge-risk confirmation), guess Critical/Major (over-cautious, but safe), or stop and ask -- none of these is specified.

## Expected Behavior
The Workflow should specify a conservative default (e.g. treat an unlabeled finding as Major until a human confirms otherwise) or explicitly require asking the user to classify it, rather than leaving the classification undefined at the exact step that gates the Hard Cap's safety protection.

## Actual Behavior
No fallback is defined; the classification step is silently underspecified for this case.

## Error Details
~~~
N/A -- design gap, not a runtime error.
~~~

## Impact
**Major** -- an undefined severity classification at exactly the step that decides whether the Hard Cap exception's merge-risk confirmation applies risks a real Critical/Major finding (from a human reviewer who didn't use a severity badge) silently bypassing that protection if an implementation guesses "Minor" by default.

## Additional Context
Found by a live Codex review round on PR #88. Not fixed as part of PR #88 itself -- this PR is well past its own two-round fix cap at the point this was found, so per `handling-review-findings`'s own round-cap policy this routes to the Issue path rather than another in-session fix.

**Suggested fix** (not prescriptive): default an unlabeled finding to Major (the conservative choice -- triggers the Hard Cap exception's protections rather than risking a silent bypass) unless/until a human explicitly reclassifies it, and state this default explicitly in `references/round-and-dedup-rules.md`'s severity definition alongside the existing "reviewer's own stated severity" language.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/88
- **Head SHA at time of finding**: `b100f43cfe64b65961a3a3b9f65d3cc351d06d7a`
- **Thread/comment**: https://github.com/AndreHahm/andres-cc-marketplace/pull/88#discussion_r3833471814
- **Reviewer**: Codex (`chatgpt-codex-connector[bot]`)
- **Stated severity**: P2
