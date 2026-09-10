# Task: Merge PR #51 (ENG-203) and Disposition the Linear Issue

No named skill/procedure was available for this run. I do not have live GitHub or Linear connector
access in this environment, so I cannot actually execute the API calls below. What follows is the exact,
concrete sequence of steps I would take, in order, using only standard `gh` CLI / git operations and
Linear's UI or API, plus the judgment calls I'd make at each decision point and what I'd need to verify
before proceeding. Where I'd normally run a command, I show the exact command I'd run and what output I'd
be checking for.

## Assumptions stated up front

- "PR #51" refers to a GitHub pull request in whatever repository is checked out in the current working
  directory (or a repository the user specifies) — I'd confirm the remote/repo with `git remote -v` /
  `gh repo view` before doing anything else, since "PR #51" alone is only unambiguous within one repo.
- "Approved" means GitHub shows an approving review from someone with actual review authority (not just
  a comment), and I'd double check there are no *outstanding* change-request reviews from anyone else
  that haven't been superseded.
- "All checks pass" means the PR's status-check list (CI, lint, tests, any required checks branch
  protection names) shows green, not merely "not failing" (e.g., not stuck in `pending`).
- "Linked to Linear issue ENG-203" means either the PR description contains a Linear magic-word reference
  (e.g. `Closes ENG-203` / `Fixes ENG-203`) or a Linear↔GitHub integration has already attached the PR as
  an attachment on the issue. I'd verify which is actually true rather than assume the auto-link exists,
  because that determines whether merging alone will auto-transition Linear or whether I have to do it by
  hand.
- "Disposition the Linear issue" means: move it to the correct terminal (or next) state — almost always
  "Done"/"Completed" if the PR fully resolves it — and leave a clear audit trail (a comment linking the
  merged PR, and confirming any release/deploy step if this team gates "Done" behind a deploy).
- I do not have credentials to actually call `gh` or Linear's API in this sandboxed exercise, so I'm
  describing the real commands/actions I would run against a live environment.

If any of these assumptions were wrong in a real session, I'd stop and confirm with the user before
merging — merging is a one-way door for a shared branch, and mis-dispositioning a tracked issue creates
noise other people have to clean up later.

## Plan

```
1. Verify PR #51's real state (approval, checks, mergeability, target branch) → verify: gh pr view output
2. Verify Linear ENG-203's current state and confirm it's the right issue for this PR → verify: Linear issue fetch matches PR title/branch/description
3. Merge the PR using the appropriate strategy → verify: gh pr view shows MERGED, target branch has the commit
4. Sync local repo state to the newly-updated base branch → verify: git log/git status clean, no dangling branch
5. Disposition ENG-203 in Linear → verify: issue state = Done (or appropriate terminal state), comment posted with PR link
6. Clean up (delete merged branch, close out any related follow-ups) → verify: branch deleted, no orphaned work items
```

## Step 1 — Verify PR #51's actual state before touching anything

Never trust "the user says it's approved and green" as the terminal source of truth — I'd re-check
directly, because the state could have drifted (a new commit pushed, a check re-run, a review dismissed)
between when the user last looked and now.

```bash
gh pr view 51 --json number,title,state,mergeable,mergeStateStatus,baseRefName,headRefName,reviews,statusCheckRollup,body
```

What I'm looking for in that output, specifically:

- `state` is `OPEN` (not already merged/closed — if it's already merged, step 1 is done and I only need
  to handle Linear).
- `mergeable` is `MERGEABLE` (not `CONFLICTING` — if there's a conflict, I'd stop, flag it to the user,
  and would not attempt to resolve conflicts unilaterally without confirming the intended resolution).
- `mergeStateStatus` is `CLEAN` or `UNSTABLE`-but-not-blocking, not `BLOCKED` — `BLOCKED` on a
  protected branch usually means either checks aren't done or a required review is missing, contradicting
  the premise that it's approved and green, so I'd re-verify before proceeding rather than force through.
- `reviews` contains at least one `APPROVED` review from someone with write/CODEOWNERS authority, and no
  unresolved `CHANGES_REQUESTED` review that postdates the approval.
- `statusCheckRollup` shows every required check as `SUCCESS` (not `PENDING`, `FAILURE`, or `SKIPPED` on a
  required check).
- `baseRefName` — confirm it's merging into the branch the user expects (almost always the default
  branch, e.g. `main`), not some other integration branch.
- `body` — I'd scan this for the Linear linking syntax (`Fixes ENG-203`, `Closes ENG-203`, or a Linear
  attachment link) to confirm the PR is actually the one tied to ENG-203, not just correlated by the
  user's message.

I'd also check who has merge rights — i.e., confirm the acting user (or me, acting on their behalf) is
actually allowed to merge into the protected branch (repo admin, or a role with merge permission), since
attempting a merge without rights just fails loudly, but it's better to know in advance.

```bash
gh api repos/{owner}/{repo}/collaborators/{username}/permission
```

If any of the above checks come back different from "approved + green + no conflicts," I would stop and
report the discrepancy to the user rather than proceed on the original assumption.

## Step 2 — Verify the Linear issue before merging

I'd pull ENG-203's current state before merging, for two reasons: (a) to confirm it's genuinely the issue
this PR closes (title/branch-name sanity check — e.g. does the branch name look like
`eng-203-something` or does the PR body explicitly reference it), and (b) because if ENG-203 is already
in a terminal state (Done/Canceled) that would be a signal something is off — maybe this PR is closing a
*different* issue, or the issue was already handled another way.

Via Linear's UI/API I'd fetch:
- Current status (e.g. "In Review", "In Progress")
- Assignee (to know whether reassignment or notification is appropriate)
- Any sub-issues or blocking relationships (if ENG-203 has open sub-issues, merging the parent's PR
  shouldn't auto-close the parent if children aren't done — I'd check that before transitioning state)
- Any existing linked PR attachment on the issue (to see whether the Linear-GitHub integration already
  has this PR attached, which tells me whether merging will auto-transition the issue or whether I need
  to do it by hand)

If ENG-203 has open sub-issues or is part of a larger project where "Done" isn't appropriate yet (e.g.
this PR is one of several needed to fully resolve the issue), I would not blindly mark it Done just
because *a* PR merged — I'd either mark it appropriately (e.g. leave it "In Progress" with a comment
noting partial completion) or ask the user to confirm scope, since over-closing a tracked issue creates
real cleanup work for whoever notices later.

## Step 3 — Merge the PR

Given the premise ("approved, all checks pass") holds after re-verification, I'd merge using whatever
merge strategy this repo's convention favors — I'd check for a stated convention first (CONTRIBUTING.md,
repo default merge setting) rather than assume:

```bash
gh pr view 51 --json mergeStateStatus
gh repo view --json mergeCommitAllowed,squashMergeAllowed,rebaseMergeAllowed
```

Most teams squash-merge feature PRs to keep main's history linear; I'd default to that unless the repo's
settings only allow a different strategy, or the PR is a multi-commit unit where preserving individual
commits matters (rare for a single feature). Then:

```bash
gh pr merge 51 --squash --delete-branch
```

(`--delete-branch` cleans up the remote head branch as part of the same operation — assuming this repo's
norm is to delete feature branches after merge, which is standard. If a Linear magic-word like `Closes
ENG-203` is present in the PR body/commit message *and* the Linear-GitHub integration is active for this
workspace, the act of merging itself may already auto-transition ENG-203 to Done — in that case Step 5
becomes a verification step rather than a manual state change. I would not assume that happened, though;
I'd verify it explicitly in Step 5.)

Immediately after, I'd re-check:

```bash
gh pr view 51 --json state,mergedAt,mergeCommit
```

confirming `state == MERGED` and capturing the merge commit SHA — I'd want that SHA to reference in the
Linear comment for traceability.

## Step 4 — Sync local repo state

```bash
git checkout main
git pull --ff-only origin main
git branch -d <local-feature-branch>   # only if it exists locally and is now fully merged
```

I'd use `--ff-only` rather than a plain pull to avoid accidentally creating a merge commit locally if
something unexpected happened; if `--ff-only` fails, that's a signal local main has diverged and needs
investigation before I trust it, not something to force past.

## Step 5 — Disposition ENG-203 in Linear

1. Re-fetch the issue to see whether merging already auto-transitioned it (if the GitHub-Linear
   integration is wired up and the PR body used a recognized closing keyword). If it already shows
   "Done"/"Completed," I'd still add a confirming comment with the merge commit link rather than assume
   silence means it's fully wired up correctly.
2. If it did *not* auto-transition, I'd manually move ENG-203 to the appropriate state:
   - **Done / Completed** — the standard case, since the premise is that the PR fully resolves the issue.
   - Not "Done" if, per Step 2, there are open sub-issues or the issue tracks more work than this one PR
     — in that case I'd leave it in progress (or whatever intermediate status this team's workflow uses,
     e.g. "In Review" → "Ready to Deploy" if this team gates completion behind an actual deploy rather
     than just a merge) and say so explicitly rather than silently marking it Done.
3. Add a comment on ENG-203 recording what happened, concretely, e.g.:
   > Merged via PR #51 (squash-merged to `main`, commit `<sha>`). Marking Done.
   This gives anyone auditing the issue later a direct trail back to the exact change, without having to
   cross-reference GitHub separately.
4. Check whether this team's workflow expects a release/deploy tag or changelog entry before truly
   calling work "Done" (some teams use a "Merged" vs. "Deployed" vs. "Done" distinction). If unclear, I'd
   default to marking it Done on merge (the most common convention) but flag the ambiguity to the user
   rather than silently assume.
5. If ENG-203 has an assignee different from whoever merged, no reassignment is needed for closing — but
   I'd confirm the assignee still matches who actually did the work, and leave a note if there's a
   mismatch worth calling out.

## Step 6 — Final verification and report back

- `gh pr view 51 --json state,mergedAt` → confirm `MERGED`.
- Confirm the feature branch was deleted both locally and on the remote (`git branch -a` /
  `gh pr view 51 --json headRepositoryOwner,headRefName` no longer resolving to a live branch).
- Confirm ENG-203's Linear state reflects the disposition decided in Step 5, with the trailing comment
  linking the merge commit.
- Report back to the user: PR #51 merged (strategy used, commit SHA, target branch), and ENG-203's final
  Linear state with a one-line justification if it's anything other than a straightforward "Done."

## Things I would explicitly NOT do

- I would not force-merge past a failing or pending required check even if the user asserts "all checks
  pass" — I'd re-verify live status first, since check status can change between when someone looked and
  when I act.
- I would not mark ENG-203 Done if Step 2 reveals open sub-issues or a broader scope than this single PR
  covers — I'd disclose that instead of silently closing it to make the task look "done."
- I would not delete the remote branch if there's any indication another open PR or reference still
  depends on it (I'd check `gh pr list --search "head:<branch>"` for any other open PR referencing the
  same head before deleting).
- I would not skip the Linear side even if the GitHub integration might auto-handle it — I'd verify the
  actual resulting state rather than assume the integration fired correctly, since a silent integration
  failure would otherwise leave a merged PR with a stale, un-transitioned tracked issue and no one would
  notice until someone went looking for ENG-203 later.
