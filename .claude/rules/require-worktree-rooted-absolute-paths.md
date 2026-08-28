# Require Worktree-Rooted Absolute Paths for Read/Edit/Grep in Worktree-Bound Sessions

## When this applies

Any point in a session whose current working directory is bound to a git worktree — one `starting-work`
created, or any other worktree the session is actively working in — before typing an absolute path
argument to `Read`, `Edit`, or `Grep`. Especially relevant right after a context-compaction event: the
discipline of "prefix every absolute path with the worktree segment" tends to live only in conversation
reasoning, and doesn't reliably survive into a compaction summary — only the environment block's "Primary
working directory" line does, which `Bash`'s own persistent cwd honors automatically, but `Read`/`Edit`/
`Grep` take independent absolute-path arguments that don't inherit `Bash` cwd at all.

## Rule

In a worktree-bound session, never type an absolute path for `Read`/`Edit`/`Grep` rooted at the main
checkout when the intended target is the worktree's own copy of a file (or vice versa). Both are real,
independently valid git checkouts on the same machine — often on different branches with differently
populated files at the same relative path — so a wrong-but-plausible absolute path resolves and succeeds
silently against the wrong file, with no error at any layer.

**Incorrect** — worktree is `.claude/worktrees/my-fix`, but the path is typed from habit rooted at the
main checkout:
```
Read("C:/Dev/Repos/andres-cc-marketplace/plugins/git-kit/skills/starting-work/SKILL.md")
```
This succeeds silently against the main checkout's own copy of the file — a real, valid file, just not
the one actually being worked on — with no error to signal the mistake.

**Correct** — the same call, rooted at the worktree:
```
Read("C:/Dev/Repos/andres-cc-marketplace/.claude/worktrees/my-fix/plugins/git-kit/skills/starting-work/SKILL.md")
```

Before typing an absolute path in a worktree-bound session:
- Confirm the path includes the worktree segment (e.g. `.claude/worktrees/<name>/...` or
  `.codex/worktrees/<name>/...`) whenever the intended target is the worktree's own copy of a file —
  never the bare main-checkout-rooted form.
- `Read`/`Edit` require an absolute path in this environment (per their own tool schemas) — there's no
  relative-path escape hatch for them. For any operation that *can* take a relative path (chiefly
  `Bash`), prefer `cd`-ing into the worktree and using a relative path there over hand-typing a full
  absolute path — this is also what actually resolved the real incident below.
- When in doubt, or right after a context-compaction event, confirm the worktree root via `Bash` (its
  own cwd is already worktree-bound, so a plain `pwd`/`Get-Location` confirms it directly) — **but see
  the caveat below before reaching for `git rev-parse --show-toplevel`** as that confirmation step.

**Caveat — don't lean on `git rev-parse --show-toplevel` unconditionally:** if the worktree may have
just been removed while cwd is still pointed at it,
[[orphaned-worktree-git-read-fallthrough]] documents that this exact command (and other git reads)
silently falls through to the *main checkout's* state instead of erroring. In that situation, cross-check
with a plain filesystem listing (`ls`/`Get-ChildItem`, not git-mediated) rather than trusting
`git rev-parse` alone — the two rules complement each other here rather than one superseding the other.

**Scope note:** this rule names `Read`/`Edit`/`Grep` specifically, matching the incident that motivated
it. `Write` takes an absolute path too and could suffer the same silent-wrong-location failure — it's
out of scope here only because the motivating incident didn't involve it, not because it's exempt in
principle; extend this rule to cover it if the same failure is ever observed with `Write`.

This complements [[orphaned-worktree-git-read-fallthrough]], which covers a narrower, related case: a
`git`-mediated read falling through to the main checkout's real state *after* a worktree has been
removed. This rule is broader — it applies to any absolute-path argument to `Read`/`Edit`/`Grep`, at any
point in a worktree-bound session, not only after removal, and not only to git-mediated reads.

## Why

**Incident (issue #150):** a real session had `starting-work` create and lock a worktree, with the
session's `Bash` cwd auto-bound to it immediately after — no explicit `cd` needed. The session correctly
self-derived, in the moment, that absolute paths should be typed under the worktree root, and did so
correctly for a stretch. That discipline lived only in conversation reasoning, not in any rule file.
After a later context-compaction event, several `Read`/`Edit`/`Grep` calls on
`plugins/plugin-devkit/skills/plugin-lifecycle-downstream/SKILL.md` used a habitually-typed path rooted
at the main checkout instead of the worktree. The main-checkout path was a real, valid, differently
populated directory (an actual separate git checkout on a different branch), so the read/edit call
succeeded silently against the wrong file, with no error — initially misdiagnosed mid-session as a tool
caching bug before the real cause was found. No data loss occurred (the main checkout's `git status`
stayed clean throughout, and all real edits landed correctly in the worktree via `Bash`-`cd`-plus-
relative-path calls, cross-verified against `git show`/`sed`), but the failure mode — silent success on
the wrong file — is the worst kind for a coding agent: it produces confidently wrong analysis with no
error signal, and the discipline that prevents it currently doesn't reliably survive compaction.
