# Plugin File Surface: Plugin Scope vs. CWD Scope

Shared file-enumeration definition used by any reviewer agent that needs to scan "everything in and around a plugin" rather than a single component. Currently used by `language-reviewer`, `external-references-reviewer`, `consistency-reviewer`, `completeness-reviewer`, and `scripts-reviewer` — keep all five in sync with this file rather than letting each redefine its own scope inline.

## The Two Scopes

**Plugin scope:** the target plugin's own directory tree — `plugins/<plugin-name>/**`, including `skills/`, `agents/`, `commands/`, `hooks/`, `scripts/`, any `rules/` the plugin ships, and the plugin's own root-level `CLAUDE.md`, `AGENTS.md`, `README.md`, `CONTRIBUTING.md` if present. Also include the plugin's `.claude/` in-development staging mirror if one exists (per R19's documented mirror exception) — it's the same content under a different path, not a separate scope.

**CWD scope:** the project-root `CLAUDE.md`, `AGENTS.md`, `README.md`, `CONTRIBUTING.md` (if they exist and are distinct from the plugin's own copies), the repo's own `.claude-plugin/marketplace.json` if present, and any project-level `.claude/skills/`, `.claude/agents/`, `.claude/commands/`, `.claude/rules/` components that do **not** belong to the plugin being reviewed (e.g. standalone project skills). **CWD scope explicitly excludes the internal component trees of *other* plugins** (e.g. `plugins/<other-plugin>/**` for any plugin other than the one being reviewed, or a monorepo's sibling projects) — those get reviewed independently, on their own terms, when someone targets them directly. Reviewing them incidentally while scoped to a different plugin produces noise disproportionate to the task.

State both resolved absolute paths in the report header (mirrors R19's own path-resolution discipline).

## Gitignore Exclusion

Before including any file found via the enumeration below in either scope, exclude gitignored paths per `${CLAUDE_SKILL_DIR}/references/gitignore-exclusion.md`. This applies to both scopes — a gitignored draft or backup directory (`.temp/`, `.draft/`, `.backup/`) is not part of what the plugin or project actually ships, in either scope.

## File Enumeration

For **each** scope, Glob broadly rather than narrowly — the goal is every text file a human or Claude would read as documentation or instruction, not just `SKILL.md`/agent/command files:

- All `SKILL.md`, `agents/*.md`, `commands/*.md`, rule `*.md` files
- All `references/*.md`, `workflows/*.md`, `examples/*.md`, `templates/*` files
- All scripts under `scripts/` and `hooks/` (any extension — `.sh`, `.py`, `.js`, `.ts`, etc.) and any script referenced from a `SKILL.md`/agent/command body even if it lives elsewhere in the plugin
- Config/text assets: `hooks/hooks.json`, `.claude-plugin/plugin.json`, any `marketplace.json`, any `assets/*` text file (`.json`, `.txt`, `.md`) — JSON has no comments, but string values (descriptions, messages) still count
- `CLAUDE.md`, `AGENTS.md`, `README.md`, `CONTRIBUTING.md` wherever they're found in either scope

Skip binary/non-text assets (images, etc.) — they aren't checkable by any of the reviewers that use this definition.

## Consumer-Specific Notes

A consuming agent may apply scope-dependent severity differently — e.g. `language-reviewer` treats plugin-scope findings as blocking and CWD-scope findings as non-blocking warnings. That severity mapping belongs in the consuming agent's own file, not here; this file defines *what to scan*, not *how to score what's found*.
