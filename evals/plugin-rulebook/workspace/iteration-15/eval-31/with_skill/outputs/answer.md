# R34 Reference Integrity: demo-skill (example-kit) SKILL.md

Scope: `demo-skill` is a structurally-modified skill, so R34 applies. Only prose outside fenced blocks is checked.

Rules applied (from `plugins/plugin-devkit/skills/plugin-rulebook/SKILL.md`, R34, and the R34 row of `references/compact-rule-checklist.md`):
- A relative markdown link or `${CLAUDE_SKILL_DIR}/...` path that does not resolve is Critical.
- A link that leaves the skill folder is Critical unless it lands in plugin-root `references/` or `assets/` (or `scripts/` for `scripts_mirrors` plugins). `docs/`, repo-root files and sibling skill folders are all Critical.
- A bare backticked `references/<file>.md` missing from the skill's own `references/` is ADVISORY.
- Bare backticked paths other than `references/<file>.md` (for example `.github/...` or `agents/...`) are not resolved by R34 and are not findings.

| # | Mention | Finding? | Severity | Why |
|---|---------|----------|----------|-----|
| 1 | `` `.github/mutation-modules.yml` `` (bare backticked) | No | None | R34 only resolves bare backticked `references/<file>.md`. `.github/...` is explicitly outside what R34 checks, so the repo-root file existing or not does not matter here. |
| 2 | `` `agents/mutation-tester.md` `` (bare backticked) | No | None | Same rule: `agents/...` is explicitly outside R34's bare-backtick check. The file existing in the plugin's `agents/` folder is not evaluated by R34. |
| 3 | `[...](../../../../docs/ci.md)` (markdown link) | Yes | Critical | From `plugins/example-kit/skills/demo-skill/`, four `..` segments resolve to the repo root, so the link targets repo-root `docs/ci.md`. It exists, so it is not a dead link, but it leaves the skill folder and lands in `docs/`, which is never allowed. The correct plugin-root target would be `../../references/...`. Existence does not make it compliant. |
| 4 | `` `references/missing-guide.md` `` (bare backticked) | Yes | ADVISORY | This matches the bare backticked `references/<file>.md` pattern, and the file is absent from demo-skill's own `references/` folder. It is ADVISORY, not Critical, and is usually a pointer meant for another skill. The fix is to create the file, move the pointer, or qualify it as `<skill>/references/<file>.md`. |

Summary: one Critical (item 3), one ADVISORY (item 4), and no findings for items 1 and 2.
