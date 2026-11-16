# Trust and configuration

Two JSON files, decided by the repository owner on 2026-11-16:

| File | Tracked | Role |
|---|---|---|
| `reviewadapters-kit.settings.json` (plugin root) | Yes, ships with the plugin | Defaults: every vendor off, `timeout_ms` 600000, a default `model` per vendor |
| `.claude/reviewadapters-kit.local.json` (under `--cwd`, the repository's top level) | Must not be | The only place a vendor can be enabled; may lower the timeout, pin a model, and opt in to the sibling codex-kit |

```json
{ "vendors": { "pi": { "enabled": true, "model": "nvidia/nvidia/nemotron-3-ultra-550b-a55b" },
               "devin": { "enabled": true } } }
```

## Why only the local file can enable a vendor

Enabling a vendor sends repository content to that vendor. A tracked file can be changed by anyone with
write access to the repository, including through the very change under review, so a tracked
`"enabled": true` could widen egress without the owner noticing. The dispatcher runs
`git ls-files -z -- ':(icase).claude/reviewadapters-kit.local.json'` and treats any output as tracked,
refusing with `vendor_not_allowed`: the same trust-boundary pattern git-kit uses for
`commit_confirm_before_commit`. The `:(icase)` match means a committed
`.claude/ReviewAdapters-Kit.local.json`, which a macOS or Windows filesystem would open under the
lowercase name, still counts as tracked; any git error counts as tracked too. The file is read only under
its exact lowercase name, in a `.claude` directory that is not a symbolic link, and only when the file and
that directory are owned by the current user and writable by nobody else (group write is allowed only
for the user's private group, the rule the dispatcher's input files follow). A shipped default can only
switch a vendor off.

A lower `timeout_ms` and a `model` are read from both files; the local file wins. A `timeout_ms` above the
shipped value is ignored. A `model` is not egress-neutral for pi: its first segment picks the provider
that receives the data, so pinning a pi model is an egress choice, and the egress confirmation names the
provider. A caller's `--model` for pi must therefore be exactly the configured model or one listed in
the local file's `vendors.pi.models` array; anything else, including a bare id or another id under the
same provider prefix, is refused (`vendor_not_allowed`), because how pi maps an id to a provider is not
pinned down. `models` is read from the local file only.

`"allow_unprobed_version": true` under a vendor (local file only) lets devin or agy run when the installed
CLI is not the probed version; without it the dispatcher refuses that run before sending
(`unsupported_cli_version`), because their isolation was verified only for the probed version. pi always
runs with `--no-tools` and only gets an `inspection_limits` note.

`"dev_sibling_codex_kit": true` (local file only) lets the dispatcher import the codex-kit next to this
plugin in a marketplace checkout when none is installed; see `references/codex-kit-locator.md`. It has
the same tracked-copy refusal, since it decides which code validates the review.

## Interactive and unattended callers

- **Interactive** (cross-model-review, `rva-review-diff`): the caller asks the user which vendors to use
  and confirms egress per vendor before calling. The allow-list is a second, mechanical gate on top.
- **Unattended** (CI, scripts): the caller names the vendors in its own arguments; the allow-list is the
  only consent. A CI job enables a vendor by writing the untracked local file at job time, never by
  committing it.

## Secret-named paths

If a target path or a path named in the diff's headers matches codex-kit's `matchesSecretFilename`, the
dispatcher refuses unless the caller passes `--secret-paths-confirmed`; a diff header naming a path
missing from the target list is refused outright, so a deleted file or the old side of a rename cannot
slip past this check. The owner decided (2026-11-16) that an optional reviewer may run on
such a diff only after an extra confirmation naming the hit; the flag is how an interactive caller
records that it asked. This plugin does not see `DISPATCHER_TOUCHED`, which is cross-model-review's own
signal; that caller applies the same extra confirmation before passing the flag.
