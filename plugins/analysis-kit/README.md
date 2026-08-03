# Analysis Kit

Session analysis toolkit for Claude Code: retrospective SWOT analyses, self-critiques, and self-reflections for every skill, sub-agent, command, workflow-skill, and rule used across a session or date range, plus tool and developer-framework usage auditing, with classified improvement suggestions grouped by component and priority.

## Plugin Target

- Turn a completed development session into a concrete, prioritized improvement backlog
- Catch systemic issues that span more than one component, not just isolated bugs
- Re-verify prior artifacts' own "still open" claims against current repo state instead of trusting them at face value
- Identify which external tools and developer frameworks a session actually used, and whether a framework's execution companion stayed within its subordinate role

## Overview

`analysis-kit` provides two skills. `analyzing-plugin-components` (renamed from `analyzing-sessions-by-project-and-time`) inventories every component active in a session (or date range), produces a SWOT and a self-critique/self-reflection for each, and derives classified, prioritized improvement suggestions from the findings. Reports are persisted to `.claude/output/analyzing-plugin-components/`, one file per run, so later runs can link back to a specific prior retrospective. `analyzing-tool-and-framework-use` inventories which external tools a session actually invoked, auto-detects which developer framework(s) the project uses (GSD, OpenSpec, Speckit, BMAD, GG-SAD, or an unrecognized "other" framework), and — when a detected framework pairs a governing method with a subordinate execution companion — checks whether the companion stayed within its role.

This plugin is standalone — it has no dependency on any other plugin.

## Installation

```bash
/plugin install analysis-kit@andres-cc-marketplace
```

Or for local development:

```bash
cc --plugin-dir /path/to/analysis-kit
```

## Quick Start

```bash
# Post-session component retrospective, current conversation
> /analyzing-plugin-components

# Post-session component retrospective, since a given date
> /analyzing-plugin-components 2026-07-10

# Tool and framework use for the current conversation
> /analyzing-tool-and-framework-use
```

1. Choose scope — this conversation, a start date, or today.
2. For `analyzing-plugin-components`: confirm the component inventory before the full analysis runs. For `analyzing-tool-and-framework-use`: framework detection runs before the tool inventory.
3. Review SWOT/critique or tool/framework findings in priority order.
4. Act on the recommendations, then check the persisted report path.

## Skills

| Skill | Use when |
|---|---|
| `analyzing-plugin-components` | Running a post-session retrospective, auditing skill/agent/rule performance, or building a prioritized improvement backlog from a session or date range |
| `analyzing-tool-and-framework-use` | Auditing which external tools or developer frameworks a session actually used, or checking whether a framework's execution companion stayed within its subordinate role |

## Configuration

`analysis-kit` ships a git-tracked default at `analysis-kit.settings.json` (plugin root) with a `framework_override` field, used by `analyzing-tool-and-framework-use`'s auto-detection. Set an optional `.claude/analysis-kit.local.json` (gitignored, per-project) with the same field to override auto-detection for that project — the local override always wins over both the plugin default and auto-detection.

## License

Apache-2.0 — see [`LICENSE`](./LICENSE).

## Attribution

`analysis-kit` began as a standalone port of the `analyzing-sessions` skill originally built inside this marketplace's `plugin-devkit` plugin, renamed to `analyzing-sessions-by-project-and-time` and decoupled from that plugin's other components so it has no cross-plugin dependency.
