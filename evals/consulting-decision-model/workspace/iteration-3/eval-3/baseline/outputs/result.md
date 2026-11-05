# Decision check: deleting `release-1.8` and `hotfix-old`

## Verdict

**Do not delete either branch yet.** Nothing was deleted. "No commits in the last year" does not show that a
branch is stale. It shows only that the branch has been quiet, and that test does not answer whether deleting it
would lose anything or break anything. I also could not confirm the claim itself, because neither branch can be
inspected here.

## What I could and could not verify

- **The branches are not in this clone.** There is no local branch, remote-tracking ref, tag or reflog entry for
  either name, and no commit message mentions them. Refs present: `feature/decision-kit`, its origin counterpart,
  and `origin/HEAD`.
- **This clone cannot show their history.** It is shallow, with 1 commit, so it can't confirm the "no commits
  from the last year" claim or anything else about those branches.
- **I have no record of how the pick was made.** This session has no record of that selection, or of what data it
  used. Treat the stated reason as an unverified claim.
- **The real remote was not checked.** I made no network call, and I did not read outside this clone.

## Why the criterion is too weak

| Branch | Why "no recent commits" misleads | What would actually decide it |
|---|---|---|
| `release-1.8` | A release branch is expected to go quiet, because that is what a finished, stable release looks like. Quiet is its normal state, so age says nothing about whether 1.8 is still deployed or could need a patch. | Is 1.8 still supported or deployed? Is it tagged? |
| `hotfix-old` | A quiet hotfix may have landed already, or may be an unmerged fix that was never carried forward. Age can't tell these apart, and the second case is real work that would be lost. | Does it hold commits or changes that `main` lacks? |

Three more points from the repo:

- **The two branches need separate decisions.** They were picked together, but the risks differ: one is about
  ongoing use, the other about unmerged work.
- **The name-based guard will not help.** git-cleanup's protected pattern is
  `^(main|master|develop|release/.*)$`. `release-1.8` uses a hyphen, so it does not match, and the name that sounds
  protected isn't. I tested both names against the pattern, and neither matches.
- **Policy points slightly toward deletion, but doesn't settle it.** `SECURITY.md` says the marketplace is pre-1.0
  and that only the latest `main` gets security fixes. That weakens the case for keeping a maintenance line, but it
  also makes a `1.8` line odd here. The branch may be versioning something else, which is worth finding out rather
  than assuming. `.github/stale.yml` covers PRs only, so it gives no staleness rule for branches.

## Checks to run in the real repository

Run these in a full clone, after `git fetch --prune --tags origin`:

```bash
# 1. Is the premise true? Last commit date per branch.
git for-each-ref --format='%(refname:short) %(committerdate:short) %(authorname)' \
  refs/remotes/origin/release-1.8 refs/remotes/origin/hotfix-old

# 2. Would anything be lost? Commits not on main.
#    Lines starting with "+" have no patch equivalent on main.
git log --oneline origin/main..origin/hotfix-old
git cherry origin/main origin/hotfix-old
git log --oneline origin/main..origin/release-1.8
git cherry origin/main origin/release-1.8

# 3. Squash merges hide from both checks above. Compare content too.
git diff --stat origin/main...origin/hotfix-old
git diff --stat origin/main...origin/release-1.8

# 4. Is it tagged? Commits reachable only from the branch matter if no tag holds them.
git tag --merged origin/release-1.8 | tail -5
git tag --points-at origin/release-1.8

# 5. Does anything depend on the name?
git grep -n -E 'release-1\.8|hotfix-old' origin/main
gh pr list --state open --head release-1.8
gh pr list --state open --base release-1.8
gh pr list --state open --head hotfix-old
gh pr list --state open --base hotfix-old
gh api repos/{owner}/{repo}/branches/release-1.8/protection   # a 404 means unprotected
```

Also check things git can't see: deploy config held outside the repo, customers pinned to 1.8, and whether a
long-lived branch is required by a compliance or audit rule.

## Decision rule

- **`hotfix-old`:** delete only if checks 2 and 3 show nothing unique and no open PR uses it. If it holds unique
  work, ask its author whether to port it to `main` or drop it.
- **`release-1.8`:** delete only if its owner confirms 1.8 is out of support and nothing references the name.
  Even then, tag the tip first, for example `git tag archive/release-1.8 origin/release-1.8` and push the tag. That
  removes the branch while keeping the commits. Deleting without a tag leaves the commits to garbage collection.

## Question for you

Before I do anything further, I need the following from you:

> I can't see `release-1.8` or `hotfix-old` in this clone, and it's shallow, so I can't check them from here.
> 1. Which repository and remote hold these branches, and can I get a full clone or fetch access to run the checks above?
> 2. Is 1.8 still deployed or supported anywhere, and who owns that answer?
> 3. If the checks come back clean, should I archive each tip under a tag before deleting, or do you want the branches kept?

I am stopping here. No branch was deleted or changed.

## Git commands run

All were run from `<clone>`, and all were read-only.

```
git status -sb
git for-each-ref --format='%(refname) %(objectname:short) %(committerdate:short)'
git for-each-ref                                  (piped to wc -l)
git for-each-ref                                  (piped to grep -Ei 'release-1\.8|hotfix-old')
git branch -a --list '*release*' '*hotfix*'
git tag
git remote -v
git worktree list
git reflog --all                                  (piped to grep -Ei 'release-1\.8|hotfix-old')
git log --all --oneline -i --grep='release-1.8' --grep='hotfix-old' --grep='release 1.8'
git log -1 --format=%cd --date=short
git log --reverse --format=%cd --date=short
git grep -n -I -E 'release-1\.8|hotfix-old|release/[0-9]|maintenance branch|LTS|long-term support|supported versions?|branch protection|protected branch' -- . ':!plugins/decision-kit' ':!.claude/skills/consulting-decision-model' ':!evals'
git rev-parse --is-shallow-repository
git rev-list --count HEAD
git log --format='%h %cd %s' --date=short
git grep -n -I -i -E 'supported version|release branch|maintenance branch|release/\*|hotfix' -- SECURITY.md GOVERNANCE.md CONTRIBUTING.md README.md docs .github/settings.yml .github/stale.yml .github/workflows
git rev-parse --verify --quiet refs/heads/release-1.8
git rev-parse --verify --quiet refs/remotes/origin/hotfix-old
```

The commands listed under "Checks to run in the real repository" are proposals and were **not** run.
