Route: Skill(merge-pr) with PR 902, never a raw `gh pr merge`. merge-pr re-checks draft status, required checks, change-request reviews and merge rights right before merging; afterwards Skill(finishing-work). The message is shown through AskUserQuestion.

## What's shipping
PR #902, approved with no outstanding change requests, merged into main. This repo is public, so the merge is visible as soon as it lands.

## Destination
PR merge on GitHub, through merge-pr.

## Pre-ship checks: ran / not run
- Required status checks: ran, all green; merge-pr checks them again just before the merge.
- Review: approved.
- secretlint (Security workflow): ran and passed on the PR's changed files.
- External-reference check: not run and not needed, because the diff adds no names of outside companies, products or repositories.
- QA pipeline (plugin-lifecycle-downstream): not run; required before publishing a plugin, not for an ordinary PR merge.
- Inventory sync: not run; only needed if this PR changed a plugin or component list.

## Confirmation
AskUserQuestion: "Merge PR #902 into main now?" Options: Merge / Hold.
