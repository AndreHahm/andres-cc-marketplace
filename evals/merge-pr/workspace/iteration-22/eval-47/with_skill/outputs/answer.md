# merge-pr on octo/widgets PR 953 (fork PR, no flags): the coverage tier at step 5

Sources followed: `plugins/git-kit/skills/merge-pr/SKILL.md` (steps 1-5) and
`plugins/git-kit/skills/merge-pr/references/advisory-disclosures.md` (the "Coverage tier" bullet).

## Steps up to the confirmation

1. **Step 1**: the PR reference `953` is digits only, so it is valid. No other flags were given. `gh pr view 953 --json ...`
   resolves the PR. `{owner}/{repo}` = `octo/widgets` comes from the PR's `url`. The `origin` comparison is
   skipped because a PR reference was given. `headRefName` and `baseRefName` are validated against the ref allowlist.
2. **Step 1.5**: `isCrossRepository` is `true`, so the checkout-match check fails at its first condition,
   and the step skips to step 2 after reporting that summary. **Step 1.6**: nothing in the given data calls for a
   body edit, so no edit is made and no wait for a skill-caused CI run is triggered.
3. **Step 2**: all six required checks pass (given). The not-behind-base check uses
   `mergeStateStatus` for the fork PR, and `CLEAN` passes it. The fork path cannot give an exact
   behind count, and the step says so. `--stop-on-review-findings` was not given, so the
   "Review findings" bullet is skipped entirely. The three advisory disclosures are then computed:
   - `mergeStateStatus`: `CLEAN`.
   - Unresolved review threads: `0`, from the paginated `reviewThreads` GraphQL query. A fresh `gh-pr-review`
     marker is written before each page.
   - Coverage tier: see below.
4. **Step 3**: the merge-rights check (`references/merge-rights-check.md`) must end in `MERGE ALLOWED` before
   step 5 is reached. **Step 4** is skipped because the run is not on the bypass path.

## The coverage tier

The skill reads `gh pr view 953 --json comments` and looks for the first comment with `author.login`
`github-actions` whose body starts with `<!-- quality-kit:coverage-tier -->`. The call returns no
comments at all, so **no tier comment exists**.

It also reads the latest `statusCheckRollup` entry for the head from the `Coverage` workflow named
`Coverage tier` or `coverage-tier`. The name `coverage-tier` comes from quality-kit's template, whose job
sets no name, which matches this repository. The entry is there: `coverage-tier` (workflow
`Coverage`), `status` `COMPLETED`, `conclusion` `FAILURE`, for the current head.

This is the "entry exists but there is no comment" case, so step 5 reports the entry's state and says
that no tier comment exists. That fits a fork PR, because the workflow skips the comment for a fork.
In substance, the confirmation says:

> Coverage tier: no quality-kit coverage-tier comment on this PR (expected for a fork PR: the workflow
> does not post one). The non-required `coverage-tier` check (workflow `Coverage`) completed with
> **FAILURE** for the current head. That means the patch-coverage tier is **orange or red, or could
> not be computed**. This is informational only and does not block the merge.

Other points about this case:
- No exact tier (`green`/`yellow`/`orange`/`red`) is reported, because no comment exists to read it
  from. The `FAILURE` is never reported as a particular tier and never as green.
- The "likely stale" warning does not apply. The entry exists and is `COMPLETED` with `FAILURE`, which
  is a recognized conclusion, and there is no comment whose tier could disagree with it. The "may describe an
  earlier head" caveat is about the comment, and no comment exists here. The check entry itself belongs to the current head.
- `coverage-tier` is not a required check, so step 2's status-check classification
  (`git-required-checks.py`) never sees it, and it has no effect on readiness.

## Does it block?

**No.** The coverage tier is an advisory disclosure. It never blocks readiness and never stops the run,
with or without `--stop-on-review-findings`, and this run has no flags anyway. The SKILL.md Boundaries
section records it as disclosure only (git-kit 31). Step 5 still asks with `AskUserQuestion` whether
to merge now. Its readiness summary always states all three disclosures: `mergeStateStatus` `CLEAN`,
`0` unresolved review threads, and the coverage-tier statement above. The prompt also carries the usual
note about a possible local worktree error during branch deletion. The merge goes ahead only on an
explicit yes. On the fork path, steps 7(e) and onward never delete the contributor's branch.
