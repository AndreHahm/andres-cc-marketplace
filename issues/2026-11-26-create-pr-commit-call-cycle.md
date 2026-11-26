## Summary
create-pr and commit invoke each other, held apart only by a skip instruction; CI's dependency-reviewer blocks on the pair as a call cycle

## Environment
- **Product/Service**: git-kit `create-pr` and `commit` skills; plugin-devkit `dependency-reviewer`, run by CI's `Codex delta review` job
- **Region/Version**: PR #925 head f81a0290
- **Browser/OS**: n/a

## Reproduction Steps
1. `create-pr`'s Pre-flight Checks step 2 invokes `Skill(commit)` for uncommitted work, telling it to skip its push (step 16) and its Auto-PR step (step 17).
2. `commit`'s step 17 (Auto-PR) invokes `Skill(create-pr)` after a push when no PR is open.
3. Change any line of `create-pr`'s Loop-Breaker Convention section and open or update a PR; CI's dependency-reviewer reviews the diff.

## Expected Behavior
The two lifecycle skills do not depend on each other in both directions, so no call cycle exists to guard or to flag.

## Actual Behavior
The pair is a real two-way call. The skip instruction stops it from nesting within one run, but dependency-reviewer reports it as a blocking Major (`dependency-graph`) whenever a PR touches the lines that document it.

## Error Details
~~~
dependency-reviewer, Major, high confidence: create-pr invokes Skill(commit) for uncommitted work; commit invokes Skill(create-pr) in its Auto-PR step. The loop-breaker instructions suppress Auto-PR and push for create-pr's nested commit call, but both components still declare calls to each other.
~~~

## Visual Evidence
n/a

## Impact
**Medium** - Not a runtime failure (the skip instruction holds), but any PR that edits the Loop-Breaker text is blocked until the finding is waived, and the guard depends on every future caller passing the instruction.

## Additional Context
Options: have `commit`'s Auto-PR step hand off to the user instead of dispatching `create-pr`, or have `create-pr` require a clean tree instead of dispatching `commit`. PR #925 removed the sibling `create-pr` and `collaborating-on-a-pr` loop the same way: one side checks for itself, and the call becomes one-way.

## Review Finding Source
- **PR**: https://github.com/AndreHahm/andres-cc-marketplace/pull/925
- **Head SHA**: f81a0290da0342b300f16ef15fa9290f915a0036
- **Finding**: CI `Codex delta review` result, `dependency-graph` on `plugins/git-kit/skills/create-pr/SKILL.md:425`, fingerprint 611b8936a5894d5c46c4712d524fb0b3
- **Reviewer**: dependency-reviewer (CI Codex delta review)
- **Severity**: Major
