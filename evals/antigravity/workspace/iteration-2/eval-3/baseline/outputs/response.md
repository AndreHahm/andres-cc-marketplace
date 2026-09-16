# Migrating a Claude Code setup to Antigravity

Short answer up front: **I can't give you a fully verified, step-by-step migration guide**, because I don't have confirmed, current documentation for Antigravity's exact configuration file formats/locations in front of me, and I don't want to invent specifics that might be wrong or out of date for you. What I can do is give you a solid mental model, a safe migration process, and the exact questions to answer from Antigravity's own docs/UI before you flip over. Treat the concrete file paths below as "where to look," not gospel — confirm each one against Antigravity's current settings/docs, since it's a fast-moving product and details can change between releases.

## 1. Inventory what you actually have in Claude Code

Before touching Antigravity, get a clear list of what you're moving. In a typical Claude Code setup that's:

- **Skills** — `~/.claude/skills/` (user-level) and `<project>/.claude/skills/` (project-level), each a folder with a `SKILL.md` plus any `references/`, `scripts/`, `assets/`.
- **Memory** — `~/.claude/CLAUDE.md` (global) and `<project>/CLAUDE.md` / `CLAUDE.local.md` (project-level, some gitignored). Also check `~/.claude/settings.json` for any persisted preferences.
- **MCP servers** — your MCP client config, typically `~/.claude.json` (or `.mcp.json` at the project level), listing each server's command/args/env or URL.

Run something like:
```
ls ~/.claude/skills
ls .claude/skills
cat CLAUDE.md
cat ~/.claude/CLAUDE.md
cat ~/.claude.json   # or .mcp.json
```
so you have a concrete checklist rather than migrating "from memory."

## 2. Map each piece to its Antigravity equivalent

- **MCP servers** — this is the easiest part. MCP is an open, cross-vendor protocol, and most modern agentic IDEs (Antigravity included, as far as I'm aware) support connecting to MCP servers via a config file listing server name → command/args/env (stdio) or URL (SSE/HTTP). If Antigravity supports MCP, you should be able to take your existing server *definitions* (the actual `npx`/`uvx`/binary commands and their env vars/API keys) and re-register them in Antigravity's own MCP settings UI or config file. You likely won't need to change the servers themselves — just re-point the client config. Confirm the exact file/UI location in Antigravity's settings before assuming a path.
- **Memory (CLAUDE.md)** — CLAUDE.md is Claude Code's own convention for persistent, always-loaded project/user instructions. Antigravity almost certainly has *some* mechanism for persistent context or "rules" (agentic IDEs generally do — a rules file, a system-prompt override, or per-project instructions), but the exact filename/format is Antigravity-specific and not something I have confirmed in front of me. Practically: take the content of your CLAUDE.md files (your conventions, guardrails, workflow rules) and re-author them into whatever Antigravity's equivalent context/instructions mechanism is. Don't assume it's a drop-in file copy — check whether Antigravity expects markdown, YAML, or something else, and whether it has a size/token budget like CLAUDE.md does.
- **Skills** — this is the part I'd flag as most likely to *not* have a clean 1:1 equivalent. Claude Code's Agent Skills (`SKILL.md` + supporting files, with progressive disclosure and a description-based auto-activation system) are a Claude-specific packaging format. If Antigravity has its own extension/plugin/custom-workflow mechanism, you'll likely need to manually port the *content* of each skill (the procedure, the reference material, any scripts) into whatever structure Antigravity uses — not just copy the folder over. For each skill, ask: what's the trigger condition, what's the actual instructions/procedure, and what supporting scripts/references does it depend on? Re-express those in Antigravity's format rather than assuming the file will just work.

## 3. A safe migration process

1. **Freeze and export.** Get your Claude Code skills, CLAUDE.md contents, and MCP server list into one place (e.g., a scratch folder) as your source of truth.
2. **Check Antigravity's own docs/settings UI first**, specifically for: (a) does it support MCP, and where do servers get registered; (b) what's its persistent-context/rules mechanism and its format/limits; (c) does it have anything analogous to reusable skills/workflows, and how are they packaged.
3. **Migrate MCP servers first** — lowest risk, since the servers themselves don't change, only the client registering them.
4. **Migrate memory/rules next** — port CLAUDE.md content into Antigravity's equivalent, adapting format as needed rather than copy-pasting blindly.
5. **Migrate skills last, one at a time** — pick your most-used skill, port its logic/content manually, and test it in Antigravity before doing the rest. Skills are the most bespoke piece, so batch-converting all of them before validating the pattern risks redoing the work.
6. **Run both side by side for a while.** Don't delete or disable your Claude Code setup until you've confirmed the Antigravity equivalents actually work for your real workflows — keep Claude Code as a fallback during the transition.
7. **Re-check secrets/env vars.** MCP servers and any credentials referenced in CLAUDE.md or skills often carry API keys/tokens. When re-registering servers or re-authoring instructions in Antigravity, make sure secrets go through Antigravity's own secret-handling mechanism rather than getting hardcoded into a new config file.

## What I'd do next if I were you

Open Antigravity's settings/docs and answer three concrete questions: (1) its MCP config location and format, (2) its persistent-instructions/rules mechanism and format, (3) whether it has any packaged-skill/extension concept at all. Once you have those three answers, the migration above becomes a mechanical port rather than a guess. If you paste me Antigravity's actual docs or config file examples, I can help you map your specific CLAUDE.md/skills/MCP config into its format precisely instead of speaking in generalities.
