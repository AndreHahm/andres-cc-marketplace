# R33 — Component-File Naming: Plugin Prefix Required (Full Detail)

Extracted from `SKILL.md`'s R33 entry to keep the skill under its own R13 line-budget threshold (the
same reason R28-R32's detail already lives in dedicated reference files). See `SKILL.md`'s R33 entry
for the one-line summary and severity.

This rule and `scripts/marketplace_ci/prefix_check.py` are two independent enforcement layers — a policy
check here, a mechanical CI check there — that must always agree on scope; if either changes, update
both together (R20).

## In scope (recursive)

Every file discovered anywhere beneath a registered plugin's own:

- `scripts/`
- `references/`
- `assets/` (forward-looking — no plugin has a root `assets/` directory yet as of this rule's own
  writing; when one appears, its files follow the same rule)
- `hooks/` (including nested `hooks/scripts/`)
- `commands/`

Each file's **basename** (not its full path) must start with `<prefix>-`, where `<prefix>` is that
plugin's own registered value from `marketplace-inventory.json`.

## Temporary, single-plugin exception

For `antigravity-kit` **only**, this same recursive rule also covers its root-level `bin/` and `docs/`
directories — a retained exception carried over from the concept draft's v1, not a general directory
type. No other plugin has `bin/`/`docs/` at plugin-root level today. Retire this exception only when
`antigravity-kit`'s own planned refactor removes or relocates those directories, with an explicit update
to this rule and to `prefix_check.py`'s `ANTIGRAVITY_ONLY_DIRS`.

## Explicit exclusions

- `hooks/hooks.json` itself — structurally merged by `scripts/marketplace_ci/sync.py`'s
  `plan_hooks_merge`, never a plugin-authored filename choice.
- Every skill-scoped resource under `skills/**/{scripts,references,assets}/` — already namespaced by
  the skill's own directory path when mirrored; no flat-collision risk.
- The plugin-root `agents/` directory — out of scope for this rule's first rollout. A collision risk
  alone is not sufficient reason to enlarge this rule's scope; revisit only via a separately approved
  scope change.
- The plugin-root `rules/` directory — also out of scope for the first rollout, despite being mirrored
  by the same `COMPONENT_DIRS` mechanism as `commands/`/`hooks/` and carrying the identical collision
  exposure. Rule files are referenced by ID in `assets/settings.json` (e.g. this very rule's own
  `R33_component_file_prefix` key) and other config, making a rename costlier than a command/hook
  rename — it would require updating every config reference, not just invocation paths. The residual
  collision risk is accepted; revisit only via a separately approved scope change naming the
  settings.json-reference migration cost.
- codex-kit's root `prompts/` and `schemas/` directories — mirrored via `sync.py`'s
  `EXTERNAL_HOOK_SCRIPT_MIRRORS` explicit list, not via `COMPONENT_DIRS`; collision is already
  prevented by that explicit-list mechanism, so these stay outside the prefix convention.
- `.claude/scripts/cleanup-scratchpad.sh`/`.ps1` and any other file with no owning plugin at all —
  repository-internal tooling, not a plugin-root source file; this rule only governs a plugin's own
  canonical `plugins/<plugin>/` tree.

## Gating: inert until registered

This rule produces **zero findings** for any plugin whose `marketplace-inventory.json` record has no
`prefix` field yet — not a warning, not an ADVISORY, nothing. This is the same "vacuous until
registered" gate `prefix_check.py` uses mechanically, so a plugin migrates from "unchecked" to "fully
checked" atomically the moment its own migration PR registers a curated prefix — no plugin is ever
partially or ambiguously in scope.

Additionally, a plugin whose `status` is `superseded` or `retired` is skipped **only if it has also been
removed from `.claude-plugin/marketplace.json`** — its source files may be stale or entirely gone at that
point, and checking them would produce false positives on content nobody maintains anymore. A
`superseded`/`retired` plugin that is still listed in `marketplace.json` (still installed) is checked
regardless of its curated status: `status` is a separately human-editable field, and a PR could otherwise
set it to a skip-eligible value while the plugin remains live, exempting it from the check entirely. See
`prefix_check.py`'s own `CHECKED_STATUSES`/`authoritative_sources` logic — a plugin is in scope if
*either* its status is `active`/`deprecated` *or* its name still appears in the manifest.

## Fix

Rename the flagged file to `<prefix>-<original-name>` (or a shorter, more natural `<prefix>-<rest>` —
see the worked git-kit example below for why a mechanical prepend isn't always the best rename) and
update every reference to it: SKILL.md bodies, `hooks/hooks.json` command strings, other scripts'
invocation paths (including Python `import` statements, not just shell invocation), documentation
links, and the `.claude/` mirror.

**Worked example — avoid a stutter:** a file already containing the plugin name mid-name (e.g.
git-kit's own `write-git-kit-marker.sh`) produces an awkward stutter under a blind prepend
(`git-write-git-kit-marker.sh`). Prefer a cleaner rename that still satisfies the rule (e.g.
`git-write-marker.sh`) over a mechanical, unreadable prepend — the requirement is the `<prefix>-`
basename prefix, not a specific transformation of the rest of the name.

## Relationship to the existing kit/devkit "Suffix/Prefix Taxonomy" Open Item

`references/naming-conventions.md` already has an unrelated, pre-existing "Open Item: Plugin
Suffix/Prefix Taxonomy" section about the `-kit`/`-devkit` **plugin-name** suffix convention (e.g.
`git-kit`, `plugin-devkit`) — a naming question about the plugin itself. R33 is about a different
concept that happens to share the word "prefix": a **file-naming** convention applied to files *inside*
an already-named plugin (`git-kit`'s own `scripts/git-check-pr-title.py`). The two are unrelated and
independently decided; do not conflate them. See `naming-conventions.md`'s own R33 section for the
explicit disambiguation.
