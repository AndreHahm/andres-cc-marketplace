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

## EpicenterHQ — `epicenter` (`standalone-commits`)

The `standalone-commits` skill (including its `references/splitting-into-ordered-waves.md` file) began as this plugin's own copy of the `standalone-commits` skill from EpicenterHQ's `epicenter` monorepo, lightly adapted (fixing a cross-reference to a sibling skill that doesn't exist in this plugin, replacing it with a reference to `gitkit`'s own `commit` skill; genericizing one example that named the source project).

- **Author:** Braden Wong (EpicenterHQ)
- **Source:** `EpicenterHQ/epicenter`, `.claude/skills/standalone-commits` and `.agents/skills/standalone-commits`
- **License:** GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later) — `epicenter`'s repository uses a split-license model where only specific `packages/*` (not skills content) are MIT; everything else, including its skills, defaults to AGPL-3.0-or-later per the repository's own `LICENSE` index.

Because the upstream skill is AGPL-3.0-or-later and this plugin's own `LICENSE` is GPL-3.0, this combination is handled under GPLv3 §13 ("Use with the GNU Affero General Public License"), which explicitly permits combining a GPL-3.0 covered work with AGPL-3.0 work into a single combined work — the GPL-3.0 terms continue to apply to `gitkit`'s own GPL-3.0-derived content, while AGPL-3.0's additional terms (notably its network-use clause) apply to the combination as such. `gitkit` is a set of Claude Code skills with no network-service component, so the AGPL network clause has no practical trigger here, but this notice records the combination for transparency.

## Unattributed items

The `git-rebase-sync`, `explain-pr-changes`, and `github-issue-creator` skills were added to this plugin from a staging area whose own provenance could not be confirmed — no `url.txt`/author/license marker was present, and a search of the known external sources cited elsewhere in this notice (`context-engineering-kit`, `claude-code-skills`, `epicenter`) found no match for any of them. They are treated as original content for this plugin. If a source is later identified, this notice should be updated accordingly.

The `dependency-updater`, `merge-pr`, and `manage-codeowners` skills are original content written directly for this plugin — no external source to attribute.

---

This notice reflects provenance as of `gitkit`'s initial bootstrap into this marketplace, updated when `git-rebase-sync`, `explain-pr-changes`, `github-issue-creator`, `standalone-commits`, `dependency-updater`, `merge-pr`, and `manage-codeowners` were added. It does not itself grant or restrict any rights — see this plugin's own `LICENSE` (GPL-3.0) for `gitkit`'s own licensing terms.
