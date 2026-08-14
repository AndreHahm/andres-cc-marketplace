# Report Discovery Convention

Canonical definitions for two facts every report-producing skill and `starting-an-analysis` restate inline: the `<scope-slug>` convention and the report-discovery glob. This file is the source of truth for both — if either changes, sweep every site listed below (R20-style) rather than editing one copy and leaving the rest stale.

## `<scope-slug>`

A short kebab-case description of the scope a report covers, used as the filename prefix: `.claude/output/<skill-name>/<scope-slug>-<timestamp>.md`.

- **Date-range skills** (`analyzing-plugin-components`, `analyzing-tool-and-framework-use`, `analyzing-actor-behavior`, `analyzing-governance-and-conflicts`, `mining-recurring-patterns`): derive from the scope argument — `this-conversation`, `today`, or `<start-date>-to-today` (e.g. `2026-07-10-to-today`).
- **`comparing-sessions`**: derive from the two things being compared, e.g. `<current-scope>-vs-<prior-report-slug>`. `<current-scope>` must never itself contain the literal substring `-vs-` — `starting-an-analysis` Phase 4 parses this compound apart by splitting on the first `-vs-`, so a `<current-scope>` value that already contains it (e.g. inherited from an earlier compound-slugged report) would split wrong; fall back to `this-conversation` in that case.
- **`comparing-session-to-specification`**: derive from the spec document's own filename, e.g. `<spec-basename>-compliance`.
- **`reviewing-analysis-findings`**: derive from the reports being cross-checked, e.g. `<skill-a>-and-<skill-b>-<date>`.
- **`generating-analysis-recommendations`**: derive from the source report's own scope-slug, or `pasted-findings-<date>` if findings were pasted directly rather than read from a report.

**Two different things share this one name — read this before wiring a new discovery glob.** `<scope-slug>` is used two ways in this plugin: as a *filename prefix* (always — every skill's own Persist step, per the derivations above), and as a *cross-skill discovery filter* (a `<value>-*.md` glob checking "do 2+ reports share this scope," used only at the specific sites listed below — not universally). Whether a site can filter by scope, and by what value, depends entirely on whether that skill's own persisted-filename slug is a value a sibling report could plausibly share:

| Site | Filter used | Why |
|---|---|---|
| 5 date-range skills' own Next-step blocks | `<own-scope-slug>-*.md` | Their own scope-slug *is* the shared session identifier |
| `starting-an-analysis` Phase 5, when a date-range skill or `comparing-sessions` was dispatched | `<captured-value>-*.md` | Mirrors whichever filtered check the dispatched skill's own Next-step block just performed |
| `comparing-sessions`' own Next-step block | `<current-scope>-*.md` (only the shared-identifier half of its own compound slug) | Its full persisted slug (`<current-scope>-vs-<prior-report-slug>`) is unique to one comparison and would never match a sibling report |
| `comparing-session-to-specification`'s own Next-step block | none — any other report besides the one just written | No shared-scope input exists (only a spec path); its own slug (`<spec-basename>-compliance`) is a per-report identifier with no shared counterpart |
| `starting-an-analysis` Phase 5, when `comparing-session-to-specification` was dispatched | none — same "any other report" check | Same reason as above |
| `comparing-sessions` Phase 1 "latest" resolution, `mining-recurring-patterns` Phase 3 memory-recall, `generating-analysis-recommendations` Phase 1, `reviewing-analysis-findings` Arguments block and Phase 1 | none — bare, unfiltered glob | These sites list/discover candidate reports generally, not a "does this specific scope already have 2+ reports" check |

`comparing-sessions` and `mining-recurring-patterns` each appear twice above — once with a filter, once without — since each uses both forms in different places within its own file.

## Report-Discovery Glob

analysis-kit's own 9 report directories, named explicitly rather than matched by a prefix wildcard:

```
.claude/output/{analyzing-plugin-components,analyzing-tool-and-framework-use,analyzing-actor-behavior,analyzing-governance-and-conflicts,mining-recurring-patterns,comparing-sessions,comparing-session-to-specification,generating-analysis-recommendations,reviewing-analysis-findings}/*.md
```

**Why explicit, not a prefix wildcard:** a pattern like `.claude/output/{analyzing,comparing,mining,generating,reviewing}-*/*.md` also matches `plugin-devkit`'s unrelated `analyzing-sessions` output directory — confirmed on disk to hold real, unrelated reports. The explicit enumeration above cannot match a foreign plugin's directory no matter what gets added elsewhere in `.claude/output/`.

## Sites That Restate These Facts

Every site below must match this file. If you change either definition here, update all of them in the same pass. Paths are relative to `plugins/analysis-kit/`. **Note on the anti-pattern example above:** the prefix-wildcard pattern shown in "Why explicit, not a prefix wildcard" is a deliberate counter-example kept for documentation — do not count it as a stale site to fix.

- `skills/starting-an-analysis/SKILL.md` — Phase 4 (captures whatever Phase 5 needs from the dispatched skill's printed report path, per the per-site table above) and Phase 5 step 1 (glob, branched by which skill was dispatched). This skill has no `<scope-slug>` derivation step of its own — Phase 4 derives the capture from whatever the dispatched skill actually produced.
- `skills/analyzing-plugin-components/SKILL.md`, `skills/analyzing-tool-and-framework-use/SKILL.md`, `skills/analyzing-actor-behavior/SKILL.md`, `skills/analyzing-governance-and-conflicts/SKILL.md` — each skill's own Persist step (scope-slug) and Next-step block (glob)
- `skills/mining-recurring-patterns/SKILL.md` — Phase 3 memory-recall (glob), Persist step (scope-slug), Next-step block (glob) — three sites
- `skills/comparing-sessions/SKILL.md` — Phase 1 "latest" resolution (glob) and `<current-scope>` derivation (scope-slug), Persist step (scope-slug), Next-step block (glob) — three sites
- `skills/comparing-session-to-specification/SKILL.md` — Persist step (scope-slug), Next-step block (glob)
- `skills/generating-analysis-recommendations/SKILL.md` — Phase 1 (glob), Persist step (scope-slug) — two sites
- `skills/reviewing-analysis-findings/SKILL.md` — Arguments block (glob), Phase 1 (glob), Persist step (scope-slug) — three sites
- `skills/running-a-full-retrospective/SKILL.md` — Phase 1 reuse check (glob, filtered per chosen analysis
  type's own scope-slug), Phase 3 Persist step (scope-slug, reusing whichever date-range scope this run's
  own dispatches used) — two sites. Its own persisted report is deliberately *not* added to the 9-directory
  report-discovery glob enumeration above — see this skill's own Gotchas section for why a meta-report
  consolidating other reports shouldn't count as a 10th independent one
