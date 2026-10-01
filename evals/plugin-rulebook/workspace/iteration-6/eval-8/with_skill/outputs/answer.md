# R34 (Reference Integrity) results for `example-kit/demo-skill`

R34 is REQUIRED. A markdown link that resolves to nothing is Critical. So is a path that leaves the skill folder and lands outside the allowed folders. A link resolves against the directory of the file that contains it. A path that leaves the skill folder may land only in a plugin-root `references/` or `assets/`. It may land in `scripts/` only for plugins listed in `scripts_mirrors`. `..` alone is not a finding.

| # | Reference | Finding? | Severity | Fix |
|---|---|---|---|---|
| 1 | `../../references/shared-contract.md` | No | PASS | None. From `skills/demo-skill/`, `../..` reaches the plugin root. The target is in plugin-root `references/`, which the `.claude/` mirror carries for every plugin, and the file exists. |
| 2 | `../../docs/design-notes.md` | Yes | Critical (blocking) | The file exists, but it escapes into plugin-root `docs/`, which the `.claude/` mirror does not carry. The same relative path would resolve in `plugins/example-kit/` but not in `.claude/`. Move the shared content into plugin-root `references/` (or `assets/`) and relink to `../../references/design-notes.md`. Alternatively, inline it or put it under the skill's own `references/`. |
| 3 | `references/missing-guide.md` | Yes | Critical (blocking) | This is a markdown link that resolves to nothing, so it is a dead link. It is not the bare-backtick ADVISORY case, which applies only to unlinked backticked pointers. Create `references/missing-guide.md` in the skill, correct the path, or remove the link. |

## Notes

- `example-kit` is not in `scripts_mirrors`, but that has no effect here. None of the three paths targets `scripts/`. Only references 1 and 2 leave the skill folder, and those targets are `references/` and `docs/`. The `scripts/` carve-out is irrelevant.
- `.claude/marketplace-sync.json`'s `scripts_mirrors` list (read from the worktree) is plugin-devkit, git-kit, analysis-kit, session-kit, workmanagement-kit and context-kit. `example-kit` is not on it.
- R34 is forward-looking and applies because `demo-skill` is newly created.
- Overall verdict: FAIL. There are two Critical findings (2 and 3) and one pass (1).
