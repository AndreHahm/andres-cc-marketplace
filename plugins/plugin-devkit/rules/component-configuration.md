# Component Configuration

## When this applies

Designing or building a plugin/skill/command whose behavior should vary — a threshold, a toggle, a default that differs per user or per project. Not every component needs configuration; this only applies once the need for it is real.

## Rule

Before writing any config-reading logic, ask the user via `AskUserQuestion`:

1. **Storage**: a git-tracked, shippable config file (defaults that travel with the plugin); a local-only config file (gitignored, user/project-specific overrides); or both.
2. **Format**: JSON, YAML, or a `CLAUDE.md`/`CLAUDE.local.md`-style markdown/instruction file.

Don't default silently to whatever this repo's most recent precedent happened to use — the right answer depends on the component (does it need per-project overrides at all? does a human need to hand-edit it, favoring a commentable format over strict JSON?).

## Precedent, not a default

`git-kit`'s own settings are the working example of the "both" answer: a git-tracked `git-kit.settings.json` at the plugin root carries the defaults, and an optional `.claude/git-kit.local.json` (gitignored, untracked) overrides specific fields per project — with a trust-boundary check (`commit`'s `commit_confirm_before_commit`/`commit_auto_stage` handling) that refuses to honor safety-weakening fields from a *tracked* copy of the local file, since a tracked copy could have been committed by anyone with repo write access. That trust-boundary pattern is worth reusing whenever a local-config answer includes fields that weaken a safety gate or trigger further automation — but the storage/format choice itself is still a per-component decision, not something to assume from this one example.

## Why

A configurable component built with the wrong storage or format choice is a real rework cost later — a JSON file the user actually wanted to hand-edit with comments, or a shippable-only config that a team then can't override per project without editing the plugin's own tracked defaults. Asking once, before any config-reading logic exists, is cheaper than migrating a working format after the fact.
