# Rulebook Audit Decisions

Log of gaps surfaced by `plugin-rulebook`'s Upstream Audit procedure and how each was resolved, for this repository specifically. Checked here before re-asking the user about a previously-decided gap.

This file is repo-specific config for the `plugin-dev` plugin's `plugin-rulebook` skill — not part of the plugin package itself. See `.claude/plugin-rulebook.config.json` for the sibling repo-specific rule overrides (R23 whitelist/blacklist/excluded_paths), and `plugins/plugin-dev/skills/plugin-rulebook/SKILL.md`'s Upstream Audit Procedure section for how this file is used.

## 2026-07-05 — hook event/type list vs an external reference plugin and official docs

Gap: Discovered while inspecting an independently-versioned, third-party plugin's hook system
during a comparative audit. Three sources disagreed on the canonical hook event names and
handler types:

- `validate-hook-schema.sh`'s `VALID_EVENTS`: 9 events, only 2 accepted handler types (`command`, `prompt`)
- `hook-development/references/event-reference.md`: ~22 events named across its dedicated
  sections and "Newer Events" catch-all line; 5 handler types already correctly documented
- The external plugin's `HOOK_EVENTS`/`HOOK_TYPES`: 26 events, 4 handler types (missing `mcp_tool`)

Fetched `code.claude.com/docs/en/hooks` directly (twice, since the first exhaustive-listing
pass silently dropped `SessionEnd`) to get ground truth rather than picking between two stale
caches: **30 events, 5 handler types** (`command`, `http`, `mcp_tool`, `prompt`, `agent`).

Decision: **Keep official docs** (supersedes both `plugin-rulebook`'s cached knowledge and
the external plugin's list, since that list itself was incomplete — missing `Setup`,
`UserPromptExpansion`, `PostToolBatch`, `MessageDisplay`, and the `mcp_tool` type).

Applied:
- `hook-development/scripts/validate-hook-schema.sh`: `VALID_EVENTS` expanded 9→30; hook-type
  check now accepts all 5 types with proportionate required-field checks for `http`
  (`url`) and `mcp_tool` (`server`, `tool`).
- `hook-development/references/event-reference.md`: "Newer Events" catch-all line expanded to
  name all 17 events not covered by a dedicated section (was 10, missing `PermissionDenied`,
  `StopFailure`, `InstructionsLoaded`, `ConfigChange`, `FileChanged`, `PostCompact`,
  `Elicitation`, `ElicitationResult`).
- Left `hook-development/SKILL.md`'s own abbreviated event table and "not the full event
  list...see references/event-reference.md" line as-is — it already discloses it's partial
  and defers to the reference file, so it wasn't a stale claim.
- Did not touch the external plugin's installed files — it's an independently-versioned, third-party plugin outside this project.

Rationale: user approved "fix everything to match official docs" (the recommended option)
after a timed-out confirmation prompt; proceeded on best judgment per session norms.

**Unrelated bug found and fixed along the way:** `validate-hook-schema.sh` had a classic
`set -e` + `((counter++))` bug — incrementing `error_count`/`warning_count` from 0 evaluates
to the pre-increment value 0, which `((...))` reports as a failing exit status, aborting the
whole script under `set -e` before the summary block. This silently ate the pass/fail summary
and gave a wrong exit code (1 instead of 0) on any warning-only file. Fixed by switching all
14 occurrences to `count=$((count + 1))`.

## 2026-07-06 — repo-specific plugin-rulebook data split out of the plugin package

Gap: `assets/settings.json`'s R23 `whitelist`/`blacklist`/`excluded_paths` and this file
(`audit-decisions.md`) were living inside `plugins/plugin-dev/skills/plugin-rulebook/assets/` —
shipped as part of the plugin package. That meant installing `plugin-dev` into a different
repository would silently inherit this repo's own external-reference policy (`rcc`/`daymade`
blacklist, the `acme-tools`/`tessl`/etc. whitelist) and this repo's own audit history, neither
of which apply anywhere else.

Decision: split repo-specific data out to `.claude/plugin-rulebook.config.json` (R23 overrides)
and `.claude/plugin-rulebook-audit-decisions.md` (this file, moved here). The plugin's own
`assets/settings.json` keeps R1-R22 and R23's rule shape (portable), with R23's list fields
reset to `[]` as the clean default for a fresh install.

Rationale: user-directed (see conversation) — recommended during a review of the plugin's own
structure, confirmed by the user with two path adjustments (flat `.claude/`-relative paths
instead of a `.claude/config/<plugin>/` subdirectory, to stay visually distinct from the
`.claude/skills/plugin-rulebook/` in-development plugin mirror).

**Note on the audit-decisions.md path specifically:** the user's originally-specified path
(`.claude/output/plugin-rulebook-audit-decisions.md`) was changed to the current flat path
without a confirmed response — `.claude/output/` is gitignored in this repo, which would have
made this log local-only and uncommitted, defeating the purpose of a shared, persistent repo
audit trail (and violating this same plugin's own "no component may reference a gitignored
path as a live dependency" rule). Flagging this deviation explicitly in case the gitignored
location was actually intended for a different reason.
