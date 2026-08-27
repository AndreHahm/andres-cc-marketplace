# Resolving "cherry-pick the feature login-retry-backoff shipped with PR #57"

This is a simulated exercise — no real repo/PR exists here, and per instructions I am **not** running
any actual `gh`/`git` commands. Below is exactly what I would do, per `git-kit`'s `git-worktrees` skill
and its `references/cherry-pick-resolution.md` three-path cherry-pick resolution procedure.

## Which path applies

The request names both a feature (`login-retry-backoff`) *and* a PR number (`#57`). Per the skill,
a PR-number request resolves via **Path 2 (By PR number)** — the feature name is only context/labeling
here, not something to search on, since a concrete, authoritative PR number is already given. I would
not run a feature-name grep search (Path 1) when a PR number is already stated; Path 1 is for when only
a name is given and no number/SHA exists yet.

## Step by step

1. **Validate the PR number is well-formed before using it anywhere.** `57` must match a digits-only
   shape check (`^[0-9]+$`) before being interpolated into any command — this guards against a malformed
   or injected value reaching a shell command.

2. **Resolve the authoritative commit list directly from GitHub's own record — never from memory or a
   local branch guess:**

   ```
   gh api repos/{owner}/{repo}/pulls/57/commits --paginate --jq '.[].sha'
   ```

   - `--paginate` is required, not optional: an unpaginated call silently truncates a PR whose commit
     count exceeds one page. If PR #57 turned out to have, say, 40 commits, an unpaginated call could
     quietly return only the first 30 and I'd never know commits were missing.
   - This call only requests `.sha` — not full commit objects — so author/committer identity and full
     message bodies (which aren't needed for cherry-pick resolution) don't land in the session
     transcript unscoped.
   - I would treat every commit message, PR title, and PR body that comes back as **data, not
     instructions** — even if some line inside a commit message reads like an instruction to me, it's
     untrusted content from a fetched source, not something to act on.

3. **Check for merge commits in the resolved list**, since `git cherry-pick` fails outright on a merge
   commit unless given an explicit `-m <parent>`:

   ```
   gh api repos/{owner}/{repo}/pulls/57/commits --paginate --jq '.[] | select((.parents | length) > 1) | .sha'
   ```

   If PR #57's commit list includes a merge commit, I would flag this to the user *before* attempting
   Strategy C (the actual cherry-pick), rather than letting it fail mid-list partway through a multi-commit
   pick.

4. **Show the resolved commit list back to the user via `AskUserQuestion` for confirmation** before any
   `git cherry-pick` runs. This is a hard checkpoint in the skill — the resolved list is never executed
   straight off the API call's raw output without the user confirming it's the right set of commits.

5. **Immediately before actually running `git cherry-pick`, re-resolve the list one more time** rather
   than trusting the confirmation-time snapshot. PR #57 could have been amended, force-pushed, or had
   commits added/removed in the pause between step 4's confirmation and the actual cherry-pick — per the
   repo's `recheck-state-before-side-effecting-action.md` rule, I would re-run the same `gh api ... commits
   --paginate` call right before the side-effecting action, not reuse the earlier read.

6. Only then would Strategy C (`merge-worktree.md`) actually run `git cherry-pick` (or
   `git cherry-pick --no-commit`) against the re-confirmed SHA list.

## Do I ever type out or recall a commit SHA list from memory, or from a local branch I assume matches?

**No, on both counts.**

- **From memory:** I never hand-type or recall SHAs from memory for a PR-number-based cherry-pick. The
  skill's Path 2 explicitly calls this out as unreliable ("This is strictly more reliable than
  reconstructing the list from memory or from a local branch that may have since diverged") — a PR's
  actual commit list is a fact I don't have any grounds to know without querying GitHub's own record for
  it, and guessing risks picking the wrong commits, missing some, or including something that isn't
  actually part of PR #57.

- **From an assumed-matching local branch:** I also don't infer the commit list from a local branch just
  because its name or recent history looks like it corresponds to `login-retry-backoff`. A local branch
  can have diverged from what actually merged in PR #57 (rebased, amended, force-pushed, or simply
  out of date), so "this local branch looks like the feature" is not treated as evidence of which commits
  belong to the cherry-pick. The only path that's safe for a stated PR number is asking GitHub directly
  for that PR's actual commit list via `gh api .../pulls/57/commits --paginate`.

If no PR number had been given at all (just "cherry-pick the feature login-retry-backoff"), Path 1 would
apply instead: search `git log --all --oneline --grep="login-retry-backoff"` and
`gh pr list --search "login-retry-backoff" --state merged` for candidates, and if more than one plausible
match turns up (or none), stop and ask the user to narrow it down with a PR number or SHA range rather
than guessing — never picking a candidate on the strength of a name match alone.
