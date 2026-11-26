# PR 953 (octo/widgets): step 5's coverage-tier disclosure

Simulated exercise: no `gh`/`git` call, script or edit was run. The data in the prompt stands in for what
those calls would return.

## Steps up to the confirmation

1. **Step 1.** The PR reference `953` is digits only, so it is valid. No flags were given, so there is no
   `--expected-head-sha`, no `--bypass-codex-review` and no `--stop-on-review-findings`.
   `gh pr view 953 --json ...` resolves the PR, and `{owner}/{repo}` = `octo/widgets` comes from its `url`.
   The PR reference was non-empty, so the `origin` identity check is skipped. `headRefName` and
   `baseRefName` are checked against the allowlist and are assumed to pass.
2. **Step 1.5.** `isCrossRepository` is `true`, so the checkout-match check fails at once. No session scan,
   fix or push runs, and the step reports that it was skipped because this is a fork PR.
3. **Step 1.6.** The PR-body currency check runs as documented. It is assumed to propose no change, so the
   body is not edited and step 2's first pass needs no re-fetch.
4. **Step 2, the six required checks.** All six pass:
   - not draft
   - `git-required-checks.py` exits `0`
   - no `CHANGES_REQUESTED`
   - `mergeable` is `MERGEABLE`
   - not behind base: on this fork path `mergeStateStatus` is `CLEAN`, a terminal value that is not
     `BEHIND`, so the gate passes. The exact count of commits behind is not available for a fork PR, and
     the report says so instead of showing `0`.
   - review outcomes recorded
5. **Step 2, the advisory disclosures** (`references/advisory-disclosures.md`):
   - `mergeStateStatus`: `CLEAN`.
   - Unresolved review threads: the paginated `reviewThreads` query, with a fresh `gh-pr-review` marker
     before each page, returns **0**.
   - Coverage tier: see below.
6. **Step 3.** The merge-rights check runs. Steps 5 to 8 below assume it returns `MERGE ALLOWED`.
7. **Step 4.** Skipped, because no bypass path applies.

## What the coverage-tier bullet finds

- **Comment:** `gh pr view 953 --json comments` returns no comments. So there is no comment from
  `github-actions` whose body starts with `<!-- quality-kit:coverage-tier -->`, and no tier line to read.
  This is expected for a fork PR, because the workflow skips that comment for fork PRs.
- **Check entry:** the reference says to report "the latest `statusCheckRollup` entry named
  `Coverage tier`". The rollup has no entry with that exact name. If the instruction is read literally,
  neither the comment nor the entry exists, and the reference's wording would be "no coverage tier was
  reported".
- **What I would actually report:** the rollup does hold a CheckRun named `coverage-tier`, with
  workflowName `Coverage`, status `COMPLETED` and conclusion `FAILURE` for the current head. It is not a
  required check. The repository copied quality-kit's coverage workflow template, so this is very likely
  the same coverage-tier job under its job id instead of its display name. Reporting "no coverage tier
  was reported" while a coverage check has failed for this head would hide the one signal that exists. So
  the disclosure names the entry and says that the exact-name match does not cover it.

## What step 5's confirmation says

The `AskUserQuestion` prompt shows PR 953, its title and the readiness summary. It also gives all three
advisory disclosures:

- **Merge state:** `CLEAN`.
- **Unresolved review threads:** 0.
- **Coverage tier:** "No coverage-tier comment was posted. This is a fork PR, and the workflow skips the
  comment for fork PRs, so no tier value (green, yellow, orange or red) is available. The non-required
  check `coverage-tier` (workflow `Coverage`) has completed for the current head with conclusion
  `FAILURE`. That conclusion means the patch coverage tier was orange or red, or could not be computed;
  the run does not say which. It is not the exact `Coverage tier` entry name the skill looks for, but it
  is very likely the same job. This is informational only and does not block the merge."

The same prompt also:

- states that a fork PR has no exact commit-behind count
- states that the branch lives in the contributor's fork, so this skill will not delete it after the
  merge
- carries the standard note that deleting the branch may report a local
  `fatal: '<default>' is already used by worktree ...` error even though the merge succeeds
- asks whether to merge now

## Does it block?

**No.** The coverage tier is informational only, under the skill's Boundaries and
`references/advisory-disclosures.md`. An orange, red or uncomputed tier, and a failed coverage check
that is not required, are disclosed at step 5 and never stop the run, with or without
`--stop-on-review-findings` (and that flag was not given here). All six required checks pass, so the run
continues to step 5's confirmation. A merge happens only if the user explicitly says yes. Steps 6 and 7
then run, including 7(b)'s final recheck and `--match-head-commit`. Because `isCrossRepository` is
`true`, step 7(e) does no branch-deletion fallback.

## Gap noted in the skill text

The coverage-tier bullet matches the check only by the exact name `Coverage tier`. A repository whose
job reports as `coverage-tier` (its job id) slips through that match. Followed literally, the bullet
would then report "no coverage tier was reported" even though a coverage check failed for this head. The
bullet could match the entry by workflow name or by job id as well, or say what to do when only a
differently named coverage entry exists.
