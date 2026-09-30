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

Each file's **basename** (not its full path) must start with `<prefix>-` or `<domain>-` (2026-09-27
addendum — see "domain_prefix: a human-readable alternative to prefix" below), where `<prefix>` is that
plugin's own registered `prefix` value and `<domain>` is its registered `domain_prefix` value, both from
`marketplace-inventory.json`. A `.py` file may **additionally** use snake_case for its **entire basename**
instead (`<prefix>_`/`<domain>_`, underscores throughout, no leftover hyphen anywhere else in the name) —
see "Python files may use snake_case" below. This is an optional alternative for `.py` files only, never
a replacement for the kebab-case form every extension (including `.py`) already accepts.

## domain_prefix: a human-readable alternative to prefix

`domain_prefix` is a second, optional, curator-approved plugin identifier (`^[a-z][a-z0-9]{2,11}$` — 3-12
lowercase alphanumeric characters, starting with a letter), assigned the same way `prefix` is (propose →
check marketplace-wide uniqueness → human `AskUserQuestion` approval), permanent once assigned, and
cross-checked for marketplace-vs-plugin-inventory equality the same way `prefix` already is. It exists to
avoid an unnecessary rename when a file's existing name already reads naturally with the plugin's full
domain word — e.g. context-kit's `context-audit.md` already reads fine and doesn't need a `ctx-` rename
just to satisfy this rule. (Named `domain_prefix`, not `domain` or `id`: `marketplace-inventory.json`'s
plugin record already has an unrelated opaque `id` field and an unrelated plural `domains` topic-tag
list, and `plugin-inventory.json`'s own per-component records already have their own unrelated singular
`domain` field describing that component's functional/topic area — `domain_prefix` avoids echoing any of
the three.)

**Free mix, not a preference order.** A file satisfies R33 if its basename starts with *either*
`<prefix>-` or `<domain>-` (the plugin's registered `prefix`/`domain_prefix` values respectively) — there
is no rule preferring one over the other for a new file. The curator picks whichever reads better per
file; a plugin legitimately mixes both forms across its own tree (e.g. `ctx-a.md` alongside
`context-b.md` in the same directory).

**Independent, optional field.** `domain_prefix` is optional independently of `prefix` — a plugin may
register it or not. The `prefix` key itself is required in both inventory schemas; an explicit `null`
(with no `domain_prefix`) opts a plugin out, and R33 is inert for it. Once either is set, every in-scope
file must match at least one of whichever field(s) are registered.

## Python files may use snake_case

Every `.py` file anywhere in R33's in-scope directories (`scripts/`, `references/`, `assets/`, `hooks/`
incl. `hooks/scripts/`, `commands/`) may **optionally** use **snake_case for its entire basename** instead
of kebab-case — both the prefix/domain separator (`_` instead of `-`) and every hyphen elsewhere in the
name — but the ordinary kebab-case form stays valid too, exactly like every other extension.
`git-check-pr-title.py` already satisfies R33 as-is (kebab-case, starts with `git-`); a curator may
instead rename it to `git_check_pr_title.py` (full snake_case) if that reads better, but neither form is
required over the other. A `.py` basename that starts with the `<prefix>_`/`<domain>_` snake_case form
but still contains a hyphen later in the name (e.g. `git_check-pr-title.py`) is a violation either way —
mixing separators within one basename is never valid; pick kebab-case throughout or snake_case
throughout. Every non-`.py` file is unaffected and only ever accepts kebab-case, as before.

**Why optional, not mandatory (relaxed 2026-09-27, same day as the original addendum):** CI's
`prefix-permanence` job restores `scripts/marketplace_ci/prefix_check.py` from the PR's **trusted base
SHA**, not the PR's own copy — a deliberate security hardening from R33's original rollout that stops a
PR from rewriting its own checker to pass. A mandatory-only Python rule introduced in the very PR that
also needs to rename an already-registered plugin's existing `.py` files can never pass that trust
boundary: the base-restored checker doesn't know the new rule exists yet, so it evaluates renamed files
against the old kebab-case-only rule and fails them; reverting the rename instead fails the *PR's own*
checker once merged, since `find_prefix_violations` scans every registered plugin's **whole** tree
unconditionally, not just the current PR's diff — breaking every future PR touching this repo, not just
this one. Making snake_case optional (not exclusive) removes the forced-simultaneous-migration
requirement entirely: a plugin's existing kebab-case `.py` files stay valid indefinitely, and a curator
opts into snake_case per-file, on their own schedule, with no trust-boundary conflict either way.

## Temporary, single-plugin exception

For `antigravity-kit` **only**, this same recursive rule also covers its root-level `bin/` and `docs/`
directories — a retained exception carried over from the concept draft's v1, not a general directory
type. No other plugin has `bin/`/`docs/` at plugin-root level today. Retire this exception only when
`antigravity-kit`'s own planned refactor removes or relocates those directories, with an explicit update
to this rule and to `prefix_check.py`'s `ANTIGRAVITY_ONLY_DIRS`.

## Explicit exclusions

- `hooks/hooks.json` itself — structurally merged by `scripts/marketplace_ci/sync.py`'s
  `plan_hooks_merge`, never a plugin-authored filename choice.
- A Python package's `__init__.py` (exact basename) under a plugin's root-level `scripts/` directory —
  a language-mandated filename; renaming it breaks the package. The package's other modules stay in
  scope and must carry the prefix, and an `__init__.py` under any other scoped directory (`commands/`,
  `hooks/`, `references/`, `assets/`) is still checked.
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

## Gating: inert for an explicit `null` opt-out

This rule produces **zero findings** for any plugin whose `marketplace-inventory.json` record has
`prefix: null` and no `domain_prefix` — not a warning, not an ADVISORY, nothing. That is a deliberate,
recorded opt-out (today only `example-plugin`, a test fixture), not a transition state: the `prefix` key
is required in both inventory schemas, so no plugin can be silently unregistered. This is the same
"vacuous when neither is set" gate `prefix_check.py` uses mechanically, so a plugin that registers a
curated prefix and/or domain_prefix is atomically and unambiguously in scope. Once registered, every
in-scope file must match at least one of whichever field(s) are registered.

Additionally, a plugin whose `status` is `superseded` or `retired` is skipped **only if it has also been
removed from `.claude-plugin/marketplace.json`** — its source files may be stale or entirely gone at that
point, and checking them would produce false positives on content nobody maintains anymore. A
`superseded`/`retired` plugin that is still listed in `marketplace.json` (still installed) is checked
regardless of its curated status: `status` is a separately human-editable field, and a PR could otherwise
set it to a skip-eligible value while the plugin remains live, exempting it from the check entirely. See
`prefix_check.py`'s own `CHECKED_STATUSES`/`authoritative_sources` logic — a plugin is in scope if
*either* its status is `active`/`deprecated` *or* its name still appears in the manifest.

## Fix

Rename the flagged file to `<prefix>-<original-name>` or `<domain>-<original-name>` (or a shorter, more
natural `<prefix>-<rest>`/`<domain>-<rest>` — see the worked git-kit example below for why a mechanical
prepend isn't always the best rename), or, for a `.py` file, to snake_case
(`<prefix>_<rest>`/`<domain>_<rest>`, underscores throughout) — and update every reference to it:
SKILL.md bodies, `hooks/hooks.json` command strings, other scripts' invocation paths (including Python
`import` statements, not just shell invocation), documentation links, and the `.claude/` mirror.

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
