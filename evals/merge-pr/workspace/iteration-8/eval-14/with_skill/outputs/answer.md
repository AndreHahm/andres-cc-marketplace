# Eval 14: reproducing a CONFLICTING fork PR locally

No. I would not tell the user to run `git fetch origin contributor-branch`.

## What I do at step 2

`mergeable` is `CONFLICTING`, so the "No merge conflicts" check fails. I stop and report: "PR #88 has merge conflicts with `main`. GitHub reports `mergeable: CONFLICTING`." I do not go on to the merge-rights check.

This skill detects the conflict remotely and never fetches or merges locally itself. So I give the user the commands to reproduce it themselves. I do not point them at `resolving-merge-conflicts` first, because that skill needs unmerged paths already showing in `git status`.

## Why not `git fetch origin contributor-branch`

- `origin` only points at the PR's repository when the checkout is a clone of that same repository. The skill supports checking a PR the current checkout isn't a clone of, and `origin` could then be a different repository.
- `isCrossRepository` is `true`, so `contributor-branch` lives in the contributor's fork. It is not a branch on `acme-org/acme-repo`. Fetching it by name from the base repository would fail or, worse, resolve to an unrelated same-named branch.

## What I tell the user to run

I build the fetch URL from step 1's resolved `{owner}/{repo}`, which is `acme-org/acme-repo`. For a fork PR I fetch GitHub's synthetic per-PR ref for the head (`pull/88/head`) instead of `headRefName`. I use `<number>`-suffixed local branch names so they can't collide with branches the user already has:

```
git fetch https://github.com/acme-org/acme-repo.git pull/88/head:pr-88-head main:pr-88-base
git checkout pr-88-head
git merge pr-88-base
```

- The refspec has an explicit local destination. A fetch without one only updates `FETCH_HEAD`, which `git merge` can't name.
- `main` is `baseRefName`. `88` is the validated digits-only PR number.
- Only once `git status` shows unmerged paths do I tell the user to run `resolving-merge-conflicts`.

(For a same-repository PR, `isCrossRepository: false`, I would use `<headRefName>:pr-88-head` in place of `pull/88/head:pr-88-head`, still from the explicit URL.)

## Caveat for a fork PR

I can't push a resolution to the contributor's fork branch from here. The contributor needs to update their branch.
