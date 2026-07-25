# Third-Party Notices

`plugin-devkit` is not a bundled/vendored-dependency package — it does not ship third-party code, libraries, or MCP servers as part of its own tree. This notice instead documents the provenance of two other projects this plugin's content and structure originated from or were adapted from.

## Anthropic — `plugin-dev` (original scaffold)

`plugin-devkit` began as this repository's own copy of Anthropic's official `plugin-dev` example plugin from the Claude Code Plugins directory.

- **Source:** [`anthropics/claude-plugins-official`, `plugins/plugin-dev`](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/plugin-dev)
- **License:** Apache License 2.0

Since that starting point, this plugin has diverged substantially — over 150 commits ahead of the point it was copied from, with the large majority of its current skills, agents, commands, rules, and workflows newly built or substantially rewritten for this repository's own conventions. See `README.md` for the plugin's current scope.

This repository's own `LICENSE` file is the same Apache License 2.0 text as the original, consistent with that starting point.

## Reflexive-Claude-Code (author: Wei Hung)

Some structural ideas and patterns in `plugin-devkit` were adapted from **Reflexive-Claude-Code**, a separate Claude Code plugin collection, after it was installed and used locally alongside this plugin's own development.

- **Author:** Wei Hung
- **Source:** [`wayne930242/Reflexive-Claude-Code`](https://github.com/wayne930242/Reflexive-Claude-Code)
- **License:** MIT License

No code from this project is vendored into `plugin-devkit`'s own tree — ideas and patterns observed while using it informed some of this plugin's independently-implemented design choices.

---

This notice reflects provenance as of the `plugin-dev` → `plugin-devkit` rename. It does not itself grant or restrict any rights — see this repository's own `LICENSE` (Apache License 2.0) for `plugin-devkit`'s own licensing terms.
