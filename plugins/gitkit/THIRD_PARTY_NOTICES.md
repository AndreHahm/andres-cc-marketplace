# Third-Party Notices

`gitkit` is not a bundled/vendored-dependency package — it does not ship third-party code, libraries, or MCP servers as part of its own tree. This notice instead documents the provenance of two other projects this plugin's skills originated from or were adapted from.

## NeoLabHQ — `context-engineering-kit` (`plugins/git`)

The `commit`, `create-pr`, `git-notes`, and `git-worktrees` skills began as this plugin's own copies of the `git` plugin from NeoLabHQ's `context-engineering-kit`, lightly adapted (e.g. dropping the emoji convention from commit messages, simplifying the branch-naming pattern).

- **Author:** Vlad Goncharov (NeoLabHQ)
- **Source:** [`NeoLabHQ/context-engineering-kit`, `plugins/git`](https://github.com/NeoLabHQ/context-engineering-kit/tree/master/plugins/git)
- **License:** GNU General Public License v3.0 (GPL-3.0)

Because the upstream project is GPL-3.0 licensed, this plugin's own `LICENSE` file carries forward the same GPL-3.0 terms rather than this repository's top-level Apache-2.0 license — required by GPL-3.0's copyleft terms for a work based on GPL-3.0 code. This differs from other plugins in this marketplace (e.g. `plugin-devkit`, which is Apache-2.0) and is intentional.

The `git-bisect`, `git-cleanup` skills and the `git-status`, `sync-branch`, `update-branch-name` commands in this plugin are not derived from `context-engineering-kit` and are not covered by this notice.

## fernandezbaptiste — `claude-code-skills` (`github-ops`)

The `gh-operations` skill (including its `references/` files) began as this plugin's own copy of the `github-ops` skill from `claude-code-skills`.

- **Source:** [`fernandezbaptiste/claude-code-skills`, `github-ops`](https://github.com/fernandezbaptiste/claude-code-skills/tree/main/github-ops)
- **License:** MIT License

---

This notice reflects provenance as of `gitkit`'s initial bootstrap into this marketplace. It does not itself grant or restrict any rights — see this plugin's own `LICENSE` (GPL-3.0) for `gitkit`'s own licensing terms.
