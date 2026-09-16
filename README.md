# Andre's Claude Code Plugin Marketplace

> ⚠️ **In Conception & Development** — this marketplace is not yet stable. Plugin names,
> structure, and behavior can change without notice, and nothing here should be treated as a
> finished, production-ready release. Use at your own risk.

A [Claude Code](https://docs.claude.com/en/docs/claude-code) plugin marketplace: a collection of
plugins that extend Claude Code with skills, agents, commands, hooks, and rules for plugin
development, git/GitHub workflows, session analysis, and more.

## Plugins

| Plugin | Description |
|---|---|
| [`plugin-devkit`](./plugins/plugin-devkit) | Claude Code plugin development — create, validate, audit, and grade plugins and their components. |
| [`git-kit`](./plugins/git-kit) | Git and GitHub workflow toolkit: branching, committing, PRs, reviews, merging, cleanup, and more. |
| [`analysis-kit`](./plugins/analysis-kit) | Session analysis toolkit: retrospectives, behavior/outcome auditing, recurring-pattern mining. |
| [`codex-kit`](./plugins/codex-kit) | Delegate work to OpenAI's Codex CLI from Claude Code, with independent verification. |
| [`workmanagement-kit`](./plugins/workmanagement-kit) | Notion/Linear integration for knowledge capture and tracked execution work. |
| [`session-kit`](./plugins/session-kit) | Claude Code session management: list, search, diff, export, resume, and clean up sessions. |
| [`context-kit`](./plugins/context-kit) | Automatic, hook-driven context-window management for Claude Code sessions. |
| [`example-plugin`](./plugins/example-plugin) | Minimal example/test-fixture plugin used by plugin-devkit's own tooling. |

See each plugin's own README for details.

## Installation

Add this marketplace to Claude Code, then install the plugin(s) you want:

```
/plugin marketplace add AndreHahm/andres-cc-marketplace
/plugin install <plugin-name>@andres-cc-marketplace
```

## Community

- [CONTRIBUTING.md](./CONTRIBUTING.md) — how to propose changes
- [GOVERNANCE.md](./GOVERNANCE.md) — project roles and decision-making
- [CODE_OF_CONDUCT.md](./CODE_OF_CONDUCT.md) — community standards
- [SECURITY.md](./SECURITY.md) — how to report a vulnerability

## License

Apache-2.0 — see [LICENSE](./LICENSE).
