# Migration Notes

Where each entry from `plugin-rulebook`'s retired "Tracked Upstream Sources" table
(`references/upstream-audit-procedure.md`) and `assets/settings.json → _meta.review_triggers`
moved to in this registry.

Those two locations had already drifted from each other before this migration (6 rows in the
reference-doc table vs. 4 in `_meta.review_triggers`) — this table reconciles both against the
single list now in `assets/sources.json`.

## Migrated

| Old entry | Old rule(s) affected | New registry `id` |
|---|---|---|
| Platform frontmatter field list | R5 | `skill-agent-frontmatter-spec` |
| Platform tool-scoping syntax | R6 | `tool-scoping-syntax-spec` |
| Platform description/when_to_use combined listing cap | R21 | `skill-description-listing-spec` |
| Platform $ARGUMENTS/$N/$name substitution semantics | R22 | `argument-substitution-spec` |

These four were genuine official-source citations and are now tracked with real classification
(authority/volatility), a derived re-check priority, and freshness state — none of which the old
table had.

## Not Migrated (Intentionally)

| Old entry | Old rule(s) affected | Why not migrated |
|---|---|---|
| `skill-development/references/size-limits.md` | R13, R18 | This is a plugin-dev **internal** file, not an official Claude Code source — it was miscategorized in the old table. A change to this file is exactly what `R20`'s Duplicate Fact Sweep already exists to catch; it does not belong in a registry of *external* sources. |
| `skill-reviewer` severity-tier logic | R13, R18 | Same — an internal component, not an official source. Same reasoning as above. |

If `R13`/`R18` need their own tracked upstream source in the future (e.g. an actual official
Claude Code doc stating a recommended line-count convention), add it as a new entry with a real
`url` — do not resurrect these two internal-file rows as if they were external sources.

## New (Not in the Old Table)

| New registry `id` | Why added |
|---|---|
| `claude-code-changelog` | Broadened scope decided during this registry's own design: track the changelog itself as a `frequent`-volatility signal for *when* to re-check the four `spec`-tier sources above |
| `anthropics-claude-code-repo` | Same broadening — an `informal`-authority source for corroborating evidence from GitHub issues/discussions/example plugins, explicitly requested during design |

## What Changed Procedurally

The old table was read by a human-driven "Rulebook Audit" procedure (six numbered steps in
`.claude/rules/plugin-rulebook-enforcement.md`, run at most monthly, triggered by noticing an
upstream change). That procedure is retired. Its replacement:

- **Source tracking/classification/freshness** — this skill (`upstream-sources-registry`).
- **Gap comparison against a local rule, and resolution** — `find-dev-rule`/`verify-dev-rules`/
  `update-dev-rule`, which now consult this registry instead of doing blind `WebSearch`.
- **Intentional divergence (the old "Keep plugin-rulebook" choice)** — recorded via
  `verify-dev-rules`'s widened Exclusion mechanism, not a separate decision log.
- **Historical decisions made under the old mechanism** — retained as-is in
  `.claude/plugin-rulebook-audit-decisions.md`; still-relevant ones should be re-recorded as an
  Excluded Candidate the next time `verify-dev-rules` runs against `plugin-rulebook`, so they
  aren't silently re-flagged as fresh gaps now that the old procedure no longer runs.
