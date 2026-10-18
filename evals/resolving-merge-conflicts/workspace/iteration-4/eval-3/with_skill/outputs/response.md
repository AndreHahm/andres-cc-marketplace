# Eval 3 trace (simulated): PR #640, clean local tree

## Skill path
Read SKILL.md, then Step 1a (clean tree, PR conflicts on GitHub) and references/remote-only-conflicts.md.
Steps 2-7 do not apply to this case.

## Validation before any command
- PR number "640" matches ^[0-9]+$ : ok.
- baseRefName "main" matches ^[A-Za-z0-9_][A-Za-z0-9._/-]*$ : ok.

## Commands, in order (simulated output as given by the prompt)
1. "${CLAUDE_PLUGIN_ROOT}/scripts/git-pr-conflict-preview.sh" view 640
   -> CONFLICTING / DIRTY, base main, head patch-1, headRefOid cccc333, isCrossRepository true, url .../AndreHahm/andres-cc-marketplace/pull/640
2. git status -> clean (the prompt supplies it; the skill's Step 1 also runs it)
3. git fetch origin -> succeeds
4. git rev-parse HEAD -> cccc333 (equals headRefOid: ok)
5. git branch --show-current -> patch-1 (equals headRefName: ok)
6. git remote get-url origin -> https://github.com/AndreHahm/andres-cc-marketplace.git (equals the url's owner/repo: ok)

NOT run: "git-pr-conflict-preview.sh merge-tree main", `gh repo view ...`, and Skill(git-rebase-sync).
The prompt supplies no output for them, and the stop condition below fires first.

## Decision: STOP. Neither preview nor route.
`isCrossRepository` is true, so this is a fork PR. Step 1a says to stop when isCrossRepository is true
(fork PR not supported on this route). Reason: git-rebase-sync ends by pushing `origin HEAD:<branch>`, and for a
fork PR checked out from the base repo's clone, `origin` is the base repo, so the push could create or overwrite a
same-named branch there while the fork PR stays unchanged.
(Note: the origin check passed on its own, since origin matches the PR url's repo. The stop comes solely from
isCrossRepository being true. The local-branch checks, HEAD == headRefOid and branch == headRefName, also passed.)
No merge, no trial merge, no merge commit, no worktree change, no hand-off to git-rebase-sync.

## AskUserQuestion calls
None. The skill prescribes a stop with an unsupported-case message, not a question.

## Message to the user
PR #640 (patch-1 -> main) is reported by GitHub as CONFLICTING/DIRTY, and your local tree is clean, so the conflict
exists only on the remote. However, PR #640 comes from a fork (isCrossRepository: true), and this route does not
support fork PRs. The follow-up rebase would push `origin HEAD:patch-1`, and here `origin` is the base repository
(AndreHahm/andres-cc-marketplace), so the push could create or overwrite a branch named patch-1 there while the fork's
PR stays unchanged. I stopped before the conflict preview and did not route to git-rebase-sync. I changed nothing
(no merge, no rebase, no commit). The conflict has to be resolved from the fork's own branch (by the fork's owner, or
from a clone whose `origin` is the fork), or tell me how you want to proceed.
