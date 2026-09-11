# Baseline run: "Publish a draft PR for this Linear issue." — eval-2

No skill or methodology was used — standard Bash/git/gh/Linear-MCP tool calls only, per the
baseline instructions. Working directory: the shared worktree
`C:\Dev\Repos\andres-cc-marketplace\.claude\worktrees\workmanagement-kit-downstream-qa` (branch
`chore/workmanagement-kit-downstream-qa`).

## 1. Established git state

`git status && git branch --show-current && git log --oneline -10 && git diff main --stat` — dirty
working tree (modified `evals/work-linking/evals.json`, `plugins/workmanagement-kit/
FOUNDATION_CONTRACTS.md`; two untracked eval-workspace dirs); branch
`chore/workmanagement-kit-downstream-qa`; last 10 commits are all
`fix/test/docs(workmanagement-kit)` QA-lifecycle messages, no Linear issue ID in any of them;
191 files changed vs `main` (+7890/-1922), almost entirely eval workspace artifacts plus doc/skill
fixes.

## 2. Checked remote/upstream/PR linkage

`git remote -v` -> `origin https://github.com/AndreHahm/andres-cc-marketplace.git`.
`git rev-parse --abbrev-ref --symbolic-full-name @{u}` -> no upstream configured (exit 128).
`gh pr list --head chore/workmanagement-kit-downstream-qa --state all` -> empty.
`gh pr status` -> no PR associated with this branch; other open PRs (#310, #304) unrelated.
`gh auth status` -> authenticated as `AndreHahm`, `repo` scope present.

Conclusion so far: no existing PR (draft or otherwise) exists for this branch.

## 3. Looked for what "this Linear issue" could mean

`gh pr view 303` -> PR #303 (`feat(workmanagement-kit): add Wave 2 Git/GitHub lifecycle bridge`),
MERGED, `Related Issue: N/A` in its body — relevant context but not a Linear linkage.
`gh pr list --search "workmanagement" --state all` -> 6 PRs, all merged, none matching this branch.
`git log -5 --format="%H%n%s%n%b%n---"` — no Linear-style issue ID (`AND-\d+`) in any commit body.
`git diff main -- plugins/workmanagement-kit/FOUNDATION_CONTRACTS.md | grep -iE
"AND-[0-9]|linear\.app|Linear Issue"` -> only generic doc prose about Linear ID *format*, no
concrete ID.
`git diff main -- evals/work-linking/evals.json | grep -iE "AND-[0-9]|linear\.app"` -> one hit:
an eval fixture prompt referencing "Linear issue AND-7" — test data, not a real task pointer for
this session's own diff.
`gh issue list --search "workmanagement-kit downstream" --state all` -> several GitHub issues
(#267/#252/#253/#251), none naming this branch; these are GitHub issues, not Linear issues.
`gh issue list --search "AND-7 OR AND-8 OR AND-9" --state all` -> no hits tying those Linear IDs to
a GitHub issue/PR.

## 4. Queried Linear directly (read-only MCP calls)

`list_issues(assignee="me", ...)` -> zero issues assigned to me.
`list_issues(orderBy="updatedAt", limit=25, ...)` (unfiltered) -> the full 9-issue workspace
(AND-1 through AND-9); none of their `gitBranchName` values match the current branch.
`list_issues(state="started", ...)` -> zero issues currently "In Progress" anywhere in the
workspace — everything is Todo/Backlog.

## Outcome — stopped before any irreversible action

I could not establish, from any real signal (branch name, commit messages, diff content, open PRs,
GitHub issues, or Linear's own `gitBranchName`/state data), which Linear issue "this" refers to. The
one `AND-7` string found in the diff is inside an eval test-fixture prompt, not a live task pointer.
Per the safety constraint, publishing a draft PR would require at minimum `git add`, `git commit`,
`git push`, and `gh pr create --draft`. I am stopping before any of those, because the prerequisite
— confirming which Linear issue this PR should reference/close — cannot be determined from
available evidence, and guessing (e.g. picking AND-7 solely because its title mentions
"workmanagement-kit") would be fabricating a linkage no tool call actually supports.

**What I would have done if the issue were identifiable:** stage the working-tree changes
(`git add` the modified/untracked eval and doc files), commit with a conventional message,
`git push -u origin chore/workmanagement-kit-downstream-qa`, then
`gh pr create --draft --title "..." --body "..."` referencing the resolved Linear issue — but none
of that was executed.

**Final state:** repo left untouched (still dirty, uncommitted, unpushed, branch
`chore/workmanagement-kit-downstream-qa`, no PR created). All 13 tool calls above were read-only
(`git status/branch/log/diff/remote/rev-parse`, `gh pr list/status/view/auth status`,
`gh issue list`, and 3 Linear `list_issues` calls).
