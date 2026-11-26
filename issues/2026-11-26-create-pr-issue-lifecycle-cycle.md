## Summary
create-pr, github-issue-lifecycle and collaborating-on-a-pr form a gated three-skill call cycle that CI's dependency-reviewer blocks on

## Environment
- **Product/Service**: git-kit `create-pr`, `github-issue-lifecycle` and `collaborating-on-a-pr` skills; plugin-devkit `dependency-reviewer`, run by CI's `Codex delta review` job
- **Region/Version**: PR #925 head f81a0290
- **Browser/OS**: n/a

## Reproduction Steps
1. `create-pr`'s Pre-flight step 3.5 invokes `Skill(github-issue-lifecycle)` to file untouched session findings, telling it to skip its Workflow 1 Step 6 (PR linking).
2. `github-issue-lifecycle`'s create-an-issue workflow Step 6 invokes `Skill(collaborating-on-a-pr)` to link a PR to the new issue.
3. `collaborating-on-a-pr`'s Path A invokes `Skill(create-pr)`.
4. Change `create-pr`'s `allowed-tools` (or another line in the cycle) and open or update a PR; CI's dependency-reviewer reviews the diff.

## Expected Behavior
No call cycle runs through the three skills, so nothing depends on a skip instruction to keep them from nesting.

## Actual Behavior
The cycle exists in the component graph. `create-pr`'s skip instruction keeps it from nesting within one run, but dependency-reviewer reports it as a blocking Major (`dependency-graph`, medium confidence, gated-only cycle).

## Error Details
~~~
dependency-reviewer, Major, medium confidence: create-pr -> github-issue-lifecycle (Pre-flight step 3.5), github-issue-lifecycle -> collaborating-on-a-pr (create-an-issue Step 6), collaborating-on-a-pr -> create-pr (Path A). These calls are conditional and human-gated, so this is a gated-only cycle.
~~~

## Visual Evidence
n/a

## Impact
**Medium** - Not a runtime failure (each call is gated and step 3.5 passes the skip), but a PR that touches any of the three skills' call lines can be blocked until the finding is waived.

## Additional Context
It surfaced when PR #925 removed the direct `create-pr` and `collaborating-on-a-pr` loop. Options: have `github-issue-lifecycle`'s Step 6 tell the user to link the PR through `collaborating-on-a-pr` instead of dispatching it, or have `create-pr`'s step 3.5 file issues without dispatching `github-issue-lifecycle`.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/925
- **Head SHA**: f81a0290da0342b300f16ef15fa9290f915a0036
- **Finding**: CI `Codex delta review` result, `dependency-graph` on `plugins/git-kit/skills/create-pr/SKILL.md:9`, fingerprint 1399c60cf1713b518bd66515116b503d
- **Reviewer**: dependency-reviewer (CI Codex delta review)
- **Severity**: Major
