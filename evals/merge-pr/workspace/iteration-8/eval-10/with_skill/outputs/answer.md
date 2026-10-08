# merge-pr step 2, "No merge conflicts" bullet: mergeable = CONFLICTING

## Checks I perform for this bullet

1. Read `mergeable` from the PR data already fetched in step 1. This is the first pass, so no re-fetch is needed. The value is `CONFLICTING`.
2. Confirm the value is terminal. `mergeable` is a 3-value enum: `MERGEABLE`, `CONFLICTING`, `UNKNOWN`. Only `UNKNOWN` ("still being calculated") triggers the bounded polling of up to 5 attempts. `CONFLICTING` is already terminal, so I do not poll, and I never treat it as passing.
3. Confirm the ref names were validated. Step 1 already checked `baseRefName` (`main`) and `headRefName` (`fix/typo`) against `^[A-Za-z0-9._/@+=-]+$`, and both pass. That is why they are safe to put in the fetch commands below.
4. Reuse the `{owner}/{repo}` step 1 already resolved, `acme-org/acme-repo`. I use it to build an explicit `https://github.com/acme-org/acme-repo.git` URL. I do not use a bare `origin` or `gh repo view`, because the current checkout may not be a clone of this repository at all.
5. Read `isCrossRepository` (from step 1) only to choose which head ref to fetch. The task does not give its value, so I show both forms below.
6. Stop here. Step 2 says: if any check fails and no bypass exception applies, stop and do not proceed to the rights check on a not-ready PR. So there is no step 3, no merge-rights check, no confirmation and no merge.
   - The `--bypass-codex-review` exception does not apply. It covers only the `Publish Codex policy result` status check, never a merge conflict.
7. I run no local git commands myself. This skill detects the conflict remotely from GitHub's computed field. It never fetches or merges locally.

## What I tell the user

> The PR (`fix/typo` into `main` in `acme-org/acme-repo`) is not ready to merge. GitHub reports `mergeable: CONFLICTING`, so the PR has merge conflicts with `main`. I'm stopping here and have not run the merge-rights check or offered to merge.

## Do I point them directly at `resolving-merge-conflicts`? No

I do not hand them `resolving-merge-conflicts` with nothing else. That skill needs a local working tree that already shows unmerged paths in `git status`. A remote `CONFLICTING` signal alone gives it nothing to act on. So I give them a reproduction step first.

Replace `<number>` with the PR number (digits only, validated at step 1).

**If `isCrossRepository` is `false`** (head branch lives in this repository):

```
git fetch https://github.com/acme-org/acme-repo.git fix/typo:pr-<number>-head main:pr-<number>-base
git checkout pr-<number>-head
git merge pr-<number>-base
```

**If `isCrossRepository` is `true`** (fork PR). The fork's `fix/typo` is not a ref this URL exposes by that name, so I use GitHub's synthetic per-PR ref instead:

```
git fetch https://github.com/acme-org/acme-repo.git pull/<number>/head:pr-<number>-head main:pr-<number>-base
git checkout pr-<number>-head
git merge pr-<number>-base
```

- The explicit `:pr-<number>-head` and `:pr-<number>-base` destinations are needed because a bare fetch only updates `FETCH_HEAD`, which `git merge` cannot name directly.
- The `<number>`-suffixed local names avoid colliding with a branch the user already has locally.

Only once `git status` actually shows unmerged paths do I tell them to run `resolving-merge-conflicts` to resolve them. After resolving and pushing, re-invoke `merge-pr` so readiness is re-checked from scratch.
