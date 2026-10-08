# Resolve the Plugin Root to the .claude Mirror in This Repo's Own Sessions

## When this applies

Running a command that a skill, slash command, agent, reference or rule documents with a
`${CLAUDE_PLUGIN_ROOT}/...` path, in a session working on this repository itself, when `CLAUDE_PLUGIN_ROOT` is
empty or unset (skills load from the byte-identical `.claude/` mirror there, not from an installed plugin).

## Rule

An empty `CLAUDE_PLUGIN_ROOT` makes a documented `"${CLAUDE_PLUGIN_ROOT}/scripts/x.sh"` expand to `/scripts/x.sh`,
which fails with exit 127. You MUST substitute the mirror root, `.claude/`, under the repo or worktree root (the
session's primary working directory):

- `${CLAUDE_PLUGIN_ROOT}/<dir>/...` → `"$PWD/.claude/<dir>/..."` for a mirrored component dir: `skills`, `agents`,
  `commands`, `hooks`, `rules`, `references` or `assets` (when the plugin has it).
- `${CLAUDE_PLUGIN_ROOT}/scripts/<file>` → `"$PWD/.claude/scripts/<file>"`. Shared scripts are mirrored only for the
  plugins listed under `scripts_mirrors` in `.claude/marketplace-sync.json` (git-kit is one).

`$PWD` is right only while the shell's cwd is that root; otherwise write the root out explicitly.

Substitute the path only while executing a step of an already-dispatched skill, slash command, agent or rule.
Never run a marker-writing helper such as `git-write-marker.sh` on its own to satisfy a guard outside the skill
that owns it.

Confirm the mirrored file exists first. Stop and report in either of two cases: the file is missing, or the
substituted command is still denied. Never fall back to a different command or endpoint.

Do not edit mirrored skill files to hard-code the substitution: `.claude/` must stay byte-identical to `plugins/`.
A pre-approved `allowed-tools` grant is written with the variable, so the substituted command may raise a
permission prompt (not verified against how Claude Code matches grants).

## Incorrect

```
"${CLAUDE_PLUGIN_ROOT}/scripts/git-write-marker.sh" gh-pr-review triaging-dependabot-prs
```
It fails with `/scripts/git-write-marker.sh: No such file or directory` (exit 127), and the session gives up
although the script exists in the mirror.

## Correct

```
"$PWD/.claude/scripts/git-write-marker.sh" gh-pr-review triaging-dependabot-prs
```

## Why

2026-10-08: `triaging-dependabot-prs` stopped before posting a `@dependabot rebase` comment because of the exit 127
above. The script exists at `.claude/scripts/git-write-marker.sh`, and the substituted path wrote the
`git-branch-create` marker that `starting-work` needed in the same session (observed live; no issue filed).
Rewriting the variable into the mirrored text was rejected: it would break the mirror's byte-identity, which the
`Marketplace mirror/export parity` job in `.github/workflows/marketplace-ci.yml` and `plugin-rulebook`'s R19
in-development-mirror exception both depend on.

## Enforcement

Policy gate, no backing hook: the substitution is prose guidance for the session, not a check on the command.
