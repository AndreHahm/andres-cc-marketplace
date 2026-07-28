# Repo-Specific Configuration

Two files hold data that's specific to the repository this plugin is installed in, rather than portable plugin defaults — neither lives inside the plugin package, and neither is part of the `.claude/skills/plugin-rulebook/` in-development staging mirror (that mirror is a different thing: a staged copy of the plugin package itself, per R19's exception; these are a separate, repo-level override layer on top of it):

| File | Purpose | Format |
|---|---|---|
| `{REPO_ROOT}/.claude/plugin-rulebook.config.json` | R23's `whitelist`/`blacklist`/`excluded_paths` for this repo | JSON, same shape as `assets/settings.json`'s `rules.R23_external_reference_policy.config` |
| `{REPO_ROOT}/.claude/plugin-rulebook-audit-decisions.md` | This repo's own Upstream Audit decision log | Markdown, same format as before the split |

**Load procedure:** always read `assets/settings.json` first for the full rule set (R1–R27, defaults). Then check for `{REPO_ROOT}/.claude/plugin-rulebook.config.json` — if present, its `rules.R23_external_reference_policy.config.{whitelist,blacklist,excluded_paths}` values replace the (empty) plugin defaults for those three keys only; every other rule and config value comes from the plugin's own `assets/settings.json` unchanged. If the repo-config file is absent (e.g. a fresh install of this plugin into a different repository), R23 runs with empty lists rather than silently inheriting another repo's policy.

**Why this file, not `.claude/plugin-rulebook.local.md`:** the `plugin-settings` skill's `.claude/<plugin-name>.local.md` pattern is for personal, gitignored, per-developer state. R23's whitelist/blacklist and the audit log are the opposite — team-shared, project-wide decisions that should be committed and visible to everyone working in the repo, the same way `.claude/settings.json` (not `.claude/settings.local.json`) holds shared team hooks. Both new files are ordinary committed files, not `.local.*`.

Committing new whitelist/blacklist decisions or a new audit-log entry means editing `{REPO_ROOT}/.claude/plugin-rulebook.config.json` / `{REPO_ROOT}/.claude/plugin-rulebook-audit-decisions.md` directly — never the plugin's own `assets/settings.json`, which should stay at the clean, portable defaults so the plugin remains installable elsewhere without carrying this repo's policy along.
