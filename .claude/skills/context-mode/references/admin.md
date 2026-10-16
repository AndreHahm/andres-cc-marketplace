# Admin Mode

Mode: configuration, permissions, setup, and the post-merge cleanup session on the main checkout
Focus: change how the tooling is configured or remove branches and worktrees, without breaking or
surprising a future session

Config and permission changes outlive this session, and cleanup is destructive, so the bar for
"confirm first" is higher here than in ordinary work.

## Posture

- **Risk tolerance**: low. Prefer the narrowest, most reversible change that satisfies the request.
- **Scope**: default to the smallest scope (session, then project, then global) unless told otherwise.
  State the scope before applying anything.
- **Reversibility**: say how to undo every change.
- **Weakening a safety gate** (a deny becoming an allow, a blocking hook made non-blocking, a blanket
  `Bash` allow): name the implication, offer the narrower alternative, and confirm even when the request
  sounded routine.
- **Verbosity**: low to medium. State what changed, its scope, and how to undo it.

## Output structure

```markdown
## What's changing (config, permission, setup or cleanup)
## Scope (session / project / global ~/.claude)
## Reversibility (how to undo)
## Confirmation needed before applying?
```

## Repo-specific routing

- "Do X automatically from now on" needs a hook in `settings.json`; a memory or stated preference cannot
  do it. Route through `update-config`.
- Permission friction: `fewer-permission-prompts` builds an allowlist from observed use;
  `pdk-find-permissions`, `pdk-trim-permissions` and `pdk-verify-permissions` audit or narrow grants.
- Inventory `bootstrap` writes immediately with no plan step. Get `AskUserQuestion` approval before it
  runs, never after.
- `~/.claude/settings.json`'s `autoMode` is classifier-blocked from direct edits. Draft the change to a
  `.local.json` for the user to apply.
- Post-merge cleanup: `finishing-work` hands branch and worktree deletion to `git-cleanup`; never a raw
  `git branch -D` or `git worktree remove`. After a worktree is removed, a git read can fall through to
  the primary checkout, so cross-check with a plain filesystem listing before trusting `git status`.
- Never change git config, skip hooks (`--no-verify`) or bypass signing unless the user asks. CODEOWNERS
  changes go through `manage-codeowners`.

## Anti-patterns

- Do not promise "I'll remember to do X every time" for something that needs a hook.
- Do not run inventory `bootstrap` without prior approval.
- Do not run a destructive branch, worktree or config operation without confirming scope and
  reversibility first.
- Do not widen a permission grant beyond what was asked.
