## Summary
merge-pr: same-name required checks grouped by workflow display name can be masked

## Environment
- **Product/Service**: git-kit `merge-pr`, step 2 "Status checks" (`plugins/git-kit/skills/merge-pr/SKILL.md`)
- **Region/Version**: branch `fix/merge-pr-readiness-and-ci-reruns`

## Reproduction Steps
1. A required context is reported by a real workflow, and that run fails.
2. A pull request adds a second workflow with the same `name:` and a job with the same name that passes,
   started later.
3. merge-pr step 2 groups same-name `statusCheckRollup` entries by the CheckRun's `workflowName` and
   takes the latest `startedAt` in each group.

## Expected Behavior
Each real source of a required context must pass. A second source with the same display name never hides
a failing one.

## Actual Behavior
Both entries land in one group, because `workflowName` is a display name. The later, passing entry wins,
so the failing required check reads as passing.

## Error Details
~~~
None: a security-review finding (m-A1), not a runtime error.
~~~

## Visual Evidence
None.

## Impact
**Medium** - weakens a merge gate. It needs same-repository write access, and GitHub's own ruleset
enforcement still applies unless the merging user may bypass the ruleset.

## Additional Context
A fix was tried and reverted. It split a group by the run id parsed from each entry's `detailsUrl`, then
looked up the run's workflow file. A security review found two problems with it:
- **M2:** `detailsUrl` is set by whoever creates the check run through the Checks API. A spoofed entry can
  name an older successful run of the real workflow, join the real group and still mask the failure.
- **M1:** the lookup needed a `gh api -X GET repos/*/actions/runs/*` grant. That prefix also matches the
  rerun, cancel, delete and approve endpoints, and a later `-X` flag likely overrides the method.

Proposed fix: bind each entry to data the server sets, not to `detailsUrl`. Use the check suite's app
slug, the workflow run id and the workflow id, through GraphQL `CheckRun.checkSuite` or a REST join of
check runs to workflow runs. Then require the expected app. If the lookup needs a grant, prefer the
read-only `gh run view <id> --json workflowDatabaseId` (the field exists, checked live).

Informational: a later run of the same workflow file under a different event can report the job as
`SKIPPED`, which counts as passing and is the newest entry in its group. That hides an earlier failure.
