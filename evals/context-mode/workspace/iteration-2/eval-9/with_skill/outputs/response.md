Route: Skill(merge-pr) for PR #902, never a raw `gh pr merge`; confirmation through AskUserQuestion; afterwards Skill(finishing-work).

## What's shipping
PR #902, approved, merged into `main` (public repo, visible immediately).

## Destination
PR merge -> `main`, via `merge-pr`.

## Pre-ship checks: ran / not run
- Required status checks: ran, all green.
- Review: approved, no outstanding change requests.
- Secretlint (`Security` workflow, PR's changed files): ran, passed. It is not a required check, so I'm stating it here.
- External-reference check: not run and not needed. The diff adds no names of outside companies, products or repositories.
- QA pipeline / inventory sync: not run. This is a PR merge, not a plugin or marketplace publish.
- Merge rights / draft state: `merge-pr` checks these again just before merging.

## Confirmation
Merge PR #902 into `main` now? (Merge PR #902 / Hold)
