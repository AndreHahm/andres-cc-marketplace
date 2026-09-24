# R27 Check: `misc-kit` — `commands/config-settings.md`

## Facts
- Plugin: `misc-kit`
- `marketplace-inventory.json`: no `prefix` field registered for this plugin (R33 is inert here — no R33 finding is raised until a migration PR registers a prefix).
- File: `commands/config-settings.md`
- Frontmatter: `name: config-settings` — but per R27, command files "have no `name` field — check the filename itself," so the basename `config-settings` (i.e. `config-settings.md` minus extension) is the actual check target, not the frontmatter `name` value.
- Description and body are minimal but valid (no other rule violations under consideration here).

## Applying R27 (Component Naming: Grammatical Form)
R27's expected form for a command: "starts with a verb (`create-plugin`, `review-rules`). For a command in a plugin that has an R33-registered prefix, check the filename portion *after* the prefix — `<prefix>-<rest>`, where `<rest>` must start with a verb ... For a plugin with no prefix registered yet, check the full basename as before."

Since `misc-kit` has no registered R33 prefix, there is no prefix to strip — the full basename `config-settings` is checked as-is (not `config-settings` minus some prefix segment).

The first token of `config-settings` is `config`. `config` is a noun (a configuration/settings object), not a verb — the task statement itself confirms this. A command basename that doesn't start with a recognizable verb is exactly R27's stated violation example: "A command that doesn't start with a recognizable verb (checked after stripping a registered R33 prefix, if one applies — see above)."

## Conclusion
**R27 flags `commands/config-settings.md` as an ADVISORY violation.** The basename `config-settings` does not start with a verb — `config` is a noun, and no verb-first framing (e.g. `configure-settings`, `set-config`, `update-settings`) is present. Per R27's own severity, this is `ADVISORY` only, never `REQUIRED` — it's an interpretive, judgment-based check, and the maintainer may have a considered reason to keep the name as-is. The fix suggested by R27 would be to rename the command to a verb-first form, or flag-and-move-on if the maintainer declines.

Note on scope interaction with R33: because `misc-kit` has no registered prefix, R33 itself raises no finding for this file (R33 is inert with no prefix registered). This has no bearing on R27's own verdict — R27's basename check simply uses the full, unstripped basename when there's no prefix to strip, and that full basename still fails the verb-first test independently of R33's status.
