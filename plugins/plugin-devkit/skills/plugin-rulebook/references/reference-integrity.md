# Reference Integrity (R34)

Full detail for R34. `SKILL.md` carries the rule's statement and a pointer here. Forward-looking, like
R28-R30: checked on newly-created or structurally-modified skills, not as a sweep of every existing one.

## What is checked

In a skill's `SKILL.md` and its own `references/*.md` (fenced code blocks excluded):

1. **Markdown links** — `[text](<relative-path>)`.
2. **`${CLAUDE_SKILL_DIR}/...` paths** — written in backticks or in a link.
3. **Bare backticked `references/<file>.md` paths** — a `references/` path with no `${CLAUDE_SKILL_DIR}`
   prefix and no owning-skill qualifier.

## What is skipped

- URLs and `mailto:` targets.
- Same-document anchors (`#some-heading`). A `file.md#heading` link is checked as `file.md` only — the
  fragment is dropped (issue #390).
- Placeholders: any path containing `<`, `>` or `*` (`references/<topic>.md`, `references/*.md`), a `{` or `}` other than the recognized `${CLAUDE_SKILL_DIR}` variable (expand that one first, then check the result exists), or a path whose segment is `...` (`${CLAUDE_SKILL_DIR}/...`). Rule-describing prose that quotes a path as an example (e.g. R34's and R37's own text) is an illustrative example.
- Illustrative examples: a filename shown to explain a rule (`references/patterns.de.md`,
  `references/advanced/patterns.md`, `path/to/file.md`). Judgment call — an example is exempt only when
  the surrounding text presents it as one.
- Bare backticked `scripts/...` and `assets/...` paths. This repo's convention makes those mean the
  plugin's own folder or a repo-root path, so they are not resolved against the skill folder.

## Resolution

- A link resolves against the directory of the file that contains it.
- `${CLAUDE_SKILL_DIR}` is the skill's own folder.
- A repo-root path such as `scripts/marketplace_ci/prefix_check.py` is tried against the repo root when it
  does not exist under the skill folder (issue #427). That only stops it being reported as dead, and it does
  not make the path portable: a link or `${CLAUDE_SKILL_DIR}` path that resolves only at the repo root still
  lands outside the allowed folders and is flagged under "Paths that leave the skill folder" below. A bare
  backticked `scripts/...` mention is skipped, as before.

## Severity

| Finding | Severity |
|---|---|
| A link or `${CLAUDE_SKILL_DIR}/...` path that resolves to nothing | Critical (blocking) |
| A path that leaves the skill folder and lands outside the allowed folders below | Critical (blocking) |
| A path containing `..` that normalizes back inside the skill folder (`references/../SKILL.md`) | Critical (blocking) — obfuscated path, issue #223 |
| A bare backticked `references/<file>.md` that does not exist in this skill's own `references/` | ADVISORY — usually a pointer meant for another skill; qualify it as `<skill>/references/<file>.md` |

## Paths that leave the skill folder

A path that resolves outside the skill folder may land only in a plugin-root folder that the `.claude/`
mirror also carries:

- `references/` and `assets/` — mirrored for every plugin.
- `scripts/` — mirrored only for the plugins listed in `.claude/marketplace-sync.json`'s `scripts_mirrors`
  field (read the live list there; it is not copied into this file, so it cannot drift).

Anything else is flagged: `docs/`, `bin/`, a repo-root file, or a sibling skill's own folder
(`../other-skill/references/x.md`). Content shared between skills belongs in the plugin-root `references/`,
`assets/` or `scripts/` folder, never in one skill's folder that a second skill reaches into. There are two
separate reasons. For `docs/`, `bin/` and repo-root files it is the `.claude/` mirror: a plugin-root
`FOUNDATION_CONTRACTS.md` or `docs/` file is not part of it, so the same relative path resolves in
`plugins/<plugin>/` but not in `.claude/` (issues #259, #316, #350, #446, #450). For a sibling skill's folder
it is coupling, not resolvability: sibling skills are mirrored too, so a same-plugin path usually resolves in
both layouts, but one skill then depends on another's internal layout.

A *named* reference to another plugin, skill or marketplace is R23's domain, not this rule's. A relative path that crosses into another plugin's folder still leaves the skill folder, so it is flagged here under the rule above.

`..` itself is not a violation: `../../references/x.md` from a skill folder is the normal way to reach the
plugin-root `references/` folder. Only the outcomes in the severity table above are findings.

## Fix

Correct the path, or move the shared file into the plugin-root `references/`, `assets/` or `scripts/` folder
and point at it from there. For a bare `references/` pointer meant for another skill, qualify it.
