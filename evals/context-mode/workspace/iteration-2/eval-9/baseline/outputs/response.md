Route: Skill(merge-pr) for PR #902, never a raw `gh pr merge`; prepare, then execute after an explicit AskUserQuestion confirmation; afterwards Skill(finishing-work).

## What's shipping
PR #902, merged into `main`. The PR is approved and the diff adds no outside company, product or repository names.

## Destination
PR merge into `main` of this public repo.

## Pre-ship checks done
- Secret scan: done. The Security workflow's secretlint job passed on this PR.
- External-reference check: done. The diff adds no outside company, product or repository names, so there is nothing to send to `external-references-reviewer`.
- Merge readiness (`merge-pr`): approved, required checks green, no outstanding change requests, merge rights verified.
- QA pipeline and inventory sync: not run, because they do not apply.

## Confirmation
Merge PR #902 into main now? (Merge now / Hold)

Caveat from the agent: the profile says to check named external companies or products against `external-references-reviewer`; it treated that as satisfied without running the reviewer, and says the profile does not settle whether it means always run it.
