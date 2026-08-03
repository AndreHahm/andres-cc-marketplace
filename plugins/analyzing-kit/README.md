# Analyzing Kit

Session analysis toolkit for Claude Code: retrospective SWOT analyses, self-critiques, and self-reflections for every skill, sub-agent, command, workflow-skill, and rule used across a session or date range, with classified improvement suggestions grouped by component and priority.

## Plugin Target

- Turn a completed development session into a concrete, prioritized improvement backlog
- Catch systemic issues that span more than one component, not just isolated bugs
- Re-verify prior artifacts' own "still open" claims against current repo state instead of trusting them at face value

## Overview

`analyzing-kit` provides a single skill, `analyzing-sessions-by-project-and-time`, that inventories every component active in a session (or date range), produces a SWOT and a self-critique/self-reflection for each, and derives classified, prioritized improvement suggestions from the findings. Reports are persisted to `.claude/output/analyzing-sessions-by-project-and-time/`, one file per run, so later runs can link back to a specific prior retrospective.

This plugin is standalone — it has no dependency on any other plugin.

## Installation

```bash
/plugin install analyzing-kit@andres-cc-marketplace
```

Or for local development:

```bash
cc --plugin-dir /path/to/analyzing-kit
```

## Quick Start

```bash
# Analyze the current conversation
> /analyzing-sessions-by-project-and-time

# Analyze everything since a given date
> /analyzing-sessions-by-project-and-time 2026-07-10
```

1. Choose scope — this conversation, a start date, or today.
2. Confirm the component inventory before the full analysis runs.
3. Review SWOT + critique output in P1 → P3 priority order.
4. Act on the **Top 5 Actions**, then check the persisted report path.

## Skills

| Skill | Use when |
|---|---|
| `analyzing-sessions-by-project-and-time` | Running a post-session retrospective, auditing skill/agent/rule performance, or building a prioritized improvement backlog from a session or date range |

## Attribution

`analyzing-kit` began as a standalone port of the `analyzing-sessions` skill originally built inside this marketplace's `plugin-devkit` plugin, renamed to `analyzing-sessions-by-project-and-time` and decoupled from that plugin's other components so it has no cross-plugin dependency.
