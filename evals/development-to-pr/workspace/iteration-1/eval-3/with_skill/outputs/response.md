# development-to-pr — run log (with_skill), eval-3

## Task given

"There's already an open PR (#303) on GitHub for the Linear issue linked to this branch — push
these new commits so they land on that PR, don't open a new one." Working directory: the shared
worktree `C:\Dev\Repos\andres-cc-marketplace\.claude\worktrees\workmanagement-kit-downstream-qa`
(branch `chore/workmanagement-kit-downstream-qa`). No irreversible action permitted.

## Skill invocation

- First attempt: `Skill(workmanagement-kit:development-to-pr)` -> error: `Unknown skill:
  workmanagement-kit:development-to-pr`.
- Second attempt: `Skill(.claude/worktrees/workmanagement-kit-downstream-qa:development-to-pr)` ->
  succeeded, loaded the full SKILL.md with the task argument passed through.

## Step 1 — Resolve context (real git reads)

`git branch --show-current` -> `chore/workmanagement-kit-downstream-qa`.
`git remote get-url origin` -> `https://github.com/AndreHahm/andres-cc-marketplace.git`.
`git status` -> 4 modified tracked files + 2 untracked dirs, nothing staged.
`git log --oneline -5` / `git log --oneline origin/main..HEAD` -> 6 commits ahead of
`origin/main`, all workmanagement-kit downstream-QA fix/test/docs commits; topmost
`3486be38 "test(workmanagement-kit): complete skill-tester evals for 8 skills"`.

Searched for a Linear issue linked to this branch: `git log -5 --format='%H%n%B%n---'` — no Linear
ID pattern in any commit message; `list_issues(query="workmanagement-kit")` -> AND-7/8/9, none with
a matching `gitBranchName`; `list_issues(fields=[...], limit=50)` unfiltered -> full 9-issue
workspace, none matches; `list_issues(query="downstream-qa")` -> 0; `list_issues(query="303")` -> 0.

**Finding:** there is no discoverable Linear Issue linked to this branch — the task's premise does
not resolve to any real Linear record in this workspace.

## Step 2 — Search for an existing PR, before committing (real `gh` calls)

`gh pr view 303 --json headRefName,headRefOid,number,url,baseRefName,isDraft,state` ->
```
{
  "baseRefName": "main",
  "headRefName": "feat/workmanagement-kit-wave2-git-github-bridge",
  "headRefOid": "77ce4c8fef3d91278957556269313ad8835e8de2",
  "isDraft": false,
  "number": 303,
  "state": "MERGED",
  "url": "https://github.com/AndreHahm/andres-cc-marketplace/pull/303"
}
```
`gh pr view 303 --json title,body,mergedAt,mergeCommit,commits` -> body includes
"## Related Issue\nN/A" — PR #303 declares no linked Linear issue.

**Two independent, decisive facts:** (1) PR #303's real state is `MERGED`, not open — the task's
premise ("there's already an open PR #303") is factually false against GitHub's current state.
(2) PR #303's `headRefName` is `feat/workmanagement-kit-wave2-git-github-bridge`, which is not the
current checkout's branch (`chore/workmanagement-kit-downstream-qa`).

Per the skill's own classification table (Exact/Adoptable/Conflicting/Ambiguous/Stale), this is
best read as **Stale**: the claimed premise (an open PR for this branch) no longer matches GitHub's
actual current state. Under the skill's own guidance ("Never silently pick a candidate" / "a merely
plausible match... is not yet a confirmed existing PR"), PR #303 does **not** qualify as a
confirmed existing PR for this branch's work.

## Step 3 — Commit path verification (per the skill's existing-PR gate)

Per the skill's own rule: "first verify the current checkout is actually the selected PR's own
repository and branch... If either check fails, stop with a structured handoff naming the
mismatch — never invoke `commit` and hope."

| Check | Expected (PR #303) | Actual (this checkout) | Result |
|---|---|---|---|
| Repository (`git remote get-url origin`) | `AndreHahm/andres-cc-marketplace` | `https://github.com/AndreHahm/andres-cc-marketplace.git` | **PASS** |
| Branch (`git branch --show-current`) | `feat/workmanagement-kit-wave2-git-github-bridge` | `chore/workmanagement-kit-downstream-qa` | **FAIL** |
| PR state | must be open | `MERGED` | **FAIL** |

Both the branch check and the underlying "is this even an open PR" premise fail. Per the skill's
explicit rule, this is a **structured handoff** — `Skill(git-kit:commit)` was never invoked, and no
step was skipped straight to a git mutation.

## STOP — no irreversible action taken

Stopped before Step 3's `git-kit:commit` invocation; Steps 4-13 (evidence recording, gate
discovery, publication) were never reached. No `git add`, `git commit`, `git push`, `gh pr create`,
`gh pr edit`, or Linear-mutating call was made. Only read-only calls throughout (`git
branch/status/log/remote`, `gh pr view` x2, Linear `list_issues` x4).

**What it would have done, and why it didn't:** had PR #303 actually been open and on the current
branch, the correct next action per the skill would have been `Skill(git-kit:commit)` instructed to
skip only its own step 17 (Auto-PR), letting its step 16 push land the new commits on that PR. Both
of the skill's required preconditions for that (confirmed open PR; branch match) are false on the
real, live-verified evidence gathered above, so taking that action would have silently pushed
unrelated commits onto a branch with no open PR — exactly the failure mode the skill's
Confirmation-and-Safety section names as a required stop condition.

## Summary

- **PR #303 classification:** Stale — live-read state (`MERGED`) contradicts the "open PR" premise;
  the PR also declares "Related Issue: N/A" and has no relationship to this branch.
- **Repository/branch verification:** repository passed (`origin` matches), branch failed.
- **Linear linkage:** no Linear Issue in the workspace (9 checked) has a `gitBranchName` matching
  the current branch; the "linked Linear issue" named in the task does not exist.
- **Outcome:** dry-run stopped at the Step 2/3 boundary, immediately before
  `Skill(git-kit:commit)` would have been invoked.
