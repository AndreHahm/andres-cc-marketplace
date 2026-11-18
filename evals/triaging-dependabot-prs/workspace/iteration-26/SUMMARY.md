# Iteration 26

New eval 23, for issue #741: a Dependabot PR whose bumped package is clean but whose head lockfile adds a package
version with a known advisory (the PR #628 case: markdownlint-cli2 0.24.0 pulls in re2js 2.8.6,
GHSA-gg6h-894w-4m9c). Step 3 now fetches the head lockfile too and `assess --head-lock` reports `added_packages` and
`adds_vulnerable_package`, which rule (d) turns into a hold; step 6.4 now reads the `Dependency review` check with
`dependency-review <n>`, whether or not it is required, and skips the PR when it fails. One simulated answer from a
general-purpose subagent that read the updated skill, graded by the author. A baseline answer from the pre-change
skill (`98f86ec2`, its SKILL.md and references only) was also graded; it was handed the same `assess` result,
including the `added_packages` block the pre-change script cannot produce.

| Eval | with_skill | baseline |
|---|---|---|
| 23: A vulnerable package added through a dependency holds the PR, and a failing Dependency review check skips it | 5 of 5 | 2 of 5 |

The baseline fetched only the base lockfile, said no rule of its skill covers the added-package signal and held the
PR on its own judgement (assertion 2 fails: the hold rests on no rule, and without the scenario handing it the data
it would not have seen re2js at all). At 6.4 it had no `dependency-review` read, ignored the not-required check as
the pre-change skill says, and sent #628 to `merge-pr`. Assertions 3 (it named 0.24.1 and left the call to the
user) and 5 passed.
