# CLAUDE.md Guidelines

Guidance for writing and maintaining a project's `CLAUDE.md` file. `CLAUDE.md` is project-scoped context that Claude Code loads automatically at session start — it is not a place for procedures, exhaustive references, or personal preferences. This reference covers what belongs in it, what doesn't, how it interacts with `.claude/rules/`, imports, and `AGENTS.md`, and how to keep it from drifting out of date.

**Note:** these are guidelines for a project's own `CLAUDE.md`. A `CLAUDE.md` placed at a *plugin's* root behaves differently — see [Plugin-Scope Notes](#plugin-scope-notes) below and `references/plugin-architecture.md`.

## Length and Budget

- Keep `CLAUDE.md` under 200 lines. 60 lines is the practical optimum for most projects.
- Content that pushes the file past 200 lines is a strong signal it belongs somewhere else — in `.claude/rules/`, a skill, or a hook — not that it needs a bigger file.
- Avoid long architecture overviews or full directory trees. A brief pointer to where things live (e.g., "core logic is in `src/core/`, tests in `tests/`") is acceptable; detailed structure documentation belongs in `README.md`.

## What Doesn't Belong in CLAUDE.md

- **Scoped coding conventions** — focused style or convention rules (naming, formatting, error-handling patterns for a specific language or directory) belong in `.claude/rules/` files, not CLAUDE.md.
- **Multi-step workflows** — step-by-step procedures belong in `.claude/skills/`. Don't embed a workflow's steps directly in CLAUDE.md.
- **Standard language conventions** — don't include conventions Claude already knows (e.g., "use camelCase in JavaScript"). Only include project-specific deviations from the default.
- **README content** — don't restate what's already in `README.md`. Duplication wastes context and drifts out of sync with the source of truth.
- **Package manifests** — don't restate `package.json`, `pyproject.toml`, `Cargo.toml`, or similar. Tech stack and dependencies are derivable directly from those files.
- **Content already in `.claude/rules/`** — don't duplicate a rule file's content in CLAUDE.md. Rules are auto-loaded already; duplication wastes tokens and the two copies will eventually drift apart.

## Quality Bar for Instructions

Every instruction in CLAUDE.md must be specific, verifiable, non-obvious, and actionable. Vague instructions like "write clean code" or "follow best practices" give the model nothing to act on and should be removed or replaced with something concrete.

- Prefer "use `snake_case` for Python file names" over "follow naming conventions."
- Prefer "run `pytest tests/` before committing" over "make sure tests pass."
- If an instruction can't be checked (by the model or a reviewer), it isn't actionable — rewrite it or drop it.
- Any path referenced in CLAUDE.md (a file, a directory, a script) must actually exist and be reachable. Verify referenced paths with Glob or Bash after writing or editing CLAUDE.md; a stale reference is worse than no reference.

## Enforcement

Text-only instructions in CLAUDE.md are advisory — models following them achieve roughly 70% compliance, not 100%. Two consequences follow:

- **Linter-enforceable or mechanically checkable rules** (formatting, import order, forbidden patterns) should be enforced by a hook, not just stated in CLAUDE.md — a hook gives deterministic enforcement where prose only gives a reminder.
- **Any `MUST NEVER` directive about a destructive or irreversible action** (deleting data, force-pushing, dropping a database, etc.) must be backed by a deterministic enforcement mechanism — a hook or a permission rule — in addition to the textual instruction. The instruction alone is not sufficient for anything destructive.

## Imports and the AGENTS.md Bridge

- `CLAUDE.md` supports `@path` imports. Use them for organization only, not for reducing token usage — imported files are loaded in full at session start and count against context just like inline content would.
- Imports recurse up to four hops; don't build import chains deeper than that.
- Claude Code reads `CLAUDE.md`, not `AGENTS.md`. If a repository already maintains an `AGENTS.md` for another agent framework, create a `CLAUDE.md` that imports it (`@AGENTS.md`) and adds any Claude-specific instructions, rather than duplicating its content into CLAUDE.md by hand.

## Plugin-Scope Notes

- A `CLAUDE.md` at a plugin's root is not the same thing as a project's `CLAUDE.md` — it is not loaded as project context at all. Everything above in this file describes a project's own `CLAUDE.md`; it does not apply to plugin-root files. See `references/plugin-architecture.md` for what plugins should use instead to deliver runtime context.
- `CLAUDE.md` itself is project-scope context, meant for project-wide guidance that applies to everyone working in the repository. It is not the place for machine-specific setup or an individual's personal preferences — those belong in a personal/local configuration layer, not in a file that's checked into the repo and shared with the whole team.

## Nested CLAUDE.md for Subdirectories

Guidance specific to a subdirectory (e.g., conventions that only apply inside `services/billing/`) belongs in a nested `CLAUDE.md` inside that directory, not in the root `CLAUDE.md`. This keeps the root file focused on cross-cutting, project-wide context and lets subdirectory-specific detail load only when Claude is actually working in that area.

## Maintenance

Instruction layers drift: CLAUDE.md, nested CLAUDE.md files, `.claude/rules/`, skills, agents, and hooks are all edited independently over time, and Claude may resolve contradictions between them arbitrarily. Periodically audit all of these layers together for conflicts, duplicated instructions, and stale references — don't assume a rule written months ago still matches current practice.

## Optional Pattern: Conditional Blocks

For task-specific guidance that should only activate in narrow contexts, `<important if="...">` blocks are an optional pattern — they let a section of CLAUDE.md apply only when a stated condition holds, rather than always being in scope. Treat this as an internal convention rather than a required structure; plain sections are fine when the guidance applies unconditionally.
