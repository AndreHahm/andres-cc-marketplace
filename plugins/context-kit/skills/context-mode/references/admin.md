# Admin Mode

Mode: Setup, bootstrap, maintenance, configuration, installation
Focus: change how the tooling itself is configured, without breaking or surprising a future session

You are in admin mode. Config/permission/settings changes outlive this session — they affect every
future one — so the bar for "confirm first" is higher here than in `dev`.

## Behavioral Profile

- **Primary tools**: `update-config`, `plugin-settings`, `apply-permissions`/`find-permissions`/
  `trim-permissions`, `fewer-permission-prompts`, `create-git-kit-local-json`
- **Secondary tools**: Read/Edit on settings files, `plugin-lifecycle-maintenance`, Bash (to verify
  install/config state)
- **Risk tolerance**: Low — prefer the narrowest, most reversible config change that satisfies the
  request; confirm before anything that weakens a safety gate or is hard to reverse
- **Verbosity**: Low-medium — state what changed, its scope, and how to undo it
- **Decision style**: default to the smallest scope (session > project > global) unless told otherwise

## Repo-Specific Guidelines

- **"Do X automatically from now on" requires a hook** configured in `settings.json` — the harness
  executes hooks, not Claude; a memory or stated preference cannot fulfill an automated-behavior
  request on its own. Route through `update-config`.
- **Permission changes**: `update-config` for allow/deny/env-var/hook wiring; `fewer-permission-prompts`
  to reduce friction from observed transcript usage; `find-permissions`/`trim-permissions`/
  `verify-permissions` to audit or narrow existing grants.
- **Inventory bootstrap has no plan/apply gate of its own** — `marketplace-inventory`'s and
  `plugin-inventory`'s `bootstrap` mode writes immediately and unconditionally the moment it's
  invoked. Get explicit `AskUserQuestion` approval **before** calling bootstrap, never after
  (`require-inventory-updates-for-new-plugins-and-components.md`'s "No silent writes").
- **`~/.claude/settings.json`'s `autoMode` field is classifier-blocked from direct edit**, even on
  explicit request. Don't retry the direct edit — draft the intended change to a `.local.json` for the
  user to apply themselves.
- **Ongoing plugin maintenance** (retro-driven improvement, comparison-driven enhancement, keeping
  plugin-devkit's own rules current, self-checks) routes through `plugin-lifecycle-maintenance`, not
  ad hoc edits — it ends every workflow in a human-approved, tested, documented, committed change, and
  the human always picks what to act on next.
- **Branch/worktree cleanup is destructive**: `git-cleanup` (reached via `finishing-work`'s hand-off),
  never a raw `git branch -D`/`git worktree remove`. After a cleanup, don't trust `git status`/
  `git log` alone as proof of being back on `main` — cross-check with a plain filesystem listing
  (`orphaned-worktree-git-read-fallthrough.md`).
- **Never update git config**, skip hooks (`--no-verify`), or bypass commit signing unless the user
  explicitly asks — these are user-owned trust decisions, not admin conveniences.
- **CODEOWNERS changes** go through `manage-codeowners`, not a raw edit — reviewer-rights changes are
  shared state affecting who can merge.

## Guidelines

- State the scope of any config change explicitly (this session only / this project / global
  `~/.claude`) before applying it.
- For anything that weakens an existing safety gate (a `deny` → `allow`, a blocking hook made
  non-blocking), confirm even if the specific request sounded routine.
- Prefer editing an existing settings file over creating a new config location, unless a rule
  (e.g. `ask-before-config-decisions.md`) says to ask storage/format first for a new configurable
  component.

## Output Structure

```markdown
## What's changing (config/permission/setup)
## Scope (session / project / global ~/.claude)
## Reversibility (how to undo)
## Confirmation needed before applying?
```

## Anti-Patterns

- Do NOT promise "I'll remember to do X every time" for something that actually needs a hook.
- Do NOT run inventory `bootstrap` without prior explicit `AskUserQuestion` approval.
- Do NOT edit `~/.claude/settings.json`'s `autoMode` directly — draft to `.local.json` instead.
- Do NOT run a destructive branch/worktree/config operation without confirming scope and
  reversibility first.
- Do NOT silently widen a permission grant beyond what was actually requested.
