Good news: most of what you've built is portable *in spirit*, but Claude Code and Antigravity aren't drop-in compatible — different vendor, different agent runtime, different config file formats. So this is a "map and rebuild," not a "copy-paste." A few assumptions I'm making up front (correct me if wrong):

- By "skills" you mean Claude Code's Agent Skills (`SKILL.md` + supporting scripts/references, using progressive disclosure).
- By "memory" you mean your `CLAUDE.md` files (global `~/.claude/CLAUDE.md` and per-project) plus any session/memory-tool state, not a specific third-party memory plugin.
- "The works" also implies commands, subagents, hooks, and MCP servers — I'll cover those too since they're usually part of the same `.claude/` setup.

## Step 1: Inventory what you actually have

Before touching Antigravity, get a clean list of your current Claude Code config:

```
~/.claude/CLAUDE.md              # global memory/instructions
~/.claude/settings.json          # global settings, permissions
~/.claude/skills/                # personal skills, if any
<project>/.claude/CLAUDE.md      # project memory
<project>/.claude/skills/        # project skills
<project>/.claude/agents/        # subagents
<project>/.claude/commands/      # slash commands
<project>/.claude/hooks/ + settings.json hooks   # event hooks
<project>/.mcp.json or settings  # MCP server configs
```

Skills and commands can also come from installed plugins/marketplaces, so check `~/.claude/plugins/` or your marketplace config too if you've installed any (sounds like you have, given this repo).

## Step 2: Understand what Antigravity actually supports today

This is the part I can't give you with full confidence — Antigravity is a newer, fast-moving product (Google's agentic IDE, built on a VS Code-style fork, oriented around an "Agent Manager" and multiple parallel agent surfaces). Before mapping anything, check Antigravity's current docs/changelog for:

- Does it have a persistent "rules"/"instructions" file analogous to `CLAUDE.md` (some tools call this `AGENTS.md`, `.rules`, or a project-settings field)?
- Does it support MCP servers natively? (High-confidence yes in general — MCP is an open, increasingly standard protocol — but confirm the exact config file format/location, since it won't be `.mcp.json` verbatim.)
- Does it have anything like Skills (a discoverable, progressively-loaded capability bundle), or only a flatter "custom tool"/"extension" model?
- Does it support hook-like lifecycle events (pre/post tool-use), or is that concept Claude-Code-specific?
- Does it support named subagents/multi-agent delegation, or is "Agent Manager" a different, coarser-grained thing (multiple independent agent sessions rather than in-session subagent dispatch)?

I don't want to assert specifics I'm not certain are current, since this product's feature set is evolving quickly — check the live docs rather than trusting a mental snapshot here.

## Step 3: Map component-by-component

| Claude Code concept | Migration approach |
|---|---|
| **MCP servers** | Most portable piece. MCP is a protocol, not a Claude-only thing — if Antigravity speaks MCP, just point it at the same server binaries/configs you already run. Reformat the config file, don't rebuild the servers. |
| **CLAUDE.md (memory/instructions)** | Port the *content*, not the file. Find Antigravity's equivalent instructions/rules surface and paste your standing instructions in there. If there's no direct equivalent, fold the most important always-needed rules into whatever system/project-prompt field it does expose — you may not get the same hierarchical (global → project → local) precedence Claude Code gives you, so prioritize what's load-bearing. |
| **Skills** | The least portable piece, because `SKILL.md`'s progressive-disclosure model (a short description that triggers loading, then deeper reference files) is fairly specific to how Claude Code's own model decides what to load. If Antigravity has no equivalent, you have two fallback options: (1) flatten a skill's guidance into plain reference docs the agent can be told to read, or (2) if the skill's value is really "run this deterministic logic," reimplement it as a callable tool/MCP server instead of a prose skill — that survives the migration much better than prose does. |
| **Subagents** | Depends entirely on whether Antigravity has an in-session delegation concept vs. only separate parallel agent sessions. If it's the latter, you may need to restructure subagent-based workflows into separate agent runs coordinated by you, rather than in-session dispatch. |
| **Slash commands** | If Antigravity supports custom commands/snippets, recreate the useful ones directly — these are usually short enough to hand-port. |
| **Hooks** | Likely the biggest architectural gap. If there's no lifecycle-hook system, anything you relied on hooks for (auto-formatting, blocking dangerous commands, injecting context at session start) may need to move to an external wrapper script, a git hook, or just get dropped if there's no equivalent extension point. |

## Step 4: Migrate in priority order, not all at once

1. **MCP servers first** — highest portability, immediate payoff, lets you validate the new environment works at all.
2. **Core memory/instructions** — the handful of rules you'd be lost without.
3. **Your 3-5 most-used skills**, reimplemented in whatever form Antigravity supports best (prose doc vs. tool).
4. **Everything else**, skill-by-skill or command-by-command, only once you've confirmed the pattern works — don't try to port a large `.claude/` tree in one shot, since you'll be discovering Antigravity's real constraints as you go.

## A question worth answering before you start

Do you want *full parity* (recreate everything, even rarely-used skills/hooks), or just the *highest-value subset* (memory + your most-used skills + MCP servers)? Given the architectural gaps above (especially hooks and skills), full parity may not even be achievable depending on what Antigravity currently exposes — so it's worth deciding your actual bar for "done" before you sink time into porting low-value pieces.

If you can share Antigravity's actual current docs or config file layout, I can turn this into a concrete field-by-field mapping instead of a conceptual one.
