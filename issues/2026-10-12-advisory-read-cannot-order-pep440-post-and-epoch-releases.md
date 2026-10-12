## Summary
triaging-dependabot-prs: rank, check and assess PEP 440 post-release and epoch releases in the advisory/compatibility read

## Environment
- **Product/Service**: git-kit `triaging-dependabot-prs`, `scripts/dependabot_advisory_read.py` (added in PR #539)
- **Region/Version**: uv (PyPI) ecosystem only; Python 3.13 stdlib script
- **Browser/OS**: not relevant

## Reproduction Steps
1. Take a PyPI package whose final releases include a post-release, e.g. `1.0`, `1.0.post1` and `0.9`, and a Dependabot PR bumping it to `1.0`.
2. Call `stable_releases()` with that release list, then `newest_compatible()` with the PR at `1.0`.
3. Observe the status and version it returns, and which signals step 3 of the skill receives.

## Expected Behavior
`1.0.post1` is ordered above `1.0`, its advisories are looked up, its declared constraints are checked against the base lockfile, and the signals `new_is_newest_compatible` and `new_safer_than_newest_compatible` are non-null when its data is known, so step 3 rule (c) can apply.

## Actual Behavior
The script only orders plain dotted-number versions (`version_key()` returns a tuple of ints, or `None`). Final PEP 440 releases that are not plain numbers — post-releases such as `1.0.post1` and releases with an epoch such as `1!2.0` — cannot be ordered.

Since PR #539, `stable_releases()` returns them in a separate "unordered" list, and `newest_compatible()` returns status `unknown` with version `null` when one of them may be at or above the PR's version (`may_outrank()`). Before that fix they were dropped silently and an older version could be reported as the newest compatible one. Consequences that remain:
- while such a release exists at or above the PR's version, the two "newest compatible" signals are `null`, so rule (c) can never fire for that dependency;
- that release's own advisories and declared constraints are never looked up or checked.

## Error Details
~~~
No error: the result degrades to {"status": "unknown", "version": null, "newer_incompatible": []}.
~~~

## Visual Evidence
None.

## Impact
**Low** - an edge case that degrades to `unknown`, never to a wrong answer. A recommendation that could have been "rebase and merge although a newer compatible version exists" is withheld, and a post-release that fixes an advisory is not considered.

## Additional Context
- Wanted: PEP 440-aware parsing and ordering for the uv ecosystem (epoch, release, pre, post and dev segments) in `version_key()` / `cmp_release()`, which the new/old/latest comparisons also use. Pre-releases and dev releases must stay excluded, as today.
- Constraint: no new third-party dependency in a read-only stdlib script unless the maintainers decide otherwise; hand-rolled parsing needs a property test.
- Origin: the Codex connector's review of PR #539 (thread on `dependabot_advisory_read.py`, "Include stable non-numeric Python releases"), fixed there only as a degrade-to-unknown. Found in PR #539.
- Tests covering the current behavior: `ConnectorReviewFixTests` in `scripts/test_dependabot_advisory_read.py`.
- Related doc: `plugins/git-kit/skills/triaging-dependabot-prs/references/advisory-and-compatibility.md`.
