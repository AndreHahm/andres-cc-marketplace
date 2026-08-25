# Component Detectors

`scripts/plugin-inventory.py discover <plugin_dir>` inventories logical components, not arbitrary
files. Supporting references, scripts, examples, assets, and templates are summarized in their
owning component's `details`, never becoming independent component records.

## Convention-Detected Types

These four types are detected directly from the filesystem, no manifest declaration needed:

| Type | Detection rule | Example |
|---|---|---|
| `skill` | `skills/<name>/SKILL.md` exists | `skills/plugin-grader/SKILL.md` -> `plugin-grader` |
| `agent` | Any `.md` file directly under `agents/` | `agents/skill-reviewer.md` -> `skill-reviewer` |
| `command` | Any `.md` file directly under `commands/` | `commands/create-plugin.md` -> `create-plugin` |
| `hook` | Each matcher entry inside `hooks/hooks.json`, per event | `hooks.json`'s `PreToolUse[1]` -> `PreToolUse-1` |

A hook's logical name is synthesized as `<event>-<index>` (its position in that event's own matcher
array) since a hook registration has no standalone name field of its own. Multiple hook registrations
in one `hooks.json` become separate logical records — one per matcher entry, not one per file.

## Manifest-Declared Types

Two further types are detected only when the plugin's own `.claude-plugin/plugin.json` declares them —
there is no filesystem-convention detector for these, so their absence from the manifest means a real,
correct "not discovered," never a stub or omission:

| Type | Manifest key | Detection rule |
|---|---|---|
| `mcp-server` | `mcpServers` | Each key in the `mcpServers` object |
| `lsp-server` | `lspServers` | Each key in the `lspServers` object |

## Not Yet Detected

`rule` (`.claude/rules/*.md`), `output-style`, `theme`, `monitor`, and `custom` have no detector in
`scripts/plugin-inventory.py` today. A plugin using any of these needs a manually-approved `add`
operation (or a future detector) — `check`/`plan` will not surface them as candidates, and their
absence from a Check report is not evidence they don't exist, only that this script can't see them yet.

## Supporting Files Stay in `details`

A skill's `references/`, `scripts/`, `assets/`, `examples/`, and `templates/` subdirectories are never
themselves inventoried as separate component records — detecting one `SKILL.md` per skill directory,
not walking every file inside it, is what keeps this distinction correct. Today, `apply_add()` writes
only `details: {"schema": "<type>"}` for a newly-discovered component; it does **not** yet populate a
per-subdirectory summary (`details.entrypoint`, `details.activation`, etc.) the way the concept's
Type-Specific Details section eventually envisions — that richer summarization is unbuilt, not
silently working. A reader relying on `details` for anything beyond the type discriminator should
verify against the actual written record rather than assume it's populated.

## Determinism

Every detector lists candidates in sorted order (by directory listing, then by name) so that two runs
against an unchanged filesystem produce byte-identical `discover`/`plan` output — this is what lets
`check` mode compare a fresh discovery pass against a stored plan's `expected_hash` meaningfully.
